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
from bs4 import BeautifulSoup
from datetime import datetime

# Set up logging
log_dir = Path("logs")
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
    Version: {version}
    Commit Message: {commit_msg}
    Commit Diff:
    ```
    {commit_diff}
    ```

    Generate a structured changelog with the following sections:
    - What's New: New features and improvements
    - Bug Fixes: Any bug fixes or issues resolved
    - How to Upgrade: Instructions for upgrading to this version
    - Deprecated: Any deprecated features or functionality

    For each section:
    - Use clear, concise bullet points
    - Focus on user-facing changes
    - Include relevant technical details where necessary
    - If a section has no changes, mark it as "No changes in this version"

    Output the changelog in Markdown format with proper headers and sections. Do not include the date or version in the output.
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

def validate_confluence_settings(domain, space, user, token):
    """Validate Confluence settings before attempting to publish."""
    errors = []
    if not domain:
        errors.append("CONF_DOMAIN is not set")
    elif not domain.endswith('atlassian.net'):
        errors.append("CONF_DOMAIN should end with 'atlassian.net'")
    if not space:
        errors.append("CONF_SPACE is not set")
    elif not space.startswith('~') and len(space) > 10:
        errors.append(f"CONF_SPACE appears to be too long ({len(space)} chars). Space keys are typically 2-10 characters.")
    if not user:
        errors.append("CONF_USER is not set")
    elif '@' not in user:
        errors.append("CONF_USER should be an email address")
    if not token:
        errors.append("CONF_TOKEN is not set")
    return errors

def publish_to_confluence(title, new_entry_html, space, domain, auth):
    """Publish or update changelog to Confluence."""
    logger.info(f"Attempting to publish to Confluence: {title}")

    errors = validate_confluence_settings(domain, space, auth.username, auth.password)
    if errors:
        error_msg = "\n".join(errors)
        logger.error(f"Confluence settings validation failed:\n{error_msg}")
        print(f"\n=== Confluence Settings Validation Failed ===\n{error_msg}\n=======================================\n")
        return None

    if not domain.startswith('https://'):
        domain = f"https://{domain}"
    if domain.endswith('/'):
        domain = domain.rstrip('/')
    if not domain.endswith('/wiki'):
        domain += '/wiki'

    # Search for existing page
    search_url = f"{domain}/rest/api/content?title={title}&spaceKey={space}"
    response = requests.get(search_url, auth=auth)
    
    if response.status_code == 200 and len(response.json()['results']) > 0:
        # Page exists, update it
        page = response.json()['results'][0]
        page_id = page['id']
        current_version = page['version']['number']
        existing_content = page['body']['storage']['value']
        
        # Parse and update content
        soup = BeautifulSoup(existing_content, 'html.parser')
        entries_div = soup.find('div', class_='changelog-entries')
        if entries_div:
            new_entry_soup = BeautifulSoup(new_entry_html, 'html.parser')
            entries_div.insert(0, new_entry_soup)  # Prepend new entry
            new_content = str(soup)
        else:
            new_content = new_entry_html + existing_content  # Fallback prepend
        
        # Update page
        update_url = f"{domain}/rest/api/content/{page_id}"
        update_data = {
            "version": {"number": current_version + 1},
            "title": title,
            "type": "page",
            "body": {
                "storage": {
                    "value": new_content,
                    "representation": "storage"
                }
            }
        }
        update_response = requests.put(update_url, json=update_data, auth=auth)
        update_response.raise_for_status()
        logger.info("Updated existing Confluence page")
        page_url = f"{domain}/pages/viewpage.action?pageId={page_id}"
    else:
        # Page doesn't exist, create it
        create_url = f"{domain}/rest/api/content"
        create_data = {
            "type": "page",
            "title": title,
            "space": {"key": space},
            "body": {
                "storage": {
                    "value": f'<h1>{title}</h1><div class="changelog-entries">{new_entry_html}</div>',
                    "representation": "storage"
                }
            }
        }
        create_response = requests.post(create_url, json=create_data, auth=auth)
        create_response.raise_for_status()
        page_id = create_response.json()['id']
        page_url = f"{domain}/pages/viewpage.action?pageId={page_id}"
        logger.info("Created new Confluence page")

    print(f"\n=== Confluence Page Updated ===\nTitle: {title}\nURL: {page_url}\nSpace: {space}\n==============================\n")
    return page_url

def render_html(markdown_content, project_name, page_url, commit_hash, version):
    """Render HTML using Jinja2 template or fallback."""
    logger.info("Rendering HTML output")
    try:
        env = Environment(loader=FileSystemLoader("."))
        template = env.get_template("changelog_template.html")
        html_output = template.render(
            project_name=project_name,
            markdown_content=markdown.markdown(markdown_content, extensions=['tables', 'fenced_code']),
            page_url=page_url or "Not published",
            commit_hash=commit_hash,
            current_date=version
        )
        logger.info("HTML rendered successfully from file")
        return html_output
    except Exception as e:
        logger.warning(f"HTML rendering failed, using fallback template: {str(e)}")
        fallback_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{ project_name }} Changelog</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; color: #333; }
                .changelog { max-width: 800px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                h1 { color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }
                h2 { color: #34495e; margin-top: 30px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
                .meta { color: #666; font-size: 0.9em; background: #f8f9fa; padding: 15px; border-radius: 4px; margin-top: 20px; }
                ul { padding-left: 20px; }
                li { margin-bottom: 8px; }
                code { background: #f8f9fa; padding: 2px 4px; border-radius: 3px; font-family: monospace; }
                pre { background: #f8f9fa; padding: 15px; border-radius: 4px; overflow-x: auto; }
            </style>
        </head>
        <body>
            <div class="changelog">
                <h1>{{ project_name }} Changelog</h1>
                {{ markdown_content | safe }}
                <div class="meta">
                    <p><strong>Confluence Page:</strong> {{ page_url }}</p>
                    {% if commit_hash %}
                    <p><strong>Commit:</strong> {{ commit_hash }}</p>
                    {% endif %}
                    <p><strong>Generated:</strong> {{ current_date }}</p>
                </div>
            </div>
        </body>
        </html>
        """
        template = Template(fallback_template)
        html_output = template.render(
            project_name=project_name,
            markdown_content=markdown.markdown(markdown_content, extensions=['tables', 'fenced_code']),
            page_url=page_url or "Not published",
            commit_hash=commit_hash,
            current_date=version
        )
        logger.info("HTML rendered using fallback template")
        return html_output

def main():
    """Main function to generate and publish changelog."""
    try:
        validate_env_vars()
        prompt = build_prompt(
            commit_msg=os.getenv("COMMIT_MSG"),
            commit_diff=os.getenv("COMMIT_DIFF"),
            project_name=os.getenv("PROJECT_NAME"),
            version=os.getenv("VERSION"),
            changelog_format=os.getenv("CHANGELOG_FORMAT")
        )
        markdown_out = generate_changelog(prompt)

        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True, parents=True)
        (out_dir / "changelog.md").write_text(markdown_out, encoding="utf-8")
        logger.info(f"Markdown changelog written to {out_dir / 'changelog.md'}")
        for handler in logger.handlers:
            handler.flush()

        # Create new entry with version and date
        current_date = datetime.now().strftime("%Y-%m-%d")
        version = os.getenv("VERSION")
        new_entry_md = f"## Version {version} - {current_date}\n\n{markdown_out}"
        new_entry_html = f'<div class="changelog-entry">{markdown.markdown(new_entry_md, extensions=["tables", "fenced_code"])}</div>'

        auth = HTTPBasicAuth(os.getenv("CONF_USER"), os.getenv("CONF_TOKEN"))
        project_name = os.getenv("PROJECT_NAME")
        page_url = publish_to_confluence(
            title=f"{project_name} – Changelog",
            new_entry_html=new_entry_html,
            space=os.getenv("CONF_SPACE"),
            domain=os.getenv("CONF_DOMAIN"),
            auth=auth
        )
        for handler in logger.handlers:
            handler.flush()

        html_out = render_html(
            markdown_content=markdown_out,
            project_name=project_name,
            page_url=page_url,
            commit_hash=os.getenv("COMMIT_HASH"),
            version=version
        )
        if html_out:
            (out_dir / "changelog.html").write_text(html_out, encoding="utf-8")
            logger.info(f"HTML changelog written to {out_dir / 'changelog.html'}")
        else:
            logger.warning("Skipping HTML changelog due to rendering failure")
        for handler in logger.handlers:
            handler.flush()

        os.sync()
        logger.info("Completed changelog generation, syncing files")
        import time
        time.sleep(1)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        for handler in logger.handlers:
            handler.flush()
        sys.exit(1)

if __name__ == "__main__":
    main()