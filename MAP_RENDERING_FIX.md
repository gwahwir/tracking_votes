# Map Rendering Fix

**Issue:** Map loaded but GeoJSON features were not visible (blacked out/dark areas, no boundaries)  
**Causes:** 
1. Feature property mismatch (`constituency_code` vs `code_parlimen`/`code_dun`)
2. Very low opacity (0.2) making features invisible
3. Missing Leaflet CSS import

**Solutions Applied:**

## 1. Property Name Fix (ElectionMap.jsx)
Changed feature code lookup to handle actual GeoJSON properties:
```javascript
// Before:
const code = feature.properties?.constituency_code || ...

// After:
const code = feature.properties?.constituency_code || 
             feature.properties?.code_parlimen || 
             feature.properties?.code_dun || 
             feature.properties?.code || 
             feature.properties?.id
```

GeoJSON actually contains:
- `code_parlimen`: "P.140" (for Parlimen map)
- `code_dun`: (for DUN map)
- `parlimen`: "P.140 Segamat" (full name)

## 2. Opacity & Visibility Fix (ElectionMap.jsx)
Increased visibility of features without predictions:
```javascript
// Before:
opacity: 0.3,
fillOpacity: 0.2,

// After:
opacity: 0.7,
fillOpacity: 0.4,
```

This makes constituency boundaries clearly visible instead of blending into the dark background.

## 3. Leaflet CSS Import (index.css)
Added Leaflet stylesheet import:
```css
@import 'leaflet/dist/leaflet.css';
```

This ensures map controls and elements render correctly.

## 4. Display Name Fix (ElectionMap.jsx)
Updated name fallback to use actual properties:
```javascript
// Before:
const name = feature.properties?.name || feature.properties?.NAME || code

// After:
const name = feature.properties?.name || 
             feature.properties?.NAME || 
             feature.properties?.parlimen || 
             feature.properties?.dun || 
             code
```

## What You Should See Now

After refreshing http://localhost:5174:

✅ **GeoJSON boundaries visible** — Clear gray lines showing constituencies  
✅ **Constituency names** — When you click a feature, it shows the correct name  
✅ **Interactive features** — Click any boundary to see popup  
✅ **Map controls** — Zoom/pan controls visible  
✅ **Toggle buttons work** — Parlimen/DUN and cartogram toggle  
✅ **No more black areas** — Proper rendering without dark spots  

## How to Verify Fix

1. **Hard refresh browser** (Ctrl+Shift+R or Cmd+Shift+R)
2. **Map should load with visible boundaries** (gray lines on dark background)
3. **Click any constituency** → Popup appears with name and code
4. **Toggle "Parlimen"/"DUN"** → Map reloads with different constituencies
5. **Toggle cartogram** 🗺️ → Map reloads with cartogram variant
6. **Zoom/pan** → Works smoothly

## Technical Details

**Property lookup order:**
1. `constituency_code` (if manually added)
2. `code_parlimen` (Parlimen GeoJSON)
3. `code_dun` (DUN GeoJSON)
4. `code` (fallback)
5. `id` (fallback)

**Name lookup order:**
1. `name` (if present)
2. `NAME` (if present)
3. `parlimen` (Parlimen full name, e.g., "P.140 Segamat")
4. `dun` (DUN full name, if present)
5. `code` (fallback)

**Styling (no predictions):**
- Border: #666666 (gray), weight 2px
- Fill: #444444 (dark gray), opacity 40%
- Makes features clearly visible without overwhelming

---

**The map should now render correctly with visible constituency boundaries.**
