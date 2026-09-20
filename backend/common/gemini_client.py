import asyncio
import os
import re
from typing import Optional

# gemini-2.5-flash was retired by Google ("no longer available to new users") - this is the
# vendor-recommended replacement as of the retirement notice.
DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"


def resolve_gemini_model(explicit: Optional[str] = None) -> str:
    """Resolves the Gemini model name from an explicit override, the GEMINI_MODEL env var, or the default."""
    return explicit or os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)


def strip_markdown_json_fences(text: str) -> str:
    """Strips a leading/trailing markdown code fence (```json ... ```) Gemini sometimes wraps JSON in."""
    if text.startswith("```"):
        text = re.sub(r'^```[a-z]*\n', '', text)
        text = re.sub(r'\n```$', '', text)
    return text


async def generate_content_async(
    prompt: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    timeout: Optional[float] = 15.0,
) -> str:
    """
    Shared async wrapper around the synchronous google-genai SDK call: builds the client, runs
    generate_content in a worker thread (the SDK has no native async API), enforces a timeout
    when one is given, and returns the response text with markdown fences stripped.

    Raises asyncio.TimeoutError on timeout, or whatever exception the underlying SDK call raises.
    """
    resolved_model = resolve_gemini_model(model)

    def _sync_call() -> str:
        from google import genai
        client = genai.Client(api_key=api_key) if api_key else genai.Client()
        response = client.models.generate_content(model=resolved_model, contents=prompt)
        return strip_markdown_json_fences(response.text.strip())

    if timeout is not None:
        return await asyncio.wait_for(asyncio.to_thread(_sync_call), timeout=timeout)
    return await asyncio.to_thread(_sync_call)
