import { Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import NewInvestigation from './pages/NewInvestigation'
import Results from './pages/Results'
import GraphView from './pages/GraphView'
import EntityView from './pages/EntityView'
import Sources from './pages/Sources'
import Social from './pages/Social'
import Compare from './pages/Compare'
import Navbar from './components/Navbar'

export default function App() {
  return (
    <div className="app">
      <Navbar />
      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/new" element={<NewInvestigation />} />
          <Route path="/inv/:id" element={<Results />} />
          <Route path="/inv/:id/graph" element={<GraphView />} />
          <Route path="/inv/:id/entity/:eid" element={<EntityView />} />
          <Route path="/inv/:id/sources" element={<Sources />} />
          <Route path="/inv/:id/social" element={<Social />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}