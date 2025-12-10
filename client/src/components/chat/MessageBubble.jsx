import { useState } from 'react'
import { useAppStore } from '../../stores/appStore'

// Parse <think> blocks from content
function parseThinkingBlocks(content) {
    if (!content) return { thinking: null, content: content || '' }

    const thinkRegex = /<think>([\s\S]*?)<\/think>/g
    let thinking = []
    let match

    while ((match = thinkRegex.exec(content)) !== null) {
        thinking.push(match[1].trim())
    }

    // Remove <think> blocks from content
    const cleanContent = content.replace(/<think>[\s\S]*?<\/think>/g, '').trim()

    return {
        thinking: thinking.length > 0 ? thinking.join('\n\n') : null,
        content: cleanContent
    }
}

// Image zoom modal component
function ImageZoomModal({ src, onClose }) {
    if (!src) return null

    const handleKeyDown = (e) => {
        if (e.key === 'Escape') onClose()
    }

    return (
        <div
            className="image-zoom-overlay"
            onClick={onClose}
            onKeyDown={handleKeyDown}
            tabIndex={0}
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(0, 0, 0, 0.9)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 2000,
                cursor: 'zoom-out',
            }}
        >
            <img
                src={src}
                alt="Zoomed"
                style={{
                    maxWidth: '95vw',
                    maxHeight: '95vh',
                    objectFit: 'contain',
                    borderRadius: 'var(--radius-md)',
                    boxShadow: '0 0 40px rgba(0,0,0,0.5)',
                }}
                onClick={(e) => e.stopPropagation()}
            />
            <div style={{
                position: 'absolute',
                top: 20,
                right: 20,
                color: 'white',
                fontSize: 24,
                cursor: 'pointer',
                opacity: 0.7,
            }}>
                ✕
            </div>
        </div>
    )
}

// Collapsible thinking block component
function ThinkingBlock({ thinking }) {
    const [isOpen, setIsOpen] = useState(false)

    if (!thinking) return null

    return (
        <div style={{
            marginBottom: 'var(--space-sm)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            background: 'var(--bg-primary)',
        }}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-xs)',
                    padding: 'var(--space-xs) var(--space-sm)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--text-muted)',
                    fontSize: 12,
                }}
            >
                <span style={{ transform: isOpen ? 'rotate(90deg)' : 'none', transition: '0.2s' }}>▶</span>
                <span>💭 Thinking...</span>
                <span style={{ marginLeft: 'auto', opacity: 0.6 }}>{thinking.length} chars</span>
            </button>
            {isOpen && (
                <div style={{
                    padding: 'var(--space-sm)',
                    borderTop: '1px solid var(--border-subtle)',
                    fontSize: 12,
                    color: 'var(--text-muted)',
                    whiteSpace: 'pre-wrap',
                    maxHeight: 300,
                    overflow: 'auto',
                }}>
                    {thinking}
                </div>
            )}
        </div>
    )
}

export default function MessageBubble({ message, isStreaming, isLast, onRegenerate, greetingIndex, greetingCount, onSwipeGreeting }) {
    const { activeCharacter } = useAppStore()
    const [zoomedImage, setZoomedImage] = useState(null)

    const isUser = message.role === 'user'
    const isError = message.isError
    const charName = activeCharacter?.data?.name || 'Assistant'
    const avatar = isUser
        ? 'U'
        : charName.charAt(0).toUpperCase()

    // Check if this is the first message (potential greeting swipe)
    const isFirstMessage = message.id === 'first-mes' || greetingCount > 1

    // Parse thinking blocks from content
    const { thinking, content: displayContent } = parseThinkingBlocks(message.content)

    return (
        <div
            className={`message ${isUser ? 'message-user' : 'message-assistant'}`}
            style={isError ? {
                borderLeft: '3px solid var(--accent-error)',
                background: 'rgba(239, 68, 68, 0.1)'
            } : undefined}
        >
            <div
                className="message-avatar"
                style={{
                    backgroundColor: isUser ? 'var(--accent-primary)' : isError ? 'var(--accent-error)' : 'var(--accent-secondary)',
                    color: 'white'
                }}
            >
                {isError ? '!' : avatar}
            </div>

            <div className="message-content" style={{ flex: 1 }}>
                <div style={{
                    fontSize: 12,
                    color: isError ? 'var(--accent-error)' : 'var(--text-muted)',
                    marginBottom: 'var(--space-xs)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}>
                    <span>{isUser ? 'You' : isError ? 'Error' : charName}</span>

                    {/* Action buttons for assistant messages */}
                    {!isUser && !isStreaming && !isError && (
                        <div className="flex gap-sm" style={{ opacity: 0.7 }}>
                            {/* Greeting swipe controls */}
                            {isFirstMessage && greetingCount > 1 && (
                                <>
                                    <button
                                        className="btn btn-small"
                                        onClick={() => onSwipeGreeting?.(-1)}
                                        disabled={greetingIndex <= 0}
                                        title="Previous greeting"
                                        style={{ padding: '2px 6px', fontSize: 11 }}
                                    >
                                        ←
                                    </button>
                                    <span style={{ fontSize: 10, padding: '0 4px' }}>
                                        {greetingIndex + 1}/{greetingCount}
                                    </span>
                                    <button
                                        className="btn btn-small"
                                        onClick={() => onSwipeGreeting?.(1)}
                                        disabled={greetingIndex >= greetingCount - 1}
                                        title="Next greeting"
                                        style={{ padding: '2px 6px', fontSize: 11 }}
                                    >
                                        →
                                    </button>
                                </>
                            )}

                            {/* Regenerate button for last assistant message */}
                            {isLast && onRegenerate && (
                                <button
                                    className="btn btn-small"
                                    onClick={onRegenerate}
                                    title="Regenerate response"
                                    style={{ padding: '2px 6px', fontSize: 11 }}
                                >
                                    🔄
                                </button>
                            )}
                        </div>
                    )}
                </div>

                {/* Thinking block (collapsible) */}
                {!isUser && thinking && <ThinkingBlock thinking={thinking} />}

                <div className="message-text" style={isError ? { color: 'var(--accent-error)' } : undefined}>
                    {displayContent}
                    {isStreaming && <span className="streaming-cursor" />}
                </div>

                {message.image_url && (
                    <img
                        src={message.image_url}
                        alt="Generated"
                        className="message-image"
                        onDoubleClick={() => setZoomedImage(message.image_url)}
                        style={{ cursor: 'zoom-in' }}
                        title="Double-click to zoom"
                    />
                )}

                {zoomedImage && (
                    <ImageZoomModal src={zoomedImage} onClose={() => setZoomedImage(null)} />
                )}

                {message.audio_data && message.audio_data.length > 0 && (
                    <div style={{ marginTop: 'var(--space-md)' }}>
                        {message.audio_data.map((audio, i) => (
                            <div key={i} style={{ marginBottom: 'var(--space-sm)' }}>
                                <span className="text-sm text-muted">{audio.character}: </span>
                                <audio controls src={audio.audio_url} style={{ height: 24 }} />
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}

