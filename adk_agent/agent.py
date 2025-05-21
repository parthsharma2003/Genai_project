#!/usr/bin/env python3
import os
import sys
import datetime
import logging
import json
import time
import requests
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, GoogleAPIError
import markdown
from jinja2 import Template

# ——— Logging setup with JSON file output ———————————————————————————————————————————
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Structured JSON logging with file storage
class JSONFileHandler(logging.Handler):
    def __init__(self, filename: str):
        super().__init__()
        self.filename = filename
        os.makedirs(os.path.dirname(filename), exist_ok=True)

    def emit(self, record):
        log_entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.msg,
            "module": record.module,
            "line": record.lineno,
            "jenkins_context": {
                "pipeline_stage": os.getenv("STAGE_NAME", "unknown"),
                "commit_hash": os.getenv("COMMIT_HASH", "unknown"),
                "job_name": os.getenv("JOB_NAME", "unknown")
            },
            **getattr(record, "extra", {})
        }
        with open(self.filename, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

log_file = "/app/logs/changelog_generator.log"
json_handler = JSONFileHandler(log_file)
logger.addHandler(json_handler)

def log_structured(message: str, extra: dict = None):
    logger.info(message, extra=extra or {})

# ——— Confluence helper with retry/backoff ———————————————————————————————————————————
@retry(
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    stop=stop_after_attempt(4)
)
def _create_confluence_page(url: str, auth: tuple, payload: dict) -> dict:
    start_time = time.time()
    resp = requests.post(url, json=payload, auth=auth, timeout=30)
    duration = time.time() - start_time
    log_structured("Confluence API call", {
        "url": url,
        "status_code": resp.status_code,
        "duration_ms": duration * 1000
    })
    resp.raise_for_status()
    return resp.json()

def post_confluence(title: str, html_body: str, space: str, domain: str, auth: tuple) -> str:
    """
    Publishes an HTML page to Confluence with retry on network errors.
    On 409 conflict, retries with a timestamped title.
    """
    url = f"https://{domain}/wiki/rest/api/content"

    def build_payload(t: str) -> dict:
        return {
            "type": "page",
            "title": t,
            "space": {"key": space},
            "body": {"storage": {"value": html_body, "representation": "storage"}}
        }

    try:
        data = _create_confluence_page(url, auth, build_payload(title))
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code
        text = e.response.text
        log_structured("Confluence HTTP error", {"status": status, "error": text})
        if status == 409:
            ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
            data = _create_confluence_page(url, auth, build_payload(f"{title} – {ts}"))
        else:
            log_structured("Non-retryable Confluence error", {"status": status})
            raise
    except Exception as e:
        log_structured("Unexpected Confluence error", {"error": str(e)})
        raise

    page_id = data["id"]
    page_url = f"https://{domain}/wiki/spaces/{space}/pages/{page_id}"
    log_structured("Published to Confluence", {"page_url": page_url})
    return page_url

# ——— AI content generation with retry ——————————————————————————————————————————————
@retry(
    retry=retry_if_exception_type((ResourceExhausted, GoogleAPIError)),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    stop=stop_after_attempt(5)
)
def generate_changelog(model, prompt: str, format_type: str = "detailed") -> str:
    """
    Generates a changelog using the AI model.
    Supports 'detailed' or 'concise' formats.
    """
    start_time = time.time()
    config = genai.types.GenerationConfig(
        max_output_tokens=2048 if format_type == "detailed" else 512,
        temperature=0.5,  # Lowered for more consistent output
        top_p=0.95
    )
    response = model.generate_content(prompt, generation_config=config)
    duration = time.time() - start_time
    if not response.text:
        log_structured("LLM returned empty content", {"duration_ms": duration * 1000})
        raise ValueError("LLM returned empty content")
    log_structured("LLM content generated", {
        "duration_ms": duration * 1000,
        "token_count": len(response.text.split()),
        "format_type": format_type
    })
    return response.text.strip()

# ——— Enhanced prompt for AI agent ———————————————————————————————————————————————
def build_changelog_prompt(
    commit_msg: str,
    diff_text: str,
    commit_hash: str = None,
    author: str = None,
    format_type: str = "detailed",
    project_name: str = "Project"
) -> str:
    """
    Builds a highly refined prompt for generating a client-focused changelog.
    """
    diff_content = diff_text if diff_text.strip() else "No diff provided; rely on commit message for context."
    prompt = f"""
You are an expert technical writer and business communicator tasked with creating a professional, client-facing changelog in Markdown for {project_name}. The changelog must be polished, engaging, and accessible to both technical (developers, engineers) and non-technical (clients, stakeholders) audiences. It should highlight the business value of changes, ensure clarity, and maintain a visually appealing format.

**Commit Message**:
{commit_msg}

**Unified Diff**:
```diff
{diff_content}
```

**Instructions**:
1. **Structure**: Organize the changelog into these sections:
   - **Overview**: A 3-5 sentence summary emphasizing business benefits (e.g., improved user experience, cost savings) and key technical enhancements. Start with a strong opening sentence.
   - **Key Changes**: A bullet-point list of major changes (features, fixes, optimizations). Use action verbs (e.g., "Added", "Improved") and quantify improvements where possible (e.g., "Reduced latency by 25%").
   - **Technical Details**: A concise section for developers, summarizing code-level changes (e.g., new APIs, refactored modules) in an accessible tone. Omit in 'concise' format.
   - **Business Impact**: Highlight benefits to clients/end-users (e.g., enhanced security, faster workflows). Frame changes in terms of value (e.g., "Protects sensitive data" instead of "Fixed bug").
   - **Metadata**: Include commit hash and author (if provided) in a 'Metadata' section.
2. **Tone**: Professional, confident, and approachable. Avoid complex jargon; explain technical terms briefly for non-technical readers.
3. **Format**: Return *only* valid Markdown. Use:
   - Headers (##) for sections.
   - Bullet lists for changes.
   - Code blocks for technical terms or file names.
   - Tables for comparisons (e.g., before/after metrics) if applicable.
   - Bold/italics for emphasis (e.g., **New Feature**).
4. **Context**: Infer intent from the commit message and diff (if available). If diff is missing, focus on the commit message and assume incremental changes.
5. **Visual Appeal**: Ensure the Markdown is scannable with clear headings, short paragraphs, and consistent formatting.
6. **Format Type**: 
   - Detailed: Include all sections with comprehensive details.
   - Concise: Focus on Overview, Key Changes, and Business Impact; omit Technical Details.
7. **Client Focus**: Emphasize value to clients (e.g., "Streamlined workflows to save time" instead of "Refactored code").
8. **Error Handling**: If input data is incomplete, generate a reasonable changelog based on available information.

**Example Output**:
# Changelog: {project_name} Update
## Overview
This release introduces a **new reporting dashboard**, delivering real-time insights to users. Performance optimizations reduce data processing times, enhancing the overall experience. These changes empower clients with faster decision-making capabilities.

## Key Changes
- **Added** interactive reporting dashboard with customizable filters.
- **Optimized** database queries, reducing latency by 30%.
- **Fixed** session timeout issue during high-traffic periods.

## Technical Details
- Implemented `ReportService` module for dashboard functionality.
- Updated `db/queries.sql` with new indexes for performance.

## Business Impact
The new dashboard enables clients to monitor KPIs in real-time, improving operational efficiency. Enhanced stability ensures uninterrupted access during peak usage.

## Metadata
- **Commit**: `abc123`
- **Author**: Jane Doe

**Output**:
Return only the Markdown content, nothing else.
"""
    if commit_hash or author:
        prompt += "\n## Metadata\n"
        if commit_hash:
            prompt += f"- **Commit**: `{commit_hash}`\n"
        if author:
            prompt += f"- **Author**: {author}\n"
    return prompt.strip()

# ——— Generate client-friendly HTML documentation ———————————————————————————————————
def generate_html_documentation(markdown_content: str, project_name: str, page_url: str, commit_hash: str = None) -> str:
    """
    Generates a styled HTML documentation page for clients using Jinja2 template.
    """
    template_str = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ project_name }} Changelog</title>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 30px;
            color: #333;
            background-color: #f9f9f9;
        }
        h1 {
            color: #1a3c66;
            border-bottom: 3px solid #1a73e8;
            padding-bottom: 10px;
            font-size: 2.2em;
        }
        h2 {
            color: #1a3c66;
            font-size: 1.5em;
            margin-top: 20px;
        }
        ul {
            list-style-type: disc;
            margin-left: 25px;
            margin-bottom: 15px;
        }
        .metadata {
            background-color: #e8f0fe;
            padding: 15px;
            border-radius: 8px;
            margin-top: 25px;
            font-size: 0.9em;
        }
        a {
            color: #1a73e8;
            text-decoration: none;
            font-weight: 500;
        }
        a:hover {
            text-decoration: underline;
        }
        .container {
            background-color: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f4f4f4;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ project_name }} Changelog</h1>
        {{ markdown_content | safe }}
        <div class="metadata">
            <p><strong>Confluence Page:</strong> <a href="{{ page_url }}">{{ page_url }}</a></p>
            {% if commit_hash %}
            <p><strong>Commit:</strong> {{ commit_hash }}</p>
            {% endif %}
            <p><strong>Generated:</strong> {{ current_date }}</p>
        </div>
    </div>
</body>
</html>
"""
    template = Template(template_str)
    html_content = markdown.markdown(markdown_content, extensions=['extra', 'tables'])
    return template.render(
        project_name=project_name,
        markdown_content=html_content,
        page_url=page_url,
        commit_hash=commit_hash,
        current_date=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    )

# ——— Input validation ———————————————————————————————————————————————————————
def validate_env_vars(required_vars: list) -> None:
    """Validates that all required environment variables are set."""
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        log_structured("Missing environment variables", {"missing": missing})
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")

def validate_commit_data(commit_msg: str, diff_text: str) -> None:
    """Validates commit message; logs warning for empty diff."""
    if not commit_msg.strip():
        log_structured("Empty commit message", {})
        raise ValueError("Commit message is empty")
    if not diff_text.strip():
        log_structured("Empty diff text; proceeding with commit message only", {})

# ——— Main flow —————————————————————————————————————————————————————————————
def main():
    # Required environment variables
    required_env_vars = [
        "GOOGLE_API_KEY",
        "CONF_DOMAIN",
        "CONF_SPACE",
        "CONF_USER",
        "CONF_TOKEN",
        "COMMIT_MSG"
    ]
    validate_env_vars(required_env_vars)

    # Optional environment variables
    commit_hash = os.getenv("COMMIT_HASH", "").strip()
    author = os.getenv("COMMIT_AUTHOR", "").strip()
    diff_text = os.getenv("COMMIT_DIFF", "").strip()
    format_type = os.getenv("CHANGELOG_FORMAT", "detailed").strip().lower()
    project_name = os.getenv("PROJECT_NAME", "GenAI Project").strip()
    if format_type not in ["detailed", "concise"]:
        log_structured("Invalid changelog format, defaulting to detailed", {"format": format_type})
        format_type = "detailed"

    # Load commit data
    commit_msg = os.getenv("COMMIT_MSG").strip()
    validate_commit_data(commit_msg, diff_text)

    # Build prompt
    log_structured("Building changelog prompt", {
        "format_type": format_type,
        "project_name": project_name,
        "commit_hash": commit_hash
    })
    prompt = build_changelog_prompt(commit_msg, diff_text, commit_hash, author, format_type, project_name)

    # Initialize AI model
    log_structured("Initializing Gemini LLM", {})
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-pro')

    # Generate changelog
    try:
        markdown_content = generate_changelog(model, prompt, format_type)
    except Exception as e:
        log_structured("Failed to generate changelog", {"error": str(e)})
        raise

    # Convert Markdown to HTML for Confluence
    html_content = markdown.markdown(markdown_content, extensions=['extra', 'tables'])

    # Post to Confluence
    auth = (os.getenv("CONF_USER"), os.getenv("CONF_TOKEN"))
    try:
        page_url = post_confluence(
            title=commit_msg[:255],
            html_body=html_content,
            space=os.getenv("CONF_SPACE"),
            domain=os.getenv("CONF_DOMAIN"),
            auth=auth
        )
        print(page_url)
    except Exception as e:
        log_structured("Failed to post to Confluence", {"error": str(e)})
        raise

    # Save Markdown changelog
    output_dir = "/app/output"
    os.makedirs(output_dir, exist_ok=True)
    markdown_path = os.path.join(output_dir, "changelog.md")
    try:
        with open(markdown_path, "w") as f:
            f.write(markdown_content)
        log_structured("Saved changelog to file", {"path": markdown_path})
    except Exception as e:
        log_structured("Failed to save changelog", {"error": str(e)})
        raise

    # Generate and save HTML documentation
    html_path = os.path.join(output_dir, "changelog.html")
    try:
        html_doc = generate_html_documentation(markdown_content, project_name, page_url, commit_hash)
        with open(html_path, "w") as f:
            f.write(html_doc)
        log_structured("Saved HTML documentation", {"path": html_path})
    except Exception as e:
        log_structured("Failed to save HTML documentation", {"error": str(e)})
        raise

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_structured("Script execution failed", {"error": str(e)})
        sys.exit(1)