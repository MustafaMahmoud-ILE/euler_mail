"""
HTML safety wrapper — ensures the AI output is a full valid HTML document.
"""


def wrap_html(html: str) -> str:
    """
    If *html* is already a full document (starts with <!DOCTYPE or <html),
    return it unchanged.  Otherwise wrap it in a minimal responsive shell.
    """
    stripped = html.strip()
    if stripped.lower().startswith("<!doctype") or stripped.lower().startswith("<html"):
        return html

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>Email</title>
  <style>
    body {{ margin:0; padding:0; background:#f4f4f4; }}
    @media only screen and (max-width:600px) {{
      .email-container {{ width:100% !important; }}
    }}
  </style>
</head>
<body style="margin:0;padding:0;background-color:#f4f4f4;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#f4f4f4;">
    <tr>
      <td align="center" style="padding:24px 16px;">
        <table class="email-container" role="presentation" width="600" cellpadding="0"
               cellspacing="0" border="0" style="max-width:600px;width:100%;background:#ffffff;">
          <tr>
            <td style="padding:24px 32px;">
              {stripped}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
