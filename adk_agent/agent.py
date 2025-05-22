import os
import sys
import logging
from pathlib import Path
import markdown
import google.generativeai as genai
from requests.auth import HTTPBasicAuth
import requests
from jinja2 import Environment, FileSystemLoader, Template
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime

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

# Confluence API configuration
CONF_DOMAIN = os.getenv('CONF_DOMAIN')
CONF_SPACE = os.getenv('CONF_SPACE')
CONF_USER = os.getenv('CONF_USER')
CONF_TOKEN = os.getenv('CONF_TOKEN')
PROJECT_NAME = os.getenv('PROJECT_NAME', 'MyProject')

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

def get_confluence_page_id(title):
    """Get the page ID for a given title in Confluence."""
    url = f"https://{CONF_DOMAIN}/wiki/api/v2/pages"
    headers = {
        'Authorization': f'Basic {CONF_TOKEN}',
        'Content-Type': 'application/json'
    }
    params = {
        'space-id': CONF_SPACE,
        'title': title
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if data['results']:
            return data['results'][0]['id']
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting page ID: {str(e)}")
        return None

def create_or_update_confluence_page(title, content):
    """Create or update a page in Confluence."""
    page_id = get_confluence_page_id(title)
    
    url = f"https://{CONF_DOMAIN}/wiki/api/v2/pages"
    if page_id:
        url = f"{url}/{page_id}"
    
    headers = {
        'Authorization': f'Basic {CONF_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'spaceId': CONF_SPACE,
        'title': title,
        'body': {
            'representation': 'storage',
            'value': content
        }
    }
    
    try:
        if page_id:
            # Update existing page
            response = requests.put(url, headers=headers, json=data)
        else:
            # Create new page
            response = requests.post(url, headers=headers, json=data)
        
        response.raise_for_status()
        logger.info(f"Successfully {'updated' if page_id else 'created'} page: {title}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error {'updating' if page_id else 'creating'} page: {str(e)}")
        return False

def render_html(markdown_content, project_name, page_url, commit_hash, version):
    """Render HTML using Jinja2 template or fallback."""
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
        logger.info("HTML rendered successfully from file")
        return html_output
    except Exception as e:
        logger.warning(f"HTML rendering failed, using fallback template: {str(e)}")
        # Fallback template
        fallback_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{ project_name }} Changelog</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #333; }
                .changelog { max-width: 800px; margin: auto; }
                .meta { color: #666; font-size: 0.9em; }
            </style>
        </head>
        <body>
            <div class="changelog">
                <h1>{{ project_name }} Changelog</h1>
                {{ markdown_content | safe }}
                <div class="meta">
                    <p>Confluence Page: {{ page_url }}</p>
                    {% if commit_hash %}
                    <p>Commit: {{ commit_hash }}</p>
                    {% endif %}
                    <p>Generated: {{ current_date }}</p>
                </div>
            </div>
        </body>
        </html>
        """
        template = Template(fallback_template)
        html_output = template.render(
            project_name=project_name,
            markdown_content=markdown.markdown(markdown_content),
            page_url=page_url or "Not published",
            commit_hash=commit_hash,
            current_date=version
        )
        logger.info("HTML rendered using fallback template")
        return html_output

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

        # Save Markdown output
        out_dir = Path("/app/output")
        out_dir.mkdir(exist_ok=True, parents=True)
        (out_dir / "changelog.md").write_text(markdown_out, encoding="utf-8")
        logger.info(f"Markdown changelog written to {out_dir / 'changelog.md'}")
        # Flush logs
        for handler in logger.handlers:
            handler.flush()

        # Publish to Confluence
        if create_or_update_confluence_page(f"{PROJECT_NAME} - Changelog - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", markdown_out):
            logger.info("Successfully stored changelog in Confluence")
        else:
            logger.warning("Failed to store changelog in Confluence")
        # Flush logs
        for handler in logger.handlers:
            handler.flush()

        # Render HTML
        html_out = render_html(
            markdown_content=markdown_out,
            project_name=PROJECT_NAME,
            page_url=None,
            commit_hash=os.getenv("COMMIT_HASH"),
            version=os.getenv("VERSION")
        )
        if html_out:
            (out_dir / "changelog.html").write_text(html_out, encoding="utf-8")
            logger.info(f"HTML changelog written to {out_dir / 'changelog.html'}")
        else:
            logger.warning("Skipping HTML changelog due to rendering failure")
        # Flush logs
        for handler in logger.handlers:
            handler.flush()

        # Ensure files are written
        os.sync()
        logger.info("Completed changelog generation, syncing files")
        # Small delay to ensure file writes
        import time
        time.sleep(1)

        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        # Ensure logs are flushed before exiting
        for handler in logger.handlers:
            handler.flush()
        sys.exit(1)

if __name__ == "__main__":
    main()