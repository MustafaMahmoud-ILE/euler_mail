"""
OpenRouter API client for Euler Mail AI enhancement.
Sends the plain-text draft and style preset to an LLM and returns
{"subject": str, "html_body": str} or {"error": str}.
"""
import json
import logging
import re
from typing import Optional

import requests
from pathlib import Path

from euler_mail.config.settings import OPENROUTER_API_URL
from euler_mail.ai.style_presets import UNIFIED_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Strip markdown code fences that some models add despite instructions
_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)
_JSON_EXTRACT_RE = re.compile(r"\{.*\}", re.DOTALL)


def enhance_draft(
    plain_text: str,
    style_name: str,
    model: str,
    api_key: str,
    timeout: int = 90,
    progress_callback=None,      # optional callable(str) for status messages
) -> dict:
    """
    Call OpenRouter to produce a polished HTML email from a plain-text draft.

    Returns:
        {"subject": str, "html_body": str}  — on success
        {"error": str}                       — on any failure (human-readable)
    """
    if not api_key or not api_key.strip():
        return {"error": "No OpenRouter API key provided. Please enter your key in the AI Enhance step."}

    user_message = (
        f"SELECTED STYLE: {style_name}\n\n"
        f"RAW DRAFT:\n"
        f"---\n{plain_text}\n---\n\n"
    )

    # Load the few-shot structural anchor example
    example_path = Path(__file__).parent / "examples" / f"{style_name}.html"
    if example_path.exists():
        example_html = example_path.read_text(encoding="utf-8")
        user_message += (
            "EXPECTED OUTPUT SHAPE (Use this exactly as a structural template):\n"
            f"```html\n{example_html}\n```\n"
        )

    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/eui/euler-mail",
        "X-Title": "Euler Mail",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": UNIFIED_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.25,
        "max_tokens": 6000,
    }

    if progress_callback:
        progress_callback(f"Sending request to {model}…")

    try:
        resp = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return {"error": "The AI request timed out after 90 seconds. Please try again."}
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        try:
            body = exc.response.json()
            msg = body.get("error", {}).get("message", str(exc))
        except Exception:
            msg = str(exc)
        return {"error": f"AI API error (HTTP {status}): {msg}"}
    except requests.exceptions.RequestException as exc:
        return {"error": f"Network error: {exc}"}

    if progress_callback:
        progress_callback("Parsing AI response…")

    try:
        data = resp.json()
        content: str = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, ValueError) as exc:
        return {"error": f"Unexpected API response structure: {exc}"}

    return _parse_content(content)


def _parse_content(content: str) -> dict:
    """Extract Subject and HTML from the plain text response."""
    lines = content.strip().split("\n")
    subject = "Euler Mail Update"
    
    # Try to find a line starting with "Subject:" or "1. Subject:"
    html_start_idx = 0
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("subject:"):
            subject = line.split(":", 1)[1].strip()
            html_start_idx = i + 1
            break
        elif line.strip().lower().startswith("1. subject:"):
            subject = line.split(":", 1)[1].strip()
            html_start_idx = i + 1
            break
        elif line.strip().startswith("<!DOCTYPE html>") or line.strip().startswith("<html"):
            html_start_idx = i
            break
            
    html_body = "\n".join(lines[html_start_idx:]).strip()
    
    # Strip markdown fences if the model still added them
    m = _FENCE_RE.search(html_body)
    if m:
        html_body = m.group(1).strip()
    elif html_body.startswith("```html"):
        html_body = html_body[7:]
        if html_body.endswith("```"):
            html_body = html_body[:-3]
    elif html_body.startswith("```"):
        html_body = html_body[3:]
        if html_body.endswith("```"):
            html_body = html_body[:-3]
            
    html_body = html_body.strip()
    
    if not html_body:
        return {
            "error": (
                "The AI returned an empty response or invalid format.\n"
                "Please try again or manually paste HTML into the editor."
            )
        }
        
    return {
        "subject": subject,
        "html_body": html_body,
    }
