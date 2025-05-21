import os
import sys
import logging
from pathlib import Path
import markdown
import google.generativeai as genai
from requests.auth import HTTPBasicAuth
import requests
from jinja2 import Environment, FileSystemLoader
from tenacity import retry, stop_after_attempt, wait_exponential

# Set up logging
log_dir = Path("/app/logs")
log_dir.mkdir(exist_ok=True, parents=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "changelog_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Debug: Confirm log file setup and test write
logger.info("Starting agent.py, log directory: %s", log_dir)
for handler in logger.handlers:
    if isinstance(handler, logging.FileHandler):
        logger.debug("Log file path: %s", handler.baseFilename)
try:
    with open(log_dir / "changelog_generator.log", "a") as f:
        f.write("Test write at startup\n")
    logger.info("Test write to log file succeeded")
except Exception as e:
    logger.error("Failed to write to log file: %s", str(e))

def validate_env_vars():
    """Validate required environment variables."""
    required_vars = [
        "GOOGLE_API_KEY", "CONF_DOMAIN", "CONF_SPACE", "CONF_USER", "CONF_TOKEN",
        "COMMIT_MSG", "COMMIT_HASH", "COMMIT_AUTHOR", "COMMIT_DIFF",
        "PROJECT_NAME", "CHANGELOG_FORMAT", "VERSION", "STAGE_NAME"
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        sys.exit(1)
    logger.info("All required environment variables are present")
    # Debug: Log non-sensitive env vars
    for var in required_vars:
        value = os.getenv(var) if var not in ["GOOGLE_API_KEY", "CONF_TOKEN"] else "****"
        logger.debug(f"Env var {var}: {value}")

def build_prompt(commit_msg, commit_diff, project_name, version, changelog_format):
    """Build the prompt for the LLM."""
    logger.info("Building changelog prompt")
    if not commit_diff or commit_diff == "No diff available":
        logger.warning("Commit diff is empty, using commit message only")
        commit_diff = "No diff provided"
    return f"""
    You are an AI assistant tasked with generating a changelog for the {project_name} project.
    Changelog Format: {changelog_format}
    Version: {version}
    Commit Message: {commit_msg}
    Commit Diff:
    ```
    {commit_diff}
    ```
    Generate a concise changelog entry summarizing the changes. Include key features, fixes, or improvements.
    Output only the changelog content in Markdown format, without any additional explanations or metadata.
    """

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_changelog_with_model(model_name, prompt):
    """Generate changelog using specified Gemini model."""
    logger.info(f"Attempting to initialize Gemini LLM: {model_name}")
    try:
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        if not response.text:
            logger.error("Empty response from LLM")
            raise ValueError("LLM returned empty response")
        logger.info("Changelog generated successfully with %s", model_name)
        return response.text.strip()
    except Exception as e:
        logger.error(f"LLM generation failed with {model_name}: {str(e)}")
        raise

def generate_changelog(prompt):
    """Generate changelog, trying gemini-1.5-pro first, then gemini-1.5-flash."""
    try:
        return generate_changelog_with_model("gemini-1.5-pro", prompt)
    except Exception as e:
        logger.warning("Failed with gemini-1.5-pro, falling back to gemini-1.5-flash: %s", str(e))
        try:
            return generate_changelog_with_model("gemini-1.5-flash", prompt)
        except Exception as e:
            logger.error("Failed with gemini-1.5-flash: %s", str(e))
            logger.info("Generating fallback changelog from commit message")
            return f"- {os.getenv('COMMIT_MSG')}"

def publish_to_confluence(title, html, space, domain, auth):
    """Publish content to Confluence."""
    logger.info(f"Attempting to publish to Confluence: {title}")
    url = f"https://{domain}/rest/api/content"
    headers = {"Content-Type": "application/json"}
    data = {
        "type": "page",
        "title": title,
        "space": {"key": space},
        "body": {
            "storage": {
                "value": html,
                "representation": "storage"
            }
        }
    }
    try:
        response = requests.post(url, json=data, headers=headers, auth=auth)
        response.raise_for_status()
        page_id = response.json()["id"]
        page_url = f"https://{domain}/pages/viewpage.action?pageId={page_id}"
        logger.info(f"Successfully published to Confluence: {page_url}")
        return page_url
    except Exception as e:
        logger.error(f"Confluence publishing failed: {str(e)}")
        return None

def render_html(markdown_content, project_name, page_url, commit_hash, version):
    """Render HTML using Jinja2 template."""
    logger.info("Rendering HTML output")
    try:
        env = Environment(loader=FileSystemLoader("/app"))
        template = env.get_template("changelog_template.html")
        html_output = template.render(
            project_name=project_name,
            markdown_content=markdown.markdown(markdown_content),
            page_url=page_url or "Not published",
            commit_hash=commit_hash,
            current_date=version
        )
        logger.info("HTML rendered successfully")
        return html_output
    except Exception as e:
        logger.warning(f"HTML rendering failed, skipping HTML output: {str(e)}")
        return None

def main():
    """Main function to generate and publish changelog."""
    try:
        # Validate environment variables
        validate_env_vars()

        # Build prompt and generate changelog
        prompt = build_prompt(
            commit_msg=os.getenv("COMMIT_MSG"),
            commit_diff=os.getenv("COMMIT_DIFF"),
            project_name=os.getenv("PROJECT_NAME"),
            version=os.getenv("VERSION"),
            changelog_format=os.getenv("CHANGELOG_FORMAT")
        )
        markdown_out = generate_changelog(prompt)

        # Save Markdown output (before Confluence or HTML to ensure partial success)
        out_dir = Path("/app/output")
        out_dir.mkdir(exist_ok=True, parents=True)
        (out_dir / "changelog.md").write_text(markdown_out, encoding="utf-8")
        logger.info(f"Markdown changelog written to {out_dir / 'changelog.md'}")

        # Publish to Confluence
        auth = HTTPBasicAuth(os.getenv("CONF_USER"), os.getenv("CONF_TOKEN"))
        page_url = publish_to_confluence(
            title=f"{os.getenv('PROJECT_NAME')} – {os.getenv('VERSION')}",
            html=markdown.markdown(markdown_out),
            space=os.getenv("CONF_SPACE"),
            domain=os.getenv("CONF_DOMAIN"),
            auth=auth
        )

        # Render HTML
        html_out = render_html(
            markdown_content=markdown_out,
            project_name=os.getenv("PROJECT_NAME"),
            page_url=page_url,
            commit_hash=os.getenv("COMMIT_HASH"),
            version=os.getenv("VERSION")
        )
        if html_out:
            (out_dir / "changelog.html").write_text(html_out, encoding="utf-8")
            logger.info(f"HTML changelog written to {out_dir / 'changelog.html'}")
        else:
            logger.warning("Skipping HTML changelog due to rendering failure")

        # Ensure logs are flushed
        for handler in logger.handlers:
            handler.flush()

        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        # Ensure logs are flushed before exiting
        for handler in logger.handlers:
            handler.flush()
        sys.exit(1)

if __name__ == "__main__":
    main()