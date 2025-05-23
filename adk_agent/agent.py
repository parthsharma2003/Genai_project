import os
import sys
import logging
from pathlib import Path
import markdown
from datetime import date
import google.generativeai as genai
from requests.auth import HTTPBasicAuth
import requests
from jinja2 import Environment, FileSystemLoader, Template
from tenacity import retry, stop_after_attempt, wait_exponential

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

current_date = date.today().strftime("%Y-%m-%d")

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
    
    # Get branch name from environment
    branch_name = os.getenv("BRANCH_NAME", "unknown")
    event_type = os.getenv("EVENT_TYPE", "push")
    
    return f"""
    You are an AI assistant tasked with generating a changelog for the {project_name} project.
    Version: {version}
    Branch: {branch_name}
    Event Type: {event_type}
    Commit Message: {commit_msg}
    Commit Diff:
    ```
    {commit_diff}
    ```

    Generate a structured changelog with the following sections, using emojis and symbols:
    1. 📅 Date: {current_date}
    2. 🌿 Branch: The branch where changes were made
    3. ✨ What's New: New features and improvements
    4. 🐛 Bug Fixes: Any bug fixes or issues resolved
    5. 🔄 How to Upgrade: Instructions for upgrading to this version
    6. ⚠️ Deprecated: Any deprecated features or functionality

    For each section:
    - Use clear, concise bullet points
    - Focus on user-facing changes
    - Include relevant technical details where necessary
    - If a section has no changes, mark it as "No changes in this version"
    - Use appropriate emojis for different types of changes:
      * ✨ for new features
      * 🐛 for bug fixes
      * 🔧 for improvements
      * 🚀 for performance changes
      * 📝 for documentation updates
      * 🔒 for security updates
      * ⚠️ for deprecations
      * 🔄 for upgrade instructions

    Format the output in Markdown with proper headers and sections.
    Example format:
    # 📅 Date: YYYY-MM-DD

    ## 🌿 Branch: branch-name
    Changes made in this branch

    ## ✨ What's New
    - ✨ New feature 1
    - 🔧 Improvement 1

    ## 🐛 Bug Fixes
    - 🐛 Fixed issue 1
    - 🔧 Resolved problem 2

    ## 🔄 How to Upgrade
    - Step 1
    - Step 2

    ## ⚠️ Deprecated
    - Feature X is now deprecated
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
    
    # Validate domain
    if not domain:
        errors.append("CONF_DOMAIN is not set")
    elif not domain.endswith('atlassian.net'):
        errors.append("CONF_DOMAIN should end with 'atlassian.net'")
    
    # Validate space key
    if not space:
        errors.append("CONF_SPACE is not set")
    elif not space.startswith('~') and len(space) > 10:  # Allow longer keys for personal spaces
        errors.append(f"CONF_SPACE appears to be too long ({len(space)} chars). Space keys are typically 2-10 characters.")
    
    # Validate credentials
    if not user:
        errors.append("CONF_USER is not set")
    elif '@' not in user:
        errors.append("CONF_USER should be an email address")
    
    if not token:
        errors.append("CONF_TOKEN is not set")
    
    return errors

def get_existing_page(domain, space, auth):
    """Get the existing changelog page or create a new one if it doesn't exist."""
    if not domain.startswith('https://'):
        domain = f"https://{domain}"
    if domain.endswith('/'):
        domain = domain.rstrip('/')
    if not domain.endswith('/wiki'):
        domain += '/wiki'
    
    # Search for the changelog page
    search_url = f"{domain}/rest/api/content"
    params = {
        'type': 'page',
        'spaceKey': space,
        'title': 'Changelog',
        'expand': 'body.storage,version'
    }
    
    try:
        response = requests.get(search_url, params=params, auth=auth)
        response.raise_for_status()
        results = response.json()['results']
        
        if results:
            return results[0]  # Return the first matching page
        return None
    except Exception as e:
        logger.error(f"Error searching for existing page: {str(e)}")
        return None

def publish_to_confluence(title, html, space, domain, auth):
    """Publish content to Confluence, appending to existing page or creating new one."""
    logger.info(f"Attempting to publish to Confluence: {title}")
    
    # Validate settings first
    errors = validate_confluence_settings(domain, space, auth.username, auth.password)
    if errors:
        error_msg = "\n".join(errors)
        logger.error(f"Confluence settings validation failed:\n{error_msg}")
        print(f"\n=== Confluence Settings Validation Failed ===")
        print(error_msg)
        print(f"===========================================\n")
        return None
    
    # Ensure domain is properly formatted
    if not domain.startswith('https://'):
        domain = f"https://{domain}"
    if domain.endswith('/'):
        domain = domain.rstrip('/')
    if not domain.endswith('/wiki'):
        domain += '/wiki'
    
    # Get existing page or create new one
    existing_page = get_existing_page(domain, space, auth)
    url = f"{domain}/rest/api/content"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    if existing_page:
        # Append to existing page
        current_content = existing_page['body']['storage']['value']
        new_content = f"{current_content}\n\n---\n\n{html}"
        
        # Get current version number, default to 1 if not found
        try:
            version = existing_page.get('version', {}).get('number', 1) + 1
        except (KeyError, AttributeError):
            version = 2  # If version info is missing, start with version 2
        
        data = {
            "version": {"number": version},
            "title": "Changelog",
            "type": "page",
            "body": {
                "storage": {
                    "value": new_content,
                    "representation": "storage"
                }
            }
        }
        
        update_url = f"{url}/{existing_page['id']}"
        try:
            response = requests.put(update_url, json=data, headers=headers, auth=auth)
            response.raise_for_status()
            page_url = f"{domain}/pages/viewpage.action?pageId={existing_page['id']}"
            logger.info(f"Successfully updated Confluence page: {page_url}")
            print(f"\n=== Confluence Page Updated ===")
            print(f"Title: Changelog")
            print(f"URL: {page_url}")
            print(f"Space: {space}")
            print(f"==============================\n")
            return page_url
        except Exception as e:
            logger.error(f"Failed to update existing page: {str(e)}")
            return None
    else:
        # Create new page
        data = {
            "type": "page",
            "title": "Changelog",
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
            page_url = f"{domain}/pages/viewpage.action?pageId={page_id}"
            logger.info(f"Successfully created new Confluence page: {page_url}")
            print(f"\n=== New Confluence Page Created ===")
            print(f"Title: Changelog")
            print(f"URL: {page_url}")
            print(f"Space: {space}")
            print(f"==============================\n")
            return page_url
        except Exception as e:
            logger.error(f"Confluence publishing failed: {str(e)}")
            logger.error(f"Request URL: {url}")
            logger.error(f"Request data: {data}")
            print(f"\n=== Confluence Publishing Failed ===")
            print(f"Error: {str(e)}")
            print(f"Domain format: {domain.split('.')[-2:] if '.' in domain else 'Invalid format'}")
            print(f"Space key length: {len(space)} characters")
            print(f"Title: Changelog")
            print(f"API Endpoint: /rest/api/content")
            print(f"Full URL: {url}")
            print(f"===================================\n")
            return None


def render_html(markdown_content, project_name, page_url, commit_hash, version):
    """Render the changelog in HTML format."""
    # Get branch name from environment
    branch_name = os.getenv("BRANCH_NAME", "unknown")
    event_type = os.getenv("EVENT_TYPE", "push")
    
    # Convert markdown to HTML
    html_content = markdown.markdown(markdown_content)
    
    # Create HTML template with branch information
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{project_name} Changelog</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            .branch-info {{
                background-color: #f0f0f0;
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
            }}
            .event-type {{
                color: #666;
                font-style: italic;
            }}
            h1, h2, h3 {{
                color: #333;
            }}
            ul {{
                list-style-type: none;
                padding-left: 20px;
            }}
            li {{
                margin: 5px 0;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 10px;
                border-top: 1px solid #ccc;
                font-size: 0.9em;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="branch-info">
            <strong>Branch:</strong> {branch_name}
            <span class="event-type">({event_type})</span>
        </div>
        {html_content}
        <div class="footer">
            <p>Version: {version}</p>
            <p>Commit: {commit_hash}</p>
            <p>Project: {project_name}</p>
        </div>
    </body>
    </html>
    """
    
    return html_template

def main():
    """Main function to generate and publish changelog."""
    try:
        # Validate environment variables
        logger.info("Starting main function")
        validate_env_vars()
        logger.info("Environment variables validated successfully")

        # Build prompt and generate changelog
        logger.info("Building changelog prompt")
        prompt = build_prompt(
            commit_msg=os.getenv("COMMIT_MSG"),
            commit_diff=os.getenv("COMMIT_DIFF"),
            project_name=os.getenv("PROJECT_NAME"),
            version=os.getenv("VERSION"),
            changelog_format=os.getenv("CHANGELOG_FORMAT")
        )
        logger.info("Prompt built successfully")

        logger.info("Generating changelog with LLM")
        markdown_out = generate_changelog(prompt)
        logger.info("Changelog generated successfully")

        # Save Markdown output
        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True, parents=True)
        (out_dir / "changelog.md").write_text(markdown_out, encoding="utf-8")
        logger.info(f"Markdown changelog written to {out_dir / 'changelog.md'}")
        
        # Flush logs
        for handler in logger.handlers:
            handler.flush()

        # Publish to Confluence
        logger.info("Preparing to publish to Confluence")
        auth = HTTPBasicAuth(os.getenv("CONF_USER"), os.getenv("CONF_TOKEN"))
        logger.info("Auth object created")
        
        try:
            page_url = publish_to_confluence(
                title=f"{os.getenv('PROJECT_NAME')} – {os.getenv('VERSION')}",
                html=markdown.markdown(markdown_out),
                space=os.getenv("CONF_SPACE"),
                domain=os.getenv("CONF_DOMAIN"),
                auth=auth
            )
            logger.info("Confluence publishing completed")
        except Exception as e:
            logger.error(f"Error during Confluence publishing: {str(e)}")
            logger.error("Full error details:", exc_info=True)
            raise

        # Flush logs
        for handler in logger.handlers:
            handler.flush()

        # Render HTML
        logger.info("Rendering HTML output")
        try:
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
        except Exception as e:
            logger.error(f"Error during HTML rendering: {str(e)}")
            logger.error("Full error details:", exc_info=True)
            raise

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
        logger.error("Full error details:", exc_info=True)
        # Ensure logs are flushed before exiting
        for handler in logger.handlers:
            handler.flush()
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error("Full error details:", exc_info=True)
        sys.exit(1)