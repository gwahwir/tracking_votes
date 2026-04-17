# Phase 6 Testing Guide

**Date:** 2026-04-17  
**Status:** Agent panel layout fixed, ready for end-to-end testing

---

## Layout Fixes Applied

✅ **Agent panel now properly integrated** into flex layout  
✅ **Full agent topology visible** in agent panel  
✅ **No more overlapping elements**  
✅ **Panel resizes content above gracefully**

### What Changed
- Removed fixed positioning of agent panel
- Panel now part of main flex container (320px fixed height)
- AgentGraph and TaskMonitor styled for proper scaling
- Panel header reduced to single line

---

## Testing Steps

### 1. Open Dashboard
```
http://localhost:5174
```

### 2. Click "▲ AGENTS" Button
- Button is in bottom-right corner
- Agent panel should slide up from bottom
- Should take up ~320px height
- 3-column map should shrink proportionally

### 3. Verify Agent Topology
- **Header:** "Agent Topology • 6 agents"
- **Main area:** Should show circular graph with:
  - Control plane in center
  - 5 agents in circle around it
  - Animated edges between them
  - Each node labeled with agent name

### 4. Verify Agent Legend
- Below graph, should show list of agents:
  - Green dot = healthy
  - Red dot = down
  - Task count per agent
  - Last seen time

### 5. Test Scoring Workflow
1. Scroll **NEWS FEED** panel on left
2. If articles present, click **"Score"** button on any article
3. Agent panel should switch to **TaskMonitor** automatically
4. Should show:
   - Task ID and status (Running/Completed)
   - Live `NODE_OUTPUT::` stream
   - Color-coded node badges
   - Spinner while running

### 6. Switch Back to Topology
- Close agent panel (click "▼ AGENTS" button)
- Reopen (click "▲ AGENTS" button)
- Should see full topology again

---

## Expected Behavior

### Agent Panel Open
- 3-column layout shrinks to fit above agent panel
- Map still fully interactive
- News feed and analysis panels still scrollable
- Panel takes fixed 320px at bottom

### Agent Panel Closed
- Full height available for 3-column layout
- Agent button visible in bottom-right corner
- Clicking button opens panel

### TaskMonitor Mode
- Appears when article is scored
- Shows live streaming output
- Each NODE_OUTPUT line has colored badge
- Scrollable log area

### AgentGraph Mode
- Shows full agent topology
- Updates health status in real-time
- Legend shows all agents

---

## Troubleshooting

### Graph not visible in agent panel?
- Check browser console for errors
- Verify `npm run build` completed successfully
- Hard refresh: Ctrl+Shift+R or Cmd+Shift+R

### Panel overlapping content?
- Window size may be too small
- Try maximizing browser window
- Responsive breakpoint at 900px stacks panels

### No articles in feed?
- This is expected on cold start
- Need to:
  1. Dispatch a news_agent scrape task
  2. Wait for articles to appear
  3. Then test scoring workflow

---

## Next Steps After Testing

Once agent panel works correctly:

1. **Wire TopBar Refresh button**
   - Should dispatch `news_agent` scrape task
   - Auto-populate feed with articles

2. **Auto-chain tasks**
   - After scoring completes → trigger analyst
   - After analyst completes → trigger seat agent
   - Updates map with predictions

3. **Map interactions**
   - Click constituency → show prediction popup
   - Popup shows 6-lens signal breakdown

4. **Full workflow test**
   - Scrape → Score → Analyze → Predict → Visualize

---

## File Changes

### Modified
- `dashboard/src/components/layout/DashboardShell.jsx` — Changed to div flex layout
- `dashboard/src/components/layout/DashboardShell.css` — Agent panel flex sizing
- `dashboard/src/components/agents/AgentGraph.css` — Removed borders, full width
- `dashboard/src/components/agents/TaskMonitor.css` — Removed borders, full width

### Built
- All components rebuild successfully
- Bundle size: 674 kB (210 kB gzipped)

---

## Refresh Instructions

If you don't see changes in browser:

1. **Hard refresh the page:**
   - Mac: Cmd + Shift + R
   - Windows: Ctrl + Shift + R
   - Or: Ctrl + F5

2. **Check console for errors:**
   - F12 → Console tab
   - Should see no red errors

3. **Verify dev server is running:**
   ```bash
   curl http://localhost:5173
   ```
   Should return HTML

---

Ready to test? Open http://localhost:5174 and click the "▲ AGENTS" button!
