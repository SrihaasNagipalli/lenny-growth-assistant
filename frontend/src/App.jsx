import { useEffect } from 'react'
import { useChat } from './hooks/useChat'
import SessionList from './components/SessionList'
import Chat from './components/Chat'

export default function App() {
  const {
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
  } = useChat()

  useEffect(() => {
    loadConfig()
    loadSessions()
  }, [])

  return (
    <div className="flex h-screen bg-gray-50 font-sans">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 overflow-hidden">
        <SessionList
          sessions={sessions}
          currentSession={currentSession}
          onSelect={selectSession}
          onNew={newSession}
          onDelete={deleteSession}
        />
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        <Chat
          messages={messages}
          loading={loading}
          error={error}
          config={config}
          onSend={sendMessage}
          currentSession={currentSession}
        />
      </main>
    </div>
  )
}
