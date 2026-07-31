"""
Custom OAuth Success and Error pages for Euler Mail.
Replaces the default text-only response from google-auth-oauthlib.
"""

import wsgiref.util
import google_auth_oauthlib.flow

EULER_MAIL_SUCCESS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign-in Successful - Euler Mail</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #F7F8FA;
            color: #1B2A4A;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }
        .card {
            background: #FFFFFF;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            text-align: center;
            max-width: 400px;
            width: 90%;
            border: 1px solid #E2E5EA;
        }
        .icon {
            width: 64px;
            height: 64px;
            background: #1B2A4A;
            color: #FFFFFF;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            margin: 0 auto 20px auto;
        }
        h1 {
            font-size: 24px;
            margin: 0 0 10px 0;
        }
        p {
            color: #6B6F76;
            line-height: 1.5;
            margin: 0 0 20px 0;
        }
        .divider {
            height: 2px;
            background: #C9A227;
            margin: 20px 0;
            border: none;
        }
        .footer {
            font-size: 12px;
            color: #8A9BB0;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">✓</div>
        <h1>Sign-in Successful</h1>
        <p>You have successfully authenticated with Google. You may now close this browser tab and return to the Euler Mail application.</p>
        <hr class="divider">
        <div class="footer">Euler Mail &middot; Egypt University of Informatics</div>
    </div>
    <script>
        setTimeout(function() {
            try {
                window.close();
            } catch (e) {
                // Ignore if browser blocks script from closing tab
            }
        }, 3000);
    </script>
</body>
</html>"""

EULER_MAIL_ERROR_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign-in Failed - Euler Mail</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #FCEEED;
            color: #B3261E;
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }
        .card {
            background: #FFFFFF;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(179, 38, 30, 0.1);
            text-align: center;
            max-width: 400px;
            width: 90%;
            border: 1px solid #EFC9C6;
            border-top: 4px solid #B3261E;
        }
        .icon {
            width: 64px;
            height: 64px;
            background: #B3261E;
            color: #FFFFFF;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            margin: 0 auto 20px auto;
        }
        h1 {
            font-size: 24px;
            margin: 0 0 10px 0;
            color: #B3261E;
        }
        p {
            color: #6B6F76;
            line-height: 1.5;
            margin: 0 0 20px 0;
        }
        .divider {
            height: 2px;
            background: #E0A11C;
            margin: 20px 0;
            border: none;
        }
        .footer {
            font-size: 12px;
            color: #8A9BB0;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">✗</div>
        <h1>Sign-in Failed</h1>
        <p>Authentication was cancelled or failed. Please close this browser tab and try again from the Euler Mail application.</p>
        <hr class="divider">
        <div class="footer">Euler Mail &middot; Egypt University of Informatics</div>
    </div>
    <script>
        setTimeout(function() {
            try {
                window.close();
            } catch (e) {
                // Ignore if browser blocks script from closing tab
            }
        }, 3000);
    </script>
</body>
</html>"""


class _EulerMailRedirectWSGIApp(object):
    """WSGI app to handle the authorization redirect.
    Serves branded HTML instead of the default text response.
    """

    def __init__(self, success_message):
        # We ignore success_message since we use our custom HTML
        self.last_request_uri = None
        self._success_message = success_message

    def __call__(self, environ, start_response):
        start_response("200 OK", [("Content-type", "text/html; charset=utf-8")])
        self.last_request_uri = wsgiref.util.request_uri(environ)
        
        # If the user cancels or an error occurs, Google redirects with ?error=access_denied
        if "error=" in self.last_request_uri:
            return [EULER_MAIL_ERROR_HTML.encode("utf-8")]
            
        return [EULER_MAIL_SUCCESS_HTML.encode("utf-8")]


def patch_oauth_success_page():
    """Swap the default _RedirectWSGIApp with our custom branded version."""
    google_auth_oauthlib.flow._RedirectWSGIApp = _EulerMailRedirectWSGIApp
