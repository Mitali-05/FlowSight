import { useEffect, useState } from 'react'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar, XAxis, YAxis,
} from 'recharts'
import { reportsApi } from '../utils/api'
import toast from 'react-hot-toast'
import { format, fromUnixTime } from 'date-fns'

const CLASS_COLORS = {
  HTTP: '#6366f1', DNS: '#06b6d4', Video_Streaming: '#10b981',
  VoIP: '#f59e0b', Gaming: '#a78bfa', Torrent: '#ef4444', Unknown: '#475569',
}

function fmtBytes(b) {
  if (!b) return '0 B'
  const u = ['B','KB','MB','GB','TB']
  let i = 0; while (b >= 1024 && i < 4) { b /= 1024; i++ }
  return `${b.toFixed(2)} ${u[i]}`
}

function StatRow({ label, value, accent }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{label}</span>
      <span style={{ fontSize: 13, fontFamily: 'var(--font-mono)', fontWeight: 600, color: accent || 'var(--text-primary)' }}>
        {value}
      </span>
    </div>
  )
}

export default function ReportsPage() {
  const [summary, setSummary] = useState(null)
  const [sessionId, setSessionId] = useState('')
  const [loading, setLoading] = useState(true)
  const [downloading, setDownloading] = useState(null)

  useEffect(() => {
    reportsApi.summary()
      .then(r => { setSummary(r.data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const handleDownload = async (type) => {
    setDownloading(type)
    try {
      const url = type === 'csv'
        ? reportsApi.csvUrl(sessionId || null)
        : reportsApi.pdfUrl(sessionId || null)

      const link = document.createElement('a')
      link.href = url
      link.download = `traffic_report_${Date.now()}.${type}`
      link.click()
      toast.success(`${type.toUpperCase()} download started`)
    } catch (e) {
      toast.error(`Failed to download ${type.toUpperCase()}`)
    } finally {
      setTimeout(() => setDownloading(null), 2000)
    }
  }

  const stats = summary?.stats || {}
  const labelDist = summary?.label_distribution || []
  const anomBreakdown = summary?.anomaly_breakdown || []
  const sessions = summary?.sessions || []

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Reports Export</div>
          <div className="page-subtitle">Export session data as CSV or PDF</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20 }}>
        {/* Main content */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Stats summary */}
          <div className="card">
            <div className="section-title">Session Statistics</div>
            {loading ? (
              <div style={{ color: 'var(--text-dim)', fontSize: 12, padding: '16px 0' }}>Loading...</div>
            ) : (
              <>
                <StatRow label="Total Flows Captured" value={(stats.total_flows || 0).toLocaleString()} />
                <StatRow label="Total Packets" value={(stats.total_packets || 0).toLocaleString()} />
                <StatRow label="Total Data Volume" value={fmtBytes(stats.total_bytes || 0)} />
                <StatRow label="Anomalies Detected" value={(stats.anomaly_count || 0).toLocaleString()} accent="#ef4444" />
                <StatRow label="Average Threat Score" value={`${(stats.avg_threat || 0).toFixed(1)} / 100`} accent={stats.avg_threat > 50 ? '#f59e0b' : 'var(--text-primary)'} />
              </>
            )}
          </div>

          {/* Charts */}
          <div className="grid-2">
            <div className="card">
              <div className="section-title">Traffic by Class</div>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={labelDist}
                    dataKey="count"
                    nameKey="flow_label"
                    cx="50%" cy="50%"
                    outerRadius={75}
                    strokeWidth={0}
                  >
                    {labelDist.map((d, i) => (
                      <Cell key={i} fill={CLASS_COLORS[d.flow_label] || '#475569'} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: 'rgba(13,17,23,0.95)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }}
                    formatter={(v, n) => [v.toLocaleString(), n]}
                  />
                  <Legend formatter={(v) => <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{v}</span>} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <div className="section-title">Anomaly Breakdown</div>
              {anomBreakdown.length === 0 ? (
                <div style={{ color: 'var(--text-dim)', fontSize: 12, padding: '40px 0', textAlign: 'center' }}>
                  No anomalies recorded
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={anomBreakdown} layout="vertical">
                    <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: 'var(--text-dim)' }} />
                    <YAxis dataKey="anomaly_type" type="category" width={120} axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} />
                    <Tooltip contentStyle={{ background: 'rgba(13,17,23,0.95)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }} />
                    <Bar dataKey="count" fill="#ef4444" fillOpacity={0.7} radius={[0,4,4,0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Session history */}
          <div className="card">
            <div className="section-title">Capture Sessions</div>
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Session ID</th>
                    <th>Interface</th>
                    <th>Started</th>
                    <th>Ended</th>
                    <th>Flows</th>
                    <th>Bytes</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.length === 0 ? (
                    <tr><td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-dim)', padding: 24 }}>
                      No sessions recorded yet.
                    </td></tr>
                  ) : sessions.map(s => (
                    <tr key={s.id}>
                      <td className="mono" style={{ fontSize: 11 }}>{s.id}</td>
                      <td className="mono">{s.interface || '—'}</td>
                      <td className="mono">{s.started_at ? format(fromUnixTime(s.started_at), 'MM/dd HH:mm') : '—'}</td>
                      <td className="mono">{s.ended_at ? format(fromUnixTime(s.ended_at), 'MM/dd HH:mm') : <span className="live-dot" />}</td>
                      <td className="mono">{(s.total_flows || 0).toLocaleString()}</td>
                      <td className="mono">{fmtBytes(s.total_bytes || 0)}</td>
                      <td>
                        <button
                          className="btn btn-ghost"
                          style={{ fontSize: 11, padding: '3px 10px' }}
                          onClick={() => setSessionId(s.id)}
                        >
                          Select
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Export panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="card">
            <div className="section-title">Export Settings</div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 6, letterSpacing: '0.06em', fontWeight: 600 }}>
                SESSION ID (optional)
              </label>
              <input
                type="text"
                placeholder="Leave empty for all data"
                value={sessionId}
                onChange={e => setSessionId(e.target.value)}
                style={{
                  width: '100%',
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  padding: '8px 10px',
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 12,
                  outline: 'none',
                }}
              />
              {sessionId && (
                <button style={{ fontSize: 11, color: 'var(--text-dim)', background: 'none', border: 'none', cursor: 'pointer', marginTop: 4 }}
                  onClick={() => setSessionId('')}>
                  ✕ Clear (use all data)
                </button>
              )}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {/* CSV Export */}
              <div style={{
                background: 'rgba(6,182,212,0.07)', border: '1px solid rgba(6,182,212,0.2)',
                borderRadius: 10, padding: 16,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                  <span style={{ fontSize: 20 }}>📊</span>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 700 }}>CSV Export</div>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Flows + alerts, spreadsheet-ready</div>
                  </div>
                </div>
                <ul style={{ fontSize: 11, color: 'var(--text-secondary)', paddingLeft: 16, marginBottom: 12 }}>
                  <li>All flow records with classification</li>
                  <li>Anomaly scores and types</li>
                  <li>Alert log</li>
                  <li>GeoIP information</li>
                </ul>
                <button
                  className="btn btn-primary"
                  style={{ width: '100%', justifyContent: 'center', background: 'rgba(6,182,212,0.8)' }}
                  onClick={() => handleDownload('csv')}
                  disabled={downloading === 'csv'}
                >
                  {downloading === 'csv' ? '⏳ Preparing...' : '⬇ Download CSV'}
                </button>
              </div>

              {/* PDF Export */}
              <div style={{
                background: 'rgba(99,102,241,0.07)', border: '1px solid rgba(99,102,241,0.2)',
                borderRadius: 10, padding: 16,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                  <span style={{ fontSize: 20 }}>📄</span>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 700 }}>PDF Report</div>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Professional formatted report</div>
                  </div>
                </div>
                <ul style={{ fontSize: 11, color: 'var(--text-secondary)', paddingLeft: 16, marginBottom: 12 }}>
                  <li>Executive summary stats</li>
                  <li>Alert severity breakdown</li>
                  <li>Top 100 flagged flows</li>
                  <li>Signature-ready format</li>
                </ul>
                <button
                  className="btn btn-primary"
                  style={{ width: '100%', justifyContent: 'center' }}
                  onClick={() => handleDownload('pdf')}
                  disabled={downloading === 'pdf'}
                >
                  {downloading === 'pdf' ? '⏳ Generating...' : '⬇ Download PDF'}
                </button>
              </div>
            </div>
          </div>

          {/* Tips */}
          <div className="card">
            <div className="section-title">Notes</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
              <p>• PDF requires <code style={{ fontFamily: 'var(--font-mono)', fontSize: 11, background: 'rgba(99,102,241,0.1)', padding: '1px 5px', borderRadius: 3 }}>reportlab</code> on the backend.</p>
              <p style={{ marginTop: 8 }}>• CSV exports up to 5,000 flows per request. For larger datasets, filter by session ID.</p>
              <p style={{ marginTop: 8 }}>• GeoIP data is cached and may lag 1h behind live results.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
