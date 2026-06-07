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

def generate_content(topic: str, model: str = 'gemini-2.5-pro') -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY is not set in the environment.")
        exit(1)

    client = genai.Client(api_key=api_key)
    
    prompt = USER_PROMPT_TEMPLATE.format(topic=topic)
    
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

def create_markdown(data: dict, slug: str) -> str:
    seo = data.get("seo", {})
    article = data.get("article", {})
    
    title = seo.get("title", article.get("title", "Untitled"))
    description = seo.get("meta_description", "")
    keywords = seo.get("primary_keywords", []) + seo.get("secondary_keywords", [])
    
    date_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Frontmatter - using json.dumps to safely escape any double quotes or special characters
    frontmatter = f"""---
title: {json.dumps(title)}
description: {json.dumps(description)}
date: {date_str}
slug: {json.dumps(slug)}
tags: {json.dumps(keywords)}
author: "BreachModal Intelligence"
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
    data = generate_content(topic, model=model)
    
    slug = slugify(topic)
    if len(slug) > 50:
        slug = slug[:50].strip('-')
        
    output_dir = "content/posts"
    os.makedirs(output_dir, exist_ok=True)
    
    md_content = create_markdown(data, slug)
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
        # Check if we're in a git repo
        subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], check=True, capture_output=True)
        is_git = True
    except subprocess.CalledProcessError:
        print("Not a git repository, skipping auto-publish.")
        
    if is_git:
        try:
            print("Committing and pushing to trigger Cloudflare Pages deployment...")
            subprocess.run(["git", "add", filepath, social_filepath], check=True)
            
            # Check if there are staged changes before committing
            status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
            if status.stdout.strip():
                subprocess.run(["git", "commit", "-m", f"Auto-publish: {topic}"], check=True)
                result = subprocess.run(["git", "push"], capture_output=True, text=True)
                if result.returncode == 0:
                    print("Successfully pushed to remote repository.")
                else:
                    print(f"Git push failed (no remote configured?): {result.stderr.strip()}")
            else:
                print("No changes to commit. Skipping push.")
        except subprocess.CalledProcessError as e:
            print(f"Git operations failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Publishing System for BreachModal.com")
    parser.add_argument("topic", help="The cybersecurity topic to generate and publish")
    parser.add_argument("--dry-run", action="store_true", help="Generate files but do not run Git commit/push")
    parser.add_argument("--model", default="gemini-2.5-pro", choices=["gemini-2.5-pro", "gemini-2.5-flash"], help="Gemini model to use")
    args = parser.parse_args()
    
    publish(args.topic, model=args.model, dry_run=args.dry_run)

