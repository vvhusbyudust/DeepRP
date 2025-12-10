import { useState, useEffect } from 'react'

export default function LogViewer() {
    const [logs, setLogs] = useState([])
    const [loading, setLoading] = useState(true)
    const [expandedId, setExpandedId] = useState(null)
    const [totalCount, setTotalCount] = useState(0)

    const fetchLogs = async () => {
        setLoading(true)
        try {
            const [logsRes, countRes] = await Promise.all([
                fetch('/api/logs?limit=100'),
                fetch('/api/logs/count'),
            ])
            const logsData = await logsRes.json()
            const countData = await countRes.json()
            setLogs(logsData)
            setTotalCount(countData.count)
        } catch (err) {
            console.error('Failed to fetch logs:', err)
        }
        setLoading(false)
    }

    useEffect(() => {
        fetchLogs()
    }, [])

    const handleClearLogs = async () => {
        try {
            await fetch('/api/logs', { method: 'DELETE' })
            setLogs([])
            setTotalCount(0)
        } catch (err) {
            console.error('Failed to clear logs:', err)
        }
    }

    const formatDuration = (ms) => {
        if (ms < 1000) return `${ms}ms`
        return `${(ms / 1000).toFixed(2)}s`
    }

    const formatTimestamp = (ts) => {
        const date = new Date(ts + 'Z')
        return date.toLocaleString()
    }

    const parseJson = (str) => {
        try {
            return JSON.parse(str)
        } catch {
            return str
        }
    }

    return (
        <div>
            <div className="section-header">
                <span className="section-title">Request Logs ({totalCount})</span>
                <div className="flex gap-sm">
                    <button className="btn btn-small" onClick={fetchLogs}>
                        ↻ Refresh
                    </button>
                    <button className="btn btn-small btn-danger" onClick={handleClearLogs}>
                        Clear All
                    </button>
                </div>
            </div>

            {loading ? (
                <div className="empty-state">Loading logs...</div>
            ) : logs.length === 0 ? (
                <div className="empty-state">No request logs yet</div>
            ) : (
                <div className="log-list">
                    {logs.map(log => (
                        <div key={log.id} className="log-item">
                            <div
                                className="log-header"
                                onClick={() => setExpandedId(expandedId === log.id ? null : log.id)}
                            >
                                <div className="log-meta">
                                    <span className={`log-status ${log.status}`}>
                                        {log.status === 'success' ? '✓' : '✗'}
                                    </span>
                                    <span className="log-type">{log.request_type}</span>
                                    <span className="log-model">{log.model}</span>
                                </div>
                                <div className="log-stats">
                                    <span className="log-duration">{formatDuration(log.duration_ms)}</span>
                                    {log.tokens_in > 0 && (
                                        <span className="log-tokens">
                                            {log.tokens_in}→{log.tokens_out} tokens
                                        </span>
                                    )}
                                    <span className="log-time">{formatTimestamp(log.timestamp)}</span>
                                </div>
                            </div>

                            {log.prompt_preview && (
                                <div className="log-preview">{log.prompt_preview}</div>
                            )}

                            {expandedId === log.id && (
                                <div className="log-details">
                                    {log.error_message && (
                                        <div className="log-error">
                                            <strong>Error:</strong> {log.error_message}
                                        </div>
                                    )}

                                    <div className="log-section">
                                        <div className="log-section-title">Request</div>
                                        <pre className="log-json">
                                            {JSON.stringify(parseJson(log.full_request), null, 2)}
                                        </pre>
                                    </div>

                                    {log.full_response && (
                                        <div className="log-section">
                                            <div className="log-section-title">Response</div>
                                            <pre className="log-json">
                                                {JSON.stringify(parseJson(log.full_response), null, 2)}
                                            </pre>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
