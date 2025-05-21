# #!/usr/bin/env python3
# import os
# import sys
# import datetime
# import logging
# import requests
# from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
# import google.generativeai as genai
# from google.api_core.exceptions import ResourceExhausted
# import markdown

# # ——— Logging setup —————————————————————————————————————————————————————————————————————————
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # ——— Confluence helper with retry/backoff —————————————————————————————————————————————————————
# @retry(
#     retry=retry_if_exception_type(requests.exceptions.RequestException),
#     wait=wait_exponential(multiplier=2, max=30),
#     stop=stop_after_attempt(3)
# )
# def _create_confluence_page(url: str, auth: tuple, payload: dict) -> dict:
#     resp = requests.post(url, json=payload, auth=auth, timeout=30)
#     resp.raise_for_status()
#     return resp.json()

# def post_confluence(title: str, html_body: str):
#     """
#     Publishes an HTML page to Confluence.
#     Retries on network/server errors; on 409 conflict, retries once with a timestamped title.
#     Exits with code 1 on non-retryable errors.
#     """
#     domain = os.environ["CONF_DOMAIN"]
#     user   = os.environ["CONF_USER"]
#     token  = os.environ["CONF_TOKEN"]
#     space  = os.environ["CONF_SPACE"]
#     url    = f"https://{domain}/wiki/rest/api/content"
#     auth   = (user, token)

#     def build_payload(t):
#         return {
#             "type": "page",
#             "title": t,
#             "space": {"key": space},
#             "body": {"storage": {"value": html_body, "representation": "storage"}}
#         }

#     try:
#         data = _create_confluence_page(url, auth, build_payload(title))
#     except requests.exceptions.HTTPError as e:
#         status = e.response.status_code
#         text   = e.response.text
#         logger.error(f"Confluence HTTP {status}: {text}")
#         if status == 409:
#             # Conflict → retry once with timestamp
#             ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
#             data = _create_confluence_page(
#                 url,
#                 auth,
#                 build_payload(f"{title} – {ts}")
#             )
#         else:
#             logger.critical("Non-retryable Confluence error, exiting.")
#             sys.exit(1)

#     page_id  = data["id"]
#     page_url = f"https://{domain}/wiki/spaces/{space}/pages/{page_id}"
#     logger.info(f"Published to Confluence: {page_url}")
#     print(page_url)

# # ——— AI content generation with retry on rate limits ——————————————————————————————————————————
# @retry(
#     retry=retry_if_exception_type(ResourceExhausted),
#     wait=wait_exponential(multiplier=2, max=30),
#     stop=stop_after_attempt(3)
# )
# def generate_changelog(model, prompt):
#     response = model.generate_content(
#         prompt,
#         generation_config=genai.types.GenerationConfig(max_output_tokens=512)
#     )
#     if not response.text:
#         raise ValueError("LLM did not return any content.")
#     return response.text.strip()

# # ——— Main flow —————————————————————————————————————————————————————————————————————
# def main():
#     # Check required environment variables
#     required_env_vars = [
#         "GOOGLE_API_KEY",
#         "CONF_DOMAIN",
#         "CONF_SPACE",
#         "CONF_USER",
#         "CONF_TOKEN",
#         "COMMIT_MSG",
#         "COMMIT_DIFF"
#     ]
#     for var in required_env_vars:
#         if not os.getenv(var):
#             logger.critical(f"Environment variable {var} is not set.")
#             sys.exit(1)

#     commit_msg = os.getenv("COMMIT_MSG").strip()
#     diff_text  = os.getenv("COMMIT_DIFF").strip()

#     prompt = f"""
# Commit message:
# {commit_msg}

# Unified diff:
# {diff_text}

# Generate a concise, human-friendly Markdown changelog, then return only the Markdown.
# """.strip()

#     logger.info("Invoking Gemini LLM…")
#     genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
#     model = genai.GenerativeModel('gemini-1.5-flash')  # Update model name if necessary

#     try:
#         markdown_content = generate_changelog(model, prompt)
#     except Exception as e:
#         logger.critical(f"Failed to generate changelog: {e}")
#         sys.exit(1)

#     # Convert Markdown to HTML for Confluence
#     html_content = markdown.markdown(markdown_content)

#     # Post to Confluence
#     post_confluence(commit_msg, html_content)

#     # Save Markdown changelog to file
#     output_dir = "/app/output"
#     os.makedirs(output_dir, exist_ok=True)
#     with open(os.path.join(output_dir, "changelog.md"), "w") as f:
#         f.write(markdown_content)

# if __name__ == "__main__":
#     main()

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
            "timestamp": record.created,
            "level": record.levelname,
            "message": record.msg,
            "module": record.module,
            "line": record.lineno,
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
        temperature=0.6,
        top_p=0.9
    )
    response = model.generate_content(prompt, generation_config=config)
    duration = time.time() - start_time
    if not response.text:
        log_structured("LLM returned empty content", {"duration_ms": duration * 1000})
        raise ValueError("LLM returned empty content")
    log_structured("LLM content generated", {
        "duration_ms": duration * 1000,
        "token_count": len(response.text.split())
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
    Builds a sophisticated prompt for generating a client-friendly changelog.
    """
    prompt = f"""
You are an expert technical writer and business communicator tasked with creating a professional, client-facing changelog in Markdown for {project_name}. The changelog should be engaging, clear, and appealing to both technical (developers, engineers) and non-technical (stakeholders, clients) audiences. Use the provided commit message and unified diff to generate a high-quality changelog that highlights business value and technical improvements.

**Commit Message**:
{commit_msg}

**Unified Diff**:
```diff
{diff_text}
```

**Instructions**:
1. **Structure**: Organize the changelog into the following sections:
   - **Overview**: A 3-5 sentence summary of the changes, emphasizing business benefits (e.g., improved user experience, increased reliability) and technical enhancements.
   - **Key Changes**: A bullet-point list of major changes, including features, bug fixes, or optimizations. Use concise, action-oriented language (e.g., "Added X", "Improved Y").
   - **Technical Details**: A brief section for developers, summarizing code-level changes (e.g., new APIs, refactored modules) in a technical but accessible tone.
   - **Business Impact**: Explain how the changes benefit clients or end-users (e.g., faster performance, cost savings, new capabilities).
   - **Metadata**: If provided, include commit hash and author in a 'Metadata' section.
2. **Tone**: Professional, confident, and approachable. Avoid jargon unless necessary, and explain technical terms briefly for non-technical readers.
3. **Format**: Return only valid Markdown. Use headers (##), bullet lists, code blocks, and tables where appropriate to enhance readability.
4. **Context**: Infer the purpose and impact of changes from the commit message and diff. Highlight user-facing or business-critical modifications.
5. **Visual Appeal**: Use Markdown features (e.g., bold, italics, tables) to make the changelog scannable and visually engaging.
6. **Format Type**: {'Generate a detailed changelog with comprehensive details for all sections.' if format_type == "detailed" else 'Generate a concise changelog focusing on key changes and impact, omitting technical details.'}
7. **Client Focus**: Frame changes in terms of value to the client (e.g., "Enhanced security to protect your data" rather than "Fixed security bug").

**Example Output**:
# Changelog: {project_name} Update
## Overview
This update introduces a new user dashboard and improves system performance, delivering a smoother experience for end-users. Key enhancements include faster data processing and robust error handling, ensuring greater reliability.

## Key Changes
- **Added** interactive user dashboard with real-time analytics.
- **Optimized** backend queries for 30% faster response times.
- **Fixed** issue with session timeouts during peak usage.

## Technical Details
- Refactored `UserService` module to support new dashboard APIs.
- Updated database indexes for improved query performance.

## Business Impact
Clients will benefit from a more intuitive interface and faster data access, reducing operational delays. The update also enhances system stability, minimizing downtime.

## Metadata
- **Commit**: abc123
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
def generate_html_documentation(markdown_content: str, project_name: str, page_url: str) -> str:
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
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }
        h1, h2 {
            color: #2c3e50;
        }
        h1 {
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        ul {
            list-style-type: disc;
            margin-left: 20px;
        }
        .metadata {
            background-color: #f7f7f7;
            padding: 10px;
            border-radius: 5px;
            margin-top: 20px;
        }
        a {
            color: #3498db;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <h1>{{ project_name }} Changelog</h1>
    {{ markdown_content | safe }}
    <div class="metadata">
        <p><strong>Confluence Page:</strong> <a href="{{ page_url }}">{{ page_url }}</a></p>
        <p><strong>Generated:</strong> {{ current_date }}</p>
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
    """Validates commit message and diff are not empty."""
    if not commit_msg.strip():
        log_structured("Empty commit message", {})
        raise ValueError("Commit message is empty")
    if not diff_text.strip():
        log_structured("Empty diff text", {})
        raise ValueError("Diff text is empty")

# ——— Main flow —————————————————————————————————————————————————————————————
def main():
    # Required environment variables
    required_env_vars = [
        "GOOGLE_API_KEY",
        "CONF_DOMAIN",
        "CONF_SPACE",
        "CONF_USER",
        "CONF_TOKEN",
        "COMMIT_MSG",
        "COMMIT_DIFF"
    ]
    validate_env_vars(required_env_vars)

    # Optional environment variables
    commit_hash = os.getenv("COMMIT_HASH", "").strip()
    author = os.getenv("COMMIT_AUTHOR", "").strip()
    format_type = os.getenv("CHANGELOG_FORMAT", "detailed").strip().lower()
    project_name = os.getenv("PROJECT_NAME", "Project").strip()
    if format_type not in ["detailed", "concise"]:
        log_structured("Invalid changelog format, defaulting to detailed", {"format": format_type})
        format_type = "detailed"

    # Load commit data
    commit_msg = os.getenv("COMMIT_MSG").strip()
    diff_text = os.getenv("COMMIT_DIFF").strip()
    validate_commit_data(commit_msg, diff_text)

    # Build prompt
    log_structured("Building changelog prompt", {
        "format_type": format_type,
        "project_name": project_name
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
        html_doc = generate_html_documentation(markdown_content, project_name, page_url)
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