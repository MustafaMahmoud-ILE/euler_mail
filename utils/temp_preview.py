"""
Temp-file HTML preview — writes HTML to a temporary file and opens it
in the user's default system browser via webbrowser.open().
"""
import logging
import tempfile
import webbrowser
from pathlib import Path

logger = logging.getLogger(__name__)

_PREVIEW_FILE: Path | None = None


def open_preview(html: str) -> None:
    """
    Write *html* to a temp file and open it in the default browser.
    Reuses the same temp file path on repeated calls to avoid cluttering %TEMP%.
    """
    global _PREVIEW_FILE

    try:
        if _PREVIEW_FILE is None:
            tmp = tempfile.NamedTemporaryFile(
                suffix=".html",
                prefix="euler_mail_preview_",
                delete=False,
            )
            _PREVIEW_FILE = Path(tmp.name)
            tmp.close()

        _PREVIEW_FILE.write_text(html, encoding="utf-8")
        webbrowser.open(_PREVIEW_FILE.as_uri())
        logger.debug(f"Preview opened: {_PREVIEW_FILE}")

    except Exception as exc:
        logger.error(f"Failed to open preview: {exc}")
        raise RuntimeError(f"Could not open preview in browser:\n{exc}") from exc
