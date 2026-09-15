import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import App from './App'
import { BottleneckDetailPage } from './pages/BottleneckDetailPage'
import { SupplyRiskDetailPage } from './pages/SupplyRiskDetailPage'
import { SimulatorPage } from './pages/SimulatorPage'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        {/* Main dashboard (/) */}
        <Route path="/" element={<App />} />
        <Route path="/dashboard" element={<App />} />

        {/* Bottleneck detail (/bottlenecks/:toolId) */}
        <Route path="/bottlenecks/:toolId" element={<BottleneckDetailPage />} />

        {/* Supply risk detail (/supply-risk/:materialId) */}
        <Route path="/supply-risk/:materialId" element={<SupplyRiskDetailPage />} />

        {/* What-if simulator (/simulator) */}
        <Route path="/simulator" element={<SimulatorPage />} />

        {/* Fallback → dashboard */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
