// Mock data for Johor Election Monitor prototype

const PARTY_COLORS = {
  'BN': '#3366cc',
  'UMNO': '#3366cc',
  'DAP': '#33cc33',
  'PKR': '#ff6633',
  'PN': '#ff3333',
  'PAS': '#00aa00',
  'Amanah': '#ffcc00',
  'Bersatu': '#990000',
  'Independent': '#999999',
  'No Data': '#444444',
};

const MOCK_SEATS = [
  { code: 'P.140', name: 'Ledang', party: 'BN', confidence: 82, mapType: 'parlimen', region: 'north' },
  { code: 'P.141', name: 'Bakri', party: 'DAP', confidence: 76, mapType: 'parlimen', region: 'north' },
  { code: 'P.142', name: 'Muar', party: 'BN', confidence: 68, mapType: 'parlimen', region: 'north' },
  { code: 'P.143', name: 'Parit Sulong', party: 'BN', confidence: 71, mapType: 'parlimen', region: 'north' },
  { code: 'P.144', name: 'Ayer Hitam', party: 'BN', confidence: 55, mapType: 'parlimen', region: 'north' },
  { code: 'P.145', name: 'Sri Gading', party: 'BN', confidence: 63, mapType: 'parlimen', region: 'west' },
  { code: 'P.146', name: 'Batu Pahat', party: 'DAP', confidence: 88, mapType: 'parlimen', region: 'west' },
  { code: 'P.147', name: 'Simpang Renggam', party: 'PN', confidence: 72, mapType: 'parlimen', region: 'west' },
  { code: 'P.148', name: 'Kluang', party: 'DAP', confidence: 79, mapType: 'parlimen', region: 'central' },
  { code: 'P.149', name: 'Sembrong', party: 'BN', confidence: 84, mapType: 'parlimen', region: 'central' },
  { code: 'P.150', name: 'Mersing', party: 'BN', confidence: 67, mapType: 'parlimen', region: 'east' },
  { code: 'P.151', name: 'Tenggara', party: 'PAS', confidence: 58, mapType: 'parlimen', region: 'east' },
  { code: 'P.152', name: 'Kota Tinggi', party: 'BN', confidence: 73, mapType: 'parlimen', region: 'east' },
  { code: 'P.153', name: 'Pengerang', party: 'BN', confidence: 77, mapType: 'parlimen', region: 'east' },
  { code: 'P.154', name: 'Bekok', party: 'PN', confidence: 44, mapType: 'parlimen', region: 'central' },
  { code: 'P.155', name: 'Segamat', party: 'DAP', confidence: 81, mapType: 'parlimen', region: 'north' },
  { code: 'P.156', name: 'Sekijang', party: 'BN', confidence: 60, mapType: 'parlimen', region: 'north' },
  { code: 'P.157', name: 'Labis', party: 'BN', confidence: 65, mapType: 'parlimen', region: 'central' },
  { code: 'P.158', name: 'Pagoh', party: 'Bersatu', confidence: 91, mapType: 'parlimen', region: 'north' },
  { code: 'P.159', name: 'Johor Bahru', party: 'DAP', confidence: 85, mapType: 'parlimen', region: 'south' },
  { code: 'P.160', name: 'Pulai', party: 'PKR', confidence: 70, mapType: 'parlimen', region: 'south' },
  { code: 'P.161', name: 'Gelang Patah', party: 'DAP', confidence: 86, mapType: 'parlimen', region: 'south' },
  { code: 'P.162', name: 'Kulai', party: 'DAP', confidence: 75, mapType: 'parlimen', region: 'south' },
  { code: 'P.163', name: 'Pontian', party: 'BN', confidence: 59, mapType: 'parlimen', region: 'west' },
  { code: 'P.164', name: 'Tanjung Piai', party: 'BN', confidence: 52, mapType: 'parlimen', region: 'west' },
  { code: 'P.165', name: 'Iskandar Puteri', party: 'PKR', confidence: 66, mapType: 'parlimen', region: 'south' },
];

const SIGNAL_BREAKDOWN_TEMPLATES = [
  { political: { direction: 'BN', strength: 78, summary: 'Strong UMNO machinery active in the constituency, recent ceramah attendance up 30%.' },
    demographic: { direction: 'BN', strength: 65, summary: 'Malay majority seat at 72%. Youth voter registration increased significantly.' },
    historical: { direction: 'BN', strength: 80, summary: 'BN has held this seat for 4 consecutive elections. 2018 was closest at 1,200 margin.' },
    strategic: { direction: 'BN', strength: 70, summary: 'Incumbent advantage strong. Opposition split between PKR and PN candidates.' },
    factcheck: { direction: 'NEUTRAL', strength: 55, summary: '2 of 4 viral claims checked; one misleading narrative around local infrastructure debunked.' },
    bridget_welsh: { direction: 'BN', strength: 72, summary: 'Historical patterns favour BN in low-income rural Malay seats; swing unlikely to exceed 5%.' }
  },
  { political: { direction: 'DAP', strength: 88, summary: 'DAP candidate is incumbent with strong service record. Active ground presence since Jan 2025.' },
    demographic: { direction: 'DAP', strength: 82, summary: 'Chinese majority at 61%. High-density urban area. Voter turnout historically 78%+.' },
    historical: { direction: 'DAP', strength: 90, summary: 'DAP stronghold since 2008. Won with 15,000+ majority in GE15.' },
    strategic: { direction: 'DAP', strength: 85, summary: 'BN running a weaker candidate. No significant PN presence in this urban seat.' },
    factcheck: { direction: 'NEUTRAL', strength: 60, summary: 'Allegations of voter roll manipulation investigated — found unsubstantiated.' },
    bridget_welsh: { direction: 'DAP', strength: 87, summary: 'Urban DAP seats in Johor show resilience despite national headwinds. Margin stable.' }
  },
  { political: { direction: 'PN', strength: 62, summary: 'PAS mobilisation increasing in semi-rural areas. Bersatu grassroots recovering post-GE15.' },
    demographic: { direction: 'PN', strength: 58, summary: 'Mixed Malay-Chinese seat. New voters from nearby township development may tilt balance.' },
    historical: { direction: 'BN', strength: 55, summary: 'BN held 2013–2022 but with declining margins. 2022 result was within 800 votes.' },
    strategic: { direction: 'UNCERTAIN', strength: 45, summary: 'Three-way contest likely. Vote splitting could benefit either BN or PN.' },
    factcheck: { direction: 'NEUTRAL', strength: 40, summary: 'One claim about candidate background flagged as potentially misleading.' },
    bridget_welsh: { direction: 'UNCERTAIN', strength: 48, summary: 'Contested seats with multi-party races historically unpredictable. Watch turnout differential.' }
  }
];

const MOCK_ARTICLES = [
  {
    id: 1, title: 'BN machinery revs up in Johor ahead of by-election season', source: 'thestarms',
    created_at: '2025-04-17T08:30:00Z', reliability_score: 72,
    constituency_ids: ['P.140', 'P.142', 'P.143'], analysisIdx: 0,
    url: '#', summary: 'UMNO division leaders confirm full mobilisation of grassroots volunteers...'
  },
  {
    id: 2, title: 'DAP Johor holds town hall in Batu Pahat, draws 3,000 crowd', source: 'malaysiakini',
    created_at: '2025-04-16T14:15:00Z', reliability_score: 85,
    constituency_ids: ['P.146', 'P.141'], analysisIdx: 1,
    url: '#', summary: 'The packed town hall signals strong ground support for DAP...'
  },
  {
    id: 3, title: 'PN targets swing seats in Johor\'s semi-rural corridors', source: 'freemalaysiatoday',
    created_at: '2025-04-16T09:00:00Z', reliability_score: 61,
    constituency_ids: ['P.147', 'P.154'], analysisIdx: 2,
    url: '#', summary: 'Perikatan Nasional strategists identified 6 winnable seats in Johor...'
  },
  {
    id: 4, title: 'Pagoh voters remain loyal to Muhyiddin despite legal battles', source: 'thestarms',
    created_at: '2025-04-15T11:20:00Z', reliability_score: 68,
    constituency_ids: ['P.158'], analysisIdx: 0,
    url: '#', summary: 'On-the-ground interviews in Pagoh suggest Muhyiddin\'s personal vote remains strong...'
  },
  {
    id: 5, title: 'Johor Bahru development projects boost DAP incumbents, say analysts', source: 'malaymail',
    created_at: '2025-04-15T08:45:00Z', reliability_score: 77,
    constituency_ids: ['P.159', 'P.161', 'P.162'], analysisIdx: 1,
    url: '#', summary: 'Infrastructure improvements in JB linked to DAP-led ministry credited to incumbents...'
  },
  {
    id: 6, title: 'Tanjung Piai voters split over MUDA candidate announcement', source: 'malaysiakini',
    created_at: '2025-04-14T16:30:00Z', reliability_score: 55,
    constituency_ids: ['P.164'], analysisIdx: 2,
    url: '#', summary: 'MUDA\'s surprise candidate announcement divides opinion among younger voters...'
  },
  {
    id: 7, title: 'New voter registration surges in Iskandar Puteri ahead of polling', source: 'bernama',
    created_at: '2025-04-14T10:00:00Z', reliability_score: 91,
    constituency_ids: ['P.165', 'P.160'], analysisIdx: 1,
    url: '#', summary: 'SPR reports 8,000 new voters registered in Iskandar Puteri since January 2025...'
  },
  {
    id: 8, title: 'Mersing fishing community voices concern over coastal development policy', source: 'freemalaysiatoday',
    created_at: '2025-04-13T13:45:00Z', reliability_score: 48,
    constituency_ids: ['P.150'], analysisIdx: 0,
    url: '#', summary: 'Fisherfolk in Mersing express frustration with development plan affecting traditional fishing grounds...'
  },
  {
    id: 9, title: 'Analysis: Johor\'s electoral geography shifting in post-GE15 landscape', source: 'thevibes',
    created_at: '2025-04-12T09:30:00Z', reliability_score: 83,
    constituency_ids: ['P.140', 'P.148', 'P.155', 'P.159'], analysisIdx: 2,
    url: '#', summary: 'Demographic shifts and internal party dynamics reshaping traditional strongholds...'
  },
  {
    id: 10, title: 'PAS claims moral high ground in rural Johor campaign blitz', source: 'harakahdaily',
    created_at: '2025-04-11T15:00:00Z', reliability_score: 38,
    constituency_ids: ['P.151', 'P.150'], analysisIdx: 2,
    url: '#', summary: 'PAS Johor commissioner declares party ready to contest 15 state seats...'
  },
];

const MOCK_WIKI_PAGES = [
  { path: 'johor/overview', title: 'Johor State Overview', updated_at: '2025-04-15T00:00:00Z' },
  { path: 'johor/demographics', title: 'Johor Electoral Demographics', updated_at: '2025-04-14T00:00:00Z' },
  { path: 'parties/bn-umno', title: 'BN/UMNO in Johor', updated_at: '2025-04-13T00:00:00Z' },
  { path: 'parties/dap', title: 'DAP Johor Division', updated_at: '2025-04-13T00:00:00Z' },
  { path: 'parties/pn', title: 'Perikatan Nasional Johor', updated_at: '2025-04-12T00:00:00Z' },
  { path: 'analysis/bridget-welsh', title: 'Bridget Welsh Framework', updated_at: '2025-04-10T00:00:00Z' },
  { path: 'constituencies/p158-pagoh', title: 'P.158 Pagoh Constituency Profile', updated_at: '2025-04-11T00:00:00Z' },
  { path: 'constituencies/p159-jb', title: 'P.159 Johor Bahru Constituency Profile', updated_at: '2025-04-11T00:00:00Z' },
  { path: 'history/ge15-results', title: 'GE15 Johor Results', updated_at: '2025-04-09T00:00:00Z' },
  { path: 'history/ge14-results', title: 'GE14 Johor Results', updated_at: '2025-04-09T00:00:00Z' },
  { path: 'methodology/reliability-scoring', title: 'Article Reliability Scoring', updated_at: '2025-04-08T00:00:00Z' },
  { path: 'methodology/signal-lenses', title: 'The 6-Lens Analysis Framework', updated_at: '2025-04-08T00:00:00Z' },
];

const MOCK_HISTORY = {
  'P.146': [
    { election_year: 2022, winner: 'DAP', margin: 15234, turnout: 79 },
    { election_year: 2018, winner: 'DAP', margin: 12890, turnout: 82 },
    { election_year: 2013, winner: 'DAP', margin: 8450, turnout: 85 },
    { election_year: 2008, winner: 'DAP', margin: 3200, turnout: 78 },
  ],
  'P.158': [
    { election_year: 2022, winner: 'Bersatu', margin: 8901, turnout: 74 },
    { election_year: 2018, winner: 'Bersatu', margin: 14200, turnout: 80 },
    { election_year: 2013, winner: 'BN', margin: 7800, turnout: 77 },
  ],
  'default': [
    { election_year: 2022, winner: 'BN', margin: 4100, turnout: 72 },
    { election_year: 2018, winner: 'PKR', margin: 2300, turnout: 76 },
    { election_year: 2013, winner: 'BN', margin: 5600, turnout: 80 },
  ]
};

const MOCK_TASKS = [
  { id: 'task_001', agent: 'news_agent', status: 'completed', message: 'Scraped 12 articles from 4 sources', ts: '08:32' },
  { id: 'task_002', agent: 'scorer_agent', status: 'completed', message: 'Scored article #7: reliability 91%', ts: '08:33' },
  { id: 'task_003', agent: 'analyst_agent', status: 'running', message: 'Running political lens analysis on P.159...', ts: '08:35' },
  { id: 'task_004', agent: 'predictor_agent', status: 'pending', message: 'Awaiting analyst_agent completion', ts: '08:35' },
];

Object.assign(window, { PARTY_COLORS, MOCK_SEATS, MOCK_ARTICLES, MOCK_WIKI_PAGES, MOCK_HISTORY, MOCK_TASKS, SIGNAL_BREAKDOWN_TEMPLATES });
