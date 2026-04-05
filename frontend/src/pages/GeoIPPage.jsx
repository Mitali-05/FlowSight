import { useEffect, useState, useCallback, useRef } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'
import { flowsApi } from '../utils/api'
import 'leaflet/dist/leaflet.css'

function threatToColor(score) {
  if (score >= 80) return '#ef4444'
  if (score >= 60) return '#f59e0b'
  if (score >= 40) return '#eab308'
  if (score >= 20) return '#10b981'
  return '#6366f1'
}

function threatToRadius(score) {
  return 4 + (score / 100) * 12
}

function fmtBytes(b) {
  if (!b) return '0 B'
  const u = ['B','KB','MB','GB']
  let i = 0; while (b >= 1024 && i < 3) { b /= 1024; i++ }
  return `${b.toFixed(1)} ${u[i]}`
}

// Aggregate points by IP for the sidebar
function aggregateByIP(points) {
  const map = {}
  for (const p of points) {
    if (!p.src_ip) continue
    if (!map[p.src_ip]) {
      map[p.src_ip] = {
        ip: p.src_ip, lat: p.lat, lon: p.lon,
        country: p.country, city: p.city,
        maxThreat: p.threat_score, count: 0,
        labels: new Set(),
      }
    }
    map[p.src_ip].count += 1
    map[p.src_ip].maxThreat = Math.max(map[p.src_ip].maxThreat, p.threat_score)
    if (p.flow_label) map[p.src_ip].labels.add(p.flow_label)
  }
  return Object.values(map)
    .sort((a, b) => b.maxThreat - a.maxThreat)
}

// Custom map style updater for dark theme
function DarkTileLayer() {
  return (
    <TileLayer
      url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      attribution='&copy; <a href="https://carto.com">CARTO</a>'
      subdomains="abcd"
      maxZoom={19}
    />
  )
}

export default function GeoIPPage() {
  const [points, setPoints] = useState([])
  const [aggregated, setAggregated] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const load = useCallback(async () => {
    try {
      const r = await flowsApi.geoip(300)
      const pts = (r.data.points || []).filter(p => p.lat !== 0 || p.lon !== 0)
      setPoints(pts)
      setAggregated(aggregateByIP(pts))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    let interval
    if (autoRefresh) {
      interval = setInterval(load, 15_000)
    }
    return () => clearInterval(interval)
  }, [load, autoRefresh])

  const countByCountry = points.reduce((acc, p) => {
    if (p.country) acc[p.country] = (acc[p.country] || 0) + 1
    return acc
  }, {})
  const topCountries = Object.entries(countByCountry)
    .sort((a,b) => b[1]-a[1]).slice(0, 10)

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">GeoIP Map</div>
          <div className="page-subtitle">Source IP geolocation — {points.length} active origins</div>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <label style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={e => setAutoRefresh(e.target.checked)}
              style={{ accentColor: 'var(--accent)' }}
            />
            Auto-refresh (15s)
          </label>
          <button className="btn btn-ghost" onClick={load} style={{ fontSize: 12 }}>↻ Refresh</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 16, height: 'calc(100vh - 200px)', minHeight: 500 }}>
        {/* Map */}
        <div className="card" style={{ padding: 0, overflow: 'hidden', position: 'relative' }}>
          {loading && (
            <div style={{
              position: 'absolute', inset: 0, zIndex: 1000,
              background: 'rgba(8,11,20,0.7)', display: 'flex',
              alignItems: 'center', justifyContent: 'center',
              color: 'var(--text-secondary)', fontSize: 13,
            }}>
              Loading GeoIP data...
            </div>
          )}
          <MapContainer
            center={[20, 0]}
            zoom={2}
            style={{ width: '100%', height: '100%', background: '#0d1117' }}
            zoomControl={true}
          >
            <DarkTileLayer />
            {points.map((p, i) => (
              <CircleMarker
                key={`${p.src_ip}-${i}`}
                center={[p.lat, p.lon]}
                radius={threatToRadius(p.threat_score || 0)}
                pathOptions={{
                  fillColor: threatToColor(p.threat_score || 0),
                  fillOpacity: 0.75,
                  color: threatToColor(p.threat_score || 0),
                  weight: 1,
                  opacity: 0.9,
                }}
                eventHandlers={{ click: () => setSelected(p) }}
              >
                <Popup>
                  <div style={{ fontFamily: 'var(--font-sans)', fontSize: 12, minWidth: 180 }}>
                    <div style={{ fontWeight: 700, marginBottom: 6, fontFamily: 'monospace' }}>{p.src_ip}</div>
                    <div>📍 {p.city}, {p.country}</div>
                    <div>🏷 {p.flow_label}</div>
                    <div style={{ color: threatToColor(p.threat_score || 0) }}>
                      ⚠ Threat: {p.threat_score || 0}/100
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>

          {/* Legend */}
          <div style={{
            position: 'absolute', bottom: 16, left: 16, zIndex: 999,
            background: 'rgba(8,11,20,0.9)', border: '1px solid var(--border)',
            borderRadius: 8, padding: '10px 14px', backdropFilter: 'blur(10px)',
          }}>
            <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginBottom: 8, letterSpacing: '0.1em', fontWeight: 600 }}>
              THREAT SCORE
            </div>
            {[
              { label: 'Critical (80+)', color: '#ef4444' },
              { label: 'High (60+)',     color: '#f59e0b' },
              { label: 'Medium (40+)',   color: '#eab308' },
              { label: 'Low (20+)',      color: '#10b981' },
              { label: 'Info',           color: '#6366f1' },
            ].map(l => (
              <div key={l.label} style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 5 }}>
                <span style={{ width: 10, height: 10, borderRadius: '50%', background: l.color, display: 'inline-block' }} />
                <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{l.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Sidebar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, overflowY: 'auto' }}>
          {/* Selected IP detail */}
          {selected && (
            <div className="card" style={{ borderColor: threatToColor(selected.threat_score || 0) }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                <div style={{ fontSize: 12, fontWeight: 700 }}>Selected IP</div>
                <button onClick={() => setSelected(null)} style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', fontSize: 14 }}>✕</button>
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 14, color: threatToColor(selected.threat_score || 0), marginBottom: 8 }}>
                {selected.src_ip}
              </div>
              {[
                { label: 'Country', value: selected.country },
                { label: 'City',    value: selected.city },
                { label: 'Label',   value: selected.flow_label },
                { label: 'Threat',  value: `${selected.threat_score}/100` },
                { label: 'Coords',  value: `${selected.lat?.toFixed(2)}, ${selected.lon?.toFixed(2)}` },
              ].map(r => (
                <div key={r.label} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5, fontSize: 12 }}>
                  <span style={{ color: 'var(--text-dim)' }}>{r.label}</span>
                  <span style={{ color: 'var(--text-primary)' }}>{r.value || '—'}</span>
                </div>
              ))}
            </div>
          )}

          {/* Top countries */}
          <div className="card">
            <div className="section-title">Top Countries</div>
            {topCountries.map(([country, count], i) => (
              <div key={country} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span style={{ fontSize: 11, color: 'var(--text-dim)', width: 16 }}>{i+1}</span>
                <span style={{ flex: 1, fontSize: 12 }}>{country}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--accent2)' }}>{count}</span>
              </div>
            ))}
            {topCountries.length === 0 && (
              <div style={{ color: 'var(--text-dim)', fontSize: 12 }}>No GeoIP data yet.</div>
            )}
          </div>

          {/* Threat IPs list */}
          <div className="card" style={{ flex: 1 }}>
            <div className="section-title">High Threat IPs</div>
            <div style={{ overflowY: 'auto', maxHeight: 300 }}>
              {aggregated.filter(a => a.maxThreat >= 40).slice(0, 20).map(a => (
                <div
                  key={a.ip}
                  onClick={() => setSelected({ src_ip: a.ip, lat: a.lat, lon: a.lon, country: a.country, city: a.city, threat_score: a.maxThreat, flow_label: [...a.labels].join(', ') })}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    marginBottom: 8, cursor: 'pointer',
                    padding: '6px 8px', borderRadius: 6,
                    background: 'transparent',
                    transition: 'background 0.15s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-glass)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: threatToColor(a.maxThreat), flexShrink: 0 }} />
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, flex: 1 }}>{a.ip}</span>
                  <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>{a.country}</span>
                  <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: threatToColor(a.maxThreat) }}>{a.maxThreat}</span>
                </div>
              ))}
              {aggregated.filter(a => a.maxThreat >= 40).length === 0 && (
                <div style={{ color: 'var(--text-dim)', fontSize: 12 }}>No high-threat IPs.</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
