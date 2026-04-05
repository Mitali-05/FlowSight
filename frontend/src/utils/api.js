import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    console.error('API error:', err.response?.data || err.message)
    return Promise.reject(err)
  }
)

export default api

export const captureApi = {
  interfaces: () => api.get('/capture/interfaces'),
  start: (interface_, sessionId) =>
    api.post('/capture/start', { interface: interface_, session_id: sessionId }),
  stop: () => api.post('/capture/stop'),
  status: () => api.get('/capture/status'),
}

export const flowsApi = {
  list: (params) => api.get('/flows/', { params }),
  stats: (sessionId) => api.get('/flows/stats', { params: { session_id: sessionId } }),
  geoip: (limit = 200) => api.get('/flows/geoip', { params: { limit } }),
  timeline: (hours = 1) => api.get('/flows/timeline', { params: { hours } }),
  distribution: () => api.get('/flows/distribution'),
  topTalkers: (limit = 10) => api.get('/flows/top-talkers', { params: { limit } }),
}

export const alertsApi = {
  list: (params) => api.get('/alerts/', { params }),
  acknowledge: (id) => api.post(`/alerts/${id}/acknowledge`),
  delete: (id) => api.delete(`/alerts/${id}`),
  summary: () => api.get('/alerts/summary'),
}

export const reportsApi = {
  summary: (sessionId) => api.get('/reports/summary', { params: { session_id: sessionId } }),
  csvUrl: (sessionId) => `/api/reports/csv${sessionId ? `?session_id=${sessionId}` : ''}`,
  pdfUrl: (sessionId) => `/api/reports/pdf${sessionId ? `?session_id=${sessionId}` : ''}`,
}
