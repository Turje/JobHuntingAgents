# CastNet Redesign + Public Deployment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign CastNet from AI-generated dark template to polished Linear/Vercel-style premium dark theme, then deploy frontend to GitHub Pages and backend to Fly.io.

**Architecture:** Three static HTML pages (landing, dashboard, how-it-works) served from `docs/` via GitHub Pages, connecting to FastAPI backend on Fly.io. Visual system uses Geist fonts, zinc color scale, shadow-based depth, CSS noise texture. Backend gets Docker containerization, persistent volume for SQLite, and CORS lockdown.

**Tech Stack:** Vanilla HTML/CSS/JS (no frameworks), FastAPI, Fly.io, GitHub Pages, Geist/Inter fonts via CDN

**Spec:** `docs/superpowers/specs/2026-03-28-redesign-and-deploy-design.md`

---

## File Map

### New Files
- `docs/index.html` — Landing page (hero, pipeline strip, value cards, footer)
- `.dockerignore` — Exclude docs, tests, .git from Docker build
- `Dockerfile` — Python 3.12 slim, pip install, uvicorn CMD
- `fly.toml` — Fly.io config with persistent volume, health check, WebSocket timeout

### Renamed Files
- `docs/index.html` → `docs/app.html` (existing dashboard)

### Modified Files
- `docs/app.html` — Full visual reskin (colors, fonts, shadows, layout, remove connect bar)
- `docs/how-it-works.html` — Visual reskin matching new design system
- `src/pylon/main.py:26-28,55-60,460-469` — Update file paths, routes, CORS
- `src/pylon/store.py:16` — Read DATABASE_PATH env var
- `src/pylon/config.py` — Add CORS_ORIGINS, DATABASE_PATH, EXCEL_OUTPUT_DIR
- `src/pylon/pipeline.py:52` — Wire EXCEL_OUTPUT_DIR into ExcelManager

---

## Task 1: Backend Config Changes (database path, CORS, config)

**Files:**
- Modify: `src/pylon/config.py:77` (add new env vars after DSPY_OPTIMIZED_PATH)
- Modify: `src/pylon/store.py:16` (read DATABASE_PATH)
- Modify: `src/pylon/main.py:55-60` (CORS from config)
- Modify: `src/pylon/pipeline.py:52` (wire EXCEL_OUTPUT_DIR into ExcelManager)
- Test: `tests/test_store.py`, `tests/test_api.py`

- [ ] **Step 1: Add new env vars to config.py**

Open `src/pylon/config.py`. After line 77 (DSPY_OPTIMIZED_PATH), add:

```python
# CORS
CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

# Database
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "")

# Excel output
EXCEL_OUTPUT_DIR: str = os.getenv("EXCEL_OUTPUT_DIR", "")
```

- [ ] **Step 2: Update store.py to read DATABASE_PATH**

In `src/pylon/store.py`, replace line 16:

```python
_DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "pylon.db"
```

with:

```python
import os

_DEFAULT_DB = Path(
    os.getenv("DATABASE_PATH")
    or str(Path(__file__).resolve().parent.parent.parent / "data" / "pylon.db")
)
```

- [ ] **Step 3: Update CORS in main.py**

In `src/pylon/main.py`, update the import on line 23 to also import `CORS_ORIGINS`:

```python
from pylon.config import CORS_ORIGINS, DSPY_ENABLED, HOST, LLM_PROVIDER, PORT
```

Replace lines 55-60:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 4: Wire EXCEL_OUTPUT_DIR into pipeline.py**

In `src/pylon/pipeline.py`, update line 20 import:

```python
from pylon.config import EXCEL_OUTPUT_DIR
```

Update line 52:

```python
self._excel = ExcelManager(output_dir=EXCEL_OUTPUT_DIR or None)
```

This ensures Excel files are written to the persistent volume on Fly.io (`/data/exports/`).

- [ ] **Step 5: Run existing tests to verify no breakage**

Run: `pytest tests/test_store.py tests/test_api.py tests/test_pipeline.py -v`
Expected: All pass (defaults unchanged)

- [ ] **Step 6: Commit**

```bash
git add src/pylon/config.py src/pylon/store.py src/pylon/main.py src/pylon/pipeline.py
git commit -m "feat: add DATABASE_PATH, CORS_ORIGINS, EXCEL_OUTPUT_DIR config"
```

---

## Task 2: Rename dashboard + update backend routes

**Files:**
- Rename: `docs/index.html` → `docs/app.html`
- Modify: `src/pylon/main.py:26-28,460-469` (routes)

- [ ] **Step 1: Rename the dashboard file**

```bash
git mv docs/index.html docs/app.html
```

- [ ] **Step 2: Update main.py file paths and routes**

In `src/pylon/main.py`, replace lines 27-28:

```python
_DASHBOARD_HTML = _PROJECT_ROOT / "docs" / "app.html"
_HOW_IT_WORKS_HTML = _PROJECT_ROOT / "docs" / "how-it-works.html"
```

Add a landing page path after line 28:

```python
_LANDING_HTML = _PROJECT_ROOT / "docs" / "index.html"
```

Replace the route at lines 460-463:

```python
@app.get("/", include_in_schema=False)
async def landing():
    if _LANDING_HTML.exists():
        return FileResponse(_LANDING_HTML, media_type="text/html")
    return FileResponse(_DASHBOARD_HTML, media_type="text/html")

@app.get("/app", include_in_schema=False)
async def dashboard():
    return FileResponse(_DASHBOARD_HTML, media_type="text/html")
```

Keep the `/how-it-works` route as-is (lines 466-469).

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_api.py -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add docs/app.html src/pylon/main.py
git commit -m "feat: rename dashboard to app.html, add landing page route"
```

---

## Task 3: Create the landing page (`docs/index.html`)

**Files:**
- Create: `docs/index.html`

- [ ] **Step 1: Create the landing page**

Create `docs/index.html` with the full design system:
- Geist Sans + Inter + Geist Mono font CDN links
- Zinc color palette CSS variables
- CSS noise overlay on body
- Meta tags (description, Open Graph)

**Hero section:**
- Headline: "Your job search, on autopilot."
- Subtext: "7 AI agents research companies, tailor your resume, and draft outreach — in minutes."
- Dot grid background with radial glow
- Two CTAs: "Launch App" → `app.html` (solid blue), "How it works" → `how-it-works.html` (ghost)

**Pipeline strip:**
- Horizontal row: Discovery → Research → Skills → Tools → Contacts → Resume → Outreach
- Connected by thin lines
- IntersectionObserver: when strip enters viewport, names light up sequentially (200ms stagger)
- "Light up" = text transitions from `var(--text-dim)` to `var(--accent)`

**Value cards (3-column grid):**
- "Discover" — inline SVG search icon + "Searches the web to find companies that match your goals, across any industry."
- "Personalize" — inline SVG user icon + "Tailors your resume and analyzes skill fit for each target company."
- "Reach out" — inline SVG mail icon + "Drafts personalized cold emails to hiring managers and decision-makers."
- Cards use box-shadow depth, zinc surface background

**Footer:**
- "Built with Gemini + Claude" centered
- GitHub icon link to `https://github.com/Turje/JobHuntingAgents`
- "Launch App" CTA repeated

All icons are hand-coded inline SVGs (~20px, stroke-based, 1.5px stroke). No icon library.

- [ ] **Step 2: Test locally**

Open `docs/index.html` directly in browser. Verify:
- Fonts load (Geist headings, Inter body)
- Noise texture visible on dark background
- Hero dot grid + glow visible
- Pipeline strip animates on scroll
- Links point to `app.html` and `how-it-works.html`
- Mobile responsive at 375px width

- [ ] **Step 3: Commit**

```bash
git add docs/index.html
git commit -m "feat: add landing page with hero, pipeline strip, value cards"
```

---

## Task 4: Reskin dashboard (`docs/app.html`) — CSS + layout

**Files:**
- Modify: `docs/app.html` (the renamed dashboard)

This task covers CSS variables, fonts, header, and structural changes. The next task covers JS/functional changes.

- [ ] **Step 1: Replace CSS variables and add fonts**

In `docs/app.html`, add font CDN links in `<head>` before `<style>`:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fontsource-variable/inter@5/index.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/geist@1/dist/fonts/geist-sans/style.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/geist@1/dist/fonts/geist-mono/style.min.css">
```

Replace the `:root` block (lines 8-34) with new zinc palette:

```css
:root {
    --bg: #09090b;
    --surface: #111113;
    --surface-hover: #18181b;
    --surface-raised: #27272a;
    --border: rgba(255,255,255,0.06);
    --border-light: rgba(255,255,255,0.1);
    --text: #fafafa;
    --text-muted: #a1a1aa;
    --text-dim: #52525b;
    --accent: #3b82f6;
    --accent-glow: rgba(59,130,246,0.15);
    --green: #22c55e;
    --green-glow: rgba(34,197,94,0.12);
    --red: #ef4444;
    --red-glow: rgba(239,68,68,0.12);
    --radius: 10px;
    --radius-sm: 6px;
}
```

Update body font-family:

```css
body {
    font-family: 'Geist Sans', 'Inter Variable', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    min-height: 100vh;
}
```

Add noise overlay:

```css
body::before {
    content: ''; position: fixed; inset: 0; z-index: 9999; pointer-events: none;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
    background-repeat: repeat; background-size: 256px 256px;
}
```

- [ ] **Step 2: Replace header**

Remove the CSS grid header, `.hiw-box`, `.header-center`, and `.connect-bar` styles.

Replace header HTML with simple flex nav:

```html
<div class="header">
    <div class="header-left">
        <a href="index.html" class="logo">CastNet</a>
    </div>
    <nav class="header-nav">
        <a href="app.html" class="nav-link active">Dashboard</a>
        <a href="how-it-works.html" class="nav-link">How It Works</a>
        <a href="https://github.com/Turje/JobHuntingAgents" target="_blank" class="nav-link nav-icon" title="GitHub">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
        </a>
    </nav>
</div>
```

New header CSS:

```css
.header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 24px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
}
.logo {
    font-family: 'Geist Sans', sans-serif;
    font-size: 1.15rem; font-weight: 600; color: var(--text);
    text-decoration: none;
}
.logo:hover { text-decoration: none; opacity: 0.8; }
.header-nav { display: flex; align-items: center; gap: 20px; }
.nav-link {
    font-size: 0.82rem; color: var(--text-muted); text-decoration: none;
    font-weight: 500; transition: color 0.15s;
}
.nav-link:hover, .nav-link.active { color: var(--text); text-decoration: none; }
.nav-icon { display: flex; align-items: center; }
```

- [ ] **Step 3: Update card styles to shadow-based**

Remove all colored glow variables (`--purple-glow`, `--orange-glow`, `--teal-glow`, `--pink`). These are no longer used.

Replace any `border: 1px solid var(--border)` card pattern with:

```css
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: 0 1px 2px rgba(0,0,0,0.3), 0 4px 16px rgba(0,0,0,0.2);
    transition: transform 0.15s, box-shadow 0.15s;
}
.card:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0,0,0,0.4), 0 8px 24px rgba(0,0,0,0.3);
}
```

- [ ] **Step 4: Update search area — pill toggle + taller input**

Replace the `<select id="searchMode">` dropdown with a pill toggle:

```html
<div class="mode-toggle">
    <button class="mode-pill active" data-mode="general" onclick="setMode('general')">General</button>
    <button class="mode-pill" data-mode="ds_ml" onclick="setMode('ds_ml')">DS / ML</button>
</div>
```

CSS:

```css
.mode-toggle {
    display: flex; gap: 0; margin-bottom: 12px;
    background: var(--surface); border-radius: var(--radius-sm);
    border: 1px solid var(--border); overflow: hidden; width: fit-content;
}
.mode-pill {
    padding: 6px 20px; font-size: 0.78rem; font-weight: 600;
    background: transparent; border: none; color: var(--text-dim);
    cursor: pointer; transition: all 0.15s;
}
.mode-pill.active {
    background: var(--accent); color: #fff;
}
```

Update the search input to be taller with inner shadow:

```css
.search-input {
    height: 48px; padding: 0 16px;
    background: var(--bg); border: 1px solid transparent;
    border-radius: var(--radius-sm); color: var(--text);
    font-size: 0.92rem; width: 100%;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.3);
    transition: border-color 0.15s;
}
.search-input:focus {
    outline: none; border-color: var(--accent);
}
```

Search button — solid blue, no gradient:

```css
.search-btn {
    padding: 0 24px; height: 48px;
    background: var(--accent); color: #fff;
    border: none; border-radius: var(--radius-sm);
    font-weight: 600; font-size: 0.85rem;
    transition: opacity 0.15s;
}
.search-btn:hover { opacity: 0.85; }
```

- [ ] **Step 5: Update sidebar styles**

Width to 270px. Session items:

```css
.sidebar { width: 270px; min-width: 270px; }
.session-item.active { border-left: 2px solid var(--accent); }
```

Session meta: use Geist Mono for the meta line:

```css
.session-meta {
    font-family: 'Geist Mono', monospace;
    font-size: 0.68rem; color: var(--text-dim);
}
```

Remove colored `.mode-badge-sm` styles. Replace with plain text in the meta line.

- [ ] **Step 6: Update badge styles — monochrome**

```css
.badge {
    font-family: 'Geist Mono', monospace;
    font-size: 0.65rem; padding: 2px 8px;
    border-radius: var(--radius-sm); font-weight: 600;
    background: var(--surface-raised); color: var(--text-muted);
}
.badge-running { background: var(--accent-glow); color: var(--accent); }
.badge-completed { background: var(--green-glow); color: var(--green); }
.badge-failed { background: var(--red-glow); color: var(--red); }
```

- [ ] **Step 7: Update skill bars — thin, blue on zinc**

```css
.skill-bar { height: 4px; border-radius: 2px; background: var(--surface-raised); }
.skill-bar-fill { height: 100%; border-radius: 2px; background: var(--accent); }
```

- [ ] **Step 8: Update stepper — minimal**

Small circles (20px) with thin connecting lines. No pulse animation. Checkmark SVG when done:

```css
.step-circle {
    width: 20px; height: 20px; border-radius: 50%;
    border: 1.5px solid var(--text-dim);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.65rem; color: var(--text-dim);
    font-family: 'Geist Mono', monospace;
}
.step-circle.active { border-color: var(--accent); color: var(--accent); }
.step-circle.done { background: var(--accent); border-color: var(--accent); color: #fff; }
.step-line { height: 1px; flex: 1; background: var(--border-light); }
.step-line.done { background: var(--accent); }
```

- [ ] **Step 9: Remove all emoji from UI**

Search all HTML/JS in `docs/app.html` for emoji characters (unicode ranges U+1F000-U+1FAFF, U+2700-U+27BF). Replace with:
- Status indicators: use small SVG icons or plain text
- The clipboard icon (`&#128203;`) in copy button: replace with inline SVG clipboard icon
- The delete X (`&#x2715;`): keep as-is (this is a plain symbol, not emoji)

- [ ] **Step 10: Commit**

```bash
git add docs/app.html
git commit -m "feat: reskin dashboard with zinc palette, Geist fonts, shadow cards"
```

---

## Task 5: Dashboard JS changes (API URL, remove connect bar)

**Files:**
- Modify: `docs/app.html` (JS section)

- [ ] **Step 1: Replace API URL logic**

Remove the connect bar HTML (the `<input id="backendUrl">` and `onConnect()` button).

At the top of the `<script>` block, replace the URL initialization logic (around lines 1078-1093 in the original) with:

```javascript
const API_BASE = localStorage.getItem('castnet_api') || 'https://castnet-api.fly.dev';
```

Update the state initialization:

```javascript
const S = {
    url: API_BASE,
    runId: null,
    sessions: [],
    data: { companies:[], profiles:[], skills:[], contacts:[], resumes:[], drafts:[], tool_suggestions:[] },
    searchMode: 'general',
    searchStartTime: null,
    searchTimerInterval: null,
};
```

Remove `onConnect()` function entirely. Remove `loadBackendUrl()` or equivalent.

- [ ] **Step 2: Update WebSocket URL derivation**

Find where `ws://` or `wss://` URLs are constructed. Replace with:

```javascript
function wsUrl(runId) {
    const base = S.url.replace(/^http/, 'ws');
    return `${base}/ws/${runId}`;
}
```

- [ ] **Step 3: Add setMode() function for pill toggle**

```javascript
function setMode(mode) {
    S.searchMode = mode;
    document.querySelectorAll('.mode-pill').forEach(p => {
        p.classList.toggle('active', p.dataset.mode === mode);
    });
}
```

- [ ] **Step 4: Remove orphaned connect-bar JS and HTML**

Remove these items that are no longer needed:
- Remove `onConnect()` function
- Remove `loadBackendUrl()` / init code that reads `backendUrl` input
- Remove `setDot()` function and all calls to it
- Remove `setModeBadge()` function and all calls to it
- Remove the overlay HTML element (`<div id="overlay">`) and its CSS
- Remove `S.connected` from state and remove the `!S.connected` guard in `onSearch()`
- Remove `.status-dot`, `.connect-bar` CSS rules

Replace the `DOMContentLoaded` init with:

```javascript
document.addEventListener('DOMContentLoaded', async () => {
    await loadSessions();
    try {
        const h = await json('/health');
        console.log('Backend connected:', h);
    } catch (e) {
        console.warn('Backend not reachable:', e.message);
    }
});
```

- [ ] **Step 5: Update sidebar rendering — remove colored mode badges**

In `renderSidebar()`, replace the modeBadge HTML with plain text in the meta line:

```javascript
const modeText = (s.search_mode === 'ds_ml') ? 'ds/ml' : 'general';
// In the session-meta span:
`<span>${modeText} · ${t}</span>`
```

Remove the `.mode-badge-sm` classes and HTML.

- [ ] **Step 6: Search for remaining route-path links**

Search `docs/app.html` for any remaining `href="/"` or `href="/how-it-works"` or `href="/app"` in both HTML and JS. Convert all to relative `.html` paths (`index.html`, `app.html`, `how-it-works.html`).

- [ ] **Step 7: Test locally**

Start backend: `cd /Users/turje87/Desktop/PersonalProjects/JobHuntingAgents && python -m uvicorn pylon.main:app --reload`
Open `http://localhost:8000/app` in browser.
Verify: header nav works, pill toggle switches mode, search executes, results display, no console errors about missing functions.

- [ ] **Step 8: Commit**

```bash
git add docs/app.html
git commit -m "feat: replace connect bar with hardcoded API URL, add pill toggle"
```

---

## Task 6: Reskin How It Works page

**Files:**
- Modify: `docs/how-it-works.html`

- [ ] **Step 1: Update fonts and CSS variables**

Add same font CDN links as dashboard. Replace `:root` block with zinc palette (identical to `docs/app.html`). Add noise overlay. Update body font-family.

- [ ] **Step 2: Update header to match dashboard**

Replace the current header (lines 279-284) with the same flex nav used in the dashboard:

```html
<div class="header">
    <div class="header-left">
        <a href="index.html" class="logo">CastNet</a>
    </div>
    <nav class="header-nav">
        <a href="app.html" class="nav-link">Dashboard</a>
        <a href="how-it-works.html" class="nav-link active">How It Works</a>
        <a href="https://github.com/Turje/JobHuntingAgents" target="_blank" class="nav-link nav-icon" title="GitHub">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
        </a>
    </nav>
</div>
```

- [ ] **Step 3: Restyle pipeline walkthrough**

Update `.pipe-circle`:
- Default: `border: 1.5px solid var(--text-dim)`, no background
- Active: `background: var(--accent); border-color: var(--accent); color: #fff;` — no `box-shadow` pulse
- Done: same as active but with checkmark SVG inside instead of number

Remove `@keyframes pulse` animation.

Update `.demo-box`:
- Add `box-shadow: 0 1px 2px rgba(0,0,0,0.3), 0 4px 16px rgba(0,0,0,0.2);`
- Keep border but use `var(--border)`

Update `.anim-item`:
- Remove `.dot` colored circles. Just use plain text items with fade-in.
- Remove `.tag` colored pills. Replace with monochrome `var(--surface-raised)` background.

Update `.anim-bar`:
- Height: `4px`, border-radius: `2px`
- Fill: `var(--accent)` only (no multi-color bars)
- Track: `var(--surface-raised)`

- [ ] **Step 4: Restyle DSPy section**

Update `.dspy-demo`, `.dspy-iter`:
- Use shadow-based cards matching new system
- Score badges: `var(--accent)` for high, `var(--text-dim)` for low (not orange/green)
- Company checks: `var(--green)` for valid, `var(--text-dim)` for invalid (muted)
- Feedback row: `var(--surface-raised)` background, no orange glow

- [ ] **Step 5: Restyle search modes + tech tags**

Mode cards:
- Both cards use same shadow style, no colored headings
- List items: simple `·` bullet, no colored dots

Tech tags:
- `background: var(--surface-raised); color: var(--text-muted); border: none;`

- [ ] **Step 6: Convert all route-path links to relative .html paths**

Search `docs/how-it-works.html` for any `href="/"`, `href="/how-it-works"`, `href="/app"` in HTML and JS. Convert to relative paths: `index.html`, `how-it-works.html`, `app.html`.

- [ ] **Step 7: Remove all emoji**

Replace any emoji characters in the HTML/JS with either inline SVGs or plain text. Check the STEPS array visual functions and the DSPy node icons.

- [ ] **Step 8: Test**

Open `docs/how-it-works.html` in browser. Verify:
- New fonts and colors
- Pipeline walkthrough plays (Play button)
- DSPy animation plays
- No colored dots, glows, or emoji visible
- Navigation links work (`index.html`, `app.html`)

- [ ] **Step 9: Commit**

```bash
git add docs/how-it-works.html
git commit -m "feat: reskin How It Works with zinc palette, shadows, no emoji"
```

---

## Task 7: Docker + Fly.io deployment files

**Files:**
- Create: `Dockerfile`
- Create: `fly.toml`
- Create: `.dockerignore`

- [ ] **Step 1: Create .dockerignore**

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
.ruff_cache/
```

- [ ] **Step 2: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/
COPY config/ config/
COPY knowledge/ knowledge/
COPY agents/ agents/

RUN pip install --no-cache-dir ".[dspy]"

EXPOSE 8000

CMD ["uvicorn", "pylon.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Create fly.toml**

```toml
app = "castnet-api"
primary_region = "ord"

[build]

[http_service]
  internal_port = 8000
  force_https = true
  idle_timeout = "300s"
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 0

[mounts]
  source = "castnet_data"
  destination = "/data"

[env]
  HOST = "0.0.0.0"
  PORT = "8000"
  DATABASE_PATH = "/data/pylon.db"
  EXCEL_OUTPUT_DIR = "/data/exports/"
  CORS_ORIGINS = "https://turje.github.io"

[checks]
  [checks.health]
    type = "http"
    port = 8000
    path = "/health"
    interval = "10s"
    timeout = "5s"
    grace_period = "5s"
```

- [ ] **Step 4: Test Docker build locally**

```bash
docker build -t castnet .
```

Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add Dockerfile fly.toml .dockerignore
git commit -m "feat: add Docker + Fly.io deployment config"
```

---

## Task 8: Deploy backend to Fly.io

**Files:** None (CLI operations)

- [ ] **Step 1: Install Fly CLI (if not installed)**

```bash
brew install flyctl
```

- [ ] **Step 2: Login to Fly.io**

```bash
fly auth login
```

- [ ] **Step 3: Launch the app**

```bash
fly launch --no-deploy
```

When prompted, confirm app name `castnet-api` and region `ord` (Chicago).

- [ ] **Step 4: Create persistent volume**

```bash
fly volumes create castnet_data --size 1 --region ord
```

- [ ] **Step 5: Set secrets**

```bash
fly secrets set GEMINI_API_KEY="<key>" ANTHROPIC_API_KEY="<key>" SERPER_API_KEY="<key>" GOOGLE_API_KEY="<key>" GOOGLE_CSE_ID="<id>"
```

(Use actual keys from `.env` file. GOOGLE_API_KEY and GOOGLE_CSE_ID are needed for fallback search when Serper credits are exhausted.)

- [ ] **Step 6: Deploy**

```bash
fly deploy
```

- [ ] **Step 7: Verify**

```bash
curl https://castnet-api.fly.dev/health
```

Expected: `{"status":"ok",...}`

- [ ] **Step 8: Test WebSocket**

Open browser dev tools, connect to `wss://castnet-api.fly.dev/ws/test` — should connect without error.

---

## Task 9: Deploy frontend to GitHub Pages

**Files:** None (GitHub settings)

- [ ] **Step 1: Push all changes to GitHub**

```bash
git push origin main
```

- [ ] **Step 2: Enable GitHub Pages**

Go to `https://github.com/Turje/JobHuntingAgents/settings/pages`
- Source: Deploy from a branch
- Branch: `main`
- Folder: `/docs`
- Save

- [ ] **Step 3: Wait for deployment**

GitHub Actions will build and deploy. Check the Actions tab for progress.

- [ ] **Step 4: Verify**

Open `https://turje.github.io/JobHuntingAgents/`
- Landing page loads with hero, pipeline, value cards
- "Launch App" navigates to `app.html`
- Dashboard connects to `https://castnet-api.fly.dev`
- Run a search — verify WebSocket progress + results
- "How It Works" page loads and animations play
- All pages show Geist fonts, zinc palette, no emoji

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests pass

---

## Task 10: Final polish + meta tags

**Files:**
- Modify: `docs/index.html`, `docs/app.html`, `docs/how-it-works.html`

- [ ] **Step 1: Add meta tags to all pages**

In `<head>` of each page:

```html
<meta name="description" content="CastNet — AI-powered multi-agent job hunting platform. 7 agents automate your entire job search.">
<meta property="og:title" content="CastNet">
<meta property="og:description" content="7 AI agents automate your entire job search pipeline">
<meta property="og:type" content="website">
<meta property="og:url" content="https://turje.github.io/JobHuntingAgents/">
```

- [ ] **Step 2: Verify mobile responsiveness**

Test all 3 pages at 375px, 768px, and 1280px widths. Fix any overflow, truncation, or layout issues.

- [ ] **Step 3: Cross-browser test**

Open in Chrome + Safari. Verify fonts load, shadows render, animations play.

- [ ] **Step 4: Commit**

```bash
git add docs/
git commit -m "feat: add meta tags and final responsive polish"
git push origin main
```
