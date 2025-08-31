"""Configuration module for managing constants and settings used across the project.

These configurations aim to improve modularity and readability by consolidating settings
into a single location.
"""

from fake_useragent import UserAgent


# ============================
# Paths and Files
# ============================
DOWNLOAD_FOLDER = "Downloads"    # The folder where downloaded files will be stored.
URLS_FILE = "URLs.txt"           # The file containing the list of URLs to process.
SESSION_LOG = "session_log.txt"  # The file where session logs will be recorded.

# ============================
# Download Settings
# ============================
KB = 1024             # Number of bytes in a kilobyte.
CHUNK_SIZE = 16 * KB  # The size of each chunk when downloading files.

# ============================
# HTTP / Network
# ============================
# HTTP status codes
HTTP_RATE_LIMIT = 429

CONNECTION_TIMEOUT = 30        # Timeout duration for network requests (in seconds).
RATE_LIMIT_SLEEPING_TIME = 60  # Time to wait when rate-limited (in seconds).

# ============================
# User-Agent Rotator
# ============================
# Creating a user-agent rotator
USER_AGENT_ROTATOR = UserAgent()


# Helper functions
def prepare_user_agent() -> str:
    """Prepare a random user-agent string for making requests."""
    return str(USER_AGENT_ROTATOR.firefox)
