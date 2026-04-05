import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts'
import { flowsApi } from '../utils/api'
import { format } from 'date-fns'

const CLASS_COLORS = {
  HTTP:             '#6366f1',
  DNS:              '#06b6d4',
  Video_Streaming:  '#10b981',
  VoIP:             '#f59e0b',
  Gaming:           '#a78bfa',
  Torrent:          '#ef4444',
  Unknown:          '#475569',
}
const CLASS_ICONS = {
  HTTP: '🌐', DNS: '🔍', Video_Streaming: '🎬',
  VoIP: '📞', Gaming: '🎮', Torrent: '📡', Unknown: '❓',
}

function fmtBytes(b) {
  if (!b) return '0 B'
  const u = ['B','KB','MB','GB']
  let i = 0; while (b >= 1024 && i < 3) { b /= 1024; i++ }
  return `${b.toFixed(1)} ${u[i]}`
}

export default function ClassificationPage() {
  const [distribution, setDistribution] = useState([])
  const [flows, setFlows] = useState([])
  const [selectedLabel, setSelectedLabel] = useState(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 50

  useEffect(() => {
    flowsApi.distribution()
      .then(r => setDistribution(r.data.distribution || []))
      .catch(() => {})
    setLoading(false)
  }, [])

  useEffect(() => {
    const params = { limit: PAGE_SIZE, offset: page * PAGE_SIZE }
    if (selectedLabel) params.label = selectedLabel
    flowsApi.list(params)
      .then(r => setFlows(r.data.flows || []))
      .catch(() => {})
  }, [selectedLabel, page])

  const total = distribution.reduce((s, d) => s + (d.count || 0), 0) || 1

  // Radar chart: show traffic diversity
  const radarData = distribution.map(d => ({
    label: d.flow_label,
    value: Math.round(d.percentage || 0),
  }))

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Traffic Classification</div>
          <div className="page-subtitle">ML-based flow categorization using XGBoost</div>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          {total.toLocaleString()} total flows classified
        </div>
      </div>

      {/* Class cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 10, marginBottom: 20 }}>
        {['HTTP','DNS','Video_Streaming','VoIP','Gaming','Torrent','Unknown'].map(label => {
          const d = distribution.find(x => x.flow_label === label) || { count: 0, bytes: 0, percentage: 0 }
          const active = selectedLabel === label
          return (
            <div
              key={label}
              onClick={() => setSelectedLabel(active ? null : label)}
              style={{
                background: active ? `${CLASS_COLORS[label]}22` : 'var(--bg-card)',
                border: `1px solid ${active ? CLASS_COLORS[label] : 'var(--border)'}`,
                borderRadius: 'var(--radius)',
                padding: '14px 12px',
                cursor: 'pointer',
                transition: 'all 0.15s',
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: 20, marginBottom: 6 }}>{CLASS_ICONS[label]}</div>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.06em', color: CLASS_COLORS[label], textTransform: 'uppercase', marginBottom: 4 }}>
                {label.replace('_', ' ')}
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>
                {(d.count || 0).toLocaleString()}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 2 }}>
                {(d.percentage || 0).toFixed(1)}%
              </div>
            </div>
          )
        })}
      </div>

      {/* Charts */}
      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="section-title">Flow Count by Class</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={distribution} layout="vertical">
              <XAxis type="number" axisLine={false} tickLine={false} />
              <YAxis dataKey="flow_label" type="category" width={110} tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: 'rgba(13,17,23,0.95)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }}
                formatter={(v, n, p) => [v.toLocaleString(), 'Flows']}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {distribution.map((d, i) => (
                  <Cell key={i} fill={CLASS_COLORS[d.flow_label] || '#475569'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="section-title">Bandwidth by Class</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={distribution} layout="vertical">
              <XAxis type="number" axisLine={false} tickLine={false} tickFormatter={v => fmtBytes(v)} />
              <YAxis dataKey="flow_label" type="category" width={110} tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: 'rgba(13,17,23,0.95)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 11 }}
                formatter={v => [fmtBytes(v), 'Bytes']}
              />
              <Bar dataKey="bytes" radius={[0, 4, 4, 0]}>
                {distribution.map((d, i) => (
                  <Cell key={i} fill={CLASS_COLORS[d.flow_label] || '#475569'} fillOpacity={0.7} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Flow table */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <div className="section-title" style={{ marginBottom: 0, flex: 1 }}>
            {selectedLabel ? `${selectedLabel} Flows` : 'All Classified Flows'}
          </div>
          {selectedLabel && (
            <button className="btn btn-ghost" style={{ fontSize: 11, padding: '4px 10px' }} onClick={() => setSelectedLabel(null)}>
              ✕ Clear filter
            </button>
          )}
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Src IP</th>
                <th>Dst IP</th>
                <th>Proto</th>
                <th>Port</th>
                <th>Duration</th>
                <th>Bytes</th>
                <th>Pkts</th>
                <th>Label</th>
                <th>App</th>
                <th>Threat</th>
              </tr>
            </thead>
            <tbody>
              {flows.length === 0 ? (
                <tr><td colSpan={11} style={{ textAlign: 'center', color: 'var(--text-dim)', padding: 30 }}>
                  No flows yet. Start a capture session.
                </td></tr>
              ) : flows.map((f, i) => (
                <tr key={f.id || i}>
                  <td className="mono">{format(new Date((f.timestamp ?? 0) * 1000), 'HH:mm:ss')}</td>
                  <td className="mono">{f.src_ip}</td>
                  <td className="mono">{f.dst_ip}</td>
                  <td><span className="badge badge-info">{f.protocol}</span></td>
                  <td className="mono">{f.dst_port}</td>
                  <td className="mono">{(f.duration ?? 0).toFixed(2)}s</td>
                  <td className="mono">{fmtBytes(f.byte_count)}</td>
                  <td className="mono">{f.packet_count}</td>
                  <td>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 4,
                      padding: '2px 8px', borderRadius: 99, fontSize: 11, fontWeight: 600,
                      background: `${CLASS_COLORS[f.flow_label] || '#475569'}22`,
                      color: CLASS_COLORS[f.flow_label] || '#475569',
                    }}>
                      {CLASS_ICONS[f.flow_label]} {f.flow_label}
                    </span>
                  </td>
                  <td style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{f.app_fingerprint || '—'}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{
                        fontFamily: 'var(--font-mono)', fontSize: 11,
                        color: f.threat_score >= 70 ? '#ef4444' : f.threat_score >= 40 ? '#f59e0b' : 'var(--text-dim)',
                      }}>
                        {f.threat_score}
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 14 }}>
          <button className="btn btn-ghost" onClick={() => setPage(p => Math.max(0, p-1))} disabled={page === 0} style={{ fontSize: 12, padding: '5px 12px' }}>
            ← Prev
          </button>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)', alignSelf: 'center' }}>
            Page {page + 1}
          </span>
          <button className="btn btn-ghost" onClick={() => setPage(p => p+1)} disabled={flows.length < PAGE_SIZE} style={{ fontSize: 12, padding: '5px 12px' }}>
            Next →
          </button>
        </div>
      </div>
    </div>
  )
}
