"""Configuration module for managing constants and settings used across the project.

These configurations aim to improve modularity and readability by consolidating settings
into a single location.
"""

from fake_useragent import UserAgent

DOWNLOAD_FOLDER = "Downloads"    # The folder where downloaded files will be stored.
FILE = "URLs.txt"                # The name of the file containing URLs.
SESSION_LOG = "session_log.txt"  # The file where session logs will be recorded.

KB = 1024             # Number of bytes in a kilobyte.
CHUNK_SIZE = 16 * KB  # The size of each chunk when downloading files.

CONNECTION_TIMEOUT = 30        # Timeout duration (in seconds) for network requests.
RATE_LIMIT_SLEEPING_TIME = 60  # Time (in seconds) to wait when rate-limited.

# HTTP status codes.
HTTP_RATE_LIMIT = 429

# Creating a user-agent rotator
USER_AGENT_ROTATOR = UserAgent(use_external_data=True)


def prepare_user_agent() -> str:
    """Prepare a random user-agent string for making requests."""
    return str(USER_AGENT_ROTATOR.firefox)
