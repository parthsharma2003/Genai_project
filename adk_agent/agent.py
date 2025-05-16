#!/usr/bin/env python3
import os
import sys
import datetime
import logging
import requests
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
import markdown

# ——— Logging setup —————————————————————————————————————————————————————————————————————————
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ——— Confluence helper with retry/backoff —————————————————————————————————————————————————————
@retry(
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    wait=wait_exponential(multiplier=2, max=30),
    stop=stop_after_attempt(3)
)
def _create_confluence_page(url: str, auth: tuple, payload: dict) -> dict:
    resp = requests.post(url, json=payload, auth=auth, timeout=30)
    resp.raise_for_status()
    return resp.json()

def post_confluence(title: str, html_body: str):
    """
    Publishes an HTML page to Confluence.
    Retries on network/server errors; on 409 conflict, retries once with a timestamped title.
    Exits with code 1 on non-retryable errors.
    """
    domain = os.environ["CONF_DOMAIN"]
    user   = os.environ["CONF_USER"]
    token  = os.environ["CONF_TOKEN"]
    space  = os.environ["CONF_SPACE"]
    url    = f"https://{domain}/wiki/rest/api/content"
    auth   = (user, token)

    def build_payload(t):
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
        text   = e.response.text
        logger.error(f"Confluence HTTP {status}: {text}")
        if status == 409:
            # Conflict → retry once with timestamp
            ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
            data = _create_confluence_page(
                url,
                auth,
                build_payload(f"{title} – {ts}")
            )
        else:
            logger.critical("Non-retryable Confluence error, exiting.")
            sys.exit(1)

    page_id  = data["id"]
    page_url = f"https://{domain}/wiki/spaces/{space}/pages/{page_id}"
    logger.info(f"Published to Confluence: {page_url}")
    print(page_url)

# ——— AI content generation with retry on rate limits ——————————————————————————————————————————
@retry(
    retry=retry_if_exception_type(ResourceExhausted),
    wait=wait_exponential(multiplier=2, max=30),
    stop=stop_after_attempt(3)
)
def generate_changelog(model, prompt):
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(max_output_tokens=512)
    )
    if not response.text:
        raise ValueError("LLM did not return any content.")
    return response.text.strip()

# ——— Main flow —————————————————————————————————————————————————————————————————————
def main():
    # Check required environment variables
    required_env_vars = [
        "GOOGLE_API_KEY",
        "CONF_DOMAIN",
        "CONF_SPACE",
        "CONF_USER",
        "CONF_TOKEN",
        "COMMIT_MSG",
        "COMMIT_DIFF"
    ]
    for var in required_env_vars:
        if not os.getenv(var):
            logger.critical(f"Environment variable {var} is not set.")
            sys.exit(1)

    commit_msg = os.getenv("COMMIT_MSG").strip()
    diff_text  = os.getenv("COMMIT_DIFF").strip()

    prompt = f"""
Commit message:
{commit_msg}

Unified diff:
{diff_text}

Generate a concise, human-friendly Markdown changelog, then return only the Markdown.
""".strip()

    logger.info("Invoking Gemini LLM…")
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')  # Update model name if necessary

    try:
        markdown_content = generate_changelog(model, prompt)
    except Exception as e:
        logger.critical(f"Failed to generate changelog: {e}")
        sys.exit(1)

    # Convert Markdown to HTML for Confluence
    html_content = markdown.markdown(markdown_content)

    # Post to Confluence
    post_confluence(commit_msg, html_content)

    # Save Markdown changelog to file
    output_dir = "/app/output"
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "changelog.md"), "w") as f:
        f.write(markdown_content)

if __name__ == "__main__":
    main()