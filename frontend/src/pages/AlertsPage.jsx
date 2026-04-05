import { useEffect, useState, useCallback } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  AreaChart, Area,
} from 'recharts'
import { alertsApi } from '../utils/api'
import { format, fromUnixTime } from 'date-fns'
import toast from 'react-hot-toast'

const SEV_ORDER = ['critical', 'high', 'medium', 'low', 'info']
const SEV_COLORS = {
  critical: '#ef4444', high: '#f59e0b',
  medium: '#eab308', low: '#10b981', info: '#6366f1',
}
const SEV_BG = {
  critical: 'rgba(239,68,68,0.1)', high: 'rgba(245,158,11,0.1)',
  medium: 'rgba(234,179,8,0.1)', low: 'rgba(16,185,129,0.1)', info: 'rgba(99,102,241,0.1)',
}

function SeverityBadge({ severity }) {
  return (
    <span className={`badge badge-${severity}`} style={{ textTransform: 'uppercase', fontSize: 10 }}>
      {severity}
    </span>
  )
}

export default function AlertsPage({ wsAlerts }) {
  const [alerts, setAlerts] = useState([])
  const [summary, setSummary] = useState({})
  const [filter, setFilter] = useState('all')
  const [unackOnly, setUnackOnly] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const [alertRes, sumRes] = await Promise.all([
        alertsApi.list({ limit: 200 }),
        alertsApi.summary(),
      ])
      setAlerts(alertRes.data.alerts || [])
      setSummary(sumRes.data.summary || {})
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (wsAlerts?.length) {
      setAlerts(prev => {
        const existingIds = new Set(prev.map(a => a.id))
        const newOnes = wsAlerts.filter(a => !existingIds.has(a.id))
        if (newOnes.length) {
          newOnes.forEach(a => {
            const toastFn = a.severity === 'critical' ? toast.error : a.severity === 'high' ? toast.error : toast
            toastFn(`🚨 ${a.alert_type}: ${a.message.slice(0, 80)}`)
          })
          return [...newOnes, ...prev].slice(0, 200)
        }
        return prev
      })
    }
  }, [wsAlerts])

  const handleAck = async (id) => {
    try {
      await alertsApi.acknowledge(id)
      setAlerts(prev => prev.map(a => a.id === id ? { ...a, acknowledged: true } : a))
      toast.success('Alert acknowledged')
    } catch {
      toast.error('Failed to acknowledge')
    }
  }

  const handleDelete = async (id) => {
    try {
      await alertsApi.delete(id)
      setAlerts(prev => prev.filter(a => a.id !== id))
    } catch {
      toast.error('Failed to delete')
    }
  }

  const handleAckAll = async () => {
    const unacked = filtered.filter(a => !a.acknowledged)
    await Promise.all(unacked.map(a => alertsApi.acknowledge(a.id).catch(() => {})))
    setAlerts(prev => prev.map(a => ({ ...a, acknowledged: true })))
    toast.success(`Acknowledged ${unacked.length} alerts`)
  }

  let filtered = filter === 'all' ? alerts : alerts.filter(a => a.severity === filter)
  if (unackOnly) filtered = filtered.filter(a => !a.acknowledged)

  const alertTimeline = (() => {
    const buckets = {}
    alerts.forEach(a => {
      const key = Math.floor(a.timestamp / 60) * 60
      buckets[key] = (buckets[key] || 0) + 1
    })
    return Object.entries(buckets)
      .sort(([a], [b]) => Number(a) - Number(b))
      .slice(-30)
      .map(([t, count]) => ({
        t: format(fromUnixTime(Number(t)), 'HH:mm'),
        count,
      }))
  })()

  const totalUnack = SEV_ORDER.reduce((s, k) => s + (summary[k] || 0), 0)

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Alerts & Threat Analysis</div>
          <div className="page-subtitle">{totalUnack} unacknowledged · {alerts.length} total</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-ghost" onClick={load} style={{ fontSize: 12 }}>↻ Refresh</button>
          {filtered.some(a => !a.acknowledged) && (
            <button className="btn btn-primary" onClick={handleAckAll} style={{ fontSize: 12 }}>
              ✓ Ack All
            </button>
          )}
        </div>
      </div>

      {/* Severity summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 20 }}>
        {SEV_ORDER.map(sev => (
          <div
            key={sev}
            onClick={() => setFilter(filter === sev ? 'all' : sev)}
            style={{
              background: filter === sev ? SEV_BG[sev] : 'var(--bg-card)',
              border: `1px solid ${filter === sev ? SEV_COLORS[sev] : 'var(--border)'}`,
              borderRadius: 'var(--radius)',
              padding: '16px',
              cursor: 'pointer',
              textAlign: 'center',
              transition: 'all 0.15s',
            }}
          >
            <div style={{ fontSize: 22, fontFamily: 'var(--font-mono)', fontWeight: 700, color: SEV_COLORS[sev] }}>
              {summary[sev] || 0}
            </div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: SEV_COLORS[sev], textTransform: 'uppercase', marginTop: 4 }}>
              {sev}
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="section-title">Alerts Over Time</div>
          <ResponsiveContainer width="100%" height={150}>
            <AreaChart data={alertTimeline}>
              <defs>
                <linearGradient id="alertGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="t" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: 'var(--text-dim)' }} />
              <YAxis axisLine={false} tickLine={false} width={28} tick={{ fontSize: 10, fill: 'var(--text-dim)' }} />
              <Tooltip
                contentStyle={{ background: 'rgba(13,17,23,0.95)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }}
                formatter={v => [v, 'alerts']}
              />
              <Area type="monotone" dataKey="count" stroke="#ef4444" strokeWidth={2} fill="url(#alertGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="section-title">Alerts by Type</div>
          {(() => {
            const typeCounts = alerts.reduce((acc, a) => {
              acc[a.alert_type] = (acc[a.alert_type] || 0) + 1
              return acc
            }, {})
            const data = Object.entries(typeCounts).map(([name, count]) => ({ name, count })).sort((a,b) => b.count - a.count).slice(0,6)
            return (
              <ResponsiveContainer width="100%" height={150}>
                <BarChart data={data} layout="vertical">
                  <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: 'var(--text-dim)' }} />
                  <YAxis dataKey="name" type="category" width={110} axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} />
                  <Tooltip contentStyle={{ background: 'rgba(13,17,23,0.95)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }} />
                  <Bar dataKey="count" fill="#ef4444" fillOpacity={0.7} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )
          })()}
        </div>
      </div>

      {/* Alert table */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14, gap: 10 }}>
          <div className="section-title" style={{ marginBottom: 0 }}>Alert Log</div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={unackOnly}
                onChange={e => setUnackOnly(e.target.checked)}
                style={{ accentColor: 'var(--accent)' }}
              />
              Unacknowledged only
            </label>
            {['all', ...SEV_ORDER].map(s => (
              <button key={s} onClick={() => setFilter(s)} style={{
                background: filter === s ? (SEV_BG[s] || 'rgba(99,102,241,0.12)') : 'transparent',
                border: `1px solid ${filter === s ? (SEV_COLORS[s] || 'var(--accent)') : 'var(--border)'}`,
                color: filter === s ? (SEV_COLORS[s] || 'var(--text-primary)') : 'var(--text-secondary)',
                padding: '3px 10px', borderRadius: 99, fontSize: 11, cursor: 'pointer',
              }}>{s}</button>
            ))}
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Severity</th>
                <th>Type</th>
                <th>Source IP</th>
                <th>Destination</th>
                <th>Message</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={8} style={{ textAlign: 'center', color: 'var(--text-dim)', padding: 30 }}>
                  {loading ? 'Loading...' : 'No alerts found.'}
                </td></tr>
              ) : filtered.map((a, i) => (
                <tr key={a.id || i} style={{
                  opacity: a.acknowledged ? 0.5 : 1,
                  borderLeft: `3px solid ${SEV_COLORS[a.severity] || 'transparent'}`,
                }}>
                  <td className="mono" style={{ whiteSpace: 'nowrap' }}>
                    {format(fromUnixTime(a.timestamp || 0), 'HH:mm:ss')}
                  </td>
                  <td><SeverityBadge severity={a.severity} /></td>
                  <td style={{ fontSize: 12, fontWeight: 600 }}>{a.alert_type}</td>
                  <td className="mono" style={{ color: SEV_COLORS[a.severity] }}>{a.src_ip || '—'}</td>
                  <td className="mono">{a.dst_ip || '—'}</td>
                  <td style={{ fontSize: 11, color: 'var(--text-secondary)', maxWidth: 300 }}>
                    <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {a.message}
                    </div>
                  </td>
                  <td>
                    {a.acknowledged
                      ? <span className="badge badge-normal">ACK</span>
                      : <span className="badge badge-high">NEW</span>
                    }
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {!a.acknowledged && (
                        <button
                          onClick={() => handleAck(a.id)}
                          style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)', color: '#10b981', padding: '3px 8px', borderRadius: 4, fontSize: 11, cursor: 'pointer' }}
                        >✓</button>
                      )}
                      <button
                        onClick={() => handleDelete(a.id)}
                        style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#ef4444', padding: '3px 8px', borderRadius: 4, fontSize: 11, cursor: 'pointer' }}
                      >✕</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
