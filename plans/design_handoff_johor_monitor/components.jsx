
// ── TopBar ─────────────────────────────────────────────────────────────────
const TopBar = ({ mapType, useCartogram, onMapTypeChange, onCartogramToggle, onRefresh, onWikiOpen, refreshing }) => {
  const [pulse, setPulse] = React.useState(true);
  React.useEffect(() => { const t = setInterval(() => setPulse(p => !p), 1000); return () => clearInterval(t); }, []);
  return (
    <div style={topBarStyles.bar}>
      <div style={topBarStyles.left}>
        <span style={topBarStyles.title}>JOHOR ELECTION MONITOR</span>
      </div>
      <div style={topBarStyles.center}>
        <div style={topBarStyles.liveBadge}>
          <span style={{ ...topBarStyles.liveDot, opacity: pulse ? 1 : 0.3 }} />
          LIVE
        </div>
      </div>
      <div style={topBarStyles.right}>
        <div style={topBarStyles.toggleGroup}>
          <button style={{ ...topBarStyles.toggleBtn, ...(mapType === 'parlimen' ? topBarStyles.toggleActive : {}) }}
            onClick={() => onMapTypeChange('parlimen')}>Parlimen</button>
          <button style={{ ...topBarStyles.toggleBtn, ...(mapType === 'dun' ? topBarStyles.toggleActive : {}) }}
            onClick={() => onMapTypeChange('dun')}>DUN</button>
        </div>
        <button title={useCartogram ? 'Regular Map' : 'Cartogram'} onClick={onCartogramToggle}
          style={{ ...topBarStyles.iconBtn, ...(useCartogram ? topBarStyles.iconBtnActive : {}) }}>⊞</button>
        <button title="Refresh" onClick={onRefresh} style={topBarStyles.iconBtn}
          className={refreshing ? 'spin' : ''}>↻</button>
        <button title="Wiki" onClick={onWikiOpen} style={topBarStyles.iconBtn}>⊟</button>
      </div>
    </div>
  );
};

const topBarStyles = {
  bar: { display:'flex', alignItems:'center', justifyContent:'space-between', padding:'0 1rem', height:'48px',
    background:'#0a0a0f', borderBottom:'1px solid #373a40', flexShrink:0 },
  left: { flex:'0 0 auto' },
  title: { fontFamily:"'JetBrains Mono',monospace", fontWeight:700, fontSize:'14px', color:'#00d4ff', letterSpacing:'0.12em' },
  center: { flex:'0 0 auto' },
  liveBadge: { display:'flex', alignItems:'center', gap:'6px', padding:'3px 10px', border:'1px solid #39ff14',
    borderRadius:'3px', color:'#39ff14', fontSize:'11px', fontWeight:700, letterSpacing:'0.15em' },
  liveDot: { width:'7px', height:'7px', borderRadius:'50%', background:'#39ff14', transition:'opacity 0.3s' },
  right: { display:'flex', alignItems:'center', gap:'8px' },
  toggleGroup: { display:'flex', border:'1px solid #373a40', borderRadius:'4px', overflow:'hidden' },
  toggleBtn: { padding:'4px 12px', background:'transparent', border:'none', color:'#909296',
    fontFamily:"'JetBrains Mono',monospace", fontSize:'11px', cursor:'pointer', letterSpacing:'0.05em' },
  toggleActive: { background:'#1a3a4a', color:'#00d4ff' },
  iconBtn: { width:'32px', height:'32px', background:'#1a1b1e', border:'1px solid #373a40', borderRadius:'4px',
    color:'#909296', cursor:'pointer', fontSize:'16px', display:'flex', alignItems:'center', justifyContent:'center' },
  iconBtnActive: { background:'#1a3a4a', color:'#00d4ff', borderColor:'#00d4ff' },
};

// ── Scoreboard ────────────────────────────────────────────────────────────
const Scoreboard = ({ seats }) => {
  const counts = {};
  seats.forEach(s => { counts[s.party] = (counts[s.party] || 0) + 1; });
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const MAJORITY = Math.floor(seats.length / 2) + 1;
  return (
    <div style={scoreStyles.bar}>
      {sorted.map(([party, count]) => (
        <div key={party} style={scoreStyles.item}>
          <span style={{ ...scoreStyles.dot, background: PARTY_COLORS[party] || '#666' }} />
          <span style={{ ...scoreStyles.party, color: PARTY_COLORS[party] || '#aaa' }}>{party}</span>
          <span style={scoreStyles.count}>{count}</span>
        </div>
      ))}
      <div style={scoreStyles.majority}>
        <span style={scoreStyles.majLabel}>Majority: {MAJORITY}</span>
        <span style={scoreStyles.majSub}>{seats.length} seats predicted</span>
      </div>
    </div>
  );
};
const scoreStyles = {
  bar: { display:'flex', alignItems:'center', gap:'16px', padding:'6px 16px', background:'#0d0d14',
    borderBottom:'1px solid #373a40', flexShrink:0, overflowX:'auto' },
  item: { display:'flex', alignItems:'center', gap:'5px', flexShrink:0 },
  dot: { width:'8px', height:'8px', borderRadius:'2px' },
  party: { fontFamily:"'JetBrains Mono',monospace", fontSize:'11px', fontWeight:700 },
  count: { fontFamily:"'JetBrains Mono',monospace", fontSize:'13px', fontWeight:700, color:'#fff' },
  majority: { marginLeft:'auto', display:'flex', gap:'12px', flexShrink:0 },
  majLabel: { fontFamily:"'JetBrains Mono',monospace", fontSize:'11px', color:'#00d4ff' },
  majSub: { fontFamily:"'JetBrains Mono',monospace", fontSize:'11px', color:'#5c5f66' },
};

// ── ReliabilityBadge ──────────────────────────────────────────────────────
const ReliabilityBadge = ({ score }) => {
  if (score === null || score === undefined) return null;
  const color = score >= 70 ? '#39ff14' : score >= 40 ? '#ffcc00' : '#ff3131';
  const bg = score >= 70 ? 'rgba(57,255,20,0.1)' : score >= 40 ? 'rgba(255,204,0,0.1)' : 'rgba(255,49,49,0.1)';
  const stars = Math.round(score / 20);
  return (
    <div style={{ display:'flex', alignItems:'center', gap:'6px' }}>
      <div style={{ width:'60px', height:'4px', background:'#2c2e33', borderRadius:'2px', overflow:'hidden' }}>
        <div style={{ width:`${score}%`, height:'100%', background:color, borderRadius:'2px' }} />
      </div>
      <span style={{ fontSize:'10px', color, fontFamily:"'JetBrains Mono',monospace", fontWeight:700 }}>{score}%</span>
    </div>
  );
};

// ── ArticleCard ───────────────────────────────────────────────────────────
const ArticleCard = ({ article, isSelected, onSelect }) => {
  const [hovered, setHovered] = React.useState(false);
  const fmtDate = (d) => new Date(d).toLocaleDateString('en-MY', { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' });
  const ids = article.constituency_ids || [];
  const shown = ids.slice(0, 2).join(', ');
  const extra = ids.length > 2 ? ` +${ids.length - 2}` : '';
  return (
    <div onClick={onSelect} onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
      style={{ ...cardStyles.card, ...(isSelected ? cardStyles.selected : hovered ? cardStyles.hovered : {}) }}>
      <div style={{ ...cardStyles.title, color: isSelected ? '#00d4ff' : '#e0e0e0' }}>{article.title}</div>
      <div style={cardStyles.meta}>
        <span style={cardStyles.source}>{article.source}</span>
        <span style={cardStyles.date}>{fmtDate(article.created_at)}</span>
      </div>
      {article.reliability_score != null && <ReliabilityBadge score={article.reliability_score} />}
      {shown && <div style={cardStyles.tags}>◈ {shown}{extra}</div>}
      <div style={cardStyles.actions}>
        <button onClick={(e) => { e.stopPropagation(); onSelect(); }}
          style={{ ...cardStyles.btn, ...(isSelected ? cardStyles.btnActive : {}) }}>
          {isSelected ? '✓ Selected' : 'Select'}
        </button>
        <button style={cardStyles.btnSecondary} onClick={e => e.stopPropagation()}>
          {article.reliability_score != null ? 'Scored' : 'Score'}
        </button>
      </div>
    </div>
  );
};
const cardStyles = {
  card: { padding:'10px 12px', background:'#1a1b1e', border:'1px solid #373a40', borderRadius:'4px',
    cursor:'pointer', transition:'all 0.15s ease', display:'flex', flexDirection:'column', gap:'6px' },
  hovered: { borderColor:'#5c5f66', background:'#1e1f23' },
  selected: { borderColor:'#00d4ff', background:'#0d1f2a', boxShadow:'0 0 10px rgba(0,212,255,0.1)' },
  title: { fontFamily:"'JetBrains Mono',monospace", fontSize:'12px', fontWeight:600, lineHeight:1.4,
    display:'-webkit-box', WebkitLineClamp:2, WebkitBoxOrient:'vertical', overflow:'hidden' },
  meta: { display:'flex', justifyContent:'space-between', gap:'4px' },
  source: { fontSize:'10px', color:'#5c5f66', fontFamily:"'JetBrains Mono',monospace", textTransform:'uppercase' },
  date: { fontSize:'10px', color:'#5c5f66', fontFamily:"'JetBrains Mono',monospace" },
  tags: { fontSize:'10px', color:'#00d4ff', fontFamily:"'JetBrains Mono',monospace" },
  actions: { display:'flex', gap:'6px', marginTop:'2px' },
  btn: { flex:1, padding:'4px', background:'rgba(0,212,255,0.1)', border:'1px solid #00d4ff40',
    borderRadius:'3px', color:'#00d4ff', fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', cursor:'pointer' },
  btnActive: { background:'#00d4ff', color:'#000', fontWeight:700 },
  btnSecondary: { flex:1, padding:'4px', background:'rgba(57,255,20,0.07)', border:'1px solid #39ff1430',
    borderRadius:'3px', color:'#39ff14', fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', cursor:'pointer' },
};

// ── NewsFeedPanel ─────────────────────────────────────────────────────────
const NewsFeedPanel = ({ articles, selectedId, onSelect }) => (
  <div style={feedStyles.panel}>
    <div style={feedStyles.header}>
      <span style={feedStyles.label}>NEWS FEED</span>
      <span style={feedStyles.badge}>{articles.length}</span>
    </div>
    <div style={feedStyles.scroll}>
      <div style={feedStyles.list}>
        {articles.map(a => (
          <ArticleCard key={a.id} article={a} isSelected={selectedId === a.id} onSelect={() => onSelect(a)} />
        ))}
      </div>
    </div>
  </div>
);
const feedStyles = {
  panel: { display:'flex', flexDirection:'column', height:'100%', overflow:'hidden' },
  header: { display:'flex', alignItems:'center', gap:'8px', padding:'10px 14px', borderBottom:'1px solid #373a40', flexShrink:0 },
  label: { fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', fontWeight:700, color:'#5c5f66', letterSpacing:'0.12em' },
  badge: { background:'#1a1b1e', border:'1px solid #373a40', borderRadius:'10px', padding:'1px 7px',
    fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', color:'#909296' },
  scroll: { flex:1, overflowY:'auto', overflowX:'hidden' },
  list: { display:'flex', flexDirection:'column', gap:'6px', padding:'10px' },
};

// ── WikiModal ─────────────────────────────────────────────────────────────
const WikiModal = ({ onClose }) => {
  const [search, setSearch] = React.useState('');
  const filtered = MOCK_WIKI_PAGES.filter(p =>
    p.title.toLowerCase().includes(search.toLowerCase()) || p.path.toLowerCase().includes(search.toLowerCase())
  );
  return (
    <div style={wikiStyles.overlay} onClick={onClose}>
      <div style={wikiStyles.modal} onClick={e => e.stopPropagation()}>
        <div style={wikiStyles.header}>
          <span style={wikiStyles.title}>⊟ WIKI KNOWLEDGE BASE</span>
          <button onClick={onClose} style={wikiStyles.close}>✕</button>
        </div>
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search pages..."
          style={wikiStyles.search} />
        <div style={wikiStyles.list}>
          {filtered.map(p => (
            <div key={p.path} style={wikiStyles.item}>
              <div style={wikiStyles.pageTitle}>{p.title}</div>
              <div style={wikiStyles.pageMeta}>
                <span style={wikiStyles.pagePath}>{p.path}</span>
                <span style={wikiStyles.pageDate}>{new Date(p.updated_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
          {filtered.length === 0 && <div style={wikiStyles.empty}>No pages found</div>}
        </div>
      </div>
    </div>
  );
};
const wikiStyles = {
  overlay: { position:'fixed', inset:0, background:'rgba(0,0,0,0.8)', zIndex:1000, display:'flex', alignItems:'center', justifyContent:'center' },
  modal: { width:'540px', maxHeight:'80vh', background:'#0a0a0f', border:'1px solid #373a40', borderRadius:'6px',
    display:'flex', flexDirection:'column', boxShadow:'0 0 40px rgba(0,212,255,0.15)' },
  header: { display:'flex', justifyContent:'space-between', alignItems:'center', padding:'14px 16px', borderBottom:'1px solid #373a40' },
  title: { fontFamily:"'JetBrains Mono',monospace", fontSize:'12px', fontWeight:700, color:'#00d4ff', letterSpacing:'0.1em' },
  close: { background:'none', border:'none', color:'#909296', fontSize:'14px', cursor:'pointer' },
  search: { margin:'10px 16px', padding:'7px 10px', background:'#1a1b1e', border:'1px solid #373a40',
    borderRadius:'4px', color:'#e0e0e0', fontFamily:"'JetBrains Mono',monospace", fontSize:'12px', outline:'none' },
  list: { overflowY:'auto', padding:'0 8px 10px' },
  item: { padding:'8px 8px', borderBottom:'1px solid #1a1b1e', cursor:'pointer' },
  pageTitle: { fontFamily:"'JetBrains Mono',monospace", fontSize:'12px', color:'#e0e0e0', marginBottom:'3px' },
  pageMeta: { display:'flex', justifyContent:'space-between' },
  pagePath: { fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', color:'#5c5f66' },
  pageDate: { fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', color:'#5c5f66' },
  empty: { padding:'20px', textAlign:'center', color:'#5c5f66', fontFamily:"'JetBrains Mono',monospace", fontSize:'12px' },
};

// ── AgentPanel ────────────────────────────────────────────────────────────
const AgentPanel = ({ tasks }) => {
  const statusColor = { completed:'#39ff14', running:'#00d4ff', pending:'#5c5f66', error:'#ff3131' };
  const [tick, setTick] = React.useState(0);
  React.useEffect(() => { const t = setInterval(() => setTick(x => x+1), 800); return () => clearInterval(t); }, []);
  return (
    <div style={agentStyles.panel}>
      <div style={agentStyles.header}>
        <span style={agentStyles.title}>AGENT MONITOR</span>
        <span style={agentStyles.taskCount}>{tasks.length} tasks</span>
      </div>
      <div style={agentStyles.tasks}>
        {tasks.map((task, i) => (
          <div key={task.id} style={agentStyles.task}>
            <div style={{ ...agentStyles.statusDot, background: statusColor[task.status],
              opacity: task.status === 'running' ? (tick % 2 === 0 ? 1 : 0.4) : 1 }} />
            <span style={{ ...agentStyles.agent, color: task.status === 'running' ? '#00d4ff' : '#909296' }}>{task.agent}</span>
            <span style={agentStyles.msg}>{task.message}</span>
            <span style={agentStyles.ts}>{task.ts}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
const agentStyles = {
  panel: { background:'#0a0a0f', borderTop:'1px solid #373a40', padding:'8px 12px' },
  header: { display:'flex', alignItems:'center', gap:'8px', marginBottom:'6px' },
  title: { fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', fontWeight:700, color:'#5c5f66', letterSpacing:'0.12em' },
  taskCount: { fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', color:'#5c5f66' },
  tasks: { display:'flex', flexDirection:'column', gap:'4px' },
  task: { display:'flex', alignItems:'center', gap:'8px', padding:'4px 0' },
  statusDot: { width:'6px', height:'6px', borderRadius:'50%', flexShrink:0, transition:'opacity 0.2s' },
  agent: { fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', fontWeight:700, minWidth:'120px' },
  msg: { fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', color:'#5c5f66', flex:1 },
  ts: { fontFamily:"'JetBrains Mono',monospace", fontSize:'10px', color:'#373a40' },
};

Object.assign(window, { TopBar, Scoreboard, ReliabilityBadge, ArticleCard, NewsFeedPanel, WikiModal, AgentPanel });
