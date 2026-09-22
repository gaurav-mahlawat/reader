# Reader

Local web app that logs into [Freelancer.in](https://www.freelancer.in/), finds web development, social media, and SEO projects, and places **minimum-price** bids with slow, human-like delays. A dashboard **bid sheet** tracks every project the bot touches.

## Warning

Automating login and bidding may violate Freelancer's Terms of Service and can result in account suspension. Use low volume, start with **dry run**, and keep the browser visible until login works.

## Requirements

- Python 3.11+
- Windows / macOS / Linux

## Setup

### Quick start (Windows)

Double-click **`start.bat`** in the project folder, or run:

```powershell
cd "d:\dsa\Desktop\freelancer auto bidder"
.\start.bat
```

Then open **http://127.0.0.1:8000** in your browser.

### Manual setup

```powershell
cd "d:\dsa\Desktop\freelancer auto bidder"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
copy .env.example .env
python run.py
```

Open **http://127.0.0.1:8000**

> Keep the terminal window open while using the app — closing it stops the server.

## Usage

1. Enter your Freelancer email and password.
2. Enable **Dry run** first to verify project discovery without bidding.
3. Leave **Headless** off so you can complete CAPTCHA/2FA if needed.
4. Click **Start bot**.
5. Watch the **Bid sheet** — export CSV anytime.

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| Min delay | 180s | Minimum wait between bids |
| Max delay | 480s | Maximum wait between bids |
| Max bids/hour | 8 | Rate cap |
| Max bids/day | 40 | Daily cap |
| Delivery days | 7 | Bid delivery period |
| Dry run | on | Log projects without placing bids |

## Your skills (project targeting)

Enter your skills on the dashboard (or edit `config/keywords.yaml` → `my_skills`). The bot:

1. Searches **projects** on Freelancer for each skill (`/search/projects?q=...`) — not generic job category pages
2. Opens each project and checks title, description, and skill tags
3. Bids only if **at least one of your skills** matches

## Project filters

| Setting | Default | Rule |
|---------|---------|------|
| Max project age | **3 days** | Only projects posted in the last N days |
| Max proposals | **50** | Bid only if the project has **fewer than** 50 bids; 50+ are skipped |

Skipped projects appear in the bid sheet with status `skipped` and the reason.

## Keywords

Edit [`config/keywords.yaml`](config/keywords.yaml) to change categories and search URLs.

## Proposal template placeholders

- `{project_title}` — project title
- `{skills}` — matched category (web_dev, social_media, seo)
- `{url}` — project URL

## Data files

- `data/session.json` — saved browser session (gitignored)
- `data/bids.db` — SQLite bid log

## API

- `POST /api/bot/start` — start bot (JSON body)
- `POST /api/bot/stop` — stop bot
- `GET /api/bot/status` — bot status
- `GET /api/bids` — list bids
- `GET /api/bids/export` — CSV download
