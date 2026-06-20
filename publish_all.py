import os
import re
import json
import shutil
import subprocess

def parse_markdown_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    parts = content.split("---")
    if len(parts) < 3:
        return None
    
    frontmatter_str = parts[1]
    body = "---".join(parts[2:]).strip()
    
    frontmatter = {}
    for line in frontmatter_str.strip().split("\n"):
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        frontmatter[key] = val
        
    return frontmatter, body

def translate_markdown_to_nextjs_body(markdown_content: str) -> str:
    lines = markdown_content.split("\n")
    translated_lines = []
    for line in lines:
        stripped = line.strip()
        match = re.match(r'^(#+)\s+(.+)$', stripped)
        if match:
            heading_text = match.group(2).strip()
            translated_lines.append(f"**{heading_text}**")
        else:
            translated_lines.append(line)
    return "\n".join(translated_lines)

def determine_category(topic: str, content: str) -> str:
    topic_lower = topic.lower()
    content_lower = content.lower()
    if "soc 2" in topic_lower or "compliance" in topic_lower or "audit" in topic_lower or "gdpr" in topic_lower or "hipaa" in topic_lower or "iso 27001" in topic_lower:
        return "Compliance"
    elif "ai" in topic_lower or "artificial intelligence" in topic_lower or "llm" in topic_lower or "machine learning" in topic_lower:
        return "AI Security"
    elif "incident" in topic_lower or "response" in topic_lower or "containment" in topic_lower or "breach response" in topic_lower or "playbook" in topic_lower:
        return "Incident Response"
    elif "vulnerability" in topic_lower or "zero-day" in topic_lower or "exploit" in topic_lower or "cve" in topic_lower or "threat" in topic_lower or "attack" in topic_lower or "ransomware" in topic_lower:
        return "Threat Intelligence"
    if "compliance" in content_lower or "audit" in content_lower:
        return "Compliance"
    if "ai" in content_lower or "machine learning" in content_lower:
        return "AI Security"
    if "incident response" in content_lower or "playbook" in content_lower:
        return "Incident Response"
    return "Threat Intelligence"

def main():
    nextjs_dir = "/Users/drop/BreachLawAgency"
    posts_dir = "content/posts"
    data_ts_path = os.path.join(nextjs_dir, "src/app/blog/data.ts")
    
    if not os.path.exists(data_ts_path):
        print(f"Error: Next.js blog data file {data_ts_path} does not exist.")
        return

    with open(data_ts_path, "r", encoding="utf-8") as f:
        data_ts_content = f.read()

    # Find all md files
    md_files = [f for f in os.listdir(posts_dir) if f.endswith(".md")]
    md_files.sort()  # Optional: sort them
    
    published_count = 0
    
    for filename in md_files:
        filepath = os.path.join(posts_dir, filename)
        parsed = parse_markdown_file(filepath)
        if not parsed:
            continue
            
        frontmatter, body = parsed
        slug = frontmatter.get("slug")
        title = frontmatter.get("title", "Untitled")
        description = frontmatter.get("description", "")
        date_str = frontmatter.get("date", "")[:10]  # YYYY-MM-DD
        image_relative_path = frontmatter.get("image")
        
        if not slug:
            print(f"Skipping {filename}: no slug in frontmatter")
            continue
            
        # Check if already in data.ts
        if f'slug: "{slug}"' in data_ts_content or f"slug: '{slug}'" in data_ts_content:
            print(f"Post with slug '{slug}' already exists in Next.js database. Skipping.")
            continue
            
        print(f"Publishing post: {title} ({slug})...")
        
        # 1. Copy image
        if image_relative_path:
            src_image = os.path.join("static", image_relative_path.lstrip("/"))
            dest_image = os.path.join(nextjs_dir, "public", image_relative_path.lstrip("/"))
            if os.path.exists(src_image):
                os.makedirs(os.path.dirname(dest_image), exist_ok=True)
                shutil.copy2(src_image, dest_image)
                print(f"  Copied image to {dest_image}")
                # Force add image to git
                subprocess.run(["git", "add", "-f", dest_image], cwd=nextjs_dir, check=True)
            else:
                print(f"  Warning: Source image {src_image} does not exist.")
                
        # 2. Convert markdown headings
        body_content = translate_markdown_to_nextjs_body(body)
        category = determine_category(title, body)
        
        # Calculate readTime
        words = len(body.split())
        read_time_min = max(1, round(words / 200))
        read_time = f"{read_time_min} min read"
        
        # 3. Add to data.ts
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
        index = data_ts_content.find(target) + len(target)
        data_ts_content = data_ts_content[:index] + "\n" + new_post_str + data_ts_content[index:]
        
        published_count += 1

    if published_count > 0:
        # Write updated content to data.ts
        with open(data_ts_path, "w", encoding="utf-8") as f:
            f.write(data_ts_content)
        print(f"Successfully updated {data_ts_path} with {published_count} new posts.")
        
        # Git operations
        try:
            print("Staging, committing, and pushing changes in BreachLawAgency...")
            subprocess.run(["git", "add", data_ts_path], cwd=nextjs_dir, check=True)
            subprocess.run(["git", "commit", "-m", f"Auto-publish {published_count} blog posts"], cwd=nextjs_dir, check=True)
            
            # Retrieve GH_TOKEN or use standard git push
            gh_token = os.getenv("GH_TOKEN")
            pushed = False
            if gh_token:
                url_result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    cwd=nextjs_dir, capture_output=True, text=True
                )
                remote_url = url_result.stdout.strip()
                if remote_url.startswith("https://github.com/"):
                    auth_url = remote_url.replace("https://github.com/", f"https://{gh_token}@github.com/")
                    result = subprocess.run(["git", "push", auth_url], cwd=nextjs_dir, capture_output=True, text=True)
                    pushed = (result.returncode == 0)
            
            if not pushed:
                subprocess.run(["git", "push"], cwd=nextjs_dir, check=True)
                
            print("Successfully pushed changes to BreachLawAgency remote repository.")
        except Exception as e:
            print(f"Git operations failed: {e}")
    else:
        print("No new posts to publish.")

if __name__ == "__main__":
    main()
