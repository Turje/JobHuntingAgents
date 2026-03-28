# CastNet Redesign + Public Deployment

## Overview
Redesign the CastNet website from "AI-generated dark template" to a polished, premium dark theme (Linear/Vercel-style). Deploy frontend to GitHub Pages and backend to Fly.io so everything is publicly accessible.

## Pages
1. **Landing page** (new) — `docs/index.html` becomes the landing page
2. **Dashboard** (app) — moves to `docs/app.html`
3. **How It Works** — stays at `docs/how-it-works.html`

## Visual System

### Typography
- Headings: Geist Sans (loaded via CDN) — clean, technical
- Body: Inter (loaded via CDN) — readable UI font
- Monospace: Geist Mono — for badges, agent names, code-like elements

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
- Body: subtle CSS noise overlay at 2-3% opacity
- Landing hero: dot grid pattern background
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
- Two CTAs: "Launch App" (solid blue) + "See how it works" (ghost/outline)
- Background: dot grid pattern with radial glow behind headline

### Pipeline Strip
- Horizontal row of 7 agent names connected by thin lines
- Sequential light-up on scroll via IntersectionObserver
- Compact visual divider between hero and value props

### Value Cards (3-column grid)
- "Discover" / "Personalize" / "Reach out"
- Minimal line icon + 2-line description each
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

### Sidebar (270px)
- Session items: query text + monospace meta line (`ds/ml · 2m ago`)
- No colored mode badges inline
- Copy + delete buttons aligned right, appear on hover
- Active: 2px left blue accent bar

### Search Area
- Input: 48px tall, subtle inner shadow, border on focus only
- Mode selector: pill toggle (General | DS/ML) above input, not dropdown
- Search button: solid blue, no gradient

### Result Cards
- No colored dots — monochrome icons or labels
- Shadow-based depth
- Skill bars: 4px height, rounded, blue fill on zinc-800 track
- Stepper: small circles + thin connecting line, checkmarks when done

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
- API base URL: configurable JS constant, defaults to Fly.io production URL

### Backend — Fly.io
- New files: `Dockerfile`, `fly.toml` in repo root
- Persistent volume mounted for SQLite database
- Environment variables via `fly secrets set`:
  - `GEMINI_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `SERPER_API_KEY`
  - `GOOGLE_API_KEY`, `GOOGLE_CSE_ID`
- Deploy command: `fly deploy`
- App name: `castnet-api` (or similar)

### Dockerfile
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -e .
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
```

### CORS
- Add CORS middleware to FastAPI allowing the GitHub Pages domain

## Verification
1. Landing page loads on GitHub Pages URL with hero, pipeline, value cards
2. "Launch App" navigates to dashboard
3. Dashboard connects to Fly.io backend, search works end-to-end
4. How It Works animations play correctly
5. All pages use new visual system (Geist fonts, zinc palette, shadows)
6. No emoji in UI, no gradient text, no colored glows
7. Mobile responsive on all 3 pages
8. `pytest tests/ -v` passes (no backend changes break tests)
