# Johor Election Monitor Dashboard Layout

## Visual Structure

```
┌────────────────────────────────────────────────────────────────────────┐
│  JOHOR ELECTION MONITOR                    [LIVE]  [Parlimen/DUN] 🗺️ 🔄📚 │  TopBar
├──────────────────────────┬────────────────────────────┬────────────────┤
│                          │                            │                │
│  NEWS FEED (320px)       │  INTERACTIVE MAP (flex)    │  ANALYSIS (400)│
│  ┌────────────────────┐  │  ┌────────────────────┐    │  ┌──────────┐ │
│  │ [6 articles]       │  │  │ 🗺️ Johor           │    │  │ 6 Lenses │ │
│  │                    │  │  │                    │    │  │          │ │
│  │ ★★★★★ Article 1   │  │  │ Features colored   │    │  │ Political│ │
│  │ 72% reliability    │  │  │ by prediction      │    │  │ Demog... │ │
│  │ P.157, N.01        │  │  │                    │    │  │ Hist...  │ │
│  │ [Select]           │  │  │ Click for popup ↓  │    │  │ Strat... │ │
│  │                    │  │  │                    │    │  │ FactChk..│ │
│  │ ★★★☆☆ Article 2   │  │  │┌──────────────────┐│    │  │ Welsh... │ │
│  │ 52% reliability    │  │  ││ Constituency XYZ  ││    │  │          │ │
│  │ P.158              │  │  ││ DAP 74% confident││    │  │ Selected│ │
│  │ [Select]           │  │  ││ Signal breakdown: ││    │  │ signals │ │
│  │                    │  │  ││ Political: 80%    ││    │  │ display │ │
│  │                    │  │  ││ Demographic: 70%  ││    │  │          │ │
│  │ (scroll...)        │  │  ││ [Close ✕]        ││    │  └──────────┘ │
│  │                    │  │  │└──────────────────┘│    │                │
│  │                    │  │  │                    │    │  [Analysis    │
│  │                    │  │  │ [Parlimen/DUN]    │    │   empty if no  │
│  │                    │  │  │ [Cartogram toggle]│    │   article]     │
│  │                    │  │  │                    │    │                │
│  └────────────────────┘  │  └────────────────────┘    │  └────────────┘ │
│                          │                            │                │
│                          │                            │                │
│                          │ [Constituency Popup       │                │
│                          │  showing prediction +     │                │
│                          │  signal breakdown]        │                │
│                          │                            │                │
├──────────────────────────┴────────────────────────────┴────────────────┤
│                        [Agent Graph & Task Monitor]                     │
│  (collapsible, shows topology + real-time task updates — Phase 6)     │
└────────────────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### TopBar
- **Left**: "JOHOR ELECTION MONITOR" title in cyan
- **Center**: Status badge (LIVE with pulse animation)
- **Right**: 
  - Map type toggle (Parlimen / DUN buttons)
  - Cartogram toggle (🗺️ button switches regular↔cartogram)
  - Refresh button (🔄)
  - Wiki button (📚 opens knowledge base modal)

### Left Column: News Feed (320px)
- Header: "News Feed" badge with count
- Scrollable ArticleCard stack
- Each card shows:
  - **Title** (2-line clamp)
  - **Source** (TheStarMY, Malaysiakini, etc.)
  - **Date** (formatted as "Apr 17, 08:30")
  - **Reliability Badge** (Green ≥70%, Yellow 40–69%, Red <40%)
  - **Constituency Tags** (P.157, N.01, etc., +N more if >2)
  - **Select Button** (visual feedback when selected)

### Center Column: Interactive Map (flex-grow)
- **Basemap**: CartoDB Dark Matter tiles
- **GeoJSON Layer**: Johor boundaries (parlimen or DUN)
- **Feature Styling**:
  - **Fill**: Party colour (BN=blue, DAP=green, PN=red, PKR=orange, etc.)
  - **Border**: Confidence ring
    - Green (4px) if confidence ≥70% (strong)
    - Amber (3px) if confidence 40–69% (moderate)
    - Red (2px) if confidence <40% (weak)
  - **No Data**: Gray fill, thin border
- **Cartogram Toggle**: Switch between:
  - Regular GeoJSON (constituency boundaries)
  - Parlimen cartogram (electorate-weighted, 2022)
  - Cartogram variants (equal-area, etc.)
- **Popup**: Click constituency → shows:
  - Constituency name + code
  - Leading party badge
  - Confidence percentage
  - **Signal Breakdown Table** (6 lenses):
    - Political: direction + strength + summary
    - Demographic: direction + strength + summary
    - Historical: direction + strength + summary
    - Strategic: direction + strength + summary
    - Fact-check: flags + summary
    - Welsh: direction + strength + summary
  - **Caveats** (red-flagged warnings if any)
  - **Article count** ("Based on N articles")

### Right Column: Analysis Panel (400px)
- Header: "Analysis" with icon
- **If no article selected**: "Select an article to see analysis" (gray text)
- **If article selected with analyses**:
  - **6 Lens Tabs**: Political | Demographic | Historical | Strategic | FactCheck | Welsh
  - **Tab Content** (per lens):
    - **Direction**: Leading party/signal (e.g., "DAP" in cyan)
    - **Signal Strength**: Gradient bar (cyan→green) + percentage
    - **Summary**: Narrative from LLM (scrollable if long)
  - **Empty state per lens**: "No [lens] analysis available"
- **If analyses loading**: Spinner + "Loading..."
- **If error**: Yellow alert box with error message

## Data Flow

### Article Selection
1. User clicks article in feed
2. ArticleCard highlights (cyan border)
3. Selection triggers `onArticleSelect(article)` in DashboardShell
4. `selectedArticle` state updates
5. AnalysisPanel fetches analyses for that article
6. Tabs populate with 6-lens results

### Constituency Interaction
1. User clicks feature on map
2. Feature highlights (border brightens)
3. Popup appears (bottom-right, semi-transparent)
4. Shows full prediction + signal breakdown
5. Click [Close ✕] or click map elsewhere to hide

### Map Type Toggle
1. User clicks "Parlimen" or "DUN" button in TopBar
2. `mapType` state changes
3. ElectionMap re-loads GeoJSON file (`johor-{parlimen|dun}.geojson`)
4. Features re-style with new predictions

### Cartogram Toggle
1. User clicks 🗺️ button in TopBar
2. `useCartogram` state flips
3. ElectionMap filename changes:
   - Regular: `johor-{parlimen|dun}.geojson`
   - Cartogram: `johor_cartogram_{parlimen|electorate}_2022.geojson`
4. New GeoJSON loads, features re-render

### Refresh
1. User clicks 🔄 button in TopBar
2. `refreshTrigger` counter increments
3. All `useEffect` dependencies trigger refetch
4. `useArticles()`, `useSeatPredictions()` all call `.refetch()`
5. Entire UI updates with latest data

### Wiki
1. User clicks 📚 button in TopBar
2. `wikiOpen` state → true
3. WikiModal appears with searchable page list
4. User can search by title/path
5. Click [X] or outside to close

## Responsive Behavior

### Desktop (≥1600px)
- 3-column grid: 320px | flex | 400px
- All panels visible simultaneously
- Full map interaction

### Tablet (1200–1600px)
- 3-column grid: 280px | flex | 350px
- Columns slightly narrower

### Small Tablet (900–1200px)
- Stack: feed (300px) → map (400px) → analysis (300px)
- Single column, scroll vertically
- Each section has min-height

### Mobile (<900px)
- Single column
- feed (100vw, ~300px tall)
- map (100vw, ~400px tall)
- analysis (100vw, ~300px tall)
- All scrollable
- TopBar wraps to 2 lines if needed

## Colour Scheme

**Background**: `#0a0a0f` (near black)  
**Text**: `#fff` (white)  
**Borders**: `#373a40` (dark gray)  
**Primary (Cyan)**: `#00d4ff`  
**Secondary (Lime)**: `#39ff14`  
**Alert (Red)**: `#ff3131`

**Party Colours**:
- BN/UMNO: `#3366cc` (blue)
- DAP: `#33cc33` (green)
- PKR: `#ff6633` (orange)
- PN: `#ff3333` (red)
- PAS: `#00aa00` (dark green)
- Amanah: `#ffcc00` (yellow)
- Bersatu: `#990000` (dark red)
- Independent: `#999999` (gray)

## Animation & Effects

- **Status pulse**: Green indicator blinks when LIVE
- **Card hover**: Cyan border, slight lift effect
- **Tab transition**: Smooth fade between lenses
- **Strength bar**: Gradient fill animation on load
- **Popup shadow**: Neon cyan glow `0 0 20px rgba(0, 212, 255, 0.3)`

## Accessibility

- **Keyboard navigation**: Tab through buttons, enter to interact
- **Colour contrast**: All text meets WCAG AA
- **ARIA labels**: Buttons have titles/tooltips
- **Responsive**: Touch-friendly button sizes on mobile
- **Semantic HTML**: Nav, main, section landmarks

---

## Example Workflow

1. **User opens dashboard** → Map shows Johor, feed is empty, analysis panel empty
2. **User clicks 📚 wiki button** → WikiModal opens, shows seed pages
3. **Dashboard refreshes via API** → Articles appear in feed (news_agent ran)
4. **User selects first article** → Analysis panel loads 6 lenses from analyst_agent
5. **User clicks constituency on map** → Popup shows prediction + signals
6. **User toggles cartogram** → Map redraw with MECO cartogram variant
7. **User switches to DUN** → Map zooms/pans, shows 56 DUN seats instead of 26 Parlimen
8. **User hovers article card** → Cyan glow feedback
9. **User clicks "Parlimen" button** → Back to 26-seat map

---

This layout is production-ready and fully responsive. Phase 6 will add:
- Agent topology graph visualization (bottom panel)
- Real-time task monitor with streaming updates
- Wiki context badges showing which pages informed each analysis
