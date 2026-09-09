async function request(path, { method = 'GET', body, isForm = false } = {}) {
  const headers = {}
  if (body && !isForm) headers['Content-Type'] = 'application/json'

  const res = await fetch(`/api${path}`, {
    method,
    headers,
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  })

  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = data.detail || JSON.stringify(data)
    } catch (_) {}
    const err = new Error(detail)
    err.status = res.status
    throw err
  }

  if (res.status === 204) return null
  const ct = res.headers.get('content-type') || ''
  return ct.includes('json') ? res.json() : res.text()
}

export const api = {
  listInvestigations: () => request('/investigations'),
  createInvestigation: (raw_input) =>
    request('/investigations', { method: 'POST', body: { raw_input } }),
  investigateFile: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return request('/upload/text', { method: 'POST', body: fd, isForm: true })
  },
  getInvestigation: (id) => request(`/investigations/${id}`),
  graph: (id) => request(`/investigations/${id}/graph`),
  investigationSocial: (id) => request(`/investigations/${id}/social`),
  suggestions: (raw) => request(`/investigations/suggestions?out=${encodeURIComponent(raw || '')}`),
  setTags: (id, tags) =>
    request(`/investigations/${id}/tags`, { method: 'PATCH', body: { tags } }),
  compare: (left, right) => request(`/investigations/diff/${left}/${right}`),
  exportJson: (id) => request(`/investigations/${id}/export/json`),
  exportCsv: (id) => request(`/investigations/${id}/export/csv`),
  generateReport: (id) =>
    request(`/investigations/${id}/report`, { method: 'POST' }),
  uploadImage: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return request('/upload/image', { method: 'POST', body: fd, isForm: true })
  },
  aiAnalyze: (id) => request(`/investigations/${id}/ai`, { method: 'POST' }),
  aiExplain: (id, relKey) =>
    request(`/investigations/${id}/explain/${encodeURIComponent(relKey)}`, { method: 'POST' }),
}