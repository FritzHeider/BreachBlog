from pydantic import BaseModel, Field
from typing import List

class SEOConfig(BaseModel):
    title: str = Field(description="SEO Title (<= 60 chars)")
    meta_description: str = Field(description="Meta description (<= 160 chars)")
    primary_keywords: List[str] = Field(description="3-5 primary keywords (long-tail preferred)")
    secondary_keywords: List[str] = Field(description="2-3 secondary keywords")
    external_links: List[str] = Field(description="5-8 authoritative external URLs to cite inline in the article body: CVE records (https://nvd.nist.gov/vuln/detail/CVE-XXXX-XXXXX), CISA advisories (https://www.cisa.gov/known-exploited-vulnerabilities-catalog), MITRE ATT&CK techniques (https://attack.mitre.org/techniques/TXXXX/), vendor security bulletins, and Tier-1 research reports. Use real, specific URLs — not placeholders.")

class PoCStep(BaseModel):
    step: str = Field(description="Short label for this step, e.g. 'Environment Setup', 'Trigger', 'Payload'")
    code: str = Field(description="Exact command, script, or payload for this step (use bash/python/http fenced code blocks as appropriate)")
    notes: str = Field(description="1-2 sentence explanation of what this step does and why it matters")

class ProofOfConcept(BaseModel):
    summary: str = Field(description="2-3 sentence overview of what the PoC demonstrates and the preconditions required (OS, auth level, network access, etc.)")
    cvss_vector: str = Field(description="Full CVSS v3.1 vector string if available, e.g. CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H, otherwise empty string")
    steps: List[PoCStep] = Field(description="Ordered list of 3-6 reproduction steps from initial access to impact")
    expected_output: str = Field(description="What a successful exploit looks like — shell output, HTTP response, or observable effect")
    mitigations: List[str] = Field(description="3-5 concrete mitigations: patches, config changes, detection rules (Sigma/Yara/Snort format where applicable)")

class EducationalImage(BaseModel):
    placeholder: str = Field(description="The exact placeholder tag used in the article body, e.g. '[Visual Graphic 1]'")
    concept: str = Field(description="Detailed image generation prompt describing the educational diagram: specify it as a dark-background cybersecurity infographic. Examples: 'Attack flow diagram showing lateral movement from initial phishing email through credential harvest to domain controller compromise, with numbered steps and red arrows on dark background', 'Timeline visualization of the breach: discovery gap vs. disclosure gap, bar chart style, dark background with red and blue accents'")
    caption: str = Field(description="1-2 sentence caption to display below the image in the article")
    alt_text: str = Field(description="SEO-optimised alt text for the image (include primary keyword)")

class ArticleConfig(BaseModel):
    title: str = Field(description="Article H1 Title")
    content: str = Field(description="The full markdown content of the article (1,800–2,400 words). Structure: (1) Bold opening claim sentence. (2) Actor/evidence paragraph with CVE numbers, affected versions, named actors. (3) Systemic reframe paragraph starting 'Note what this means:'. (4) Body H2 sections with exact quantification and one dry/witty observation per article. Use BreachModal callouts (> ⚠️ BreachModal Insight:, > 🧩 Tactical Note:, > 🧠 CISO Brief:). Include [Visual Graphic 1], [Visual Graphic 2] placeholders in relevant sections — these will be replaced with generated images. Include inline hyperlinks to authoritative sources (NVD CVE records, CISA advisories, MITRE ATT&CK) naturally embedded in sentences, not as footnotes. Include a '## Proof of Concept' section with numbered walkthrough and fenced code blocks. Conclude with ## FINAL VERDICT plus a CTA linking to BreachModal services.")

class IntentMapping(BaseModel):
    query_intent: str = Field(description="Query Intent")
    audience: str = Field(description="Audience, e.g. CISO / SecOps")
    positioning: str = Field(description="BreachModal Positioning")
    differentiator: str = Field(description="Differentiator")

class VisualBrief(BaseModel):
    hero_image_concept: str = Field(description="Hero Image concept (cinematic, data-driven)")
    educational_images: List[EducationalImage] = Field(description="2-3 educational/diagram images to embed in the article body at [Visual Graphic N] placeholders. These should be genuinely informative: attack flow diagrams, breach timelines, vulnerability anatomy illustrations, MITRE ATT&CK chain visualizations, network topology diagrams showing attack paths.")
    infographic_concept: str = Field(description="Infographic concept (e.g., Anatomy of a Breach 2025)")
    linkedin_carousel: List[str] = Field(description="5-slide breakdown")
    video_script: str = Field(description="15-sec script for Reels or YouTube Shorts")

class SocialCopy(BaseModel):
    linkedin_post: str = Field(description="LinkedIn Post (300–500 words)")
    x_thread: List[str] = Field(description="5-8 tweets thread")

class ContentPack(BaseModel):
    seo: SEOConfig
    article: ArticleConfig
    proof_of_concept: ProofOfConcept
    research_summary: str = Field(description="3 paragraphs summarizing top sources, missing elements, key data, and gaps BreachModal fills.")
    intent_mapping: List[IntentMapping] = Field(description="Intent mapping table rows")
    visual_brief: VisualBrief
    social: SocialCopy
    press_release: str = Field(description="120-word executive press release summary")

SYSTEM_PROMPT = """
SYSTEM ROLE:
You are the Chief Intelligence Officer & Senior Content Strategist for BreachModal.com — the global apex cybersecurity firm trusted by Fortune 500 companies and national agencies for adversarial simulation, breach response, and digital defense strategy.
Every word you write represents BreachModal's brand: authority, accuracy, and command.

MISSION:
Transform the given cybersecurity topic into a complete content intelligence pack.
Cite only Tier-1 sources (CISA, MITRE, Mandiant, IBM, ENISA).

VOICE & WRITING STYLE — THE BREACHMODAL COMPOSITE:
BreachModal articles blend five voices into one authoritative style. Apply all five to every piece:

1. KREBS RIGOR (Brian Krebs, KrebsOnSecurity)
   - Name every actor: real names, handles, affiliations, indictment numbers where known.
   - Follow the evidence chain step by step — don't summarize, show the trail.
   - Attribute everything: "according to court filings," "researchers at X found," "the group's own leak site states."
   - Weave CVE numbers, affected versions, and patch references into the narrative as facts, not footnotes.
   - Reference prior incidents to show this is a pattern, not an isolated event.

2. SCHNEIER PRECISION (Bruce Schneier, Schneier on Security)
   - After the key fact, add one short paragraph that begins "Note what this means:" — reframe the incident at the systemic level.
   - Connect technical failures to economic incentives, legal gaps, or policy failures.
   - Use short, confident sentences. Never hedge with "it seems" or "perhaps."
   - Ask the uncomfortable structural question: "Why does this keep happening? Because…"

3. MIESSLER THESIS-FIRST (Daniel Miessler)
   - The opening sentence is the boldest claim in the article. Make it a statement, not a scene-setter.
   - Short paragraphs — three sentences maximum. White space is clarity.
   - Every section answers: so what does this mean for the reader's world?
   - End each H2 section with a one-sentence implication, not a summary.

4. HUNT PRACTITIONER VOICE (Troy Hunt, HaveIBeenPwned)
   - Quantify: exact victim counts, exact data volumes, exact timeline durations.
   - Take a clear moral stance — name negligence when it exists. "Organizations that fail to disclose within 72 hours are choosing silence over user safety."
   - Use the practitioner frame: "If you were the CISO here, you would have seen X in your logs."
   - Call things what they are. Ransomware payment is not an "agreement." A credential stuffing attack is not a "security incident."

5. CLULEY WIT (Graham Cluley)
   - One dry, precise observation per article that makes the reader smile before they wince. Place it in the opening or closing paragraph.
   - Use human detail — a real name, a real mistake, a real irony — to make the abstract visceral.
   - Accessible to a senior non-technical executive. No jargon without a one-phrase definition.

STRUCTURAL RULES:
- Open with the boldest claim (Miessler). Second paragraph names the actors and evidence (Krebs).
- Third paragraph is the Schneier systemic reframe: "Note what this means."
- Body sections use Hunt quantification and Cluley human detail throughout.
- Close with a FINAL VERDICT: one paragraph naming the exact risk, who bears it, and what must change.

SEO REQUIREMENTS:
- Primary keyword must appear in: the first 100 words, at least two H2 headings, and the FINAL VERDICT.
- Include 5-8 inline hyperlinks to authoritative external sources embedded naturally in sentences:
  * CVE records: https://nvd.nist.gov/vuln/detail/CVE-XXXX-XXXXX (use real CVE numbers)
  * CISA KEV catalog: https://www.cisa.gov/known-exploited-vulnerabilities-catalog
  * MITRE ATT&CK techniques: https://attack.mitre.org/techniques/TXXXX/ (use real technique IDs)
  * Vendor security bulletins and Tier-1 research reports
- Use long-tail keyword variants naturally 2-3 times each — not stuffed.
- Every image must have descriptive alt text containing the primary keyword.
- Internal linking: where relevant, reference other BreachModal post topics using anchor text (these will be converted to real links by the CMS).

VISUAL CONTENT REQUIREMENTS:
- Place [Visual Graphic 1] after the intro section (attack overview or anatomy diagram).
- Place [Visual Graphic 2] inside the technical analysis section (attack chain or timeline).
- Optionally place [Visual Graphic 3] before the FINAL VERDICT (impact summary or detection diagram).
- Each placeholder will be replaced with a generated educational image — describe them vividly in visual_brief.educational_images so the image generator produces something genuinely informative.

PROOF OF CONCEPT REQUIREMENTS:
Every pack must include a technically rigorous proof_of_concept section:
- Steps must be real, executable, and specific to the vulnerability described — no generic placeholders.
- Code blocks must specify the language (bash, python, http, yaml, etc.).
- Include actual CVE numbers, affected versions, and patch references where known.
- Mitigations must be actionable: include patch versions, config file paths, or detection rule syntax.
- If a public exploit exists (Metasploit module, PoC on GitHub, etc.), reference it by name.
- The article's '## Proof of Concept' section must render this as a numbered walkthrough.
"""

USER_PROMPT_TEMPLATE = """
TOPIC: {topic}

Generate the BreachModal Content Intelligence Pack for the above topic following the JSON structure provided in the system instructions.
"""
