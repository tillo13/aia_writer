import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

# Cache for blocked words (refreshed periodically)
_blocked_words_cache = None
_blocked_words_cache_time = None


def get_blocked_words():
    """
    Get blocked words from LDNOOBW repository (Shutterstock's list).
    Caches the result for 1 hour.
    """
    global _blocked_words_cache, _blocked_words_cache_time

    # Check cache (1 hour TTL)
    if _blocked_words_cache and _blocked_words_cache_time:
        if time.time() - _blocked_words_cache_time < 3600:
            return _blocked_words_cache

    # Get any custom words from environment
    env_words = os.getenv('CUSTOM_BLOCKED_WORDS', '')
    custom_words = [word.strip().lower() for word in env_words.split(',') if word.strip()]

    try:
        # TinyURL redirects to LDNOOBW repository on GitHub
        url = "https://tinyurl.com/35wba3d6"
        response = requests.get(url, timeout=5, allow_redirects=True)
        if response.status_code == 200:
            # Parse the word list (one word per line)
            ldnoobw_words = [word.strip().lower() for word in response.text.split('\n') if word.strip()]
            combined = list(set(custom_words + ldnoobw_words))
            _blocked_words_cache = combined
            _blocked_words_cache_time = time.time()
            logger.info(f"Loaded {len(combined)} blocked words for content filter")
            return combined
    except Exception as e:
        logger.warning(f"Failed to fetch LDNOOBW word list: {e}")

    # Fallback to custom words only
    _blocked_words_cache = custom_words if custom_words else []
    _blocked_words_cache_time = time.time()
    return _blocked_words_cache


def check_content_filter(message):
    """
    Check if message contains disallowed content.

    Returns:
        (is_allowed, error_message) - If allowed, error_message is None
    """
    try:
        blocked_phrases = get_blocked_words()
        if not blocked_phrases:
            return True, None

        message_lower = message.lower()

        # Check for blocked words
        for phrase in blocked_phrases:
            if phrase and phrase in message_lower:
                logger.info(f"[FILTER] BLOCKED message containing blocked content")
                return False, "Please keep your topic professional. Try a different subject."

        return True, None
    except Exception as e:
        logger.error(f"Content filter error: {e}")
        return True, None  # Fail open
