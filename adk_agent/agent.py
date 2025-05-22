import os
import sys
import logging
from pathlib import Path
from requests.auth import HTTPBasicAuth
import requests

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

def validate_env_vars():
    """Ensure required environment variables exist."""
    required = ["CONF_DOMAIN", "CONF_SPACE", "CONF_USER", "CONF_TOKEN", "PROJECT_NAME", "VERSION", "COMMIT_MSG"]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        logger.error("Missing env vars: %s", ", ".join(missing))
        sys.exit(1)
    logger.info("All required environment variables are set.")

def publish_commit_message_to_confluence(domain, space, auth, project, version, commit_msg):
    """Publish only the commit message."""
    title = f"{project} – {version}"
    url = f"https://{domain}/rest/api/content"
    payload = {
        "type": "page",
        "title": title,
        "space": {"key": space},
        "body": {
            "storage": {
                "value": commit_msg,
                "representation": "storage"
            }
        }
    }
    headers = {"Content-Type": "application/json"}
    logger.info("Publishing commit message to Confluence page '%s'", title)
    try:
        resp = requests.post(url, json=payload, headers=headers, auth=auth)
        resp.raise_for_status()
        page_id = resp.json().get("id")
        page_url = f"https://{domain}/pages/viewpage.action?pageId={page_id}"
        logger.info("Published successfully: %s", page_url)
        return page_url
    except Exception as e:
        logger.error("Failed to publish: %s", e)
        return None

def main():
    validate_env_vars()

    # Read variables
    domain     = os.getenv("CONF_DOMAIN")
    space      = os.getenv("CONF_SPACE")
    user       = os.getenv("CONF_USER")
    token      = os.getenv("CONF_TOKEN")
    project    = os.getenv("PROJECT_NAME")
    version    = os.getenv("VERSION")
    commit_msg = os.getenv("COMMIT_MSG")

    # Publish
    auth = HTTPBasicAuth(user, token)
    page_url = publish_commit_message_to_confluence(
        domain, space, auth, project, version, commit_msg
    )

    if page_url:
        logger.info("Done. Page URL: %s", page_url)
        sys.exit(0)
    else:
        logger.error("Exiting with failure.")
        sys.exit(1)

if __name__ == "__main__":
    main()
