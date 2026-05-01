import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 5000,
})

export async function submitQa(queryText) {
  const { data } = await api.post('/qa/query', { query_text: queryText })
  return data
}

export async function submitAudit(payload) {
  const { data } = await api.post('/audit/submit', payload)
  return data
}

export async function fetchQaHistory() {
  const { data } = await api.get('/qa/history')
  return data
}

export async function fetchAuditHistory() {
  const { data } = await api.get('/audit/history')
  return data
}

// 多国家API
export async function fetchCountries() {
  const { data } = await api.get('/countries')
  return data
}

export async function submitMultiAudit(payload) {
  const { data } = await api.post('/multi/audit/submit', payload)
  return data
}
