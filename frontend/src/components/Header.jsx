import { useState, useEffect } from 'react'
import { captureApi } from '../utils/api'
import toast from 'react-hot-toast'

export default function Header({ connected, alerts }) {
  const [interfaces, setInterfaces] = useState([])
  const [selectedIface, setSelectedIface] = useState('')
  const [capturing, setCapturing] = useState(false)
  const [status, setStatus] = useState(null)

  useEffect(() => {
    captureApi.interfaces()
      .then(r => {
        setInterfaces(r.data.interfaces || [])
        if (r.data.interfaces?.length) setSelectedIface(r.data.interfaces[0].name)
      })
      .catch(() => {})

    captureApi.status()
      .then(r => {
        setCapturing(r.data.running)
        setStatus(r.data)
      })
      .catch(() => {})
  }, [])

  const handleStart = async () => {
    try {
      await captureApi.start(selectedIface)
      setCapturing(true)
      toast.success(`Capture started on ${selectedIface}`)
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to start capture')
    }
  }

  const handleStop = async () => {
    try {
      const r = await captureApi.stop()
      setCapturing(false)
      toast.success(`Capture stopped · ${r.data.total_packets?.toLocaleString()} packets`)
    } catch (e) {
      toast.error('Failed to stop capture')
    }
  }

  const unackAlerts = alerts.filter(a => !a.acknowledged).length

  return (
    <header style={{
      height: 'var(--header-h)',
      borderBottom: '1px solid var(--border)',
      display: 'flex',
      alignItems: 'center',
      padding: '0 24px',
      gap: '12px',
      background: 'rgba(8,11,20,0.85)',
      backdropFilter: 'blur(12px)',
      position: 'sticky', top: 0, zIndex: 50,
    }}>
      {/* Interface selector */}
      <select
        value={selectedIface}
        onChange={e => setSelectedIface(e.target.value)}
        disabled={capturing}
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          color: 'var(--text-primary)',
          padding: '6px 10px',
          borderRadius: '6px',
          fontSize: '12px',
          fontFamily: 'var(--font-mono)',
          cursor: 'pointer',
          minWidth: '120px',
        }}
      >
        {interfaces.map(iface => (
          <option key={iface.name} value={iface.name}>
            {iface.name} ({iface.ip})
          </option>
        ))}
      </select>

      {/* Start/Stop button */}
      {capturing ? (
        <button className="btn btn-danger" onClick={handleStop}>
          <span className="live-dot red" />
          Stop Capture
        </button>
      ) : (
        <button className="btn btn-primary" onClick={handleStart} disabled={!selectedIface}>
          ▶ Start Capture
        </button>
      )}

      {/* Live stats */}
      {status && (
        <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
          {status.packet_count?.toLocaleString() || 0} pkts · {status.active_flows || 0} flows
        </span>
      )}

      <div style={{ flex: 1 }} />

      {/* Alert badge */}
      {unackAlerts > 0 && (
        <div style={{
          background: 'rgba(239,68,68,0.15)',
          border: '1px solid rgba(239,68,68,0.3)',
          color: '#ef4444',
          borderRadius: '99px',
          padding: '3px 10px',
          fontSize: '11px',
          fontWeight: 700,
        }}>
          ⚠ {unackAlerts} ALERT{unackAlerts > 1 ? 'S' : ''}
        </div>
      )}

      {/* WS status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--text-dim)' }}>
        <span style={{
          width: 6, height: 6, borderRadius: '50%',
          background: connected ? 'var(--success)' : 'var(--danger)',
          display: 'inline-block',
        }} />
        {connected ? 'Live' : 'Offline'}
      </div>
    </header>
  )
}
