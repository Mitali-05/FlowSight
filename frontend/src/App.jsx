import { Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Header from './components/Header'
import DashboardPage from './pages/DashboardPage'
import LiveMonitorPage from './pages/LiveMonitorPage'
import ClassificationPage from './pages/ClassificationPage'
import AnomalyPage from './pages/AnomalyPage'
import GeoIPPage from './pages/GeoIPPage'
import AlertsPage from './pages/AlertsPage'
import ReportsPage from './pages/ReportsPage'
import { useWebSocket } from './hooks/useWebSocket'

export default function App() {
  const ws = useWebSocket()

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-content">
        <Header connected={ws.connected} alerts={ws.alerts} />
        <main className="page-body">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard"      element={<DashboardPage ws={ws} />} />
            <Route path="/live"           element={<LiveMonitorPage ws={ws} />} />
            <Route path="/classification" element={<ClassificationPage />} />
            <Route path="/anomalies"      element={<AnomalyPage />} />
            <Route path="/geoip"          element={<GeoIPPage />} />
            <Route path="/alerts"         element={<AlertsPage wsAlerts={ws.alerts} />} />
            <Route path="/reports"        element={<ReportsPage />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
