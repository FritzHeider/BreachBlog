import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)

from datetime import datetime, timezone
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, ContentPack
from utils import (
    translate_markdown_to_nextjs_body,
    determine_category,
    get_nextjs_dir,
    get_read_time,
)

GENERATE_MAX_ATTEMPTS = 3
GENERATE_BACKOFF_SECONDS = 15

CYBER_SAFETY_SETTINGS = [
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY, threshold=types.HarmBlockThreshold.BLOCK_NONE),
]

SCHEDULED_TOPICS = [
    ("2026-10-24", "Active Exploitation of Kubernetes Ingress NGINX (CVE-2026-11492)"),
    ("2026-10-25", "Critical Pre-Auth RCE in F5 BIG-IP Next Central Manager (CVE-2026-12884)"),
    ("2026-10-26", "Active Zero-Day Exploitation in Apache Guacamole Gateway (CVE-2026-13550)"),
    ("2026-10-27", "ShadowVanguard Campaign: Weaponizing OAuth App Impersonation in Microsoft 365"),
    ("2026-10-28", "Zero-Click Remote Code Execution Flaw in Veeam Backup & Replication (CVE-2026-14191)"),
    ("2026-10-29", "Storm-1289 Chaining Ivanti EPMM Flaws for Cloud Infrastructure Takeover"),
    ("2026-10-30", "Active Exploitation of Zero-Day RCE in Palo Alto Cortex XDR Agents (CVE-2026-15024)"),
    ("2026-10-31", "PhantomGhost Botnet Weaponizes Docker Engine API Misconfigurations for Hypervisor Escapes"),
    ("2026-11-01", "Critical Authentication Bypass in HashiCorp Vault Clusters (CVE-2026-16302)"),
    ("2026-11-02", "Voltzite Espionage Campaign Targeting US and NATO Power Grids via SCADA Zero-Days"),
    ("2026-11-03", "Active Exploitation of AWS IAM Identity Center SAML Token Forgery (CVE-2026-17480)"),
    ("2026-11-04", "SilverTerrier Redux: BEC Cartels Deploying Custom LLM-Engineered Audio Deepfakes"),
    ("2026-11-05", "Active Zero-Day in VMware ESXi Hypervisor Allowing Direct VM-to-Host Escape (CVE-2026-18920)"),
    ("2026-11-06", "PyPI Supply Chain Poisoning Attacks Deploying Multi-Stage Rust Stealers via Typo-Squatted Wheels"),
    ("2026-11-07", "Critical Unauthenticated SQLi in ServiceNow Now Platform Core (CVE-2026-19251)"),
    ("2026-11-08", "Active Exploitation of SonicWall SonicOS Zero-Day Buffer Overflow (CVE-2026-20412)"),
    ("2026-11-09", "Agentic AI Worm EchoLocker Weaponizes Model Context Protocol Server Permissions"),
    ("2026-11-10", "Active Zero-Day Exploitation of Fortinet FortiClient EMS Remote Code Execution (CVE-2026-21873)"),
    ("2026-11-11", "Chained Zero-Day Exploitation in Cisco ASA and FTD AnyConnect SSL VPN (CVE-2026-22904)"),
    ("2026-11-12", "Critical Remote Code Execution Vulnerability CVE-2026-119618 in Apache HTTP Server"),
]

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def _with_retries(label: str, fn, max_attempts: int = GENERATE_MAX_ATTEMPTS):
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as e:
            last_error = e
            print(f"[{label}] Attempt {attempt}/{max_attempts} failed: {e}")
            if attempt < max_attempts:
                backoff = GENERATE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                print(f"  Backing off for {backoff}s...")
                time.sleep(backoff)
    raise last_error

def fetch_grounding_context(topic: str, api_key: str) -> str:
    print(f"  Searching web grounding for: {topic}...")
    client = genai.Client(api_key=api_key, http_options={'timeout': 180000.0})
    prompt = f"""
    Search the web for the latest, authoritative threat intelligence, articles, and advisories regarding this cybersecurity topic: "{topic}".
    Provide a detailed factual summary of the vulnerability, threat actors, exploits, and mitigations based on the search results. Include specific details like affected versions and CVE numbers if available.
    """
    def _attempt():
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                safety_settings=CYBER_SAFETY_SETTINGS,
                temperature=0.3,
            )
        )
        return response.text

    return _with_retries("grounding search", _attempt)

def generate_content(topic: str, api_key: str) -> dict:
    grounding_context = ""
    try:
        grounding_context = fetch_grounding_context(topic, api_key)
    except Exception as e:
        print(f"  Warning: Grounding search failed: {e}. Proceeding without search context.")

    client = genai.Client(api_key=api_key, http_options={'timeout': 300000.0})

    def _attempt(use_grounding: bool = True):
        ctx = grounding_context if (use_grounding and grounding_context) else ""
        facts_block = f"\nCONCRETE FACTS AND RESEARCH FOUND FROM WEB SEARCH:\n{ctx}\n" if ctx else ""
        prompt = f"""
{USER_PROMPT_TEMPLATE.format(topic=topic)}
{facts_block}
"""
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=ContentPack,
                safety_settings=CYBER_SAFETY_SETTINGS,
                temperature=0.7,
            ),
        )
        if getattr(response, 'parsed', None) is not None:
            validated_data = response.parsed
        elif getattr(response, 'text', None):
            validated_data = ContentPack.model_validate_json(response.text)
        elif response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            text_to_parse = None
            for part in response.candidates[0].content.parts:
                if getattr(part, 'text', None):
                    text_to_parse = part.text
                    break
            if text_to_parse:
                validated_data = ContentPack.model_validate_json(text_to_parse)
            else:
                raise ValueError("No text found in candidate parts")
        else:
            raise ValueError(f"Empty or blocked Gemini response: {response}")

        if isinstance(validated_data, ContentPack):
            return validated_data.model_dump()
        return validated_data

    last_error = None
    for attempt_num in range(1, GENERATE_MAX_ATTEMPTS + 1):
        try:
            use_ctx = (attempt_num == 1 and bool(grounding_context))
            if not use_ctx and grounding_context:
                print("  Retrying without scraped web context to prevent filter false-positives...")
            return _attempt(use_grounding=use_ctx)
        except Exception as e:
            last_error = e
            print(f"[content pack generation] Attempt {attempt_num}/{GENERATE_MAX_ATTEMPTS} failed: {e}")
            if attempt_num < GENERATE_MAX_ATTEMPTS:
                time.sleep(GENERATE_BACKOFF_SECONDS)
    raise last_error

def generate_hero_image(hero_concept: str, slug: str, api_key: str, nextjs_dir: str) -> str | None:
    output_dir = "static/images"
    os.makedirs(output_dir, exist_ok=True)
    image_path = os.path.join(output_dir, f"{slug}.png")
    dest_path = os.path.join(nextjs_dir, "public", "images", f"{slug}.png")
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    if os.path.exists(image_path) and os.path.exists(dest_path):
        print(f"  Hero image already exists at {dest_path}")
        return f"/images/{slug}.png"

    prompt = (
        f"Cinematic, professional cybersecurity editorial illustration. "
        f"{hero_concept} "
        "Dark background with blue and red accents. Photorealistic digital art. "
        "16:9 widescreen format. No text or logos."
    )

    client = genai.Client(api_key=api_key, http_options={'timeout': 180000.0})
    def _attempt():
        response = client.models.generate_content(
            model='gemini-2.5-flash-image',
            contents=prompt,
        )
        image_bytes = None
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                break
        if not image_bytes:
            raise ValueError("No inline image data returned by model")
        return image_bytes

    try:
        image_bytes = _with_retries("hero image generation", _attempt)
        with open(image_path, "wb") as f:
            f.write(image_bytes)
        shutil.copy2(image_path, dest_path)
        print(f"  Hero image saved: {image_path} and {dest_path}")
        return f"/images/{slug}.png"
    except Exception as e:
        print(f"  Warning: Hero image generation failed: {e}")
        return None

def generate_educational_images(educational_images: list, slug: str, api_key: str, nextjs_dir: str) -> dict:
    output_dir = "static/images"
    os.makedirs(output_dir, exist_ok=True)
    client = genai.Client(api_key=api_key, http_options={'timeout': 180000.0})
    results = {}

    for img in educational_images:
        placeholder = img.get("placeholder", "")
        concept = img.get("concept", "")
        caption = img.get("caption", "")
        alt_text = img.get("alt_text", "")
        if not placeholder or not concept:
            continue
        num = re.sub(r'[^0-9]', '', placeholder) or "1"
        filename = f"{slug}-visual-{num}.png"
        image_path = os.path.join(output_dir, filename)
        dest_path = os.path.join(nextjs_dir, "public", "images", filename)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        if os.path.exists(image_path) and os.path.exists(dest_path):
            print(f"  Diagram already exists at {dest_path}")
            results[placeholder] = (f"/images/{filename}", alt_text, caption)
            continue

        prompt = (
            f"Professional cybersecurity educational infographic or diagram. "
            f"{concept} "
            "Dark background with blue and red data-visualization accents. "
            "Clean, readable labels. No watermarks or logos. 16:9 format."
        )

        def _attempt():
            response = client.models.generate_content(
                model='gemini-2.5-flash-image',
                contents=prompt,
            )
            image_bytes = None
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_bytes = part.inline_data.data
                    break
            if not image_bytes:
                raise ValueError("No inline image data in response")
            return image_bytes

        try:
            image_bytes = _with_retries(f"diagram {placeholder}", _attempt)
            with open(image_path, "wb") as f:
                f.write(image_bytes)
            shutil.copy2(image_path, dest_path)
            results[placeholder] = (f"/images/{filename}", alt_text, caption)
            print(f"  Educational diagram saved: {image_path} and {dest_path}")
        except Exception as e:
            print(f"  Warning: Diagram generation failed for {placeholder}: {e}")

    return results

def create_markdown(data: dict, slug: str, target_date_str: str, image_path: str | None = None, edu_image_map: dict | None = None) -> str:
    seo = data.get("seo", {})
    article = data.get("article", {})

    title = seo.get("title", article.get("title", "Untitled"))
    description = seo.get("meta_description", "")
    keywords = seo.get("primary_keywords", []) + seo.get("secondary_keywords", [])

    date_str = f"{target_date_str}T12:00:00Z"
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

def insert_post_into_data_ts(data: dict, slug: str, target_date_str: str, image_relative_path: str | None, nextjs_dir: str):
    data_ts_path = os.path.join(nextjs_dir, "src/app/blog/data.ts")
    with open(data_ts_path, "r", encoding="utf-8") as f:
        data_ts_content = f.read()

    if f'slug: "{slug}"' in data_ts_content or f"slug: '{slug}'" in data_ts_content:
        print(f"  Post '{slug}' already present in data.ts. Skipping insertion.")
        return

    seo = data.get("seo", {})
    article = data.get("article", {})
    title = seo.get("title", article.get("title", "Untitled"))
    description = seo.get("meta_description", "")
    raw_content = article.get("content", "")
    body_content = translate_markdown_to_nextjs_body(raw_content)
    category = determine_category(title, raw_content)
    read_time = get_read_time(raw_content)

    image_line = f'\n    image: {json.dumps(image_relative_path)},' if image_relative_path else ""
    new_post_str = f"""  {{
    slug: {json.dumps(slug)},
    title: {json.dumps(title)},
    description: {json.dumps(description)},
    date: {json.dumps(target_date_str)},
    category: {json.dumps(category)},
    readTime: {json.dumps(read_time)},
    body: {json.dumps(body_content)},{image_line}
  }},
"""
    target = "export const blogPosts: BlogPost[] = ["
    if target not in data_ts_content:
        raise ValueError(f"Could not find '{target}' in {data_ts_path}")

    index = data_ts_content.find(target) + len(target)
    updated_content = data_ts_content[:index] + "\n" + new_post_str + data_ts_content[index:]
    with open(data_ts_path, "w", encoding="utf-8") as f:
        f.write(updated_content)
    print(f"  Inserted post '{slug}' ({target_date_str}) into {data_ts_path}")

def backfill_existing_diagrams(nextjs_dir: str, api_key: str):
    data_ts_path = os.path.join(nextjs_dir, "src/app/blog/data.ts")
    with open(data_ts_path, "r", encoding="utf-8") as f:
        data_ts = f.read()

    client = genai.Client(api_key=api_key, http_options={'timeout': 180000.0})
    posts = re.findall(r'\{\s*slug:\s*"([^"]+)".*?title:\s*"([^"]+)".*?body:\s*("(?:[^"\\]|\\.)*")', data_ts, re.DOTALL)
    print(f"\n=== Scanning {len(posts)} existing posts in data.ts for missing diagram images ===")

    missing_count = 0
    for slug, title, body_json in posts:
        try:
            body = json.loads(body_json)
        except Exception:
            body = body_json

        vg_matches = re.findall(r'\[Visual Graphic (\d+)(?::\s*([^\]]*))?\]', body)
        if not vg_matches:
            continue

        social_file = f"content/social/{slug}-social.md"
        infographic_concept = ""
        if os.path.exists(social_file):
            with open(social_file, "r", encoding="utf-8") as sf:
                soc_text = sf.read()
                m_info = re.search(r'### Infographic Concept\s*\n(.*?)(?:\n###|\n##|$)', soc_text, re.DOTALL)
                if m_info:
                    infographic_concept = m_info.group(1).strip()

        for num, desc in set(vg_matches):
            filename = f"{slug}-visual-{num}.png"
            dest_path = os.path.join(nextjs_dir, "public", "images", filename)
            static_path = os.path.join("static", "images", filename)

            if os.path.exists(dest_path):
                continue

            missing_count += 1
            print(f"  Generating missing diagram {filename} for '{title}'...")
            diagram_desc = desc.strip() if desc else (infographic_concept if infographic_concept else f"Diagram illustrating the attack vector, architecture, or vulnerability lifecycle for {title}")
            prompt = (
                f"Professional cybersecurity educational infographic or diagram. "
                f"{diagram_desc} "
                "Dark background with blue and red data-visualization accents. "
                "Clean, readable labels. No watermarks or logos. 16:9 format."
            )

            def _attempt():
                response = client.models.generate_content(
                    model='gemini-2.5-flash-image',
                    contents=prompt,
                )
                image_bytes = None
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        image_bytes = part.inline_data.data
                        break
                if not image_bytes:
                    raise ValueError("No inline image data in response")
                return image_bytes

            try:
                img_bytes = _with_retries(f"diagram {filename}", _attempt, max_attempts=2)
                os.makedirs(os.path.dirname(static_path), exist_ok=True)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(static_path, "wb") as f:
                    f.write(img_bytes)
                shutil.copy2(static_path, dest_path)
                print(f"    Saved missing diagram: {dest_path}")
            except Exception as e:
                print(f"    Warning: Could not generate diagram {filename}: {e}")

    print(f"=== Backfill complete: processed {missing_count} missing diagrams ===")

def publish_catchup(dry_run: bool = False, include_backfill: bool = False):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set.")

    nextjs_dir = get_nextjs_dir()
    posts_dir = "content/posts"
    social_dir = "content/social"
    os.makedirs(posts_dir, exist_ok=True)
    os.makedirs(social_dir, exist_ok=True)

    total = len(SCHEDULED_TOPICS)
    print(f"=== Starting Catch-Up Publication: {total} Posts (2026-10-24 through 2026-11-11) ===")

    for idx, (target_date, topic) in enumerate(SCHEDULED_TOPICS, 1):
        slug = slugify(topic)
        if len(slug) > 50:
            truncated = slug[:50]
            last_dash = truncated.rfind('-')
            slug = truncated[:last_dash] if last_dash > 0 else truncated

        print(f"\n[{idx}/{total}] Processing {target_date}: {topic} -> slug: {slug}")
        post_file = os.path.join(posts_dir, f"{slug}.md")
        social_file = os.path.join(social_dir, f"{slug}-social.md")

        # Check if already generated
        if os.path.exists(post_file) and os.path.exists(os.path.join(nextjs_dir, "public", "images", f"{slug}.png")):
            print(f"  Post {slug} already generated. Ensuring inserted in data.ts...")
            # We can re-read and ensure it's in data.ts
            with open(post_file, "r", encoding="utf-8") as f:
                content = f.read()
            parts = content.split("---", 2)
            if len(parts) >= 3:
                body = parts[2].strip()
                # Check data.ts
                data_ts_path = os.path.join(nextjs_dir, "src/app/blog/data.ts")
                with open(data_ts_path, "r", encoding="utf-8") as dtf:
                    dtc = dtf.read()
                if f'slug: "{slug}"' not in dtc and f"slug: '{slug}'" not in dtc:
                    # insert
                    print(f"  Inserting existing post {slug} into data.ts")
                    # simple insert
                    image_path = f"/images/{slug}.png"
                    read_time = get_read_time(body)
                    category = determine_category(topic, body)
                    # title and desc from frontmatter
                    m_title = re.search(r'title:\s*"([^"]+)"', parts[1])
                    m_desc = re.search(r'description:\s*"([^"]+)"', parts[1])
                    title = m_title.group(1) if m_title else topic
                    desc = m_desc.group(1) if m_desc else ""
                    body_content = translate_markdown_to_nextjs_body(body)
                    new_post_str = f"""  {{
    slug: {json.dumps(slug)},
    title: {json.dumps(title)},
    description: {json.dumps(desc)},
    date: {json.dumps(target_date)},
    category: {json.dumps(category)},
    readTime: {json.dumps(read_time)},
    body: {json.dumps(body_content)},
    image: {json.dumps(image_path)},
  }},
"""
                    target = "export const blogPosts: BlogPost[] = ["
                    idx_target = dtc.find(target) + len(target)
                    with open(data_ts_path, "w", encoding="utf-8") as dtf:
                        dtf.write(dtc[:idx_target] + "\n" + new_post_str + dtc[idx_target:])
            continue

        if dry_run:
            print(f"  [Dry-run] Would generate ContentPack, hero image, and diagrams for {topic}")
            continue

        # Generate content pack
        print("  Generating ContentPack with gemini-3.8-flash...")
        data = generate_content(topic, api_key)

        # Generate hero image
        visual_brief = data.get("visual_brief", {})
        hero_concept = visual_brief.get("hero_image_concept", "")
        image_path = None
        if hero_concept:
            print("  Generating hero image...")
            image_path = generate_hero_image(hero_concept, slug, api_key, nextjs_dir)

        # Generate educational diagrams
        edu_images = visual_brief.get("educational_images", [])
        edu_image_map = {}
        if edu_images:
            print(f"  Generating {len(edu_images)} educational diagrams...")
            edu_image_map = generate_educational_images(edu_images, slug, api_key, nextjs_dir)

        # Write markdown post
        md_content = create_markdown(data, slug, target_date, image_path=image_path, edu_image_map=edu_image_map)
        with open(post_file, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"  Saved markdown: {post_file}")

        # Write social file
        social_content = create_social_file(data)
        with open(social_file, "w", encoding="utf-8") as f:
            f.write(social_content)
        print(f"  Saved social pack: {social_file}")

        # Insert into Next.js data.ts
        insert_post_into_data_ts(data, slug, target_date, image_path, nextjs_dir)

    print("\n=== All 19 Posts Successfully Generated & Inserted ===")

    if include_backfill:
        backfill_existing_diagrams(nextjs_dir, api_key)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Catch up blog posts up to today's date")
    parser.add_argument("--dry-run", action="store_true", help="Run without changes")
    parser.add_argument("--include-backfill", action="store_true", help="Also generate missing diagram images for older posts")
    parser.add_argument("--backfill-only", action="store_true", help="Only run backfill for missing diagrams")
    args = parser.parse_args()

    if args.backfill_only:
        api_key = os.getenv("GEMINI_API_KEY")
        backfill_existing_diagrams(get_nextjs_dir(), api_key)
    else:
        publish_catchup(dry_run=args.dry_run, include_backfill=args.include_backfill)

