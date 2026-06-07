# BreachBlog Publishing System

An automated cybersecurity threat-intelligence content engine. BreachBlog leverages Gemini (via the official `google-genai` SDK) to transform complex security topics into complete content intelligence packs: SEO-optimized blog articles, research summaries, social media copy, visual briefs, and press releases.

---

## Features

- **Pydantic Validation Schemas**: Utilizes native Gemini SDK structured output validation (`ContentPack` schema) to guarantee the model output conforms perfectly to the JSON schema.
- **Dynamic Topic Generation**: If no topic is passed, the script automatically queries Gemini to discover a new trending cybersecurity topic, using existing articles to filter out duplicates.
- **Robust Git Flow**: Isolated repo validation and state checks prevent Git commits and pushes from failing or raising false errors when files are unchanged.
- **Frontmatter Safety**: Encodes YAML frontmatter keys dynamically using double-quote escaping to prevent parsing breakages in Hugo, Astro, Jekyll, or Cloudflare Pages build engines.
- **Formatted Social Copies**: Social media posts (LinkedIn, X threads) and creative briefs are compiled into human-readable Markdown files.

---

## Repository Structure

```text
├── .github/workflows/
│   └── daily-publish.yml      # Automated GitHub Action for daily generation
├── content/
│   ├── posts/                 # Output folder for article markdown files
│   └── social/                # Output folder for social copy markdown files
├── prompts.py                 # Pydantic schemas and system instructions
├── publish.py                 # Core publisher engine and Git automation
├── publish_trending.py        # Wrapper script utilizing Google Search Grounding
├── run_cron.sh                # macOS shell wrapper with a 24-hour start delay
└── .env.example               # Template environment configuration file
```

---

## Setup & Configuration

### Prerequisites
- Python 3.11+
- Virtual environment (`venv`) with dependencies installed:
  ```bash
  pip install google-genai python-dotenv pydantic
  ```

### Local Environment Variables
Create a `.env` file in the project root:
```bash
cp .env.example .env
```
Open `.env` and configure your API key from [Google AI Studio](https://aistudio.google.com/):
```env
GEMINI_API_KEY=your_api_key_here
```

---

## Usage Guide

### 1. Manual Publishing
Run the script manually using your topic of choice:
```bash
python publish.py "Software Supply Chain Security"
```

To run a dry run (generates Markdown files locally without triggering Git commits or pushes):
```bash
python publish.py "Software Supply Chain Security" --dry-run
```

To run with a specific model (options: `gemini-2.5-pro`, `gemini-2.5-flash`):
```bash
python publish.py "Software Supply Chain Security" --model gemini-2.5-flash
```

### 2. Auto-Generated Topics
If you omit the topic argument, the script will automatically inspect `content/posts/`, extract what topics you have already covered, and generate a new unique, trending cybersecurity topic to write about:
```bash
python publish.py
```

---

## Automations

### 1. GitHub Actions (Daily Automations)
Located in [daily-publish.yml](file:///Users/drop/breachblog/.github/workflows/daily-publish.yml), this workflow runs daily at `08:00 UTC`. It automatically:
1. Installs requirements.
2. Checks out the repository.
3. Invokes the python script to generate a unique daily topic and publish it.
4. Commits and pushes the generated content back to your branch, triggering any static site page updates.

> [!IMPORTANT]
> To enable the GitHub Action, make sure to add your `GEMINI_API_KEY` under your GitHub Repository secrets (`Settings > Secrets and variables > Actions`).

### 2. macOS cron Runner (Every 12 Hours)
For local or server-based automation, a cron runner is configured using [run_cron.sh](file:///Users/drop/breachblog/run_cron.sh).
- **Start Delay**: Evaluates a local `.cron_start_time` stamp to enforce a 24-hour delay before the very first article generation.
- **Search Grounding**: Runs `publish_trending.py`, which prompts Gemini (with **Google Search Grounding** enabled) to pull live, active cybersecurity news from the last 24 hours.
- **Scheduling**: Configured to run every 12 hours:
  ```text
  0 */12 * * * /Users/drop/breachblog/run_cron.sh
  ```
- **Logging**: Execution and delays are logged directly to local `cron_run.log`.
