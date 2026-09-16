const BASE_URL = import.meta.env.VITE_API_URL || ''

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw Object.assign(new Error(err.error || err.detail || 'Request failed'), {
      status: res.status,
      data: err,
    })
  }

  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // Health & Config
  health: () => request('/health'),
  config: () => request('/config'),

  // Sessions
  createSession: (data = {}) =>
    request('/api/v1/sessions', { method: 'POST', body: JSON.stringify(data) }),
  listSessions: (skip = 0, limit = 20) =>
    request(`/api/v1/sessions?skip=${skip}&limit=${limit}`),
  getSession: (id) => request(`/api/v1/sessions/${id}`),
  deleteSession: (id) => request(`/api/v1/sessions/${id}`, { method: 'DELETE' }),
  getMessages: (sessionId) => request(`/api/v1/sessions/${sessionId}/messages`),

  // Chat
  chat: (sessionId, body) =>
    request(`/api/v1/sessions/${sessionId}/chat`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
}
