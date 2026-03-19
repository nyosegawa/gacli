# gacli

[日本語](./README.ja.md)

Simple Google Analytics 4 CLI with multi-profile support. No gcloud required.

## Install

```bash
uv tool install --from . gacli
```

## Setup

### 1. Create OAuth Client ID

1. Enable the **Google Analytics Data API** ([link](https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com))
2. Create an OAuth client ID ([link](https://console.cloud.google.com/auth/clients/create)) > Application type: **Desktop app**
3. Download the JSON and save it as:

```
~/.config/gacli/client_secret.json
```

### 2. Authenticate

```bash
gacli auth
```

A browser opens. Log in with the Google account that has access to your GA4 property.

### 3. Set your property ID

Find your GA4 property ID in [Google Analytics](https://analytics.google.com/) > Admin > Property Settings.

```bash
gacli config -p <PROPERTY_ID>
```

## Usage

```bash
gacli summary          # Daily PV/users/sessions (last 7 days)
gacli summary -d 30    # Last 30 days
gacli pages            # Top pages by PV
gacli pages -n 20      # Top 20 pages
gacli realtime         # Realtime active users
```

### JSON Output

All data commands support `--json` for structured output. JSON mode is auto-enabled when piped.

```bash
gacli --json summary
gacli pages | jq '.rows[] | select(.pagePath | contains("/posts/"))'
```

## Example: Claude Code Agent Skill

gacli ships with a [Claude Code Agent Skill](./skills/google-analytics/SKILL.md). Once linked, you can ask your coding agent about analytics in natural language:

```
❯ How was today's traffic?

⏺ Skill(google-analytics)
  ⎿  Successfully loaded skill

⏺ Bash(gacli summary -d 1)
⏺ Bash(gacli pages -d 1 -n 10)
⏺ Bash(gacli realtime)

⏺ Today's access summary (3/19):

  | Metric   | Value |
  |----------|-------|
  | PV       | 66    |
  | Users    | 68    |
  | Sessions | 68    |

  Top pages:
  1. /posts/docs-in-agent-era/ — 19 PV
  2. /posts/harness-engineering-best-practices-2026/ — 19 PV
  3. /posts/japanese-handwriting-ocr-comparison/ — 7 PV

  Realtime: 261 active users (247 from Japan)
```

To enable:

```bash
ln -s /path/to/gacli/skills/google-analytics ~/.claude/skills/google-analytics
```

## Multi-Profile

Manage multiple sites or Google accounts with profiles.

```bash
# Create profiles
gacli auth --profile blog
gacli config -p 111111 --profile blog --set-default

gacli auth --profile work        # Login with a different Google account
gacli config -p 222222 --profile work

# Use a specific profile
gacli --profile work summary

# List all profiles
gacli profiles
```

Credentials and config are stored per-profile in `~/.config/gacli/profiles/<name>/`.

## Commands

| Command | Description |
|---------|-------------|
| `gacli auth` | Authenticate via browser |
| `gacli config` | Show or update configuration |
| `gacli profiles` | List all profiles |
| `gacli summary` | Daily summary (PV, users, sessions) |
| `gacli pages` | Top pages by page views |
| `gacli realtime` | Realtime active users |
