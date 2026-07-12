import os
import json
import shutil
import subprocess
import argparse

from dotenv import load_dotenv
load_dotenv()

from utils import (
    translate_markdown_to_nextjs_body,
    determine_category,
    git_push,
    get_nextjs_dir,
    get_read_time,
    WORDS_PER_MINUTE,
)


def parse_markdown_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    frontmatter_str = parts[1]
    body = parts[2].strip()

    frontmatter = {}
    for line in frontmatter_str.strip().split("\n"):
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        frontmatter[key] = val

    return frontmatter, body


def main():
    parser = argparse.ArgumentParser(description="Publish all local markdown posts to Next.js")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be published without writing changes")
    args = parser.parse_args()
    dry_run = args.dry_run

    nextjs_dir = get_nextjs_dir()
    posts_dir = "content/posts"
    data_ts_path = os.path.join(nextjs_dir, "src/app/blog/data.ts")

    if not os.path.exists(data_ts_path):
        print(f"Error: Next.js blog data file {data_ts_path} does not exist.")
        return

    with open(data_ts_path, "r", encoding="utf-8") as f:
        data_ts_content = f.read()

    target = "export const blogPosts: BlogPost[] = ["
    if target not in data_ts_content:
        print(f"Error: Could not find '{target}' in {data_ts_path}. Aborting.")
        return

    md_files = [f for f in os.listdir(posts_dir) if f.endswith(".md")]
    md_files.sort()

    published_count = 0

    for filename in md_files:
        filepath = os.path.join(posts_dir, filename)
        parsed = parse_markdown_file(filepath)
        if not parsed:
            continue

        frontmatter, body = parsed
        slug = frontmatter.get("slug", "").strip()
        title = frontmatter.get("title", "Untitled")
        description = frontmatter.get("description", "")
        date_str = frontmatter.get("date", "")[:10]
        image_relative_path = frontmatter.get("image")

        if not slug:
            print(f"Skipping {filename}: no slug in frontmatter")
            continue

        if f'slug: "{slug}"' in data_ts_content or f"slug: '{slug}'" in data_ts_content:
            print(f"Post with slug '{slug}' already exists in Next.js database. Skipping.")
            continue

        if dry_run:
            print(f"[Dry-run] Would publish: {slug}")
            published_count += 1
            continue

        print(f"Publishing post: {title} ({slug})...")

        if image_relative_path:
            src_image = os.path.join("static", image_relative_path.lstrip("/"))
            dest_image = os.path.join(nextjs_dir, "public", image_relative_path.lstrip("/"))
            if os.path.exists(src_image):
                os.makedirs(os.path.dirname(dest_image), exist_ok=True)
                shutil.copy2(src_image, dest_image)
                print(f"  Copied image to {dest_image}")
                try:
                    subprocess.run(["git", "add", "-f", dest_image], cwd=nextjs_dir, check=True)
                except subprocess.CalledProcessError as e:
                    print(f"  Warning: Could not stage image {dest_image}: {e}. Continuing without it.")
            else:
                print(f"  Warning: Source image {src_image} does not exist.")

        body_content = translate_markdown_to_nextjs_body(body)
        category = determine_category(title, body)
        read_time = get_read_time(body)

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
        index = data_ts_content.find(target) + len(target)
        data_ts_content = data_ts_content[:index] + "\n" + new_post_str + data_ts_content[index:]

        published_count += 1

    if dry_run:
        print(f"[Dry-run] {published_count} post(s) would be published.")
        return

    if published_count > 0:
        with open(data_ts_path, "w", encoding="utf-8") as f:
            f.write(data_ts_content)
        print(f"Successfully updated {data_ts_path} with {published_count} new posts.")

        try:
            print("Staging, committing, and pushing changes in BreachLawAgency...")
            subprocess.run(["git", "add", data_ts_path], cwd=nextjs_dir, check=True)
            subprocess.run(["git", "commit", "-m", f"Auto-publish {published_count} blog posts"], cwd=nextjs_dir, check=True)

            if git_push(cwd=nextjs_dir):
                print("Successfully pushed changes to BreachLawAgency remote repository.")
            else:
                print("Git push failed.")
        except Exception as e:
            print(f"Git operations failed: {e}")
    else:
        print("No new posts to publish.")


if __name__ == "__main__":
    main()
