import { NavLink } from 'react-router-dom'

const NAV = [
  { to: '/dashboard',      icon: '⬡', label: 'Dashboard' },
  { to: '/live',           icon: '◉', label: 'Live Monitor' },
  { to: '/classification', icon: '◈', label: 'Classification' },
  { to: '/anomalies',      icon: '⚠', label: 'Anomaly Detection' },
  { to: '/geoip',          icon: '◎', label: 'GeoIP Map' },
  { to: '/alerts',         icon: '⬥', label: 'Alerts & Threats' },
  { to: '/reports',        icon: '▤', label: 'Reports Export' },
]

export default function Sidebar() {
  return (
    <aside style={{
      position: 'fixed', left: 0, top: 0, bottom: 0,
      width: 'var(--sidebar-w)',
      background: 'rgba(8,11,20,0.97)',
      borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column',
      backdropFilter: 'blur(20px)',
      zIndex: 100,
    }}>
      {/* Logo */}
      <div style={{
        padding: '20px 18px 16px',
        borderBottom: '1px solid var(--border)',
      }}>
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '16px',
          fontWeight: 700,
          color: 'var(--accent)',
          letterSpacing: '0.04em',
        }}>
          FLOW<span style={{ color: 'var(--text-primary)' }}>SIGHT</span>
        </div>
        <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px', letterSpacing: '0.1em' }}>
          AI TRAFFIC CLASSIFIER AND MONITOR
        </div>
      </div>

      {/* Nav */}
      <nav style={{ padding: '12px 10px', flex: 1 }}>
        <div style={{ fontSize: '10px', color: 'var(--text-dim)', letterSpacing: '0.1em', padding: '8px 8px 6px', fontWeight: 600 }}>
          NAVIGATION
        </div>
        {NAV.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '9px 10px',
              borderRadius: '8px',
              marginBottom: '2px',
              textDecoration: 'none',
              fontSize: '13px',
              fontWeight: isActive ? 600 : 400,
              color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
              background: isActive ? 'rgba(99,102,241,0.12)' : 'transparent',
              borderLeft: isActive ? '2px solid var(--accent)' : '2px solid transparent',
              transition: 'all 0.15s',
            })}
          >
            <span style={{ fontSize: '14px', opacity: 0.8 }}>{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div style={{
        padding: '12px 18px',
        borderTop: '1px solid var(--border)',
        fontSize: '10px',
        color: 'var(--text-dim)',
      }}>
        v1.0.0 · FLOWSIGHT
      </div>
    </aside>
  )
}
