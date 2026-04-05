import { useEffect, useState, useCallback } from 'react'
import {
  ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, ReferenceLine,
} from 'recharts'
import { flowsApi } from '../utils/api'
import { format } from 'date-fns'

const ANOMALY_COLORS = {
  port_scan:           '#f59e0b',
  ddos:                '#ef4444',
  syn_scan:            '#fb923c',
  spike:               '#a78bfa',
  suspicious_port:     '#06b6d4',
  statistical_anomaly: '#e879f9',
  '':                  '#475569',
}
const ANOMALY_ICONS = {
  port_scan: '🔍', ddos: '🌊', syn_scan: '⚡',
  spike: '📈', suspicious_port: '🚫', statistical_anomaly: '🤖',
}

function fmtBytes(b) {
  if (!b) return '0 B'
  const u = ['B','KB','MB','GB']
  let i = 0; while (b >= 1024 && i < 3) { b /= 1024; i++ }
  return `${b.toFixed(1)} ${u[i]}`
}

const ScoreMeter = ({ score }) => {
  // score: isolation forest -1 to 1, lower = more anomalous
  const normalized = Math.max(0, Math.min(100, (-score + 1) / 2 * 100))
  const color = normalized > 70 ? '#ef4444' : normalized > 40 ? '#f59e0b' : '#10b981'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 4, background: 'rgba(255,255,255,0.08)', borderRadius: 99 }}>
        <div style={{ width: `${normalized}%`, height: '100%', background: color, borderRadius: 99 }} />
      </div>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color, width: 32 }}>
        {normalized.toFixed(0)}
      </span>
    </div>
  )
}

export default function AnomalyPage() {
  const [anomalies, setAnomalies] = useState([])
  const [allFlows, setAllFlows] = useState([])
  const [stats, setStats] = useState({})
  const [loading, setLoading] = useState(true)
  const [typeFilter, setTypeFilter] = useState('all')

  const load = useCallback(async () => {
    try {
      const [anomalyRes, allRes, statsRes] = await Promise.all([
        flowsApi.list({ limit: 200, anomaly_only: true }),
        flowsApi.list({ limit: 500 }),
        flowsApi.stats(),
      ])
      setAnomalies(anomalyRes.data.flows || [])
      setAllFlows(allRes.data.flows || [])
      setStats(statsRes.data || {})
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // Scatter plot: anomaly score vs byte_count
  const scatterData = allFlows.map(f => ({
    x: parseFloat((f.anomaly_score || 0).toFixed(3)),
    y: f.byte_count || 0,
    z: f.is_anomaly ? 60 : 20,
    anomaly: f.is_anomaly,
    label: f.flow_label,
    src: f.src_ip,
    type: f.anomaly_type,
  }))

  // Anomaly type counts
  const typeCounts = anomalies.reduce((acc, f) => {
    const t = f.anomaly_type || 'unknown'
    acc[t] = (acc[t] || 0) + 1
    return acc
  }, {})

  const filtered = typeFilter === 'all' ? anomalies : anomalies.filter(f => f.anomaly_type === typeFilter)

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Anomaly Detection</div>
          <div className="page-subtitle">Isolation Forest · Rule-based heuristics</div>
        </div>
        <button className="btn btn-ghost" onClick={load} style={{ fontSize: 12 }}>
          ↻ Refresh
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid-4" style={{ marginBottom: 20 }}>
        <div className="stat-card" style={{ borderColor: 'rgba(239,68,68,0.2)' }}>
          <div className="label">Total Anomalies</div>
          <div className="value" style={{ color: '#ef4444' }}>{(stats.anomaly_count || 0).toLocaleString()}</div>
          <div className="sub">of {(stats.total_flows || 0).toLocaleString()} flows</div>
          <span className="icon">⚠</span>
        </div>
        {Object.entries(ANOMALY_ICONS).slice(0, 3).map(([type, icon]) => (
          <div className="stat-card" key={type}>
            <div className="label">{type.replace('_', ' ')}</div>
            <div className="value" style={{ fontSize: 22 }}>{typeCounts[type] || 0}</div>
            <div className="sub">detections</div>
            <span className="icon">{icon}</span>
          </div>
        ))}
      </div>

      {/* Scatter plot */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="section-title">Anomaly Score vs. Byte Volume</div>
        <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 10 }}>
          Lower score (left) = more anomalous. Red dots = flagged anomalies.
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.07)" />
            <XAxis
              type="number" dataKey="x" name="Anomaly Score"
              domain={[-1.2, 1.2]}
              axisLine={false} tickLine={false}
              label={{ value: 'Decision Score', position: 'insideBottom', offset: -4, fontSize: 10, fill: 'var(--text-dim)' }}
            />
            <YAxis type="number" dataKey="y" name="Bytes" axisLine={false} tickLine={false}
              tickFormatter={v => fmtBytes(v)} width={55} />
            <ZAxis type="number" dataKey="z" range={[15, 80]} />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              contentStyle={{ background: 'rgba(13,17,23,0.95)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }}
              formatter={(v, name, props) => {
                const d = props.payload
                return [`${d.src} | ${d.label} | score: ${d.x}`, '']
              }}
            />
            <ReferenceLine x={-0.1} stroke="rgba(239,68,68,0.4)" strokeDasharray="4 4" label={{ value: 'threshold', fill: '#ef4444', fontSize: 10 }} />
            <Scatter
              data={scatterData.filter(d => !d.anomaly)}
              fill="#6366f1" fillOpacity={0.3} name="Normal"
            />
            <Scatter
              data={scatterData.filter(d => d.anomaly)}
              fill="#ef4444" fillOpacity={0.8} name="Anomaly"
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Anomaly type breakdown */}
      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="section-title">Detection Types</div>
          {Object.entries(typeCounts).length === 0 ? (
            <div style={{ color: 'var(--text-dim)', fontSize: 12, padding: '12px 0' }}>No anomalies detected yet.</div>
          ) : Object.entries(typeCounts).sort((a,b) => b[1]-a[1]).map(([type, count]) => (
            <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <span style={{ fontSize: 16 }}>{ANOMALY_ICONS[type] || '⚠'}</span>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontSize: 12, color: 'var(--text-primary)', textTransform: 'capitalize' }}>
                    {type.replace(/_/g, ' ')}
                  </span>
                  <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: ANOMALY_COLORS[type] || '#ef4444' }}>{count}</span>
                </div>
                <div className="threat-bar">
                  <div className="threat-bar-fill" style={{
                    width: `${(count / Math.max(...Object.values(typeCounts))) * 100}%`,
                    background: ANOMALY_COLORS[type] || '#ef4444',
                  }} />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Top anomalous sources */}
        <div className="card">
          <div className="section-title">Top Anomalous Sources</div>
          {(() => {
            const srcCounts = anomalies.reduce((acc, f) => {
              acc[f.src_ip] = (acc[f.src_ip] || { count: 0, country: f.src_country })
              acc[f.src_ip].count += 1
              return acc
            }, {})
            const sorted = Object.entries(srcCounts).sort((a,b) => b[1].count - a[1].count).slice(0, 8)
            if (!sorted.length) return <div style={{ color: 'var(--text-dim)', fontSize: 12 }}>No data yet.</div>
            return sorted.map(([ip, data], i) => (
              <div key={ip} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', width: 16 }}>{i+1}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, flex: 1, color: '#ef4444' }}>{ip}</span>
                <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>{data.country}</span>
                <span className="badge badge-critical">{data.count}</span>
              </div>
            ))
          })()}
        </div>
      </div>

      {/* Anomaly flow table */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <div className="section-title" style={{ marginBottom: 0, flex: 1 }}>Anomalous Flows</div>
          <div style={{ display: 'flex', gap: 6 }}>
            {['all', ...Object.keys(typeCounts)].map(t => (
              <button key={t} onClick={() => setTypeFilter(t)} style={{
                background: typeFilter === t ? 'rgba(239,68,68,0.15)' : 'transparent',
                border: `1px solid ${typeFilter === t ? 'rgba(239,68,68,0.4)' : 'var(--border)'}`,
                color: typeFilter === t ? '#ef4444' : 'var(--text-secondary)',
                padding: '3px 10px', borderRadius: 99, fontSize: 11, cursor: 'pointer',
              }}>{t}</button>
            ))}
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Src IP</th>
                <th>Dst IP</th>
                <th>Protocol</th>
                <th>Dst Port</th>
                <th>Bytes</th>
                <th>Anomaly Type</th>
                <th>Score</th>
                <th>Threat</th>
                <th>Country</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={10} style={{ textAlign: 'center', color: 'var(--text-dim)', padding: 30 }}>
                  {loading ? 'Loading...' : 'No anomalies detected yet.'}
                </td></tr>
              ) : filtered.map((f, i) => (
                <tr key={f.id || i} className="anomaly-row">
                  <td className="mono">{format(new Date((f.timestamp ?? 0) * 1000), 'HH:mm:ss')}</td>
                  <td className="mono" style={{ color: '#ef4444' }}>{f.src_ip}</td>
                  <td className="mono">{f.dst_ip}</td>
                  <td><span className="badge badge-info">{f.protocol}</span></td>
                  <td className="mono">{f.dst_port}</td>
                  <td className="mono">{fmtBytes(f.byte_count)}</td>
                  <td>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 4,
                      padding: '2px 8px', borderRadius: 99, fontSize: 11, fontWeight: 600,
                      background: `${ANOMALY_COLORS[f.anomaly_type] || '#ef4444'}22`,
                      color: ANOMALY_COLORS[f.anomaly_type] || '#ef4444',
                    }}>
                      {ANOMALY_ICONS[f.anomaly_type] || '⚠'} {f.anomaly_type?.replace(/_/g, ' ') || 'unknown'}
                    </span>
                  </td>
                  <td><ScoreMeter score={f.anomaly_score} /></td>
                  <td>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#ef4444' }}>
                      {f.threat_score}
                    </span>
                  </td>
                  <td style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{f.src_country || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
