import os
import argparse
from google import genai
from google.genai import types
from dotenv import load_dotenv
from publish import publish

load_dotenv()

def fetch_trending_topic() -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY is not set.")
        exit(1)
        
    client = genai.Client(api_key=api_key)
    
    prompt = """
    Search the web for current trending cybersecurity topics, news, or incidents from the last 24-48 hours.
    Identify one significant, specific topic or vulnerability that would be highly relevant for a professional threat intelligence blog post.
    Return ONLY a concise, high-level title of the topic (e.g., "Active Exploitation of CVE-2026-XXXX in VPN Gateways" or "New Ransomware Variant Targeting Critical Infrastructure").
    Do not add markdown formatting, quotes, or conversational preamble.
    """
    
    print("Searching for trending cybersecurity topics...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.7,
        )
    )
    
    topic = response.text.strip().strip('"').strip("'")
    return topic

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find a trending cybersecurity topic and publish content for it")
    parser.add_argument("--dry-run", action="store_true", help="Generate files but do not run Git commit/push")
    parser.add_argument("--model", default="gemini-2.5-pro", choices=["gemini-2.5-pro", "gemini-2.5-flash"], help="Gemini model to use for the main article")
    args = parser.parse_args()
    
    try:
        topic = fetch_trending_topic()
        print(f"Selected trending topic: {topic}")
        publish(topic, model=args.model, dry_run=args.dry_run)
    except Exception as e:
        print(f"Failed to fetch or publish trending topic: {e}")
        exit(1)
