# TopBar Refresh Button — Testing Guide

**Date:** 2026-04-17  
**Status:** Refresh button wired to news_agent scrape task

---

## What Was Changed

### DashboardShell.jsx Updated
- Imported `useDispatchTask` hook
- `handleRefresh()` now dispatches `news_agent` scrape task with message:
  ```
  "Scrape the latest news articles about Johor elections and Malaysian politics."
  ```
- On task dispatch:
  1. **Agent panel opens automatically** 
  2. **TaskMonitor shows live scrape progress**
  3. After 2 seconds, **articles refresh** in feed
- Error handling included

---

## Test Steps

### 1. Open Dashboard
```
http://localhost:5174
```
Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)

### 2. Click Refresh Button 🔄
- Located in TopBar (top-right area)
- Button should show rotation animation while working
- Agent panel should **automatically open**
- **TaskMonitor should appear** showing live output

### 3. Watch the Task Stream
You should see `NODE_OUTPUT::` lines like:
```
NODE_OUTPUT::fetch::Scraping RSS feeds...
NODE_OUTPUT::fetch::Found 12 articles from The Star
NODE_OUTPUT::filter::Filtering by Johor keywords...
NODE_OUTPUT::tag::Tagging constituencies...
NODE_OUTPUT::upsert::Storing in database...
```

### 4. Wait for Completion
- Status badge should change from "Running" to "Completed"
- Articles should appear in the **NEWS FEED** panel (left side)
- Feed should auto-refresh with new articles

---

## Expected Result

### ✅ Success Looks Like:
```
NEWS FEED panel shows:
├─ Article 1
│  Source: thestar.com.my
│  Constituencies: P.150, P.151, ...
│  [Select] [Score]
├─ Article 2
│  Source: malaysiakini.com
│  ...
└─ Article N
```

### 🔴 If Nothing Happens:
1. Check browser console (F12 → Console tab)
2. Look for error messages
3. Verify control plane is healthy: `curl http://localhost:8000/health`
4. Check if news_agent is registered: `curl http://localhost:8000/graph`

---

## Next Steps After Success

Once articles appear in the feed:

### 1. **Test Scoring Pipeline**
   - Click "Score" button on any article
   - Watch TaskMonitor show scorer_agent running
   - Reliability score appears on article

### 2. **Test Auto-Chain** (TODO - not yet implemented)
   - After scoring → auto-trigger analyst_agent
   - After analysis → auto-trigger seat_agent
   - Map updates with predictions

### 3. **Test Full Workflow**
   - Scrape → Score → Analyze → Predict → Visualize

---

## Technical Details

### Task Dispatch Message
```javascript
{
  role: 'user',
  parts: [
    {
      type: 'text',
      text: 'Scrape the latest news articles about Johor elections and Malaysian politics.'
    }
  ]
}
```

### Agent Response
- news_agent receives task via A2A protocol
- Calls all scrapers (RSS, NewsAPI, etc.) in parallel
- Filters by keywords (Johor, election, candidates, etc.)
- Tags articles with constituency codes
- Stores in PostgreSQL articles table
- Streams `NODE_OUTPUT::node::message` for each step

### UI Flow
1. User clicks refresh → `handleRefresh()` called
2. `dispatchTask('news_agent', message)` dispatches task
3. Control plane routes to news_agent
4. WebSocket connection to `/ws/tasks/{taskId}` established
5. TaskMonitor streams output in real-time
6. After 2 seconds, `setRefreshTrigger()` causes articles to re-fetch
7. NewsFeedPanel polls `/articles` endpoint
8. Articles appear in feed

---

## Timing Notes

- **Scrape task:** 5-15 seconds (depends on network)
- **Auto-refresh delay:** 2 seconds after dispatch (gives scraper time to store)
- **Articles fetch:** Immediate when `refreshTrigger` changes
- **Agent panel auto-open:** Instant

---

## Video Walkthrough (if needed)

1. Open http://localhost:5174
2. Click 🔄 refresh button
3. Watch agent panel open with TaskMonitor
4. See `NODE_OUTPUT::` lines stream
5. Wait for "Completed" badge
6. Verify articles appear in NEWS FEED

---

Ready to test? Click the refresh button and watch the magic happen! 🎬
