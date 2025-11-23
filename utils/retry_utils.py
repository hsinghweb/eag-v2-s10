"""
Retry utilities for API calls with exponential backoff
"""

import time
import random
from google.genai.errors import ClientError, ServerError

def generate_with_retry(client, model, contents, config=None, retries=5, initial_delay=5):
    """
    Generates content with retry logic for 429 (Resource Exhausted) and 5xx errors.
    """
    delay = initial_delay
    for attempt in range(retries):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
        except Exception as e:
            # Check for 429 or 503/500
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "503" in error_str or "500" in error_str:
                if attempt == retries - 1:
                    raise e
                
                # Add jitter
                sleep_time = delay + random.uniform(0, 2)
                print(f"⚠️ API Limit/Error hit. Retrying in {sleep_time:.2f}s... (Attempt {attempt + 1}/{retries})")
                time.sleep(sleep_time)
                delay *= 2  # Exponential backoff
            else:
                raise e
    return None
