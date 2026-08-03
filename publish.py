import argparse
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from google import genai
from google.genai import types

from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, ContentPack
from utils import (
    translate_markdown_to_nextjs_body,
    determine_category,
    git_push,
    get_nextjs_dir,
    get_read_time,
    WORDS_PER_MINUTE,
)

load_dotenv()

# Transient Gemini disconnects are the dominant cron failure mode; retry before giving up.
GENERATE_MAX_ATTEMPTS = 3
GENERATE_BACKOFF_SECONDS = 20


def _with_retries(label: str, fn, max_attempts: int = GENERATE_MAX_ATTEMPTS):
    """Call fn(), retrying transient failures with exponential backoff."""
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as e:
            last_error = e
            print(f"Error during {label} (attempt {attempt}/{max_attempts}): {e}")
            if attempt < max_attempts:
                backoff = GENERATE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                print(f"  Waiting {backoff}s before retry...")
                time.sleep(backoff)
    raise last_error

def generate_hero_image(hero_concept: str, slug: str, api_key: str) -> str | None:
    """Generate a hero image using Imagen 3 and save to static/images/. Returns relative path or None."""
    output_dir = "static/images"
    os.makedirs(output_dir, exist_ok=True)
    image_path = os.path.join(output_dir, f"{slug}.png")

    prompt = (
        f"Cinematic, professional cybersecurity editorial illustration. "
        f"{hero_concept} "
        "Dark background with blue and red accents. Photorealistic digital art. "
        "16:9 widescreen format. No text or logos."
    )

    try:
        client = genai.Client(
            api_key=api_key,
            http_options={'timeout': 300000.0}
        )
        response = client.models.generate_images(
            model='imagen-4.0-generate-001',
            prompt=prompt,
            config=types.GenerateImagesConfig(
                numberOfImages=1,
                aspectRatio='16:9',
                outputMimeType='image/png',
            )
        )
        image_bytes = response.generated_images[0].image.image_bytes
        with open(image_path, "wb") as f:
            f.write(image_bytes)
        print(f"Hero image saved to {image_path}")
        return f"/images/{slug}.png"
    except Exception as e:
        print(f"Warning: Image generation failed: {e}")
        return None

def generate_educational_images(educational_images: list, slug: str, api_key: str) -> dict:
    """Generate educational/diagram images for [Visual Graphic N] placeholders.
    Returns a dict mapping placeholder string -> (relative_path, alt_text, caption)."""
    output_dir = "static/images"
    os.makedirs(output_dir, exist_ok=True)
    client = genai.Client(api_key=api_key, http_options={'timeout': 300000.0})
    results = {}
    for img in educational_images:
        placeholder = img.get("placeholder", "")
        concept = img.get("concept", "")
        caption = img.get("caption", "")
        alt_text = img.get("alt_text", "")
        if not placeholder or not concept:
            continue
        # Derive a filename from the placeholder, e.g. "[Visual Graphic 1]" -> slug-visual-1.png
        num = re.sub(r'[^0-9]', '', placeholder) or "x"
        filename = f"{slug}-visual-{num}.png"
        image_path = os.path.join(output_dir, filename)
        prompt = (
            f"Professional cybersecurity educational infographic or diagram. "
            f"{concept} "
            "Dark background with blue and red data-visualization accents. "
            "Clean, readable labels. No watermarks or logos. 16:9 format."
        )
        try:
            response = client.models.generate_images(
                model='imagen-4.0-generate-001',
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    numberOfImages=1,
                    aspectRatio='16:9',
                    outputMimeType='image/png',
                )
            )
            image_bytes = response.generated_images[0].image.image_bytes
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            relative = f"/images/{filename}"
            results[placeholder] = (relative, alt_text, caption)
            print(f"Educational image saved: {image_path}")
        except Exception as e:
            print(f"Warning: Educational image generation failed for {placeholder}: {e}")
    return results

def fetch_grounding_context(topic: str, api_key: str) -> str:
    print(f"Searching the web for context on: {topic}...")
    client = genai.Client(
        api_key=api_key,
        http_options={'timeout': 300000.0}
    )
    prompt = f"""
    Search the web for the latest, authoritative threat intelligence, articles, and advisories regarding this cybersecurity topic: "{topic}".
    Provide a detailed factual summary of the vulnerability, threat actors, exploits, and mitigations based on the search results. Include specific details like affected versions and CVE numbers if available.
    """
    def _attempt():
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.3,
            )
        )
        return response.text

    return _with_retries("grounding search", _attempt)

def generate_content(topic: str, model: str = 'gemini-2.5-pro') -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set in the environment")

    # 1. Fetch grounding context using search tool
    grounding_context = fetch_grounding_context(topic, api_key)
    
    # 2. Build prompt with context
    prompt = f"""
{USER_PROMPT_TEMPLATE.format(topic=topic)}

CONCRETE FACTS AND RESEARCH FOUND FROM WEB SEARCH (use these to write the article and details):
{grounding_context}
"""

    client = genai.Client(
        api_key=api_key,
        http_options={'timeout': 300000.0}
    )
    
    def _attempt(target_model: str) -> dict:
        response = client.models.generate_content(
            model=target_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=ContentPack,
                temperature=0.7,
            ),
        )
        validated_data = ContentPack.model_validate_json(response.text)
        word_count = len(validated_data.article.content.split())
        if word_count < 800:
            print(f"Warning: Generated article is short ({word_count} words). Check content quality.")
        return validated_data.model_dump()

    # Each model gets several attempts with backoff before we fall back to the next one.
    models_to_try = [model] if model == 'gemini-2.5-flash' else [model, 'gemini-2.5-flash']
    last_error = None

    for target_model in models_to_try:
        if target_model != model:
            print(f"Falling back to model: {target_model}...")
        print(f"Generating content for topic: {topic} using {target_model}...")
        try:
            return _with_retries(f"generation with {target_model}", lambda: _attempt(target_model))
        except Exception as e:
            last_error = e

    print(f"All generation attempts failed across models {models_to_try}.")
    raise last_error

def create_markdown(data: dict, slug: str, image_path: str | None = None, edu_image_map: dict | None = None) -> str:
    seo = data.get("seo", {})
    article = data.get("article", {})

    title = seo.get("title", article.get("title", "Untitled"))
    description = seo.get("meta_description", "")
    keywords = seo.get("primary_keywords", []) + seo.get("secondary_keywords", [])

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    image_line = f"\nimage: {json.dumps(image_path)}" if image_path else ""

    frontmatter = f"""---
title: {json.dumps(title)}
description: {json.dumps(description)}
date: {date_str}
slug: {json.dumps(slug)}
tags: {json.dumps(keywords)}
author: "BreachModal Intelligence"{image_line}
---
"""
    content = article.get("content", "")

    # Replace [Visual Graphic N] placeholders with actual image markdown
    if edu_image_map:
        for placeholder, (rel_path, alt_text, caption) in edu_image_map.items():
            img_md = f"\n![{alt_text}]({rel_path})\n*{caption}*\n"
            content = content.replace(placeholder, img_md)

    return frontmatter + "\n" + content

def create_social_file(data: dict) -> str:
    social = data.get("social", {})
    linkedin = social.get("linkedin_post", "")
    x_thread = social.get("x_thread", [])
    
    content = "## LinkedIn Post\n\n" + linkedin + "\n\n"
    content += "## X Thread\n\n"
    for i, tweet in enumerate(x_thread, 1):
        content += f"{i}. {tweet}\n\n"
        
    if "visual_brief" in data:
        vb = data["visual_brief"]
        content += "## Visual Brief\n\n"
        content += f"### Hero Image Concept\n{vb.get('hero_image_concept', '')}\n\n"
        content += f"### Infographic Concept\n{vb.get('infographic_concept', '')}\n\n"
        
        content += "### LinkedIn Carousel\n"
        for slide in vb.get('linkedin_carousel', []):
            content += f"- {slide}\n"
        content += "\n"
        
        content += f"### Short-form Video Script\n{vb.get('video_script', '')}\n\n"
        
    if "press_release" in data:
        content += "## Press Release\n\n"
        content += data["press_release"] + "\n\n"

    poc = data.get("proof_of_concept")
    if poc:
        content += "## Proof of Concept (Structured)\n\n"
        content += f"**Summary**: {poc.get('summary', '')}\n\n"
        cvss = poc.get("cvss_vector", "")
        if cvss:
            content += f"**CVSS v3.1**: `{cvss}`\n\n"
        content += "**Steps**:\n\n"
        for i, step in enumerate(poc.get("steps", []), 1):
            content += f"### Step {i}: {step.get('step', '')}\n"
            content += f"```\n{step.get('code', '')}\n```\n"
            content += f"{step.get('notes', '')}\n\n"
        expected = poc.get("expected_output", "")
        if expected:
            content += f"**Expected Output**: {expected}\n\n"
        mitigations = poc.get("mitigations", [])
        if mitigations:
            content += "**Mitigations**:\n"
            for m in mitigations:
                content += f"- {m}\n"
            content += "\n"

    return content

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def publish(topic: str, model: str = 'gemini-2.5-pro', dry_run: bool = False, skip_image: bool = False):
    api_key = os.getenv("GEMINI_API_KEY")
    data = generate_content(topic, model=model)

    output_dir = "content/posts"
    os.makedirs(output_dir, exist_ok=True)

    slug = slugify(topic)
    if len(slug) > 50:
        truncated = slug[:50]
        last_dash = truncated.rfind('-')
        slug = truncated[:last_dash] if last_dash > 0 else truncated

    base_slug = slug
    counter = 2
    while os.path.exists(os.path.join(output_dir, f"{slug}.md")):
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Generate hero image before writing markdown so path goes into frontmatter
    visual_brief = data.get("visual_brief", {})
    hero_concept = visual_brief.get("hero_image_concept", "")
    image_path = None
    edu_image_map = {}
    if not skip_image and api_key:
        if hero_concept:
            image_path = generate_hero_image(hero_concept, slug, api_key)
        edu_images = visual_brief.get("educational_images", [])
        if edu_images:
            edu_image_map = generate_educational_images(edu_images, slug, api_key)

    md_content = create_markdown(data, slug, image_path=image_path, edu_image_map=edu_image_map)
    filepath = os.path.join(output_dir, f"{slug}.md")

    with open(filepath, "w") as f:
        f.write(md_content)
    print(f"Article saved to {filepath}")

    social_dir = "content/social"
    os.makedirs(social_dir, exist_ok=True)
    social_content = create_social_file(data)
    social_filepath = os.path.join(social_dir, f"{slug}-social.md")
    with open(social_filepath, "w") as f:
        f.write(social_content)
    print(f"Social copy saved to {social_filepath}")

    publish_to_nextjs(data, slug, image_relative_path=image_path, dry_run=dry_run, edu_image_map=edu_image_map)

    if dry_run:
        print("Dry-run mode active. Skipping Git operations.")
        return

    # Git automation for Cloudflare Pages
    is_git = False
    try:
        subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], check=True, capture_output=True)
        is_git = True
    except subprocess.CalledProcessError:
        print("Not a git repository, skipping auto-publish.")

    if is_git:
        try:
            print("Committing and pushing to trigger Cloudflare Pages deployment...")
            files_to_add = [filepath, social_filepath]
            if image_path:
                local_image_path = os.path.join("static", image_path.lstrip("/"))
                if os.path.exists(local_image_path):
                    files_to_add.append(local_image_path)
            for rel_path, _, _ in edu_image_map.values():
                local_edu_path = os.path.join("static", rel_path.lstrip("/"))
                if os.path.exists(local_edu_path):
                    files_to_add.append(local_edu_path)
            subprocess.run(["git", "add"] + files_to_add, check=True)

            status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
            if status.stdout.strip():
                subprocess.run(["git", "commit", "-m", f"Auto-publish: {topic}"], check=True)
                push_result = git_push()
                if push_result:
                    print("Successfully pushed to remote repository.")
                else:
                    print("Git push failed. Content committed locally; push manually or check GH_TOKEN in .env.")
            else:
                print("No changes to commit. Skipping push.")
        except subprocess.CalledProcessError as e:
            print(f"Git operations failed: {e}")


def publish_to_nextjs(data: dict, slug: str, image_relative_path: str | None = None, dry_run: bool = False, edu_image_map: dict | None = None):
    """Publish the blog post to the Next.js site in BreachLawAgency repository."""
    import shutil
    nextjs_dir = get_nextjs_dir()

    if not os.path.exists(nextjs_dir):
        print(f"Error: Next.js repository directory {nextjs_dir} does not exist.")
        return

    def _copy_image(rel_path: str):
        src = os.path.join("static", rel_path.lstrip("/"))
        dest = os.path.join(nextjs_dir, "public", rel_path.lstrip("/"))
        if not dry_run:
            if os.path.exists(src):
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(src, dest)
                print(f"Copied image {src} to {dest}")
                return dest
            else:
                print(f"Warning: Source image {src} does not exist.")
        else:
            print(f"[Dry-run] Would copy image {src} to {dest}")
        return None

    # 1. Copy hero image and educational images to BreachLawAgency public folder
    staged_images = []
    if image_relative_path:
        dest = _copy_image(image_relative_path)
        if dest:
            staged_images.append(dest)
    if edu_image_map:
        for rel_path, _, _ in edu_image_map.values():
            dest = _copy_image(rel_path)
            if dest:
                staged_images.append(dest)

    # 2. Extract content details
    seo = data.get("seo", {})
    article = data.get("article", {})
    title = seo.get("title", article.get("title", "Untitled"))
    description = seo.get("meta_description", "")
    
    raw_content = article.get("content", "")
    body_content = translate_markdown_to_nextjs_body(raw_content)
    
    category = determine_category(title, raw_content)
    
    read_time = get_read_time(raw_content)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data_ts_path = os.path.join(nextjs_dir, "src/app/blog/data.ts")
    
    if not os.path.exists(data_ts_path):
        print(f"Error: Next.js blog data file {data_ts_path} does not exist.")
        return
        
    with open(data_ts_path, "r", encoding="utf-8") as f:
        data_ts_content = f.read()

    if f'slug: "{slug}"' in data_ts_content or f"slug: '{slug}'" in data_ts_content:
        print(f"Post with slug {slug} already exists in Next.js blog database. Skipping database update.")
        return

    image_line = f'\n    image: {json.dumps(image_relative_path)},' if image_relative_path else ""
    new_post_str = f"""  {{
    slug: {json.dumps(slug)},
    title: {json.dumps(title)},
    description: {json.dumps(description)},
    date: {json.dumps(date_str)},
    category: {json.dumps(category)},
    readTime: {json.dumps(read_time)},
    body: {json.dumps(body_content)},{image_line}
  }},
"""

    target = "export const blogPosts: BlogPost[] = ["
    if target not in data_ts_content:
        print(f"Error: Could not find target array declaration '{target}' in {data_ts_path}.")
        return

    if not dry_run:
        index = data_ts_content.find(target) + len(target)
        updated_content = data_ts_content[:index] + "\n" + new_post_str + data_ts_content[index:]
        with open(data_ts_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
        print(f"Updated {data_ts_path} with new post {slug}")
        # Git operations
        try:
            print("Staging, committing, and pushing changes in BreachLawAgency...")
            for dest_img in staged_images:
                if os.path.exists(dest_img):
                    try:
                        subprocess.run(["git", "add", "-f", dest_img], cwd=nextjs_dir, check=True)
                    except subprocess.CalledProcessError as e:
                        print(f"  Warning: Could not stage image {dest_img}: {e}. Continuing.")
            subprocess.run(["git", "add", data_ts_path], cwd=nextjs_dir, check=True)
            
            status = subprocess.run(["git", "status", "--porcelain"], cwd=nextjs_dir, capture_output=True, text=True, check=True)
            if status.stdout.strip():
                subprocess.run(["git", "commit", "-m", f"Auto-publish: {title}"], cwd=nextjs_dir, check=True)
                push_result = git_push(cwd=nextjs_dir)
                if push_result:
                    print("Successfully pushed to BreachLawAgency remote repository.")
                else:
                    print("Git push failed for BreachLawAgency. Content committed locally.")
            else:
                print("No changes to commit in BreachLawAgency.")
        except subprocess.CalledProcessError as e:
            print(f"Git operations failed for BreachLawAgency: {e}")

    else:
        print(f"[Dry-run] Would insert the following post into {data_ts_path}:\n{new_post_str}")


def get_existing_topics() -> list:
    output_dir = "content/posts"
    if not os.path.exists(output_dir):
        return []
    
    topics = []
    for filename in os.listdir(output_dir):
        if filename.endswith(".md"):
            filepath = os.path.join(output_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    # extract title from frontmatter: title: "..."
                    match = re.search(r'^title:\s*"(.*?)"', content, re.MULTILINE)
                    if match:
                        topics.append(match.group(1))
                    else:
                        # Fallback to filename without extension
                        topics.append(filename[:-3].replace("-", " "))
            except Exception as e:
                print(f"Warning: Failed to read {filename}: {e}")
    return topics

def generate_daily_topic(model: str = 'gemini-2.5-pro') -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set in the environment")

    client = genai.Client(
        api_key=api_key,
        http_options={'timeout': 300000.0}
    )
    existing = get_existing_topics()
    
    prompt = "Generate a single, highly relevant, and trending cybersecurity topic for a blog article. "
    if existing:
        prompt += f"The following topics have already been covered, so DO NOT repeat or closely overlap with them: {', '.join(existing)}. "
    prompt += "Output ONLY the topic name as plain text (e.g., 'Software Supply Chain Security in 2026' or 'Active Directory Golden Ticket Attacks'). Do not include quotes, markdown, or any introductory/concluding text."
    
    print("Generating a new cybersecurity topic...")
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    topic = response.text.strip().strip('"').strip("'")
    print(f"Generated topic: {topic}")
    return topic

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Publishing System for BreachModal.com")
    parser.add_argument("topic", nargs="?", help="The cybersecurity topic to generate and publish (optional. If omitted, a topic will be auto-generated)")
    parser.add_argument("--dry-run", action="store_true", help="Generate files but do not run Git commit/push")
    parser.add_argument("--model", default="gemini-2.5-pro", choices=["gemini-2.5-pro", "gemini-2.5-flash"], help="Gemini model to use")
    parser.add_argument("--skip-image", action="store_true", help="Skip hero image generation")
    parser.add_argument("--topic-only", action="store_true", help="Generate and print topic only, without publishing")
    args = parser.parse_args()

    topic = args.topic
    if not topic:
        topic = generate_daily_topic(model=args.model)

    if args.topic_only:
        print(topic)
        exit(0)

    publish(topic, model=args.model, dry_run=args.dry_run, skip_image=args.skip_image)
