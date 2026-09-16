import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ breaks: true, gfm: true })

function SourceBadge({ source }) {
  return (
    <div className="flex items-start gap-2 text-xs text-gray-500 bg-gray-50 rounded-md px-3 py-2 mt-1">
      <svg className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-lenny-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <div>
        <span className="font-medium text-gray-700">{source.title}</span>
        <span className="text-gray-400 mx-1">·</span>
        <span className="font-mono">{source.episode}</span>
        <span className="text-gray-400 mx-1">·</span>
        <span className="text-green-600">{Math.round(source.relevance_score * 100)}% match</span>
        {source.excerpt && (
          <p className="mt-0.5 text-gray-400 italic truncate max-w-xs">&ldquo;{source.excerpt}&rdquo;</p>
        )}
      </div>
    </div>
  )
}

export default function MessageBubble({ message, onViewArtifact }) {
  const isUser = message.role === 'user'
  const hasSources = message.sources && message.sources.length > 0
  const hasArtifact = !!message.artifact

  const htmlContent = isUser
    ? null
    : DOMPurify.sanitize(marked.parse(message.content || ''), {
        FORBID_TAGS: ['script', 'iframe', 'object', 'embed'],
        FORBID_ATTR: ['onerror', 'onload', 'onclick'],
      })

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-sm font-bold ${
          isUser ? 'bg-lenny-500 text-white' : 'bg-gray-800 text-white'
        }`}
      >
        {isUser ? 'U' : 'L'}
      </div>

      {/* Bubble */}
      <div className={`flex flex-col gap-1.5 max-w-[85%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? 'bg-lenny-500 text-white rounded-tr-none'
              : 'bg-white border border-gray-200 text-gray-800 rounded-tl-none shadow-sm'
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div
              className="prose prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-li:my-0.5"
              dangerouslySetInnerHTML={{ __html: htmlContent }}
            />
          )}
        </div>

        {/* Sources */}
        {hasSources && (
          <div className="flex flex-col gap-1 w-full">
            <p className="text-xs text-gray-400 font-medium">Sources</p>
            {message.sources.slice(0, 3).map((src, i) => (
              <SourceBadge key={i} source={src} />
            ))}
          </div>
        )}

        {/* Artifact button */}
        {hasArtifact && (
          <button
            onClick={() => onViewArtifact(message.artifact)}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-lenny-200 bg-lenny-50 text-lenny-700 hover:bg-lenny-100 transition"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
            View {message.artifact.type === 'html' ? 'HTML' : 'Markdown'} Artifact
          </button>
        )}

        {/* Timestamp + model */}
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <span>{new Date(message.created_at).toLocaleTimeString()}</span>
          {message.llm_provider && (
            <>
              <span>·</span>
              <span className="font-mono">{message.llm_provider}/{message.llm_model?.split('-').slice(-2).join('-')}</span>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
