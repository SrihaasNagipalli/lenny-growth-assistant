export default function SessionList({ sessions, currentSession, onSelect, onNew, onDelete }) {
  return (
    <div className="flex flex-col h-full bg-gray-900 text-white">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-gray-700">
        <h1 className="text-base font-bold tracking-tight">🎙 Lenny Growth</h1>
        <p className="text-xs text-gray-400 mt-0.5">Powered by Lenny's Podcast</p>
      </div>

      {/* New chat button */}
      <div className="px-3 py-3">
        <button
          onClick={onNew}
          className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg border border-dashed border-gray-600 text-sm text-gray-300 hover:border-gray-400 hover:text-white transition"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New chat
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {sessions.length === 0 ? (
          <p className="text-xs text-gray-500 text-center mt-4 px-3">
            No chats yet. Start a new one!
          </p>
        ) : (
          <div className="flex flex-col gap-1">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`group flex items-center justify-between rounded-lg px-3 py-2.5 cursor-pointer transition ${
                  currentSession?.id === session.id
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                }`}
                onClick={() => onSelect(session)}
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    {session.title || 'New conversation'}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {new Date(session.created_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); onDelete(session.id) }}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded text-gray-500 hover:text-red-400 transition"
                  aria-label="Delete session"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
