import { useEffect, useRef, useState, useCallback } from 'react'

const WS_URL = `ws://${window.location.hostname}:8000/ws`

export function useWebSocket() {
  const wsRef = useRef(null)
  const pingRef = useRef(null)
  const [connected, setConnected] = useState(false)
  const [liveStats, setLiveStats] = useState(null)
  const [recentFlows, setRecentFlows] = useState([])
  const [alerts, setAlerts] = useState([])
  const [retryCount, setRetryCount] = useState(0)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      setRetryCount(0)
      // Keepalive ping every 25s
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }))
        }
      }, 25_000)
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'stats') {
          setLiveStats(msg.data)
          if (msg.data.recent_flows) {
            setRecentFlows(msg.data.recent_flows.slice(-50).reverse())
          }
        } else if (msg.type === 'alert') {
          setAlerts((prev) => [msg.data, ...prev].slice(0, 100))
        }
      } catch (e) {
        // ignore parse errors
      }
    }

    ws.onclose = () => {
      setConnected(false)
      clearInterval(pingRef.current)
      // Exponential backoff reconnect (max 10s)
      const delay = Math.min(1000 * 2 ** retryCount, 10_000)
      setTimeout(() => {
        setRetryCount((n) => n + 1)
        connect()
      }, delay)
    }

    ws.onerror = () => ws.close()
  }, [retryCount])

  useEffect(() => {
    connect()
    return () => {
      clearInterval(pingRef.current)
      wsRef.current?.close()
    }
  }, [])

  return { connected, liveStats, recentFlows, alerts }
}
