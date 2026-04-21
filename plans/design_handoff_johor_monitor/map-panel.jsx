// ── MapPanel ──────────────────────────────────────────────────────────────
// SVG cartogram-style constituency grid for Johor

const SEAT_LAYOUT = [
  // [code, col, row]  — 6 cols × 6 rows, geographic approximation
  ['P.155', 0, 0], ['P.156', 1, 0], ['P.140', 2, 0], ['P.141', 3, 0], ['P.142', 4, 0], ['P.158', 5, 0],
  ['P.143', 0, 1], ['P.144', 1, 1], ['P.145', 2, 1], ['P.146', 3, 1],
  ['P.157', 0, 2], ['P.154', 1, 2], ['P.147', 2, 2], ['P.148', 3, 2], ['P.149', 4, 2], ['P.150', 5, 2],
  ['P.163', 0, 3],                                                       ['P.151', 4, 3], ['P.152', 5, 3],
  ['P.164', 0, 4],                                                                        ['P.153', 5, 4],
  ['P.165', 0, 5], ['P.160', 1, 5], ['P.162', 2, 5], ['P.159', 3, 5], ['P.161', 4, 5],
];

const REGION_LABELS = [
  { label: 'NORTH', col: 2.5, row: -0.4 },
  { label: 'WEST', col: -0.5, row: 3.5 },
  { label: 'CENTRAL', col: 2.5, row: 2 },
  { label: 'EAST', col: 5.6, row: 3 },
  { label: 'SOUTH', col: 2, row: 5.7 },
];

const getConfidenceStroke = (confidence) => {
  if (confidence >= 70) return { color: '#39ff14', width: 3 };
  if (confidence >= 40) return { color: '#ffcc00', width: 2.5 };
  return { color: '#ff3131', width: 2 };
};

const CELL_W = 76, CELL_H = 58, GAP = 5;
const SVG_W = 6 * (CELL_W + GAP) + 40;
const SVG_H = 6 * (CELL_H + GAP) + 60;

const MapPanel = ({ mapType, useCartogram, seats, onSeatClick, selectedCode }) => {
  const [hoveredCode, setHoveredCode] = React.useState(null);
  const seatMap = {};
  seats.forEach(s => { seatMap[s.code] = s; });

  // For DUN mode, show placeholder message
  if (mapType === 'dun') {
    return (
      <div style={mapStyles.panel}>
        <div style={mapStyles.header}>
          <span style={mapStyles.label}>INTERACTIVE MAP</span>
          <span style={mapStyles.sublabel}>DUN · 56 state seats</span>
        </div>
        <div style={mapStyles.dunPlaceholder}>
          <div style={mapStyles.placeholderBox}>
            <div style={mapStyles.placeholderIcon}>⊞</div>
            <div style={mapStyles.placeholderText}>DUN VIEW</div>
            <div style={mapStyles.placeholderSub}>56 state constituency seats · toggle to Parlimen for full data</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={mapStyles.panel}>
      <div style={mapStyles.header}>
        <span style={mapStyles.label}>INTERACTIVE MAP</span>
        <span style={mapStyles.sublabel}>{useCartogram ? 'CARTOGRAM' : 'PARLIMEN'} · 26 seats · click to inspect</span>
      </div>
      <div style={mapStyles.svgWrap}>
        <svg width="100%" viewBox={`-20 -20 ${SVG_W} ${SVG_H}`} style={{ maxHeight: '100%' }}>
          {/* Region labels */}
          {REGION_LABELS.map(r => (
            <text key={r.label} x={r.col * (CELL_W + GAP) + CELL_W / 2} y={r.row * (CELL_H + GAP) + CELL_H / 2}
              textAnchor="middle" dominantBaseline="middle"
              style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:8, fill:'#373a40', letterSpacing:2, userSelect:'none' }}>
              {r.label}
            </text>
          ))}
          {/* Seats */}
          {SEAT_LAYOUT.map(([code, col, row]) => {
            const seat = seatMap[code];
            if (!seat) return null;
            const x = col * (CELL_W + GAP);
            const y = row * (CELL_H + GAP);
            const partyColor = PARTY_COLORS[seat.party] || '#444';
            const stroke = getConfidenceStroke(seat.confidence);
            const isSelected = selectedCode === code;
            const isHovered = hoveredCode === code;
            return (
              <g key={code} onClick={() => onSeatClick(seat)}
                onMouseEnter={() => setHoveredCode(code)}
                onMouseLeave={() => setHoveredCode(null)}
                style={{ cursor: 'pointer' }}>
                {/* Glow layer when selected */}
                {isSelected && (
                  <rect x={x-3} y={y-3} width={CELL_W+6} height={CELL_H+6}
                    rx={4} fill="none" stroke="#00d4ff" strokeWidth={2} opacity={0.5} />
                )}
                {/* Background */}
                <rect x={x} y={y} width={CELL_W} height={CELL_H} rx={3}
                  fill={partyColor} fillOpacity={isHovered ? 0.5 : isSelected ? 0.6 : 0.25}
                  stroke={isSelected ? '#00d4ff' : stroke.color}
                  strokeWidth={isSelected ? 2.5 : stroke.width}
                  style={{ transition: 'all 0.12s ease' }} />
                {/* Party strip */}
                <rect x={x} y={y} width={CELL_W} height={4} rx={2} fill={partyColor} fillOpacity={0.9} />
                {/* Code */}
                <text x={x + 5} y={y + 16} style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:8, fill:'#909296', userSelect:'none' }}>
                  {code}
                </text>
                {/* Name */}
                <text x={x + CELL_W/2} y={y + 32} textAnchor="middle"
                  style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:9, fill:'#e0e0e0', fontWeight:600, userSelect:'none' }}>
                  {seat.name.length > 10 ? seat.name.slice(0,10)+'…' : seat.name}
                </text>
                {/* Party badge */}
                <text x={x + CELL_W/2} y={y + 45} textAnchor="middle"
                  style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:8, fill:partyColor, fontWeight:700, userSelect:'none' }}>
                  {seat.party}
                </text>
                {/* Confidence */}
                <text x={x + CELL_W - 4} y={y + 16} textAnchor="end"
                  style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:7.5, fill: stroke.color, userSelect:'none' }}>
                  {seat.confidence}%
                </text>
              </g>
            );
          })}
          {/* Legend */}
          {[['≥70% Strong','#39ff14'], ['40–69% Moderate','#ffcc00'], ['<40% Weak','#ff3131']].map(([label, color], i) => (
            <g key={label} transform={`translate(${i * 130}, ${SVG_H - 28})`}>
              <rect width={8} height={8} rx={1} fill={color} fillOpacity={0.3} stroke={color} strokeWidth={1.5} />
              <text x={12} y={8} style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:8, fill:'#5c5f66', userSelect:'none' }}>{label}</text>
            </g>
          ))}
        </svg>
        {/* Hovered tooltip */}
        {hoveredCode && seatMap[hoveredCode] && (
          <div style={mapStyles.tooltip}>
            <span style={mapStyles.ttCode}>{hoveredCode}</span>
            <span style={mapStyles.ttName}>{seatMap[hoveredCode].name}</span>
            <span style={{ ...mapStyles.ttParty, color: PARTY_COLORS[seatMap[hoveredCode].party] || '#aaa' }}>
              {seatMap[hoveredCode].party}
            </span>
            <span style={mapStyles.ttConf}>{seatMap[hoveredCode].confidence}% confident</span>
          </div>
        )}
      </div>
    </div>
  );
};

const mapStyles = {
  panel: { display:'flex', flexDirection:'column', height:'100%', overflow:'hidden' },
  header: { display:'flex', alignItems:'center', gap:'10px', padding:'10px 14px', borderBottom:'1px solid #373a40', flexShrink:0 },
  label: { fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', fontWeight:700, color:'#5c5f66', letterSpacing:'0.12em' },
  sublabel: { fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', color:'#373a40' },
  svgWrap: { flex:1, overflow:'hidden', padding:'10px', position:'relative', display:'flex', alignItems:'center', justifyContent:'center' },
  tooltip: { position:'absolute', bottom:'16px', right:'16px', background:'#0a0a0f', border:'1px solid #00d4ff',
    borderRadius:'4px', padding:'8px 12px', display:'flex', flexDirection:'column', gap:'2px',
    boxShadow:'0 0 20px rgba(0,212,255,0.25)', pointerEvents:'none' },
  ttCode: { fontFamily:"'JetBrains Mono',monospace", fontSize:'9px', color:'#5c5f66' },
  ttName: { fontFamily:"'JetBrains Mono',monospace", fontSize:'12px', color:'#fff', fontWeight:700 },
  ttParty: { fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', fontWeight:700 },
  ttConf: { fontFamily:"'JetBrains Mono',monospace", fontSize:'9px', color:'#909296' },
  dunPlaceholder: { flex:1, display:'flex', alignItems:'center', justifyContent:'center' },
  placeholderBox: { display:'flex', flexDirection:'column', alignItems:'center', gap:'8px', opacity:0.35 },
  placeholderIcon: { fontSize:'40px', color:'#373a40' },
  placeholderText: { fontFamily:"'JetBrains Mono',monospace", fontSize:'13px', color:'#5c5f66', letterSpacing:'0.15em' },
  placeholderSub: { fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', color:'#5c5f66', textAlign:'center' },
};

Object.assign(window, { MapPanel });
