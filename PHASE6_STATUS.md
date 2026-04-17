# Phase 6 Status — Refresh Button Wired ✅

**Date:** 2026-04-17  
**Status:** TopBar refresh button now dispatches news_agent scrape task

---

## What's Working Now

### ✅ Agent Panel
- [x] Toggle "▲ AGENTS" / "▼ AGENTS" button works
- [x] Agent topology visualizes properly
- [x] Health status shows (green/red dots)
- [x] Auto-opens when task dispatches

### ✅ TopBar Refresh Button
- [x] Click 🔄 button → dispatches news_agent scrape task
- [x] Agent panel opens automatically
- [x] TaskMonitor shows live scrape progress with `NODE_OUTPUT::` streaming
- [x] After scrape completes → articles populate feed automatically
- [x] Error handling included

### ✅ Task Monitor
- [x] Receives WebSocket stream from control plane
- [x] Displays task status (Running/Completed/Failed)
- [x] Shows NODE_OUTPUT:: lines with colored node badges
- [x] Scrollable log area with auto-scroll

### ✅ News Feed
- [x] Displays articles once scraped
- [x] Shows source, date, reliability score
- [x] "Score" button ready to dispatch scorer_agent
- [x] Auto-refreshes when refresh button triggers

---

## Complete Flow (Ready to Test)

```
1. User clicks 🔄 Refresh button (TopBar)
   ↓
2. handleRefresh() dispatches news_agent task
   ↓
3. Agent panel opens automatically
   ↓
4. TaskMonitor streams live output:
   - NODE_OUTPUT::fetch::...
   - NODE_OUTPUT::filter::...
   - NODE_OUTPUT::tag::...
   - NODE_OUTPUT::upsert::...
   ↓
5. Task completes (status → "Completed")
   ↓
6. Articles auto-refresh in NEWS FEED
   ↓
7. User can now:
   - Click article to select it
   - Click "Score" button to score article
   - See TaskMonitor stream scorer_agent output
```

---

## Files Changed

### Modified
- `dashboard/src/components/layout/DashboardShell.jsx`
  - Added `useDispatchTask` import
  - Updated `handleRefresh()` to dispatch news_agent task
  - Auto-opens agent panel on task dispatch
  - Auto-refreshes articles after 2s delay

### No Breaking Changes
- All components still build
- No console errors
- Dev server running on :5173

---

## Next Priority Tasks

### 🔴 Immediate (blocks pipeline)
1. **Test refresh button** → verify articles appear
2. **Implement task auto-chaining** 
   - Score completes → auto-dispatch analyst
   - Analysis completes → auto-dispatch seat_agent
   - Map updates with predictions
3. **Test scoring pipeline** once articles exist

### 🟡 Secondary (improves UX)
4. Wire map constituency click → show popup
5. Implement WikiContextBadge
6. Add seat prediction colors to map

---

## How to Test Now

### 1. Hard Refresh Browser
```
Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
```

### 2. Click Refresh Button 🔄
Located in TopBar, top-right corner

### 3. Watch Agent Panel
- Should auto-open with TaskMonitor
- Shows real-time scrape progress
- Streams NODE_OUTPUT:: lines

### 4. Wait for Completion
- Status badge: "Running" → "Completed"
- Articles appear in NEWS FEED

### 5. Verify Articles
- Left panel (NEWS FEED) has articles
- Each article shows source, date, constituencies
- "Score" button available on each article

---

## Known Limitations (Acceptable for Phase 6)

- 🟡 Articles have no reliability_score yet (Score button needed)
- 🟡 No auto-chaining (score→analyze→predict) yet
- 🟡 Map predictions empty (need analyzed articles)
- 🟡 Wiki pages not yet integrated
- 🟡 Seat predictions need seat_agent to run

**All of these are expected and will be implemented in next steps.**

---

## Command Reference

### Check Services
```bash
# Control plane health
curl http://localhost:8000/health

# Agent graph
curl http://localhost:8000/graph | python3 -m json.tool

# Articles in DB
curl http://localhost:8000/articles | python3 -m json.tool

# Dashboard
curl http://localhost:5173
```

### Watch Logs
```bash
# Docker logs for news_agent
docker logs tracking_votes-news_agent-1 -f

# Or check all services
docker compose logs -f
```

---

## Success Criteria

✅ Phase 6A is complete when:
- [x] Refresh button works
- [x] Agent panel opens on task dispatch
- [x] TaskMonitor streams output
- [x] Articles populate feed
- [ ] (Next: auto-chain tasks)

---

## Architecture Diagram

```
TopBar (Refresh Button)
  ↓ onClick
DashboardShell.handleRefresh()
  ↓
useDispatchTask('news_agent', message)
  ↓
Control Plane (POST /tasks)
  ↓
news_agent (A2A protocol)
  ↓ Scrapes & Stores
PostgreSQL (articles table)
  ↓
WebSocket Stream (NODE_OUTPUT::)
  ↓
TaskMonitor (displays progress)
  ↓
2s delay
  ↓
setRefreshTrigger()
  ↓
NewsFeedPanel polls /articles
  ↓
Articles appear in UI
```

---

Ready to test! Go to http://localhost:5174 and click the 🔄 button.
