import { useState, useCallback, useRef } from 'react'
import { api } from '../api/client'

export function useChat() {
  const [sessions, setSessions] = useState([])
  const [currentSession, setCurrentSession] = useState(null)
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [config, setConfig] = useState(null)
  const abortRef = useRef(null)

  const loadConfig = useCallback(async () => {
    try {
      const data = await api.config()
      setConfig(data)
    } catch (e) {
      console.error('Config load failed:', e)
    }
  }, [])

  const loadSessions = useCallback(async () => {
    try {
      const data = await api.listSessions()
      setSessions(data.sessions || [])
    } catch (e) {
      setError('Failed to load sessions')
    }
  }, [])

  const newSession = useCallback(async () => {
    try {
      const session = await api.createSession({})
      setSessions((prev) => [session, ...prev])
      setCurrentSession(session)
      setMessages([])
      setError(null)
      return session
    } catch (e) {
      setError('Failed to create session')
    }
  }, [])

  const selectSession = useCallback(async (session) => {
    setCurrentSession(session)
    setError(null)
    try {
      const msgs = await api.getMessages(session.id)
      setMessages(msgs)
    } catch (e) {
      setMessages([])
    }
  }, [])

  const deleteSession = useCallback(async (sessionId) => {
    try {
      await api.deleteSession(sessionId)
      setSessions((prev) => prev.filter((s) => s.id !== sessionId))
      if (currentSession?.id === sessionId) {
        setCurrentSession(null)
        setMessages([])
      }
    } catch (e) {
      setError('Failed to delete session')
    }
  }, [currentSession])

  const sendMessage = useCallback(
    async (text, options = {}) => {
      if (!text.trim() || loading) return
      setError(null)

      let session = currentSession
      if (!session) {
        session = await newSession()
        if (!session) return
      }

      // Optimistic user message
      const userMsg = {
        id: `tmp-${Date.now()}`,
        role: 'user',
        content: text,
        sources: [],
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, userMsg])
      setLoading(true)

      try {
        const response = await api.chat(session.id, {
          message: text,
          generate_artifact: options.generateArtifact || false,
          artifact_type: options.artifactType || null,
          generate_ship30: options.generateShip30 || false,
        })

        setMessages((prev) => [
          ...prev.filter((m) => m.id !== userMsg.id),
          userMsg,
          response.message,
        ])

        // Update session title
        setSessions((prev) =>
          prev.map((s) =>
            s.id === session.id
              ? { ...s, title: s.title || text.slice(0, 50) }
              : s
          )
        )
        setConfig((prev) => prev
          ? { ...prev, llm_provider: response.provider, llm_model: response.model }
          : prev
        )
      } catch (e) {
        setMessages((prev) => prev.filter((m) => m.id !== userMsg.id))
        setError(e.message || 'Something went wrong. Please try again.')
      } finally {
        setLoading(false)
      }
    },
    [currentSession, loading, newSession]
  )

  return {
    sessions,
    currentSession,
    messages,
    loading,
    error,
    config,
    loadConfig,
    loadSessions,
    newSession,
    selectSession,
    deleteSession,
    sendMessage,
  }
}
