import { useEffect, useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar, Legend,
} from 'recharts'
import { flowsApi, alertsApi } from '../utils/api'
import { format } from 'date-fns'

const COLORS = ['#6366f1','#06b6d4','#10b981','#f59e0b','#ef4444','#a78bfa','#34d399']

function fmtBytes(b) {
  if (!b) return '0 B'
  const u = ['B','KB','MB','GB']
  let i = 0; while (b >= 1024 && i < 3) { b /= 1024; i++ }
  return `${b.toFixed(1)} ${u[i]}`
}

export default function DashboardPage({ ws }) {
  const { liveStats } = ws
  const [stats, setStats] = useState({})
  const [distribution, setDistribution] = useState([])
  const [topTalkers, setTopTalkers] = useState([])
  const [alertSummary, setAlertSummary] = useState({})

  useEffect(() => {
    flowsApi.stats().then(r => setStats(r.data)).catch(() => {})
    flowsApi.distribution().then(r => setDistribution(r.data.distribution || [])).catch(() => {})
    flowsApi.topTalkers(8).then(r => setTopTalkers(r.data.top_talkers || [])).catch(() => {})
    alertsApi.summary().then(r => setAlertSummary(r.data.summary || {})).catch(() => {})
  }, [])

  // Merge DB stats with live counts
  const pps = liveStats?.pps ?? 0
  const bps = liveStats?.bps ?? 0
  const history = liveStats?.stats_history ?? []
  const protoDist = liveStats?.protocol_distribution ?? distribution

  const chartData = history.map(h => ({
    t: format(new Date(h.t * 1000), 'HH:mm:ss'),
    pps: h.pps,
    bps: h.bps / 1024,
  }))

  const threatLevels = [
    { label: 'Critical', count: alertSummary.critical || 0, color: '#ef4444' },
    { label: 'High',     count: alertSummary.high || 0,     color: '#f59e0b' },
    { label: 'Medium',   count: alertSummary.medium || 0,   color: '#eab308' },
    { label: 'Low',      count: alertSummary.low || 0,      color: '#10b981' },
  ]

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Dashboard Overview</div>
          <div className="page-subtitle">Real-time network traffic analysis</div>
        </div>
        {pps > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="live-dot" />
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              {pps.toFixed(1)} pkt/s · {fmtBytes(bps)}/s
            </span>
          </div>
        )}
      </div>

      {/* Stat cards */}
      <div className="grid-4" style={{ marginBottom: 20 }}>
        {[
          { label: 'Total Flows', value: (stats.total_flows || 0).toLocaleString(), icon: '⬡', sub: 'all time' },
          { label: 'Total Packets', value: (stats.total_packets || 0).toLocaleString(), icon: '◈', sub: 'captured' },
          { label: 'Data Volume', value: fmtBytes(stats.total_bytes || 0), icon: '◉', sub: 'transferred' },
          { label: 'Anomalies', value: (stats.anomaly_count || 0).toLocaleString(), icon: '⚠', sub: 'detected', danger: true },
        ].map(s => (
          <div className="stat-card" key={s.label} style={s.danger && s.value !== '0' ? { borderColor: 'rgba(239,68,68,0.3)' } : {}}>
            <div className="label">{s.label}</div>
            <div className="value" style={s.danger && s.value !== '0' ? { color: '#ef4444' } : {}}>{s.value}</div>
            <div className="sub">{s.sub}</div>
            <span className="icon">{s.icon}</span>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid-2" style={{ marginBottom: 20 }}>
        {/* Traffic rate chart */}
        <div className="card">
          <div className="section-title">Packets / Second</div>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="ppsGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="t" tick={false} axisLine={false} tickLine={false} />
              <YAxis axisLine={false} tickLine={false} width={40} />
              <Tooltip
                formatter={(v) => [v.toFixed(1), 'pkt/s']}
                contentStyle={{ background: 'rgba(13,17,23,0.95)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: 8 }}
                labelStyle={{ color: 'var(--text-secondary)', fontSize: 11 }}
              />
              <Area type="monotone" dataKey="pps" stroke="#6366f1" strokeWidth={2} fill="url(#ppsGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Protocol distribution pie */}
        <div className="card">
          <div className="section-title">Traffic Distribution</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <ResponsiveContainer width={160} height={160}>
              <PieChart>
                <Pie data={protoDist} dataKey="count" nameKey="name" cx="50%" cy="50%" innerRadius={45} outerRadius={70} strokeWidth={0}>
                  {protoDist.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div style={{ flex: 1 }}>
              {protoDist.slice(0, 6).map((d, i) => (
                <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS[i % COLORS.length], flexShrink: 0 }} />
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)', flex: 1 }}>{d.name}</span>
                  <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>{d.pct ?? d.percentage}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid-2">
        {/* Top talkers */}
        <div className="card">
          <div className="section-title">Top Talkers</div>
          {topTalkers.length === 0 && (
            <div style={{ color: 'var(--text-dim)', fontSize: 12, padding: '20px 0', textAlign: 'center' }}>
              No flow data yet. Start a capture session.
            </div>
          )}
          {topTalkers.map((t, i) => (
            <div key={t.ip} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
              <span style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', width: 16 }}>{i+1}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, flex: 1 }}>{t.ip}</span>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{t.country}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--accent2)' }}>{fmtBytes(t.bytes)}</span>
            </div>
          ))}
        </div>

        {/* Threat levels */}
        <div className="card">
          <div className="section-title">Threat Level Summary</div>
          {threatLevels.map(t => (
            <div key={t.label} style={{ marginBottom: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{t.label}</span>
                <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: t.color }}>{t.count}</span>
              </div>
              <div className="threat-bar">
                <div className="threat-bar-fill" style={{
                  width: `${Math.min(100, (t.count / Math.max(1, alertSummary.total || 10)) * 100)}%`,
                  background: t.color,
                }} />
              </div>
            </div>
          ))}
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 12 }}>
            Total unacknowledged: {Object.values(alertSummary).reduce((a, b) => a + b, 0)}
          </div>
        </div>
      </div>
    </div>
  )
}
