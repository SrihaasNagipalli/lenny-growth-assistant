/**
 * ArtifactViewer — renders Markdown or HTML artifacts beside the chat.
 *
 * Security model:
 * - Markdown: rendered with marked.js + sanitized with DOMPurify (strip scripts, dangerous attrs)
 * - HTML: rendered in a sandboxed <iframe> with:
 *     sandbox="allow-scripts"  (scripts run, but no top-navigation, no popups, no forms)
 *     no allow-same-origin     (iframe gets a unique opaque origin — cannot access cookies or localStorage)
 *     srcdoc=                  (no external URL, so no cross-origin data exfiltration)
 *   Additional CSP via meta tag inside srcdoc blocks external resource loading.
 * - Server also sanitizes HTML with bleach before it ever reaches the client.
 */
import { useEffect, useRef, useState } from 'react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ breaks: true, gfm: true })

function MarkdownArtifact({ content }) {
  const sanitized = DOMPurify.sanitize(marked.parse(content), {
    ADD_TAGS: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
    FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover'],
  })

  return (
    <div
      className="prose prose-sm max-w-none p-4 text-gray-800"
      dangerouslySetInnerHTML={{ __html: sanitized }}
    />
  )
}

function HTMLArtifact({ content }) {
  // Inject a restrictive CSP meta tag into the artifact HTML
  const safeHtml = content.replace(
    /<head>/i,
    `<head><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';">`
  )

  return (
    <iframe
      srcDoc={safeHtml}
      sandbox="allow-scripts"
      title="Artifact Preview"
      className="w-full border-0 rounded-b-lg"
      style={{ minHeight: '400px', height: '100%' }}
    />
  )
}

export default function ArtifactViewer({ artifact, onClose }) {
  const [copied, setCopied] = useState(false)

  if (!artifact) return null

  const handleCopy = async () => {
    await navigator.clipboard.writeText(artifact.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    const ext = artifact.type === 'html' ? 'html' : 'md'
    const blob = new Blob([artifact.content], {
      type: artifact.type === 'html' ? 'text/html' : 'text/markdown',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `lenny-artifact.${ext}`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col h-full bg-white border-l border-gray-200">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-700">Artifact</span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-lenny-100 text-lenny-700 font-medium uppercase tracking-wide">
            {artifact.type}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="text-xs px-3 py-1.5 rounded-md border border-gray-300 text-gray-600 hover:bg-gray-100 transition"
          >
            {copied ? '✓ Copied' : 'Copy'}
          </button>
          <button
            onClick={handleDownload}
            className="text-xs px-3 py-1.5 rounded-md border border-gray-300 text-gray-600 hover:bg-gray-100 transition"
          >
            Download
          </button>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-lg leading-none"
            aria-label="Close artifact"
          >
            ×
          </button>
        </div>
      </div>

      {/* Security note */}
      {artifact.type === 'html' && (
        <div className="px-4 py-1.5 bg-amber-50 border-b border-amber-100 text-xs text-amber-700 flex items-center gap-1.5">
          <svg className="w-3.5 h-3.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          Rendered in sandboxed iframe — no external resources, no cookie access
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {artifact.type === 'html' ? (
          <HTMLArtifact content={artifact.content} />
        ) : (
          <MarkdownArtifact content={artifact.content} />
        )}
      </div>
    </div>
  )
}
