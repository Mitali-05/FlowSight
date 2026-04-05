import { useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { format } from 'date-fns'

function fmtBytes(b) {
  if (!b) return '0 B'
  const u = ['B','KB','MB','GB']
  let i = 0; while (b >= 1024 && i < 3) { b /= 1024; i++ }
  return `${b.toFixed(1)} ${u[i]}`
}

function threatColor(score) {
  if (score >= 80) return '#ef4444'
  if (score >= 60) return '#f59e0b'
  if (score >= 40) return '#eab308'
  if (score >= 20) return '#10b981'
  return '#475569'
}

function labelColor(label) {
  const map = {
    HTTP: '#6366f1', DNS: '#06b6d4', Video_Streaming: '#10b981',
    VoIP: '#f59e0b', Gaming: '#a78bfa', Torrent: '#ef4444', Unknown: '#475569',
  }
  return map[label] || '#475569'
}

export default function LiveMonitorPage({ ws }) {
  const { liveStats, recentFlows, connected } = ws
  const [filter, setFilter] = useState('all')

  const history = liveStats?.stats_history ?? []
  const chartData = history.slice(-60).map(h => ({
    t: format(new Date(h.t * 1000), 'HH:mm:ss'),
    pps: parseFloat(h.pps?.toFixed(1) ?? 0),
    bps: parseFloat((h.bps / 1024).toFixed(1) ?? 0),
  }))

  const filtered = filter === 'all'
    ? recentFlows
    : filter === 'anomaly'
      ? recentFlows.filter(f => f.is_anomaly)
      : recentFlows.filter(f => f.flow_label === filter)

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Live Traffic Monitor</div>
          <div className="page-subtitle">Real-time packet stream and flow analysis</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: connected ? 'var(--success)' : 'var(--danger)', display: 'inline-block' }} />
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            {connected ? 'WebSocket connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Live stats bar */}
      <div className="grid-4" style={{ marginBottom: 20 }}>
        {[
          { label: 'Packets/sec',  value: (liveStats?.pps ?? 0).toFixed(1) },
          { label: 'Throughput',   value: fmtBytes(liveStats?.bps ?? 0) + '/s' },
          { label: 'Active Flows', value: (liveStats?.active_flows ?? 0).toString() },
          { label: 'Queue Depth',  value: (liveStats?.queue_size ?? 0).toString() },
        ].map(s => (
          <div className="stat-card" key={s.label}>
            <div className="label">{s.label}</div>
            <div className="value" style={{ fontSize: 22 }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="section-title">Packets / Second (live)</div>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.08)" />
              <XAxis dataKey="t" tick={false} axisLine={false} />
              <YAxis axisLine={false} tickLine={false} width={36} />
              <Tooltip
                contentStyle={{ background: 'rgba(13,17,23,0.95)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: 8, fontSize: 11 }}
                formatter={v => [`${v} pkt/s`, 'Rate']}
              />
              <Line type="basis" dataKey="pps" stroke="#6366f1" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="section-title">Bandwidth KB/s (live)</div>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(6,182,212,0.08)" />
              <XAxis dataKey="t" tick={false} axisLine={false} />
              <YAxis axisLine={false} tickLine={false} width={36} />
              <Tooltip
                contentStyle={{ background: 'rgba(13,17,23,0.95)', border: '1px solid rgba(6,182,212,0.3)', borderRadius: 8, fontSize: 11 }}
                formatter={v => [`${v} KB/s`, 'Bandwidth']}
              />
              <Line type="basis" dataKey="bps" stroke="#06b6d4" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Live flow feed */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <div className="section-title" style={{ marginBottom: 0, flex: 1 }}>
            Live Flow Feed
            <span className="live-dot" style={{ marginLeft: 8 }} />
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {['all', 'anomaly', 'HTTP', 'DNS', 'Video_Streaming', 'VoIP', 'Gaming'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                style={{
                  background: filter === f ? 'rgba(99,102,241,0.2)' : 'transparent',
                  border: `1px solid ${filter === f ? 'rgba(99,102,241,0.5)' : 'var(--border)'}`,
                  color: filter === f ? 'var(--text-primary)' : 'var(--text-secondary)',
                  padding: '3px 10px', borderRadius: 99, fontSize: 11, cursor: 'pointer',
                }}
              >
                {f}
              </button>
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
                <th>Proto</th>
                <th>Dst Port</th>
                <th>Bytes</th>
                <th>Pkts</th>
                <th>Label</th>
                <th>App</th>
                <th>Threat</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={10} style={{ textAlign: 'center', color: 'var(--text-dim)', padding: 30 }}>
                  {connected ? 'Waiting for flows...' : 'WebSocket disconnected'}
                </td></tr>
              ) : filtered.map((f, i) => (
                <tr key={i} className={f.is_anomaly ? 'anomaly-row' : ''}>
                  <td className="mono">{format(new Date((f.timestamp ?? Date.now() / 1000) * 1000), 'HH:mm:ss')}</td>
                  <td className="mono">{f.src_ip}</td>
                  <td className="mono">{f.dst_ip}</td>
                  <td><span className="badge badge-info">{f.protocol}</span></td>
                  <td className="mono">{f.dst_port}</td>
                  <td className="mono">{fmtBytes(f.byte_count)}</td>
                  <td className="mono">{f.packet_count}</td>
                  <td>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 4,
                      padding: '2px 8px', borderRadius: 99, fontSize: 11, fontWeight: 600,
                      background: `${labelColor(f.flow_label)}22`,
                      color: labelColor(f.flow_label),
                    }}>
                      {f.flow_label}
                    </span>
                  </td>
                  <td style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{f.app_fingerprint || '—'}</td>
                  <td>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: threatColor(f.threat_score) }}>
                      {f.threat_score}
                    </span>
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
