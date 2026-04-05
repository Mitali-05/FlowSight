import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import App from './App'
import './styles/global.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'rgba(20, 20, 35, 0.95)',
            color: '#e2e8f0',
            border: '1px solid rgba(99, 102, 241, 0.3)',
            backdropFilter: 'blur(12px)',
            fontFamily: "'DM Sans', sans-serif",
            fontSize: '13px',
          },
          success: { iconTheme: { primary: '#10b981', secondary: '#0f172a' } },
          error: { iconTheme: { primary: '#ef4444', secondary: '#0f172a' } },
        }}
      />
    </BrowserRouter>
  </React.StrictMode>
)
