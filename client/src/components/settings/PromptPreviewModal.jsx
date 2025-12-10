import { useState, useEffect } from 'react'
import { useAppStore } from '../../stores/appStore'

const API_BASE = '/api'

const TABS = [
    { id: 'director', label: '🎬 Director', color: '#6366f1' },
    { id: 'writer', label: '✍️ Writer', color: '#22c55e' },
    { id: 'paint_director', label: '🎨 Paint Director', color: '#f59e0b' }
]

function MessageBadge({ role }) {
    const colors = {
        system: { bg: '#374151', text: '#d1d5db' },
        user: { bg: '#3b82f6', text: '#fff' },
        assistant: { bg: '#10b981', text: '#fff' }
    }
    const style = colors[role] || colors.user
    return (
        <span style={{
            display: 'inline-block',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: 11,
            fontWeight: 600,
            textTransform: 'uppercase',
            background: style.bg,
            color: style.text
        }}>
            {role}
        </span>
    )
}

function PlaceholderBadge({ text }) {
    return (
        <span style={{
            display: 'inline-block',
            padding: '4px 12px',
            borderRadius: '6px',
            fontSize: 13,
            fontWeight: 600,
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            color: '#fff',
            fontFamily: 'monospace'
        }}>
            {text}
        </span>
    )
}

function ContentBlock({ content, isSystem }) {
    // Highlight placeholders like {DIRECTOR_OUTLINE}
    const renderContent = (text) => {
        if (!text) return null
        const parts = text.split(/(\{[A-Z_]+\})/g)
        return parts.map((part, i) => {
            if (/^\{[A-Z_]+\}$/.test(part)) {
                return <PlaceholderBadge key={i} text={part} />
            }
            return <span key={i}>{part}</span>
        })
    }

    return (
        <pre style={{
            background: isSystem ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
            padding: 'var(--space-md)',
            borderRadius: 'var(--radius-md)',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            fontSize: 13,
            lineHeight: 1.6,
            margin: 0,
            maxHeight: isSystem ? 400 : 200,
            overflow: 'auto',
            border: '1px solid var(--border-subtle)'
        }}>
            {renderContent(content)}
        </pre>
    )
}

export default function PromptPreviewModal({ isOpen, onClose }) {
    const { activeCharacter, activeWorldbooks, activeSession } = useAppStore()
    const [activeTab, setActiveTab] = useState('director')
    const [preview, setPreview] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [sampleMessage, setSampleMessage] = useState('Hello, how are you?')
    const [systemCollapsed, setSystemCollapsed] = useState({})

    const fetchPreview = async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch(`${API_BASE}/agent/preview`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    character_id: activeCharacter?.id,
                    worldbook_ids: activeWorldbooks.map(wb => wb.id),
                    sample_message: sampleMessage,
                    session_id: activeSession?.id
                })
            })
            if (!res.ok) throw new Error(`Failed: ${res.status}`)
            const data = await res.json()
            setPreview(data)
        } catch (e) {
            setError(e.message)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (isOpen) {
            fetchPreview()
        }
    }, [isOpen])

    if (!isOpen) return null

    const currentPreview = preview?.previews?.[activeTab]
    const tabInfo = TABS.find(t => t.id === activeTab)

    return (
        <div className="settings-modal-overlay" onClick={onClose}>
            <div
                className="settings-modal"
                onClick={e => e.stopPropagation()}
                style={{ maxWidth: 900, width: '90%' }}
            >
                <div className="settings-modal-header">
                    <span className="settings-modal-icon">👁️</span>
                    <span className="settings-modal-title">Agent Prompt Preview</span>
                    <button className="settings-modal-close" onClick={onClose}>✕</button>
                </div>

                <div className="settings-modal-content" style={{ padding: 0 }}>
                    {/* Context Info Bar */}
                    {preview?.context && (
                        <div style={{
                            padding: 'var(--space-sm) var(--space-lg)',
                            background: 'var(--bg-tertiary)',
                            borderBottom: '1px solid var(--border-subtle)',
                            display: 'flex',
                            gap: 'var(--space-lg)',
                            fontSize: 13
                        }}>
                            <span>
                                <strong>Character:</strong> {preview.context.character_name || 'None'}
                            </span>
                            <span>
                                <strong>Worldbook:</strong> {preview.context.worldbook_name || 'None'}
                            </span>
                            <span>
                                <strong>Chat History:</strong> {preview.context.chat_history_length} messages
                            </span>
                        </div>
                    )}

                    {/* Sample Message Input */}
                    <div style={{
                        padding: 'var(--space-md) var(--space-lg)',
                        borderBottom: '1px solid var(--border-subtle)',
                        display: 'flex',
                        gap: 'var(--space-md)',
                        alignItems: 'center'
                    }}>
                        <label style={{ fontSize: 13, fontWeight: 500 }}>Sample Message:</label>
                        <input
                            type="text"
                            className="input"
                            value={sampleMessage}
                            onChange={e => setSampleMessage(e.target.value)}
                            style={{ flex: 1 }}
                            placeholder="Enter sample user message..."
                        />
                        <button className="btn btn-small" onClick={fetchPreview} disabled={loading}>
                            {loading ? '...' : 'Refresh'}
                        </button>
                    </div>

                    {/* Tabs */}
                    <div style={{
                        display: 'flex',
                        borderBottom: '1px solid var(--border-subtle)'
                    }}>
                        {TABS.map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                style={{
                                    flex: 1,
                                    padding: 'var(--space-md)',
                                    background: activeTab === tab.id ? 'var(--bg-secondary)' : 'transparent',
                                    border: 'none',
                                    borderBottom: activeTab === tab.id ? `2px solid ${tab.color}` : '2px solid transparent',
                                    color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-muted)',
                                    cursor: 'pointer',
                                    fontSize: 14,
                                    fontWeight: 500,
                                    transition: 'all 0.2s'
                                }}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </div>

                    {/* Content */}
                    <div style={{ padding: 'var(--space-lg)', maxHeight: 500, overflow: 'auto' }}>
                        {loading && (
                            <div style={{ textAlign: 'center', padding: 'var(--space-2xl)', color: 'var(--text-muted)' }}>
                                Loading preview...
                            </div>
                        )}

                        {error && (
                            <div style={{
                                padding: 'var(--space-md)',
                                background: 'var(--error-bg)',
                                color: 'var(--error-text)',
                                borderRadius: 'var(--radius-md)'
                            }}>
                                Error: {error}
                            </div>
                        )}

                        {currentPreview && !loading && (
                            <div>
                                {/* Preset Info */}
                                <div style={{
                                    marginBottom: 'var(--space-md)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 'var(--space-sm)'
                                }}>
                                    <span style={{
                                        padding: '4px 10px',
                                        background: tabInfo.color,
                                        color: '#fff',
                                        borderRadius: 'var(--radius-sm)',
                                        fontSize: 12,
                                        fontWeight: 600
                                    }}>
                                        Preset: {currentPreview.preset_name || 'Default'}
                                    </span>
                                </div>

                                {/* Messages */}
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
                                    {currentPreview.messages.map((msg, idx) => (
                                        <div key={idx}>
                                            <div style={{
                                                marginBottom: 'var(--space-xs)',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: 'var(--space-sm)'
                                            }}>
                                                <MessageBadge role={msg.role} />
                                                {msg.role === 'system' && (
                                                    <button
                                                        onClick={() => setSystemCollapsed(p => ({ ...p, [idx]: !p[idx] }))}
                                                        style={{
                                                            background: 'none',
                                                            border: 'none',
                                                            color: 'var(--text-muted)',
                                                            cursor: 'pointer',
                                                            fontSize: 12
                                                        }}
                                                    >
                                                        {systemCollapsed[idx] ? '▶ Expand' : '▼ Collapse'}
                                                    </button>
                                                )}
                                            </div>
                                            {(!systemCollapsed[idx] || msg.role !== 'system') && (
                                                <ContentBlock content={msg.content} isSystem={msg.role === 'system'} />
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
