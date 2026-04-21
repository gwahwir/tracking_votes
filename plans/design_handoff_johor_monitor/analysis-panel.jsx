// ── AnalysisPanel ─────────────────────────────────────────────────────────
const LENSES = [
  { id: 'political',      label: 'Political',    short: 'POL' },
  { id: 'demographic',    label: 'Demographic',  short: 'DEM' },
  { id: 'historical',     label: 'Historical',   short: 'HIST' },
  { id: 'strategic',      label: 'Strategic',    short: 'STRAT' },
  { id: 'factcheck',      label: 'Fact-Check',   short: 'FACT' },
  { id: 'bridget_welsh',  label: 'Welsh',        short: 'WELSH' },
];

const StrengthBar = ({ value }) => {
  const color = value >= 70 ? '#39ff14' : value >= 40 ? '#ffcc00' : '#ff3131';
  return (
    <div style={{ display:'flex', alignItems:'center', gap:'8px' }}>
      <div style={{ flex:1, height:'5px', background:'#1a1b1e', borderRadius:'3px', overflow:'hidden' }}>
        <div style={{ width:`${value}%`, height:'100%', background:color,
          backgroundImage:`linear-gradient(90deg, ${color}80, ${color})`, borderRadius:'3px',
          transition:'width 0.6s ease' }} />
      </div>
      <span style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', color, fontWeight:700, minWidth:'28px' }}>
        {Math.round(value)}%
      </span>
    </div>
  );
};

const LensContent = ({ data, lens }) => {
  if (!data) return (
    <div style={analysisStyles.lensEmpty}>No {lens.label.toLowerCase()} analysis available for this article.</div>
  );
  return (
    <div style={analysisStyles.lensBody}>
      {data.direction && (
        <div style={analysisStyles.lensRow}>
          <span style={analysisStyles.lensKey}>Direction</span>
          <span style={{ ...analysisStyles.lensVal, color:'#00d4ff', fontWeight:700, fontSize:'15px' }}>{data.direction}</span>
        </div>
      )}
      {data.strength != null && (
        <div style={analysisStyles.lensRow}>
          <span style={analysisStyles.lensKey}>Signal Strength</span>
          <div style={{ flex:1 }}><StrengthBar value={data.strength} /></div>
        </div>
      )}
      {data.summary && (
        <div style={analysisStyles.lensSummary}>
          <span style={analysisStyles.lensKey}>Summary</span>
          <p style={analysisStyles.summaryText}>{data.summary}</p>
        </div>
      )}
    </div>
  );
};

const AnalysisPanel = ({ article }) => {
  const [activeTab, setActiveTab] = React.useState('political');
  const analyses = article ? (SIGNAL_BREAKDOWN_TEMPLATES[article.analysisIdx] || SIGNAL_BREAKDOWN_TEMPLATES[0]) : null;

  if (!article) return (
    <div style={analysisStyles.panel}>
      <div style={analysisStyles.header}><span style={analysisStyles.headerLabel}>ANALYSIS</span></div>
      <div style={analysisStyles.empty}>
        <div style={analysisStyles.emptyIcon}>◈</div>
        <div style={analysisStyles.emptyText}>Select an article to see analysis</div>
      </div>
    </div>
  );

  return (
    <div style={analysisStyles.panel}>
      <div style={analysisStyles.header}>
        <span style={analysisStyles.headerLabel}>ANALYSIS</span>
        <span style={analysisStyles.articleTitle} title={article.title}>{article.title}</span>
      </div>
      <div style={analysisStyles.tabs}>
        {LENSES.map(l => (
          <button key={l.id} onClick={() => setActiveTab(l.id)}
            style={{ ...analysisStyles.tab, ...(activeTab === l.id ? analysisStyles.tabActive : {}) }}>
            {l.short}
          </button>
        ))}
      </div>
      <div style={analysisStyles.content}>
        {LENSES.map(l => activeTab === l.id && (
          <div key={l.id}>
            <div style={analysisStyles.lensTitle}>{l.label}</div>
            <LensContent data={analyses?.[l.id]} lens={l} />
          </div>
        ))}
      </div>
    </div>
  );
};

const analysisStyles = {
  panel: { display:'flex', flexDirection:'column', height:'100%', overflow:'hidden' },
  header: { padding:'10px 14px', borderBottom:'1px solid #373a40', flexShrink:0 },
  headerLabel: { fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', fontWeight:700,
    color:'#5c5f66', letterSpacing:'0.12em', display:'block' },
  articleTitle: { fontFamily:"'JetBrains Mono',monospace", fontSize:'11px', color:'#909296',
    display:'block', marginTop:'4px', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' },
  tabs: { display:'flex', borderBottom:'1px solid #373a40', flexShrink:0 },
  tab: { flex:1, padding:'7px 2px', background:'transparent', border:'none', borderBottom:'2px solid transparent',
    color:'#5c5f66', fontFamily:"'JetBrains Mono',monospace", fontSize:'9px', cursor:'pointer',
    letterSpacing:'0.05em', transition:'all 0.12s' },
  tabActive: { color:'#00d4ff', borderBottomColor:'#00d4ff', background:'rgba(0,212,255,0.05)' },
  content: { flex:1, overflowY:'auto', padding:'14px' },
  lensTitle: { fontFamily:"'JetBrains Mono',monospace", fontSize:'11px', fontWeight:700,
    color:'#00d4ff', marginBottom:'12px', letterSpacing:'0.08em' },
  lensBody: { display:'flex', flexDirection:'column', gap:'12px' },
  lensRow: { display:'flex', alignItems:'center', gap:'10px' },
  lensKey: { fontFamily:"'JetBrains Mono',monospace", fontSize:'9px', color:'#5c5f66',
    minWidth:'90px', letterSpacing:'0.05em', textTransform:'uppercase' },
  lensVal: { fontFamily:"'JetBrains Mono',monospace", fontSize:'13px', color:'#e0e0e0' },
  lensSummary: { display:'flex', flexDirection:'column', gap:'6px' },
  summaryText: { fontFamily:"'JetBrains Mono',monospace", fontSize:'11px', color:'#c1c2c5',
    lineHeight:1.65, margin:0 },
  lensEmpty: { fontFamily:"'JetBrains Mono',monospace", fontSize:'11px', color:'#5c5f66', padding:'16px 0' },
  empty: { flex:1, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:'10px', opacity:0.4 },
  emptyIcon: { fontSize:'28px', color:'#5c5f66' },
  emptyText: { fontFamily:"'JetBrains Mono',monospace", fontSize:'11px', color:'#5c5f66' },
};

// ── SeatDetailPanel ───────────────────────────────────────────────────────
const SeatDetailPanel = ({ seat, onClose }) => {
  const [activeTab, setActiveTab] = React.useState('overview');
  if (!seat) return null;

  const prediction = { ...seat, signal_breakdown: SIGNAL_BREAKDOWN_TEMPLATES[0], caveats: ['Data may be stale (>24h)'] };
  const partyColor = PARTY_COLORS[seat.party] || '#aaa';
  const confColor = seat.confidence >= 70 ? '#39ff14' : seat.confidence >= 40 ? '#ffcc00' : '#ff3131';
  const history = MOCK_HISTORY[seat.code] || MOCK_HISTORY['default'];

  const tabs = ['overview', 'history', 'demographics', 'articles'];

  return (
    <div style={seatStyles.panel}>
      <div style={seatStyles.header}>
        <div>
          <div style={seatStyles.name}>{seat.name}</div>
          <div style={seatStyles.code}>{seat.code}</div>
        </div>
        <button onClick={onClose} style={seatStyles.close}>✕</button>
      </div>
      <div style={{ ...seatStyles.predCard, borderLeftColor: partyColor }}>
        <div style={{ display:'flex', alignItems:'center', gap:'10px' }}>
          <span style={{ ...seatStyles.partyBadge, background: partyColor }}>{seat.party}</span>
          <span style={{ ...seatStyles.conf, color: confColor }}>{seat.confidence}% confidence</span>
        </div>
        <div style={seatStyles.predMeta}>Updated Apr 17, 2025 · Based on 4 articles</div>
      </div>
      <div style={seatStyles.tabs}>
        {tabs.map(t => (
          <button key={t} style={{ ...seatStyles.tab, ...(activeTab===t?seatStyles.tabActive:{}) }}
            onClick={() => setActiveTab(t)}>{t.toUpperCase()}</button>
        ))}
      </div>
      <div style={seatStyles.content}>
        {activeTab === 'overview' && (
          <div style={{ display:'flex', flexDirection:'column', gap:'14px' }}>
            <div>
              <div style={seatStyles.sectionLabel}>SIGNAL BREAKDOWN</div>
              {Object.entries(prediction.signal_breakdown).map(([lens, data]) => (
                <div key={lens} style={seatStyles.signalRow}>
                  <span style={seatStyles.signalLens}>{lens.replace('_', ' ')}</span>
                  <span style={{ ...seatStyles.signalDir, color: partyColor }}>{data.direction}</span>
                  <div style={{ flex:1, margin:'0 8px' }}><StrengthBar value={data.strength} /></div>
                </div>
              ))}
            </div>
            <div>
              <div style={seatStyles.sectionLabel}>CAVEATS</div>
              {prediction.caveats.map((c, i) => (
                <div key={i} style={seatStyles.caveat}>⚠ {c}</div>
              ))}
            </div>
          </div>
        )}
        {activeTab === 'history' && (
          <div>
            <div style={seatStyles.sectionLabel}>ELECTION HISTORY</div>
            <table style={{ width:'100%', borderCollapse:'collapse' }}>
              <thead>
                <tr>{['Year','Winner','Margin','Turnout'].map(h => (
                  <th key={h} style={seatStyles.th}>{h}</th>
                ))}</tr>
              </thead>
              <tbody>
                {history.map(r => (
                  <tr key={r.election_year} style={seatStyles.tr}>
                    <td style={seatStyles.td}>{r.election_year}</td>
                    <td style={{ ...seatStyles.td, color: PARTY_COLORS[r.winner] || '#aaa', fontWeight:700 }}>{r.winner}</td>
                    <td style={seatStyles.td}>{r.margin.toLocaleString()}</td>
                    <td style={seatStyles.td}>{r.turnout}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {activeTab === 'demographics' && (
          <div style={{ display:'flex', flexDirection:'column', gap:'10px' }}>
            <div style={seatStyles.sectionLabel}>VOTER DEMOGRAPHICS (est.)</div>
            {[['Malay', 58, '#3366cc'], ['Chinese', 28, '#33cc33'], ['Indian', 10, '#ff6633'], ['Other', 4, '#999']].map(([g, pct, c]) => (
              <div key={g} style={{ display:'flex', alignItems:'center', gap:'8px' }}>
                <span style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', color:'#909296', minWidth:55 }}>{g}</span>
                <div style={{ flex:1, height:'14px', background:'#1a1b1e', borderRadius:'2px', overflow:'hidden' }}>
                  <div style={{ width:`${pct}%`, height:'100%', background:c, opacity:0.7 }} />
                </div>
                <span style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', color:'#909296', minWidth:30 }}>{pct}%</span>
              </div>
            ))}
          </div>
        )}
        {activeTab === 'articles' && (
          <div style={{ display:'flex', flexDirection:'column', gap:'8px' }}>
            <div style={seatStyles.sectionLabel}>TAGGED ARTICLES</div>
            {MOCK_ARTICLES.filter(a => (a.constituency_ids||[]).includes(seat.code)).map(a => (
              <div key={a.id} style={seatStyles.articleItem}>
                <div style={seatStyles.articleTitle}>{a.title}</div>
                <div style={{ display:'flex', gap:'8px', marginTop:'3px' }}>
                  <span style={seatStyles.articleSource}>{a.source}</span>
                  {a.reliability_score != null && <ReliabilityBadge score={a.reliability_score} />}
                </div>
              </div>
            ))}
            {MOCK_ARTICLES.filter(a => (a.constituency_ids||[]).includes(seat.code)).length === 0 && (
              <div style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:'11px', color:'#5c5f66' }}>
                No articles tagged to this seat.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const seatStyles = {
  panel: { display:'flex', flexDirection:'column', height:'100%', overflow:'hidden' },
  header: { display:'flex', justifyContent:'space-between', alignItems:'flex-start', padding:'12px 14px',
    borderBottom:'1px solid #373a40', flexShrink:0 },
  name: { fontFamily:"'JetBrains Mono',monospace", fontSize:'14px', fontWeight:700, color:'#00d4ff' },
  code: { fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', color:'#5c5f66', marginTop:'2px' },
  close: { background:'none', border:'none', color:'#909296', fontSize:'14px', cursor:'pointer', padding:'2px 6px' },
  predCard: { margin:'10px 14px', padding:'10px 12px', background:'#1a1b1e', border:'1px solid #373a40',
    borderLeft:'3px solid', borderRadius:'4px', flexShrink:0 },
  partyBadge: { padding:'2px 10px', borderRadius:'3px', fontFamily:"'JetBrains Mono',monospace",
    fontSize:'11px', fontWeight:700, color:'#000' },
  conf: { fontFamily:"'JetBrains Mono',monospace", fontSize:'12px', fontWeight:700 },
  predMeta: { fontFamily:"'JetBrains Mono',monospace", fontSize:'9px', color:'#5c5f66', marginTop:'6px' },
  tabs: { display:'flex', borderBottom:'1px solid #373a40', flexShrink:0 },
  tab: { flex:1, padding:'7px 2px', background:'transparent', border:'none', borderBottom:'2px solid transparent',
    color:'#5c5f66', fontFamily:"'JetBrains Mono',monospace", fontSize:'8px', cursor:'pointer',
    letterSpacing:'0.05em', transition:'all 0.12s' },
  tabActive: { color:'#00d4ff', borderBottomColor:'#00d4ff', background:'rgba(0,212,255,0.05)' },
  content: { flex:1, overflowY:'auto', padding:'14px' },
  sectionLabel: { fontFamily:"'JetBrains Mono',monospace", fontSize:'9px', color:'#5c5f66',
    letterSpacing:'0.12em', marginBottom:'10px', paddingBottom:'4px', borderBottom:'1px solid #1a1b1e' },
  signalRow: { display:'flex', alignItems:'center', gap:'6px', padding:'4px 0', borderBottom:'1px solid #1a1b1e' },
  signalLens: { fontFamily:"'JetBrains Mono',monospace", fontSize:'9px', color:'#909296', minWidth:'80px', textTransform:'capitalize' },
  signalDir: { fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', fontWeight:700, minWidth:'50px' },
  caveat: { fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', color:'#ff3131', padding:'4px 0' },
  th: { fontFamily:"'JetBrains Mono',monospace", fontSize:'9px', color:'#5c5f66', textAlign:'left',
    padding:'4px 6px', letterSpacing:'0.08em' },
  tr: { borderBottom:'1px solid #1a1b1e' },
  td: { fontFamily:"'JetBrains Mono',monospace", fontSize:'11px', color:'#c1c2c5', padding:'6px 6px' },
  articleItem: { padding:'8px', background:'#1a1b1e', borderRadius:'3px', border:'1px solid #2c2e33' },
  articleTitle: { fontFamily:"'JetBrains Mono',monospace", fontSize:'11px', color:'#e0e0e0', lineHeight:1.4 },
  articleSource: { fontFamily:"'JetBrains Mono',monospace", fontSize:'9px', color:'#5c5f66', textTransform:'uppercase' },
};

Object.assign(window, { AnalysisPanel, SeatDetailPanel });
