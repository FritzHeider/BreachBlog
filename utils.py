import os
import re
import stat
import subprocess
import tempfile

WORDS_PER_MINUTE = 250


def translate_markdown_to_nextjs_body(markdown_content: str) -> str:
    lines = markdown_content.split("\n")
    translated_lines = []
    for line in lines:
        stripped = line.strip()
        # Match a markdown heading, e.g., "# Heading", "## Heading", "### Heading"
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
    # Fallback checking content too
    if "compliance" in content_lower or "audit" in content_lower:
        return "Compliance"
    if "ai" in content_lower or "machine learning" in content_lower:
        return "AI Security"
    if "incident response" in content_lower or "playbook" in content_lower:
        return "Incident Response"
    return "Threat Intelligence"


def git_push(cwd: str | None = None) -> bool:
    """Push to git remote. Uses GH_TOKEN env var if set for authentication."""
    gh_token = os.getenv("GH_TOKEN")
    if gh_token:
        url_result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cwd, capture_output=True, text=True
        )
        remote_url = url_result.stdout.strip()
        if remote_url.startswith("https://github.com/"):
            # Pass the token via GIT_ASKPASS so it never appears in the process
            # argument list (visible in `ps aux`).
            fd, askpass = tempfile.mkstemp(suffix=".sh")
            try:
                with os.fdopen(fd, "w") as f:
                    f.write("#!/bin/sh\necho " + gh_token + "\n")
                os.chmod(askpass, stat.S_IRWXU)
                env = os.environ.copy()
                env["GIT_ASKPASS"] = askpass
                env["GIT_TERMINAL_PROMPT"] = "0"
                result = subprocess.run(["git", "push"], cwd=cwd, capture_output=True, text=True, env=env)
                return result.returncode == 0
            finally:
                os.unlink(askpass)
    result = subprocess.run(["git", "push"], cwd=cwd, capture_output=True, text=True)
    return result.returncode == 0


def get_nextjs_dir() -> str:
    return os.getenv("NEXTJS_DIR", "/Users/drop/BreachLawAgency")


def get_read_time(text: str) -> str:
    words = len(text.split())
    read_time_min = max(1, round(words / WORDS_PER_MINUTE))
    return f"{read_time_min} min read"
