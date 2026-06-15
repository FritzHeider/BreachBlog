import argparse
import json
import os
import re
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, ContentPack

load_dotenv()

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
            http_options=types.HttpOptions(timeout=120000)
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

def fetch_grounding_context(topic: str, api_key: str) -> str:
    print(f"Searching the web for context on: {topic}...")
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=600000)
    )
    prompt = f"""
    Search the web for the latest, authoritative threat intelligence, articles, and advisories regarding this cybersecurity topic: "{topic}".
    Provide a detailed factual summary of the vulnerability, threat actors, exploits, and mitigations based on the search results. Include specific details like affected versions and CVE numbers if available.
    """
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.3,
        )
    )
    return response.text

def generate_content(topic: str, model: str = 'gemini-2.5-pro') -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY is not set in the environment.")
        exit(1)

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
        http_options=types.HttpOptions(timeout=600000)
    )
    
    print(f"Generating content for topic: {topic} using {model}...")
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=ContentPack,
            temperature=0.7,
        ),
    )
    
    try:
        validated_data = ContentPack.model_validate_json(response.text)
        return validated_data.model_dump()
    except Exception as e:
        print("Error validating response against ContentPack schema:")
        print(response.text)
        raise e

def create_markdown(data: dict, slug: str, image_path: str | None = None) -> str:
    seo = data.get("seo", {})
    article = data.get("article", {})

    title = seo.get("title", article.get("title", "Untitled"))
    description = seo.get("meta_description", "")
    keywords = seo.get("primary_keywords", []) + seo.get("secondary_keywords", [])

    date_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

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
    return frontmatter + "\n" + article.get("content", "")

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
        
    return content

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def publish(topic: str, model: str = 'gemini-2.5-pro', dry_run: bool = False):
    api_key = os.getenv("GEMINI_API_KEY")
    data = generate_content(topic, model=model)

    slug = slugify(topic)
    if len(slug) > 50:
        slug = slug[:50].strip('-')

    # Generate hero image before writing markdown so path goes into frontmatter
    hero_concept = data.get("visual_brief", {}).get("hero_image_concept", "")
    image_path = None
    if hero_concept and api_key:
        image_path = generate_hero_image(hero_concept, slug, api_key)

    output_dir = "content/posts"
    os.makedirs(output_dir, exist_ok=True)

    md_content = create_markdown(data, slug, image_path=image_path)
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
            subprocess.run(["git", "add"] + files_to_add, check=True)

            status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
            if status.stdout.strip():
                subprocess.run(["git", "commit", "-m", f"Auto-publish: {topic}"], check=True)
                push_result = _git_push()
                if push_result:
                    print("Successfully pushed to remote repository.")
                else:
                    print("Git push failed. Content committed locally; push manually or check GH_TOKEN in .env.")
            else:
                print("No changes to commit. Skipping push.")
        except subprocess.CalledProcessError as e:
            print(f"Git operations failed: {e}")


def _git_push() -> bool:
    """Push to origin, using GH_TOKEN from env if available (needed for non-interactive cron)."""
    gh_token = os.getenv("GH_TOKEN")
    if gh_token:
        # Get the remote URL and inject the token
        url_result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True
        )
        remote_url = url_result.stdout.strip()
        # Convert https://github.com/... to https://token@github.com/...
        if remote_url.startswith("https://github.com/"):
            auth_url = remote_url.replace("https://github.com/", f"https://{gh_token}@github.com/")
            result = subprocess.run(["git", "push", auth_url], capture_output=True, text=True)
            return result.returncode == 0

    result = subprocess.run(["git", "push"], capture_output=True, text=True)
    return result.returncode == 0

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
        print("Error: GEMINI_API_KEY is not set in the environment.")
        exit(1)

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=600000)
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
    args = parser.parse_args()
    
    topic = args.topic
    if not topic:
        topic = generate_daily_topic(model=args.model)
        
    publish(topic, model=args.model, dry_run=args.dry_run)
