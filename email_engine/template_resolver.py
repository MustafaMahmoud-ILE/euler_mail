"""
Placeholder substitution and attachment resolution for Euler Mail.
"""
import re
import logging
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


class _SafeDict(dict):
    """Return the original {key} literal for any missing key."""
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def resolve(template: str, row_data: Dict[str, str]) -> str:
    """
    Replace {ColumnName} tokens in *template* with values from *row_data*.
    Any placeholder not found in row_data is left unchanged.
    """
    try:
        return template.format_map(_SafeDict(row_data))
    except (ValueError, KeyError):
        # Manual fallback for edge-case format strings
        result = template
        for key, value in row_data.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result


def resolve_attachment_specs(
    patterns_str: str,
    row_data: Dict[str, str],
    attachment_folder: Optional[Path],
    html_body: str = "",
) -> List[Dict]:
    """
    Resolve comma-separated attachment pattern strings for one recipient row.

    Returns a list of dicts:
      {
        "pattern":       str,   # original pattern e.g. "{ID}.pdf"
        "resolved_name": str,   # after substitution e.g. "12345.pdf"
        "path":          Path|None,
        "exists":        bool,
        "is_image":      bool,
        "is_inline":     bool,  # True if image AND referenced in html_body
        "cid":           str,   # sanitised CID for inline images
      }
    """
    if not patterns_str.strip():
        return []

    specs: List[Dict] = []
    for raw_pattern in patterns_str.split(","):
        raw_pattern = raw_pattern.strip()
        if not raw_pattern:
            continue

        resolved_name = resolve(raw_pattern, row_data)
        ext = Path(resolved_name).suffix.lower()
        is_image = ext in IMAGE_EXTENSIONS

        path: Optional[Path] = None
        exists = False
        if attachment_folder:
            path = attachment_folder / resolved_name
            exists = path.exists()

        # Is this image referenced inside the HTML body?
        is_inline = is_image and (
            resolved_name in html_body
        )
        # Build a CID safe for MIME headers (no spaces, no dots except before ext)
        cid = re.sub(r"[^a-zA-Z0-9_\-]", "_", Path(resolved_name).stem) if is_image else ""

        specs.append({
            "pattern": raw_pattern,
            "resolved_name": resolved_name,
            "path": path,
            "exists": exists,
            "is_image": is_image,
            "is_inline": is_inline,
            "cid": cid,
        })

    return specs


def substitute_inline_cids(html_body: str, specs: List[Dict]) -> str:
    """
    In the HTML body, replace every occurrence of an inline image's filename
    with its cid: URI so the final MIME message references the embedded image.
    e.g.  src="12345_QR.jpg"  →  src="cid:12345_QR"
    Also replaces bare filenames used inside cid: references.
    """
    for spec in specs:
        if spec["is_inline"] and spec["cid"]:
            name = spec["resolved_name"]
            cid = spec["cid"]
            # Replace src="filename" / src='filename' / cid:filename
            html_body = html_body.replace(f'src="{name}"', f'src="cid:{cid}"')
            html_body = html_body.replace(f"src='{name}'", f"src='cid:{cid}'")
            html_body = html_body.replace(name, f"cid:{cid}")
    return html_body


def resolve_absolute_inline_images(html_body: str) -> tuple[str, list[tuple[Path, str]]]:
    """
    Find all absolute Windows paths inside <img src="..."> tags or [IMAGE: ...] tags in the HTML.
    For each, verify the file exists (raise FileNotFoundError if not),
    generate a unique CID, replace the tag/src with cid:..., and return the
    modified HTML and a list of (Path, cid) tuples.
    """
    import re
    import hashlib
    
    inline_images: list[tuple[Path, str]] = []
    
    # Matches:
    # 1. src="C:\..." or src='C:\...'
    # 2. [IMAGE: C:\...] or [IMAGE : C:\...]
    # 3. <img>C:\...</img>
    pattern = r'(src=(["\'])([a-zA-Z]:\\[^"\']+|[a-zA-Z]:/[^"\']+)\2|\[IMAGE\s*:\s*([a-zA-Z]:\\[^\]]+|[a-zA-Z]:/[^\]]+)\]|<img>\s*([a-zA-Z]:\\[^<]+|[a-zA-Z]:/[^<]+)\s*</img>)'
    
    def replacer(match):
        is_src_format = bool(match.group(2))
        is_image_bracket = bool(match.group(4))
        
        if is_src_format:
            quote = match.group(2)
            raw_path = match.group(3)
        elif is_image_bracket:
            raw_path = match.group(4).strip()
        else:
            raw_path = match.group(5).strip()
            
        path_obj = Path(raw_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Inline image not found: {raw_path}")
            
        path_hash = hashlib.md5(str(path_obj.absolute()).encode()).hexdigest()[:8]
        cid = f"img_{path_obj.stem}_{path_hash}"
        cid = re.sub(r"[^a-zA-Z0-9_\-]", "_", cid)
        
        inline_images.append((path_obj, cid))
        
        if is_src_format:
            return f'src={quote}cid:{cid}{quote}'
        else:
            # Wrap the [IMAGE: ...] pseudo-tag in a styled HTML image
            return f'<img src="cid:{cid}" alt="Embedded Image" style="max-width: 100%; height: auto; display: block; margin: 16px auto; border-radius: 8px;">'
            
    resolved_html = re.sub(pattern, replacer, html_body)
    return resolved_html, inline_images
