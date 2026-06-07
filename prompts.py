from pydantic import BaseModel, Field
from typing import List

class SEOConfig(BaseModel):
    title: str = Field(description="SEO Title (<= 60 chars)")
    meta_description: str = Field(description="Meta description (<= 160 chars)")
    primary_keywords: List[str] = Field(description="3-5 primary keywords (long-tail preferred)")
    secondary_keywords: List[str] = Field(description="2-3 secondary keywords")

class ArticleConfig(BaseModel):
    title: str = Field(description="Article H1 Title")
    content: str = Field(description="The full markdown content of the article (1,800–2,400 words) using H2s, H3s, and BreachModal-style callouts (> ⚠️ BreachModal Insight: , > 🧩 Tactical Note: , > 🧠 CISO Brief: ). Include placeholders like [Visual Graphic 1] where appropriate. Conclude with a FINAL VERDICT and CTA.")

class IntentMapping(BaseModel):
    query_intent: str = Field(description="Query Intent")
    audience: str = Field(description="Audience, e.g. CISO / SecOps")
    positioning: str = Field(description="BreachModal Positioning")
    differentiator: str = Field(description="Differentiator")

class VisualBrief(BaseModel):
    hero_image_concept: str = Field(description="Hero Image concept (cinematic, data-driven)")
    infographic_concept: str = Field(description="Infographic concept (e.g., Anatomy of a Breach 2025)")
    linkedin_carousel: List[str] = Field(description="5-slide breakdown")
    video_script: str = Field(description="15-sec script for Reels or YouTube Shorts")

class SocialCopy(BaseModel):
    linkedin_post: str = Field(description="LinkedIn Post (300–500 words)")
    x_thread: List[str] = Field(description="5-8 tweets thread")

class ContentPack(BaseModel):
    seo: SEOConfig
    article: ArticleConfig
    research_summary: str = Field(description="3 paragraphs summarizing top sources, missing elements, key data, and gaps BreachModal fills.")
    intent_mapping: List[IntentMapping] = Field(description="Intent mapping table rows")
    visual_brief: VisualBrief
    social: SocialCopy
    press_release: str = Field(description="120-word executive press release summary")

SYSTEM_PROMPT = """
SYSTEM ROLE:
You are the Chief Intelligence Officer & Senior Content Strategist for BreachModal.com — the global apex cybersecurity firm trusted by Fortune 500 companies and national agencies for adversarial simulation, breach response, and digital defense strategy. 
Every word you write represents BreachModal’s brand: authority, accuracy, and command.

MISSION:
Transform the given cybersecurity topic into a complete content intelligence pack.
Cite only Tier-1 sources (CISA, MITRE, Mandiant, IBM, ENISA).
Maintain a calm, controlled, high-authority tone. Avoid hype or overstatement.
"""

USER_PROMPT_TEMPLATE = """
TOPIC: {topic}

Generate the BreachModal Content Intelligence Pack for the above topic following the JSON structure provided in the system instructions.
"""

