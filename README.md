# Euler Mail

**A professional desktop mail-merge application for Egypt University of Informatics (EUI) staff.**

Built with Python 3.10 + PySide6. Authenticates each user with their own Google account, loads a recipient Excel sheet, composes a plain-text draft, enhances it into a styled HTML email with AI, and sends via the Gmail API with progress tracking and retry-on-failure.

---

## Quick Start

### 1 — Install Python 3.10.11
Download from https://python.org and install. Make sure to check "Add Python to PATH".

### 2 — Install dependencies

```cmd
cd "path\to\euler_mail"
pip install -r requirements.txt
```

### 3 — Configure Google OAuth (first time only)

> **If EUI staff use Google Workspace accounts (`@eui.edu.eg`)**:  
> In [Google Cloud Console → APIs & Services → OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent), set **User Type = Internal**. No verification is needed. All `@eui.edu.eg` accounts can sign in without any test-user list.

> **If staff use personal Gmail accounts**:  
> Set User Type = External. Add each staff member's email to the **Test Users** list (up to 100). They will see an "unverified app" warning but can still proceed. For production beyond 100 users, app verification is required.

*Note: The browser confirmation page shown after signing in is custom-branded for EUI. If you need to update the logo, colors, or text for this page in the future, edit `euler_mail/auth/oauth_success_page.py`.*

The `config/client_secret.json` file is already included in this repository (it's the **shared Desktop app** OAuth client — sharing the client ID/secret is normal and expected for installed app flows).

### 4 — Configure OpenRouter API key (for AI enhancement)

The `.env` file comes pre-seeded with the shared OpenRouter key. If you need to use your own:

1. Copy `.env.example` to `.env`
2. Set `OPENROUTER_API_KEY=your_key_here`

Or simply type your key in the AI Enhance step UI.

### 5 — Run the application

```cmd
python main.py
```

---

## Application Flow

| Step | What you do |
|------|-------------|
| 0 — Sign In | Click "Sign in with Google" → complete browser OAuth |
| 1 — Recipients | Load your `.xlsx` file with a `mail` or `email` column |
| 2 — Compose | Write your plain-text draft using `{ColumnName}` placeholders |
| 3 — AI Enhance | Pick a style, click Enhance → review/edit the generated HTML |
| 4 — Test & Send | Send a test copy to yourself, then send to all recipients |

---

## Excel File Format

- **Row 1**: Column headers (e.g., `Name`, `Mail`, `ID`, `Grade`, `Course`)
- **Required**: At least one column named `mail`, `email`, or a close variant
- **Placeholders**: In your draft, use `{ColumnName}` — e.g., `Dear {Name},` or `Your grade for {Course} is {Grade}.`

---

## Attachments

In Step 2, set an **Attachments Folder** and an **Attachment Pattern** like:

```
{ID}.pdf, {ID}_certificate.pdf, {ID}_QR.jpg
```

- `.pdf` files → sent as downloadable attachments
- Image files (`.jpg`, `.png`, etc.) referenced in the HTML body → embedded inline (CID)
- Missing files for a row → that row is flagged with an error but the batch continues

---

## AI Enhancement Styles

| Style | Use for |
|-------|---------|
| 🎓 Academic | Formal correspondence, grades, research communication |
| 📢 Announcement | Events, news, updates, invitations |
| ⚠️ Warning | Deadlines, non-compliance, urgent notices |
| ℹ️ Informative | Reports, instructions, FAQs, how-to guides |

---

## Token / Secret Files (gitignored)

| File | Description |
|------|-------------|
| `config/client_secret.json` | Shared Google OAuth client (already in repo; gitignored on clones that pull sensitive versions) |
| `%APPDATA%\EulerMail\token.json` | Per-user OAuth token (stored on your machine, never shared) |
| `.env` | OpenRouter API key (never commit) |

---

## Google Cloud OAuth Setup (for maintainers)

If you need to create a new OAuth client from scratch:

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project (or use an existing one)
3. Enable the **Gmail API** and the **Google People API (oauth2)**
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth Client ID**
5. Application type: **Desktop app**
6. Download the JSON → save as `config/client_secret.json`
7. Go to **OAuth consent screen**:
   - **Internal** (if EUI Workspace): Done. No verification needed.
   - **External**: Add scopes `gmail.send` + `userinfo.email`, fill in app info, add test users.

---

## Send Logs

After each send run, a CSV audit log is saved to:
- **Windows**: `%APPDATA%\EulerMail\send_logs\send_YYYYMMDD_HHMMSS.csv`

Columns: `timestamp, recipient, status, message_id, error`

---

## Requirements

```
PySide6>=6.6.0
google-auth>=2.27.0
google-auth-oauthlib>=1.2.0
google-api-python-client>=2.120.0
openpyxl>=3.1.2
requests>=2.31.0
keyring>=24.3.0
python-dotenv>=1.0.0
```

---

## Security Notes

- `token.json`, `client_secret.json`, and `.env` are all listed in `.gitignore`
- Each user's token is stored in their own OS user profile (`%APPDATA%\EulerMail\`) — never shared
- The app uses `gmail.send` scope only (minimal footprint — cannot read or delete emails)
- The client secret in a Desktop app OAuth flow is not truly secret; this is by design per Google's documentation

---

*Egypt University of Informatics — Euler Mail v1.0.0*
