import { useState, useCallback, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Fetch all registered agents
 */
export const useAgents = () => {
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchAgents = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/agents`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setAgents(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAgents()
    const interval = setInterval(fetchAgents, 30000)
    return () => clearInterval(interval)
  }, [fetchAgents])

  return { agents, loading, error, refetch: fetchAgents }
}

/**
 * Fetch agent topology graph
 */
export const useAgentGraph = () => {
  const [graph, setGraph] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchGraph = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/graph`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setGraph(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchGraph()
    const interval = setInterval(fetchGraph, 30000)
    return () => clearInterval(interval)
  }, [fetchGraph])

  return { graph, loading, error, refetch: fetchGraph }
}

/**
 * Fetch all articles
 */
export const useArticles = () => {
  const [articles, setArticles] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchArticles = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/articles`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      // Sort by date descending
      data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      setArticles(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchArticles()
    const interval = setInterval(fetchArticles, 60000) // 60s refresh
    return () => clearInterval(interval)
  }, [fetchArticles])

  return { articles, loading, error, refetch: fetchArticles }
}

/**
 * Fetch seat predictions by constituency or all
 */
export const useSeatPredictions = (constituencyCode = null) => {
  const [predictions, setPredictions] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchPredictions = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const url = constituencyCode
        ? `${API_BASE}/seat-predictions/${constituencyCode}`
        : `${API_BASE}/seat-predictions`
      const res = await fetch(url)
      if (res.status === 404) { setPredictions([]); return }
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setPredictions(constituencyCode ? [data] : data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [constituencyCode])

  useEffect(() => {
    fetchPredictions()
    const interval = setInterval(fetchPredictions, 60000) // 60s refresh
    return () => clearInterval(interval)
  }, [fetchPredictions])

  return { predictions, loading, error, refetch: fetchPredictions }
}

/**
 * Dispatch a task to an agent
 */
export const useDispatchTask = () => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const dispatchTask = useCallback(async (agentType, message) => {
    setLoading(true)
    setError(null)
    try {
      // Convert message object to string if needed
      const messageStr = typeof message === 'string'
        ? message
        : message.parts?.[0]?.text || JSON.stringify(message)

      const res = await fetch(`${API_BASE}/agents/${agentType}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageStr,
          metadata: {},
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      return data // { task_id, state }
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return { dispatchTask, loading, error }
}

/**
 * Subscribe to task status via WebSocket
 */
export const useTaskStream = (taskId) => {
  const [status, setStatus] = useState(null)
  const [nodeOutputs, setNodeOutputs] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!taskId) return

    const ws = new WebSocket(`ws://localhost:8000/ws/tasks/${taskId}`)

    ws.onopen = () => {
      console.log(`[TaskStream] Connected to task ${taskId}`)
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.status) setStatus(msg.status)
        if (msg.node_output) {
          setNodeOutputs((prev) => [...prev, msg.node_output])
        }
      } catch (err) {
        console.error('[TaskStream] Parse error:', err)
      }
    }

    ws.onerror = (err) => {
      setError(err.message || 'WebSocket error')
    }

    ws.onclose = () => {
      console.log(`[TaskStream] Disconnected from task ${taskId}`)
    }

    return () => {
      ws.close()
    }
  }, [taskId])

  return { status, nodeOutputs, error }
}

/**
 * Fetch wiki pages
 */
export const useWikiPages = () => {
  const [pages, setPages] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchPages = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/wiki/pages`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setPages(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPages()
    const interval = setInterval(fetchPages, 300000) // 5min refresh
    return () => clearInterval(interval)
  }, [fetchPages])

  return { pages, loading, error, refetch: fetchPages }
}

/**
 * Fetch historical results for a constituency
 */
export const useHistorical = (constituencyCode) => {
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchResults = useCallback(async () => {
    if (!constituencyCode) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/historical/${constituencyCode}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [constituencyCode])

  useEffect(() => { fetchResults() }, [fetchResults])

  return { results, loading, error }
}

/**
 * Fetch demographics for a constituency
 */
export const useDemographics = (constituencyCode) => {
  const [demographics, setDemographics] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchDemographics = useCallback(async () => {
    if (!constituencyCode) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/demographics/${constituencyCode}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setDemographics(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [constituencyCode])

  useEffect(() => { fetchDemographics() }, [fetchDemographics])

  return { demographics, loading, error }
}

/**
 * Fetch all historical results for a given year, keyed by constituency_code.
 * Used by the map tooltip for 2022 comparison.
 */
export const useHistoricalByYear = (year) => {
  const [resultsByCode, setResultsByCode] = useState({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!year) return
    setLoading(true)
    fetch(`${API_BASE}/historical?year=${year}`)
      .then((res) => res.ok ? res.json() : [])
      .then((data) => {
        const byCode = {}
        data.forEach((r) => { byCode[r.constituency_code] = r })
        setResultsByCode(byCode)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [year])

  return { resultsByCode, loading }
}

/**
 * Fetch articles tagged to a specific constituency
 */
export const useConstituencyArticles = (constituencyCode) => {
  const [articles, setArticles] = useState([])
  const [loading, setLoading] = useState(false)

  const fetchArticles = useCallback(async () => {
    if (!constituencyCode) return
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/articles?constituency=${encodeURIComponent(constituencyCode)}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setArticles(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [constituencyCode])

  useEffect(() => { fetchArticles() }, [fetchArticles])

  return { articles, loading }
}

/**
 * Cancel a running task
 */
export const useCancelTask = () => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const cancelTask = useCallback(async (taskId) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/tasks/${taskId}/cancel`, {
        method: 'POST',
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return await res.json()
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return { cancelTask, loading, error }
}
