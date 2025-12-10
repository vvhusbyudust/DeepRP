import { useState } from 'react'
import { useAppStore } from '../../stores/appStore'

export default function SessionList() {
    const {
        sessions,
        activeSession,
        loadSession,
        deleteSession,
        createSession,
        activeCharacter
    } = useAppStore()

    const [expandedCharacters, setExpandedCharacters] = useState({})

    const formatDate = (isoString) => {
        if (!isoString) return 'Unknown'
        const date = new Date(isoString)
        const now = new Date()
        const diffMs = now - date
        const diffMins = Math.floor(diffMs / 60000)
        const diffHours = Math.floor(diffMs / 3600000)
        const diffDays = Math.floor(diffMs / 86400000)

        if (diffMins < 1) return 'Just now'
        if (diffMins < 60) return `${diffMins}m ago`
        if (diffHours < 24) return `${diffHours}h ago`
        if (diffDays < 7) return `${diffDays}d ago`
        return date.toLocaleDateString()
    }

    // Get session title from first few words of latest message
    const getSessionTitle = (session) => {
        const messages = session.messages || []
        if (messages.length === 0) return 'New Session'

        const lastMessage = messages[messages.length - 1]
        if (!lastMessage?.content) return 'New Session'

        const content = lastMessage.content.replace(/<[^>]*>/g, '').trim()
        if (content.length <= 30) return content || 'New Session'

        const truncated = content.substring(0, 30)
        const lastSpace = truncated.lastIndexOf(' ')
        return (lastSpace > 15 ? truncated.substring(0, lastSpace) : truncated) + '...'
    }

    const handleDelete = async (e, sessionId) => {
        e.stopPropagation()
        await deleteSession(sessionId)
    }

    const toggleCharacter = (charName) => {
        setExpandedCharacters(prev => ({
            ...prev,
            [charName]: !prev[charName]
        }))
    }

    // Group sessions by character
    const groupedSessions = sessions.reduce((acc, session) => {
        const charName = session.character_name || 'No Character'
        if (!acc[charName]) acc[charName] = []
        acc[charName].push(session)
        return acc
    }, {})

    // Sort sessions within groups by updated_at
    Object.values(groupedSessions).forEach(group => {
        group.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
    })

    const characterEntries = Object.entries(groupedSessions)

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
            {characterEntries.map(([charName, charSessions]) => {
                const isExpanded = expandedCharacters[charName] ?? true
                const sessionCount = charSessions.length
                const hasActive = charSessions.some(s => s.id === activeSession?.id)

                return (
                    <div key={charName} className="card">
                        {/* Character Header - Expandable */}
                        <div
                            className={`card-header ${hasActive ? 'active' : ''}`}
                            style={{
                                cursor: 'pointer',
                                background: hasActive ? 'var(--bg-active)' : undefined
                            }}
                            onClick={() => toggleCharacter(charName)}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                                <span style={{ fontSize: 18 }}>👤</span>
                                <div>
                                    <div style={{ fontWeight: 500 }}>{charName}</div>
                                    <div className="text-sm text-muted">{sessionCount} session{sessionCount !== 1 ? 's' : ''}</div>
                                </div>
                            </div>
                            <span style={{ color: 'var(--text-muted)' }}>
                                {isExpanded ? '▼' : '▶'}
                            </span>
                        </div>

                        {/* Sessions List */}
                        {isExpanded && (
                            <div className="card-body" style={{ padding: 'var(--space-xs)' }}>
                                {charSessions.map(session => (
                                    <div
                                        key={session.id}
                                        className={`list-item ${activeSession?.id === session.id ? 'active' : ''}`}
                                        onClick={() => loadSession(session.id)}
                                        style={{ marginBottom: 'var(--space-xs)' }}
                                    >
                                        <div style={{ flex: 1, minWidth: 0 }}>
                                            <div
                                                className="text-sm"
                                                style={{
                                                    whiteSpace: 'nowrap',
                                                    overflow: 'hidden',
                                                    textOverflow: 'ellipsis',
                                                    fontWeight: 500
                                                }}
                                            >
                                                {getSessionTitle(session)}
                                            </div>
                                            <div className="text-sm text-muted">
                                                {formatDate(session.updated_at)}
                                            </div>
                                        </div>
                                        <button
                                            className="btn btn-small btn-danger"
                                            onClick={(e) => handleDelete(e, session.id)}
                                            title="Delete Session"
                                        >
                                            ✕
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )
            })}

            {sessions.length === 0 && (
                <div className="text-muted text-sm" style={{ textAlign: 'center', padding: 'var(--space-lg)' }}>
                    No chat sessions yet.<br />
                    Select a character to start.
                </div>
            )}
        </div>
    )
}
