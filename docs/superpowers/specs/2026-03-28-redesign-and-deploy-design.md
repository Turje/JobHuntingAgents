# CastNet Redesign + Public Deployment

## Overview
Redesign the CastNet website from "AI-generated dark template" to a polished, premium dark theme (Linear/Vercel-style). Deploy frontend to GitHub Pages and backend to Fly.io so everything is publicly accessible.

## Pages
1. **Landing page** (new) — `docs/index.html` becomes the landing page
2. **Dashboard** (app) — moves to `docs/app.html`
3. **How It Works** — stays at `docs/how-it-works.html`

All cross-page links use relative `.html` paths (e.g., `app.html`, `how-it-works.html`) so they work on both GitHub Pages and when served by FastAPI. The FastAPI backend routes are updated to match (see Backend Route Changes below).

## Visual System

### Typography
- Headings: Geist Sans — clean, technical
- Body: Inter — readable UI font
- Monospace: Geist Mono — for badges, agent names, code-like elements

CDN links:
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fontsource-variable/inter@5/index.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/geist@1/dist/fonts/geist-sans/style.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/geist@1/dist/fonts/geist-mono/style.min.css">
```

Font stack: `'Geist Sans', 'Inter Variable', -apple-system, BlinkMacSystemFont, sans-serif`
Mono stack: `'Geist Mono', 'SF Mono', 'Fira Code', monospace`

### Color Palette
All blue-tinted grays replaced with warm zinc scale:
- `--bg`: `#09090b`
- `--surface`: `#111113`
- `--surface-hover`: `#18181b`
- `--surface-raised`: `#27272a`
- `--border`: `rgba(255,255,255,0.06)`
- `--border-light`: `rgba(255,255,255,0.1)`
- `--text`: `#fafafa`
- `--text-muted`: `#a1a1aa`
- `--text-dim`: `#52525b`
- `--accent`: `#3b82f6` (blue-500, the only color)
- `--accent-glow`: `rgba(59,130,246,0.15)`
- `--green`: `#22c55e` (success only)
- `--red`: `#ef4444` (error only)

No gradients on text. No colored glows on cards. One accent color used sparingly.

### Texture & Depth
- Body noise overlay: CSS pseudo-element with inline SVG noise at 3% opacity
  ```css
  body::before {
      content: ''; position: fixed; inset: 0; z-index: 9999; pointer-events: none;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
      background-repeat: repeat; background-size: 256px 256px;
  }
  ```
- Landing hero: dot grid pattern background (CSS radial-gradient dots)
- Cards: multi-layer box-shadow (no border-heavy look)
  ```
  box-shadow: 0 1px 2px rgba(0,0,0,0.3), 0 4px 16px rgba(0,0,0,0.2);
  ```
- Hover: translateY(-1px) + increased shadow
- Borders: only `rgba(255,255,255,0.06)` for subtle separation

## Landing Page (`docs/index.html`)

### Hero
- Headline: "Your job search, on autopilot." — Geist Sans, ~3rem, `#fafafa`
- Subtext: "7 AI agents research companies, tailor your resume, and draft outreach — in minutes."
- Two CTAs: "Launch App" → `app.html` (solid blue button) + "See how it works" → `how-it-works.html` (ghost/outline)
- Background: dot grid pattern with radial glow behind headline

### Pipeline Strip
- Horizontal row of 7 agent names connected by thin lines
- Once the strip enters viewport (IntersectionObserver), all 7 names light up sequentially with 200ms stagger
- "Light up" = text transitions from `--text-dim` to `--accent`, connecting line turns `--accent`
- Compact visual divider between hero and value props

### Value Cards (3-column grid)
- "Discover" / "Personalize" / "Reach out"
- Inline SVG icons (Lucide-style, hand-coded, ~20px) — no icon library dependency
- 2-line description each
- Shadow-based cards, no heavy borders

### Footer
- "Built with Gemini + Claude" tech credit
- GitHub repo link
- Repeat "Launch App" CTA

No fake testimonials, no "trusted by" logos.

## Dashboard (`docs/app.html`)

### Header
- Simple flex layout: logo left, nav links right
- Logo: "CastNet" in Geist Sans 600, plain white, no gradient
- Nav: "Dashboard" / "How It Works" / GitHub icon link
- Links use relative paths: `app.html`, `how-it-works.html`

### Sidebar (270px)
- Session items: query text + monospace meta line (`ds/ml · 2m ago`)
- No colored mode badges inline
- Copy + delete buttons aligned right, appear on hover
- Active: 2px left blue accent bar

### Search Area
- Input: 48px tall, subtle inner shadow, border on focus only
- Mode selector: pill toggle (General | DS/ML) on its own row directly above the search input
- Search button: solid blue, no gradient

### Result Cards
- No colored dots — monochrome icons or labels
- Shadow-based depth
- Skill bars: 4px height, rounded, blue fill on zinc-800 track
- Stepper: small circles + thin connecting line, checkmarks when done

### API Connection
- JS constant at top of file: `const API_BASE = 'https://castnet-api.fly.dev';`
- Remove the localhost connect bar and manual URL input
- Keep `localStorage` override: if `localStorage.getItem('castnet_api')` exists, use that instead (for local dev)
- WebSocket URL derived from API_BASE: replace `https://` with `wss://`

### General
- No emoji in UI
- Badge pills: zinc-800 background, white text
- Generous spacing: 20px/32px padding

## How It Works (`docs/how-it-works.html`)

### Pipeline Walkthrough (keep, restyle)
- Circles: zinc borders, blue fill active, white checkmark done
- Demo box: shadow-based card
- Animated items: remove colored dots, simple fade-in stagger
- Skill bars: thin, blue on zinc
- Email preview: cleaner card styling

### DSPy Section (keep real-example layout, restyle)
- Iteration cards: shadow-based, zinc tones
- Score badges: blue = good, zinc-500 = low
- Company check/cross: muted colors

### Search Modes
- Two cards, shadow style, no colored list dots

### Tech Tags
- Monochrome pills

## Deployment

### Frontend — GitHub Pages
- Source: `docs/` folder on `main` branch
- Configure in repo Settings > Pages
- Public URL: `https://turje.github.io/JobHuntingAgents/`

### Backend — Fly.io
- New files: `Dockerfile`, `fly.toml`, `.dockerignore` in repo root
- Persistent volume mounted for SQLite database
- Environment variables via `fly secrets set`:
  - `GEMINI_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `SERPER_API_KEY`
  - `GOOGLE_API_KEY`, `GOOGLE_CSE_ID`
  - `DATABASE_PATH=/data/pylon.db`
- Deploy command: `fly deploy`
- App name: `castnet-api`
- Public URL: `https://castnet-api.fly.dev`

### Backend Route Changes (`src/pylon/main.py`)
- Update `_DASHBOARD_HTML` to point to `docs/app.html`
- Add route for landing page: `GET /` serves `docs/index.html`
- Update dashboard route to `GET /app`
- Keep `GET /how-it-works` serving `docs/how-it-works.html`

### CORS
- Add `CORS_ORIGINS` env var, default: `https://turje.github.io`
- In dev, override with `CORS_ORIGINS=*` or `CORS_ORIGINS=http://localhost:8000`
- Apply via FastAPI CORSMiddleware

### Database Path
- Update `src/pylon/store.py` to read `DATABASE_PATH` env var:
  ```python
  _DEFAULT_DB = Path(os.getenv("DATABASE_PATH", str(Path(__file__).resolve().parent.parent.parent / "data" / "pylon.db")))
  ```
- On Fly.io, `DATABASE_PATH=/data/pylon.db` points to the persistent volume
- Locally, falls back to the existing `data/pylon.db` path

### Excel File Persistence
- Excel files are written to a temp path. On Fly.io, update the Excel output directory to use the persistent volume: `EXCEL_OUTPUT_DIR=/data/exports/`
- Add env var to config, default to `data/exports/` locally

### .dockerignore
```
.git
docs/
tests/
memory/
*.pyc
__pycache__
.env
.env.*
data/
.claude/
```

### Dockerfile
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install ".[dspy]"
EXPOSE 8000
CMD ["uvicorn", "pylon.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### fly.toml
```toml
app = "castnet-api"
primary_region = "ord"

[build]

[http_service]
  internal_port = 8000
  force_https = true

[mounts]
  source = "castnet_data"
  destination = "/data"

[env]
  HOST = "0.0.0.0"
  PORT = "8000"
  DATABASE_PATH = "/data/pylon.db"

[checks]
  [checks.health]
    type = "http"
    port = 8000
    path = "/health"
    interval = "10s"
    timeout = "5s"
    grace_period = "5s"
```

### WebSocket Configuration
- Fly.io supports WebSocket natively over `wss://` with `force_https = true`
- Set idle timeout in fly.toml to handle long pipeline runs:
  ```toml
  [http_service]
    idle_timeout = "300s"
  ```

### Meta Tags (all pages)
```html
<meta name="description" content="CastNet — AI-powered multi-agent job hunting platform">
<meta property="og:title" content="CastNet">
<meta property="og:description" content="7 AI agents automate your entire job search pipeline">
<meta property="og:type" content="website">
```

## Verification
1. Landing page loads on `https://turje.github.io/JobHuntingAgents/` with hero, pipeline, value cards
2. "Launch App" navigates to `app.html` dashboard
3. Dashboard connects to `https://castnet-api.fly.dev`, search works end-to-end
4. WebSocket pipeline progress works over `wss://`
5. How It Works animations play correctly
6. All pages use new visual system (Geist fonts, zinc palette, shadows)
7. No emoji in UI, no gradient text, no colored glows
8. Mobile responsive on all 3 pages
9. `pytest tests/ -v` passes
10. SQLite persists across Fly.io deploys (persistent volume)
