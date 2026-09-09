import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { useLang } from '../i18n'

const W = 900
const H = 560

function layout(nodes, links) {
  const pos = new Map()
  nodes.forEach((n, i) => {
    const angle = (i / Math.max(nodes.length, 1)) * Math.PI * 2
    pos.set(n.id, { x: W / 2 + Math.cos(angle) * (W / 3), y: H / 2 + Math.sin(angle) * (H / 3) })
  })
  for (let iter = 0; iter < 300; iter++) {
    nodes.forEach((n) => {
      const p = pos.get(n.id)
      p.x += (W / 2 - p.x) * 0.004
      p.y += (H / 2 - p.y) * 0.004
      nodes.forEach((o) => {
        if (n.id === o.id) return
        const q = pos.get(o.id)
        const dx = p.x - q.x
        const dy = p.y - q.y
        const d2 = dx * dx + dy * dy + 1e-6
        const f = Math.min(400 / d2, 2)
        p.x += (dx / Math.sqrt(d2)) * f
        p.y += (dy / Math.sqrt(d2)) * f
      })
    })
    links.forEach((l) => {
      const p = pos.get(l.source)
      const q = pos.get(l.target)
      if (!p || !q) return
      const dx = q.x - p.x
      const dy = q.y - p.y
      const d = Math.sqrt(dx * dx + dy * dy)
      if (d < 1) return
      p.x += dx * 0.04
      p.y += dy * 0.04
      q.x -= dx * 0.04
      q.y -= dy * 0.04
    })
  }
  return pos
}

export default function GraphView() {
  const { id } = useParams()
  const { t } = useLang()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)
  const svgRef = useRef(null)

  useEffect(() => {
    api.graph(id).then(setData).catch((e) => setError(e.message))
  }, [id])

  useEffect(() => {
    if (!data) return
    const pos = layout(data.nodes, data.links)
    const svg = svgRef.current
    const ns = 'http://www.w3.org/2000/svg'
    svg.replaceChildren()

    const nodeById = new Map(data.nodes.map((n) => [n.id, n]))

    data.links.forEach((l) => {
      const p = pos.get(l.source)
      const q = pos.get(l.target)
      const line = document.createElementNS(ns, 'line')
      line.setAttribute('x1', p.x); line.setAttribute('y1', p.y)
      line.setAttribute('x2', q.x); line.setAttribute('y2', q.y)
      line.setAttribute('stroke', '#8494b0'); line.setAttribute('stroke-width', 1.2)
      svg.appendChild(line)
    })

    data.nodes.forEach((n) => {
      const p = pos.get(n.id)
      const g = document.createElementNS(ns, 'g')
      g.setAttribute('transform', `translate(${p.x},${p.y})`)
      g.setAttribute('cursor', 'pointer')
      const circle = document.createElementNS(ns, 'circle')
      circle.setAttribute('r', 16)
      circle.setAttribute('fill', colorFor(n.type))
      circle.setAttribute('stroke', '#fff')
      circle.setAttribute('stroke-width', 2)
      g.appendChild(circle)
      const text = document.createElementNS(ns, 'text')
      text.setAttribute('text-anchor', 'middle')
      text.setAttribute('y', 32)
      text.setAttribute('font-size', 11)
      text.setAttribute('fill', '#cbd5e1')
      const label = n.label.length > 26 ? n.label.slice(0, 25) + '…' : n.label
      text.textContent = label
      g.appendChild(text)
      g.addEventListener('click', () => {
        setSelected({ ...n, x: p.x, y: p.y })
      })
      svg.appendChild(g)
    })
  }, [data])

  if (error) return <p className="error">{error}</p>
  if (!data) return <p>{t('graph.loading')}</p>

  const title = data.nodes.length ? data.nodes[0].label : 'Graph'

  return (
    <div>
      <div className="page-head">
        <h2>{t('graph.title')} {title}</h2>
        <Link to={`/inv/${id}`} className="btn btn-outline">{t('graph.back')}</Link>
      </div>
      <div className="graph-wrap">
        <svg ref={svgRef} width={W} height={H} className="graph" />
        {selected && (
          <div className="graph-tip">
            <b>{selected.label}</b>
            <span>{selected.type} · {selected.id.slice(0, 12)}…</span>
          </div>
        )}
      </div>
      <div className="legend">
        <span className="chip">{t('graph.legend')}</span>
        {['domain', 'ip', 'email', 'username', 'url', 'text'].map((type) => (
          <span key={type} className="chip"><span className="dot" style={{ background: colorFor(type) }} /> {type}</span>
        ))}
      </div>
    </div>
  )
}

function colorFor(type) {
  const colors = {
    domain: '#4f8cf7', ip: '#22c55e', email: '#e879f9', username: '#fbbf24',
    url: '#38bdf8', text: '#94a3b8',
  }
  return colors[type] || '#94a3b8'
}