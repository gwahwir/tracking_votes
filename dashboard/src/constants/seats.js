export const SEAT_NAMES = {
  'P.140':'Segamat','P.141':'Sekijang','P.142':'Labis','P.143':'Pagoh','P.144':'Ledang',
  'P.145':'Bakri','P.146':'Muar','P.147':'Parit Sulong','P.148':'Ayer Hitam','P.149':'Sri Gading',
  'P.150':'Batu Pahat','P.151':'Simpang Renggam','P.152':'Kluang','P.153':'Sembrong','P.154':'Mersing',
  'P.155':'Tenggara','P.156':'Kota Tinggi','P.157':'Pengerang','P.158':'Tebrau','P.159':'Pasir Gudang',
  'P.160':'Johor Bahru','P.161':'Pulai','P.162':'Iskandar Puteri','P.163':'Kulai','P.164':'Pontian',
  'P.165':'Tanjung Piai',
  'N.01':'Buloh Kasap','N.02':'Jementah','N.03':'Pemanis','N.04':'Kemelah','N.05':'Tenang',
  'N.06':'Bekok','N.07':'Bukit Kepong','N.08':'Bukit Pasir','N.09':'Gambir','N.10':'Tangkak',
  'N.11':'Serom','N.12':'Bentayan','N.13':'Simpang Jeram','N.14':'Bukit Naning','N.15':'Maharani',
  'N.16':'Sungai Balang','N.17':'Semerah','N.18':'Sri Medan','N.19':'Yong Peng','N.20':'Semarang',
  'N.21':'Parit Yaani','N.22':'Parit Raja','N.23':'Penggaram','N.24':'Senggarang','N.25':'Rengit',
  'N.26':'Machap','N.27':'Layang-Layang','N.28':'Mengkibol','N.29':'Mahkota','N.30':'Paloh',
  'N.31':'Kahang','N.32':'Endau','N.33':'Tenggaroh','N.34':'Panti','N.35':'Pasir Raja',
  'N.36':'Sedili','N.37':'Johor Lama','N.38':'Penawar','N.39':'Tanjung Surat','N.40':'Tiram',
  'N.41':'Puteri Wangsa','N.42':'Johor Jaya','N.43':'Permas','N.44':'Larkin','N.45':'Stulang',
  'N.46':'Perling','N.47':'Kempas','N.48':'Skudai','N.49':'Kota Iskandar','N.50':'Bukit Permai',
  'N.51':'Bukit Batu','N.52':'Senai','N.53':'Benut','N.54':'Pulai Sebatang','N.55':'Pekan Nanas',
  'N.56':'Kukup',
}

/** Normalise the constituency_ids field which the API may return as a JSON string or an array. */
export const parseConstituencyIds = (raw) => {
  if (!raw) return []
  if (Array.isArray(raw)) return raw
  if (typeof raw === 'string') {
    try { return JSON.parse(raw) } catch { return [] }
  }
  return []
}

export const formatSeatLabel = (code) =>
  `${code}${SEAT_NAMES[code] ? ` — ${SEAT_NAMES[code]}` : ''}`
