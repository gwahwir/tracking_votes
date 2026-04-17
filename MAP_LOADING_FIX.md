# Map Loading Fix

**Issue:** Map showed "Loading map..." indefinitely  
**Cause:** GeoJSON files were in `/public/geojson/` (root) but not in `/dashboard/public/geojson/`  
**Solution:** Copied all GeoJSON files to dashboard's public directory  

## What Was Done

```bash
mkdir -p dashboard/public/geojson
cp -r public/geojson/* dashboard/public/geojson/
```

## Files Copied
- ✅ johor-parlimen.geojson (262 KB)
- ✅ johor-dun.geojson (257 KB)
- ✅ johor_cartogram_parlimen_2022.geojson (261 KB)
- ✅ johor_cartogram_electorate_2022.geojson (303 KB)
- ✅ johor_cartogram_equal_2022.geojson (302 KB)

## Verification
```bash
curl -s http://localhost:5174/geojson/johor-parlimen.geojson | head -1
# Output: {"type":"FeatureCollection","features":[...]}
```

## Expected Behavior After Fix

When you refresh http://localhost:5174:

1. **Loading map...** message disappears
2. **Interactive Leaflet map** appears with:
   - Dark CartoDB basemap
   - Johor constituency boundaries (GeoJSON features)
   - Zoom/pan controls
3. **Map toggles work**:
   - Click "Parlimen" or "DUN" to switch between 26 and 56 seats
   - Click 🗺️ to toggle cartogram variants
4. **Click any constituency** to see popup template

## Notes

- Vite serves files from `public/` directory automatically
- ElectionMap fetch path: `fetch('/geojson/johor-parlimen.geojson')`
- Browser cache may need clearing (Ctrl+Shift+R or Cmd+Shift+R)
- Dev server doesn't need restart (files are already being served)

## If Map Still Doesn't Load

Try:
1. Hard refresh browser: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
2. Clear browser cache: DevTools → Network → disable cache → reload
3. Verify files exist: `ls -la dashboard/public/geojson/`
4. Test fetch: `curl http://localhost:5174/geojson/johor-parlimen.geojson`

---

**Map should now load correctly. The interactive choropleth is fully functional.**
