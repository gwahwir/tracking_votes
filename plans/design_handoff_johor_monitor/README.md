# Handoff: Johor Election Monitor Dashboard

## Overview
This is a design handoff for the **Johor Election Monitor** — a real-time election intelligence dashboard that aggregates news, AI-driven constituency analysis, and seat predictions for Johor's 26 parliamentary (Parlimen) and 56 state (DUN) seats.

The dashboard was designed against the existing React/Vite/Mantine codebase at `gwahwir/tracking_votes`. The goal is to **recreate these designs in the existing codebase**, replacing the prototype's mock data with real API calls to the live backend.

---

## About the Design Files
The files in this bundle are **high-fidelity design references built in plain HTML + React/Babel**. They are prototypes showing intended look, layout, and interactive behaviour — **not production code to copy directly**. The task is to recreate these designs in the existing React/Vite/Mantine app (`dashboard/src/`), using the existing component library, hooks, and patterns already established in that codebase.

---

## Fidelity
**High-fidelity.** The prototype reflects pixel-precise decisions on:
- Layout grid, column widths, panel heights
- All colours (exact hex values from `theme.js`)
- Typography: JetBrains Mono throughout, all sizes and weights specified
- Hover/active/selected states on every interactive element
- Animation timings (pulse, strength bar fill, tab transitions)

Recreate the UI pixel-accurately using the existing Mantine theme and component library.

---

## Screens / Views

### 1. Full Dashboard Shell
**File:** `Johor Election Monitor.html` (root layout)

**Layout:**
- `display: flex; flex-direction: column; height: 100vh; overflow: hidden`
- Row 1: `TopBar` — `height: 48px; flex-shrink: 0`
- Row 2: `Scoreboard` — `~34px; flex-shrink: 0`
- Row 3: Main grid — `flex: 1; display: grid; grid-template-columns: 300px 1fr 360px`
- Row 4: `AgentPanel` — collapsible, `flex-shrink: 0`

**Background:** `#0a0a0f`
**Column dividers:** `1px solid #373a40`

---

### 2. TopBar
**Height:** 48px | **Background:** `#0a0a0f` | **Border-bottom:** `1px solid #373a40`

**Left — Title:**
- Text: `JOHOR ELECTION MONITOR`
- Font: JetBrains Mono 700, 14px, `#00d4ff`, letter-spacing 0.12em

**Center — Live Badge:**
- Border: `1px solid #39ff14`, border-radius 3px, padding `3px 10px`
- Text: `LIVE` — JetBrains Mono 700, 11px, `#39ff14`, letter-spacing 0.15em
- Animated dot: 7×7px circle, `#39ff14`, opacity pulses 1↔0.3 on 1s interval

**Right — Controls (left to right):**
1. **Map type toggle** — two-button pill (`Parlimen` / `DUN`)
   - Container: `border: 1px solid #373a40; border-radius: 4px; overflow: hidden`
   - Inactive: `background: transparent; color: #909296`
   - Active: `background: #1a3a4a; color: #00d4ff`
   - Font: JetBrains Mono 11px, padding `4px 12px`
2. **Cartogram toggle** — 32×32px icon button
   - Inactive: `background: #1a1b1e; border: 1px solid #373a40; color: #909296`
   - Active: `background: #1a3a4a; border-color: #00d4ff; color: #00d4ff`
3. **Refresh** — same 32×32px style; spins (CSS `animation: spin 0.8s linear infinite`) while loading
4. **Wiki** — same 32×32px style; opens WikiModal

---

### 3. Scoreboard
**Height:** ~34px | **Background:** `#0d0d14` | **Border-bottom:** `1px solid #373a40`

- `display: flex; align-items: center; gap: 16px; padding: 6px 16px; overflow-x: auto`
- For each party with predicted seats:
  - Coloured 8×8px square (party colour, border-radius 2px)
  - Party name: JetBrains Mono 700 11px, party colour
  - Seat count: JetBrains Mono 700 13px, `#fff`
- Right-aligned: `{n}/{total} seats predicted` — JetBrains Mono 11px, `#5c5f66`
- **Party colours** (from `theme.js`):
  - BN/UMNO: `#3366cc` | DAP: `#33cc33` | PKR: `#ff6633` | PN: `#ff3333`
  - PAS: `#00aa00` | Amanah: `#ffcc00` | Bersatu: `#990000` | Independent: `#999999`

---

### 4. News Feed Panel (Left Column, 300px)

**Header:** `padding: 10px 14px; border-bottom: 1px solid #373a40`
- Label: `NEWS FEED` — JetBrains Mono 700 10px `#5c5f66`, letter-spacing 0.12em
- Count badge: `background: #1a1b1e; border: 1px solid #373a40; border-radius: 10px; padding: 1px 7px; font: JetBrains Mono 10px #909296`

**Scrollable article list:** `gap: 6px; padding: 10px`

#### ArticleCard
- Container: `padding: 10px 12px; background: #1a1b1e; border: 1px solid #373a40; border-radius: 4px; cursor: pointer`
- **Hover state:** `border-color: #5c5f66; background: #1e1f23`
- **Selected state:** `border-color: #00d4ff; background: #0d1f2a; box-shadow: 0 0 10px rgba(0,212,255,0.1)`
- Title: JetBrains Mono 600 12px, line-clamp 2; colour `#e0e0e0` (unselected) / `#00d4ff` (selected)
- Source: JetBrains Mono 10px `#5c5f66` uppercase
- Date: JetBrains Mono 10px `#5c5f66`
- **Reliability bar:** full-width 4px bar, colour:
  - ≥70%: `#39ff14` | 40–69%: `#ffcc00` | <40%: `#ff3131`
  - Score label: JetBrains Mono 700 10px, same colour
- Constituency tags: JetBrains Mono 10px `#00d4ff` — show first 2, then `+N`
- **Action row:** two equal-width buttons (flex: 1), height ~26px
  - Select: `background: rgba(0,212,255,0.1); border: 1px solid #00d4ff40; color: #00d4ff`
    Selected state: `background: #00d4ff; color: #000; font-weight: 700`
  - Score: `background: rgba(57,255,20,0.07); border: 1px solid #39ff1430; color: #39ff14`
    Already scored: grayed out, disabled

---

### 5. Interactive Map (Center Column)

**Header:** `padding: 10px 14px; border-bottom: 1px solid #373a40`
- Label: `INTERACTIVE MAP` — JetBrains Mono 700 10px `#5c5f66`
- Sublabel: current view mode — JetBrains Mono 10px `#373a40`

**Map area background:** `#050508`

**Cartogram grid (SVG):**
- 26 rectangular tiles arranged in a 6-column × 6-row geographic grid
- Cell size: 76×58px, gap: 5px
- Each tile:
  - Fill: party colour at 25% opacity (50% on hover, 60% selected)
  - Top 4px strip: party colour at 90% opacity
  - Stroke: confidence ring colour at ring width:
    - ≥70%: `#39ff14` 3px | 40–69%: `#ffcc00` 2.5px | <40%: `#ff3131` 2px
  - Selected: outer glow rect `stroke: #00d4ff; stroke-width: 2; opacity: 0.5`
  - Text inside: constituency code (top-left, 8px `#909296`), name (centered, 9px `#e0e0e0` 600), party (centered bottom, 8px party colour 700), confidence (top-right, 7.5px confidence colour)
- **Hover tooltip** (bottom-right, fixed over map): `background: #0a0a0f; border: 1px solid #00d4ff; box-shadow: 0 0 20px rgba(0,212,255,0.25); border-radius: 4px; padding: 8px 12px`
  - Code: 9px `#5c5f66` | Name: 12px `#fff` 700 | Party: 10px party colour 700 | Confidence: 9px `#909296`

**Note:** In production, replace SVG cartogram with the existing Leaflet/GeoJSON map component. The cartogram is a prototype stand-in.

**DUN mode:** When `mapType === 'dun'`, show a centered placeholder (the real DUN GeoJSON layer isn't wired up in the prototype).

---

### 6. Analysis Panel (Right Column, 360px)

**Empty state** (no article selected):
- Centered vertically: icon `◈` at 28px `#5c5f66` + text "Select an article to see analysis"

**With article selected:**
- **Header:** `padding: 10px 14px; border-bottom: 1px solid #373a40`
  - Label: `ANALYSIS` — JetBrains Mono 700 10px `#5c5f66`
  - Article title truncated: JetBrains Mono 11px `#909296`
- **Tab bar:** 6 equal tabs — POL / DEM / HIST / STRAT / FACT / WELSH
  - Inactive: JetBrains Mono 9px `#5c5f66`
  - Active: `color: #00d4ff; border-bottom: 2px solid #00d4ff; background: rgba(0,212,255,0.05)`
- **Tab content** (`padding: 14px`):
  - Lens title: JetBrains Mono 700 11px `#00d4ff`, letter-spacing 0.08em
  - **Direction row:** label (9px `#5c5f66` uppercase, min-width 90px) + value (13–15px `#00d4ff` 700)
  - **Signal Strength row:** label + bar (`height: 5px; background: linear-gradient(90deg, {color}80, {color})`) + `{n}%` label
  - **Summary:** label + paragraph text JetBrains Mono 11px `#c1c2c5`, line-height 1.65

---

### 7. Seat Detail Panel (replaces Analysis Panel when constituency clicked)

**Header:** `padding: 12px 14px; border-bottom: 1px solid #373a40`
- Seat name: JetBrains Mono 700 14px `#00d4ff`
- Code: JetBrains Mono 10px `#5c5f66`
- Close ✕ button: top-right

**Prediction card:** `margin: 10px 14px; padding: 10px 12px; background: #1a1b1e; border: 1px solid #373a40; border-left: 3px solid {partyColor}; border-radius: 4px`
- Party badge: `background: {partyColor}; color: #000; padding: 2px 10px; border-radius: 3px; font: JetBrains Mono 700 11px`
- Confidence: JetBrains Mono 700 12px, confidence colour (≥70 lime / 40–69 amber / <40 red)
- Meta: JetBrains Mono 9px `#5c5f66`

**4 tabs:** OVERVIEW / HISTORY / DEMOGRAPHICS / ARTICLES — same tab bar style as Analysis Panel

- **Overview:** Signal breakdown table (lens → direction badge → strength bar) + Caveats list (`#ff3131`)
- **History:** Table — Year / Winner (party colour) / Margin / Turnout %
- **Demographics:** Horizontal bar chart for Malay/Chinese/Indian/Other voter breakdown
- **Articles:** Cards showing articles tagged to this constituency

---

### 8. WikiModal
- Full-screen overlay: `background: rgba(0,0,0,0.8)`
- Modal: `width: 540px; max-height: 80vh; background: #0a0a0f; border: 1px solid #373a40; border-radius: 6px; box-shadow: 0 0 40px rgba(0,212,255,0.15)`
- Header: `WIKI KNOWLEDGE BASE` — JetBrains Mono 700 12px `#00d4ff`
- Search input: `background: #1a1b1e; border: 1px solid #373a40; color: #e0e0e0; font: JetBrains Mono 12px`
- Each page item: title (12px `#e0e0e0`) + path (10px `#5c5f66`) + date (10px `#5c5f66`)
- Data source: `useWikiPages()` hook (already in codebase)

---

### 9. Agent Panel (collapsible, bottom)
- **Collapsed bar:** `border-top: 1px solid #373a40` — toggle button + status dots (6px circles, one per task, coloured by status)
- **Expanded:** `padding: 8px 12px`
- Task row: status dot (7px, animated pulse when `running`) + agent name (JetBrains Mono 700 10px `#00d4ff` if running else `#909296`) + message (10px `#5c5f66`) + timestamp (10px `#373a40`)
- Status colours: completed `#39ff14` | running `#00d4ff` (pulses) | pending `#373a40` | error `#ff3131`

---

## Interactions & Behavior

| Interaction | Behaviour |
|---|---|
| Click article card | Sets `selectedArticle`; deselects any seat; analysis panel populates |
| Click same article again | Deselects (toggles) |
| Click constituency tile | Sets `selectedSeat`; deselects any article; right panel switches to SeatDetailPanel |
| Click same seat again | Deselects (toggles) |
| Parlimen / DUN toggle | Changes `mapType` state; map reloads GeoJSON |
| Cartogram toggle | Flips `useCartogram`; map switches between geographic and cartogram GeoJSON |
| Refresh button | Dispatches `news_agent` task; spins icon; increments `refreshTrigger` after 2s delay |
| Wiki button | Opens WikiModal overlay |
| Agent panel toggle | Shows/hides task list |
| Tab switches (Analysis / Seat) | Instant, no animation needed; active tab highlighted |

**Strength bar animation:** On mount/tab-switch, bars animate from 0 → value over 0.6s ease.

**Confidence ring colours:** See party/confidence colour tables above.

---

## State Management
Matches existing `DashboardShell.jsx` state shape exactly:

```js
const [mapType, setMapType] = useState('parlimen')           // 'parlimen' | 'dun'
const [useCartogram, setUseCartogram] = useState(false)
const [selectedArticle, setSelectedArticle] = useState(null) // article object | null
const [selectedConstituency, setSelectedConstituency] = useState(null) // { code, name } | null
const [wikiOpen, setWikiOpen] = useState(false)
const [refreshTrigger, setRefreshTrigger] = useState(0)
const [activeTaskId, setActiveTaskId] = useState(null)
const [agentPanelOpen, setAgentPanelOpen] = useState(false)
```

**Persistence:** Save `mapType` to `localStorage` key `jem-session` on change; restore on mount.

**Selecting article vs. seat are mutually exclusive** — selecting one clears the other.

---

## Design Tokens

### Colors
```
Background:        #0a0a0f
Card background:   #1a1b1e
Border:            #373a40
Border subtle:     #2c2e33 / #1a1b1e
Text primary:      #e0e0e0
Text secondary:    #c1c2c5
Text dimmed:       #909296
Text muted:        #5c5f66

Cyan (primary):    #00d4ff
Lime (strong):     #39ff14
Amber (moderate):  #ffcc00
Red (weak/alert):  #ff3131

Selection bg:      #0d1f2a
Selection hover:   #1a3a4a
```

### Typography
All text: `font-family: 'JetBrains Mono', 'Courier New', monospace`

| Role | Size | Weight | Color |
|---|---|---|---|
| App title | 14px | 700 | #00d4ff |
| Section label | 10px | 700 | #5c5f66 |
| Article title | 12px | 600 | #e0e0e0 / #00d4ff |
| Body / summary | 11px | 400 | #c1c2c5 |
| Meta / date | 10px | 400 | #5c5f66 |
| Micro label | 9px | 400 | #5c5f66 |
| Seat name | 14px | 700 | #00d4ff |
| Confidence value | 12–15px | 700 | confidence colour |

### Spacing
Consistent 4px base unit. Common values: 4, 6, 8, 10, 12, 14, 16px.

### Border Radius
Cards/panels: 4px | Badges: 3px | Dots: 50% | Toggle pill: 9px

### Shadows
Selected card: `0 0 10px rgba(0,212,255,0.1)`
Popup/modal: `0 0 20–40px rgba(0,212,255,0.15–0.25)`

---

## Replacing Mock Data with Real API

The prototype uses `MOCK_ARTICLES`, `MOCK_SEATS`, `MOCK_WIKI_PAGES`, etc. from `mock-data.js`. Replace with existing hooks:

| Mock | Real hook (already in codebase) |
|---|---|
| `MOCK_ARTICLES` | `useArticles(refreshTrigger)` |
| `MOCK_SEATS` | `useSeatPredictions()` |
| `MOCK_WIKI_PAGES` | `useWikiPages()` |
| Article analyses | `fetch('/analyses?article_id={id}')` |
| Constituency history | `useHistorical(code)` |
| Constituency demographics | `useDemographics(code)` |
| Constituency articles | `useConstituencyArticles(code)` |

---

## Files in This Bundle

| File | Purpose |
|---|---|
| `Johor Election Monitor.html` | Root layout, App shell, Tweaks panel — **primary design reference** |
| `components.jsx` | TopBar, Scoreboard, ArticleCard, NewsFeedPanel, WikiModal, AgentPanel |
| `map-panel.jsx` | SVG cartogram map (replace with existing Leaflet ElectionMap in production) |
| `analysis-panel.jsx` | AnalysisPanel (6-lens tabs), SeatDetailPanel (4 tabs) |
| `mock-data.js` | All mock data — replace with real API hooks |

---

## GeoJSON Map Files

The real `ElectionMap.jsx` (Leaflet-based) is **already fully wired up** and requires no code changes. It fetches GeoJSON files at runtime from the Vite public directory.

**To activate the real map, place your GeoJSON files here:**
```
dashboard/public/geojson/johor-parlimen.geojson
dashboard/public/geojson/johor-dun.geojson
dashboard/public/geojson/johor_cartogram_parlimen_2022.geojson   ← optional
dashboard/public/geojson/johor_cartogram_dun_2022.geojson        ← optional
```

The component tries multiple GeoJSON property names for the constituency code, so your schema is flexible — it checks `constituency_code`, `code_parlimen`, `code_dun`, `code`, and `id` in that order.

Once the files are in place:
- **Parlimen/DUN toggle** → loads the correct file automatically
- **Cartogram toggle** → switches to `johor_cartogram_*` variant if present
- **Feature colours** → driven by `useSeatPredictions()` API data, matched by constituency code
- **Hover tooltip** → shows 2022 historical result + current prediction
- **Click** → fires `onConstituencySelect(code, name)` → opens `SeatDetailPanel`

The SVG cartogram grid in the prototype (`map-panel.jsx`) is a **stand-in only** — replace it entirely with the existing `ElectionMap.jsx` component.

---

## Notes for Claude Code

1. **The existing codebase already has all real components** — `ElectionMap.jsx`, `AnalysisPanel.jsx`, `SeatDetailPanel.jsx`, etc. The prototype is a **design target**, not a replacement. The task is to update those existing components to match this design.
2. **The map** in production uses Leaflet (`ElectionMap.jsx`) — keep it. The SVG cartogram in the prototype is a visual stand-in only.
3. **Mantine components** — use existing Mantine `<Tabs>`, `<Card>`, `<Badge>`, `<Button>` etc.; just override styles to match the design tokens above. The `theme.js` already has most tokens defined.
4. **DashboardShell layout** — the main change is the `grid-template-columns: 300px 1fr 360px` grid replacing the current flex layout. Also make article selection and seat selection mutually exclusive (deselect one when the other is selected).
5. **Agent panel** — currently partially implemented. Wire up `TaskMonitor` to the collapsible bottom bar as shown.
