import argparse
import json
import os
import re
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

load_dotenv()

def generate_content(topic: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY is not set in the environment.")
        exit(1)

    client = genai.Client(api_key=api_key)
    
    prompt = USER_PROMPT_TEMPLATE.format(topic=topic)
    
    print(f"Generating content for topic: {topic}...")
    response = client.models.generate_content(
        model='gemini-2.5-pro',
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.7,
        ),
    )
    
    try:
        return json.loads(response.text)
    except json.JSONDecodeError as e:
        print("Error decoding JSON from model response:")
        print(response.text)
        raise e

def create_markdown(data: dict, slug: str) -> str:
    seo = data.get("seo", {})
    article = data.get("article", {})
    
    title = seo.get("title", article.get("title", "Untitled"))
    description = seo.get("meta_description", "")
    keywords = seo.get("primary_keywords", []) + seo.get("secondary_keywords", [])
    
    date_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Frontmatter
    frontmatter = f"""---
title: "{title}"
description: "{description}"
date: {date_str}
slug: "{slug}"
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
        content += "## Visual Brief\n\n"
        content += json.dumps(data["visual_brief"], indent=2) + "\n\n"
        
    if "press_release" in data:
        content += "## Press Release\n\n"
        content += data["press_release"] + "\n\n"
        
    return content

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def publish(topic: str):
    data = generate_content(topic)
    
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
    
    # Git automation for Cloudflare Pages
    try:
        # Check if we're in a git repo
        subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], check=True, capture_output=True)
        
        print("Committing and pushing to trigger Cloudflare Pages deployment...")
        subprocess.run(["git", "add", filepath, social_filepath], check=True)
        subprocess.run(["git", "commit", "-m", f"Auto-publish: {topic}"], check=True)
        # We don't want the agent to accidentally push without remotes set up properly,
        # so we will use a generic push command. The user can configure their remote.
        result = subprocess.run(["git", "push"], capture_output=True, text=True)
        if result.returncode == 0:
            print("Successfully pushed to remote repository.")
        else:
            print(f"Git push failed (no remote configured?): {result.stderr}")
    except subprocess.CalledProcessError:
        print("Not a git repository, skipping auto-publish.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated Publishing System for BreachModal.com")
    parser.add_argument("topic", help="The cybersecurity topic to generate and publish")
    args = parser.parse_args()
    
    publish(args.topic)
