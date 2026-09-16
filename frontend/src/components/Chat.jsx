import { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'
import ArtifactViewer from './ArtifactViewer'

const SUGGESTED_PROMPTS = [
  "What's the best way to measure product-market fit?",
  "How do growth loops differ from funnels?",
  "What makes a great North Star Metric?",
  "Explain SaaS pricing strategy from Lenny's transcripts",
  "What does Lenny say about user retention?",
]

export default function Chat({
  messages,
  loading,
  error,
  config,
  onSend,
  currentSession,
}) {
  const [input, setInput] = useState('')
  const [generateShip30, setGenerateShip30] = useState(false)
  const [generateArtifact, setGenerateArtifact] = useState(false)
  const [artifactType, setArtifactType] = useState('markdown')
  const [activeArtifact, setActiveArtifact] = useState(null)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    inputRef.current?.focus()
  }, [currentSession])

  const handleSend = () => {
    if (!input.trim() || loading) return
    onSend(input.trim(), {
      generateShip30,
      generateArtifact,
      artifactType: generateArtifact ? artifactType : null,
    })
    setInput('')
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const isEmpty = messages.length === 0

  return (
    <div className="flex h-full overflow-hidden">
      {/* Main chat area */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Provider badge */}
        {config && (
          <div className="flex items-center justify-end gap-2 px-4 py-2 border-b border-gray-100 bg-gray-50">
            <span className="text-xs text-gray-500">Provider:</span>
            <span
              className={`text-xs font-mono px-2 py-0.5 rounded-full font-medium ${
                config.llm_provider === 'anthropic'
                  ? 'bg-orange-100 text-orange-700'
                  : 'bg-purple-100 text-purple-700'
              }`}
            >
              {config.llm_provider} / {config.llm_model}
            </span>
            {config.indexed_chunks > 0 && (
              <span className="text-xs text-gray-400">
                {config.indexed_chunks} chunks indexed
              </span>
            )}
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {isEmpty ? (
            <EmptyState onPrompt={(p) => { setInput(p); inputRef.current?.focus() }} />
          ) : (
            <div className="flex flex-col gap-6 max-w-3xl mx-auto">
              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  onViewArtifact={setActiveArtifact}
                />
              ))}
              {loading && <TypingIndicator />}
              {error && (
                <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                  {error}
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input area */}
        <div className="border-t border-gray-200 bg-white px-4 py-4">
          <div className="max-w-3xl mx-auto">
            {/* Skill toggles */}
            <div className="flex items-center gap-3 mb-3 flex-wrap">
              <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={generateShip30}
                  onChange={(e) => setGenerateShip30(e.target.checked)}
                  className="rounded"
                />
                <span>✍️ Ship 30 for 30 Essay</span>
              </label>
              <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={generateArtifact}
                  onChange={(e) => setGenerateArtifact(e.target.checked)}
                  className="rounded"
                />
                <span>📄 Generate Artifact</span>
              </label>
              {generateArtifact && (
                <select
                  value={artifactType}
                  onChange={(e) => setArtifactType(e.target.value)}
                  className="text-xs border border-gray-300 rounded px-2 py-0.5"
                >
                  <option value="markdown">Markdown</option>
                  <option value="html">HTML</option>
                </select>
              )}
            </div>

            {/* Text input */}
            <div className="flex gap-3 items-end">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask about product strategy, growth, pricing..."
                rows={1}
                className="flex-1 resize-none border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-lenny-500 focus:border-transparent bg-gray-50"
                style={{ minHeight: '48px', maxHeight: '200px' }}
                onInput={(e) => {
                  e.target.style.height = 'auto'
                  e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px'
                }}
                disabled={loading}
              />
              <button
                onClick={handleSend}
                disabled={loading || !input.trim()}
                className="flex-shrink-0 w-11 h-11 rounded-xl bg-lenny-500 text-white flex items-center justify-center hover:bg-lenny-600 disabled:opacity-40 disabled:cursor-not-allowed transition"
                aria-label="Send message"
              >
                {loading ? (
                  <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                )}
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-2">
              Answers grounded in Lenny's Podcast transcripts · Enter to send · Shift+Enter for new line
            </p>
          </div>
        </div>
      </div>

      {/* Artifact panel */}
      {activeArtifact && (
        <div className="w-[480px] flex-shrink-0 border-l border-gray-200 overflow-hidden">
          <ArtifactViewer artifact={activeArtifact} onClose={() => setActiveArtifact(null)} />
        </div>
      )}
    </div>
  )
}

function EmptyState({ onPrompt }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-8">
      <div className="w-16 h-16 rounded-2xl bg-lenny-500 flex items-center justify-center text-3xl mb-4">
        🎙
      </div>
      <h2 className="text-xl font-bold text-gray-900 mb-2">Lenny Growth Assistant</h2>
      <p className="text-gray-500 text-sm max-w-md mb-8">
        Ask any product or growth question. Every answer is grounded in Lenny Rachitsky's podcast transcripts.
      </p>
      <div className="flex flex-col gap-2 w-full max-w-lg">
        {SUGGESTED_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            onClick={() => onPrompt(prompt)}
            className="text-left text-sm px-4 py-3 rounded-xl border border-gray-200 hover:border-lenny-300 hover:bg-lenny-50 text-gray-700 hover:text-lenny-700 transition"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-full bg-gray-800 flex items-center justify-center text-sm font-bold text-white flex-shrink-0">
        L
      </div>
      <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-none px-4 py-3 shadow-sm">
        <div className="flex gap-1 items-center h-5">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
