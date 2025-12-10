import { useState, useEffect, useRef } from 'react'

export default function AgentLogViewer() {
    const [runs, setRuns] = useState([])
    const [loading, setLoading] = useState(true)
    const [expandedId, setExpandedId] = useState(null)
    const [selectedRun, setSelectedRun] = useState(null)
    const [totalCount, setTotalCount] = useState(0)

    const fetchRuns = async () => {
        setLoading(true)
        try {
            const [runsRes, countRes] = await Promise.all([
                fetch('/api/agent/logs?limit=100'),
                fetch('/api/agent/logs/count'),
            ])
            const runsData = await runsRes.json()
            const countData = await countRes.json()
            setRuns(runsData)
            setTotalCount(countData.count)
        } catch (err) {
            console.error('Failed to fetch agent logs:', err)
        }
        setLoading(false)
    }

    const fetchRunDetails = async (runId) => {
        try {
            const res = await fetch(`/api/agent/logs/${runId}`)
            const data = await res.json()
            setSelectedRun(data)
        } catch (err) {
            console.error('Failed to fetch run details:', err)
        }
    }

    useEffect(() => {
        fetchRuns()
    }, [])

    const handleClearLogs = async () => {
        if (!confirm('Clear all agent logs?')) return
        try {
            await fetch('/api/agent/logs', { method: 'DELETE' })
            setRuns([])
            setTotalCount(0)
            setSelectedRun(null)
        } catch (err) {
            console.error('Failed to clear logs:', err)
        }
    }

    const formatDuration = (ms) => {
        if (!ms) return '-'
        if (ms < 1000) return `${ms}ms`
        return `${(ms / 1000).toFixed(2)}s`
    }

    const formatTimestamp = (ts) => {
        if (!ts) return '-'
        const date = new Date(ts + 'Z')
        return date.toLocaleString()
    }

    const getStatusIcon = (status) => {
        switch (status) {
            case 'success': return '✓'
            case 'partial': return '⚠'
            case 'error': return '✗'
            case 'running': return '⏳'
            case 'skipped': return '⊘'
            default: return '?'
        }
    }

    const getStatusClass = (status) => {
        switch (status) {
            case 'success': return 'status-success'
            case 'partial': return 'status-warning'
            case 'error': return 'status-error'
            case 'running': return 'status-running'
            case 'skipped': return 'status-skipped'
            default: return ''
        }
    }

    const getStageName = (stage) => {
        switch (stage) {
            case 'director': return '🎬 Director'
            case 'writer': return '✍️ Writer'
            case 'paint_director': return '🎨 Paint Director'
            case 'painter': return '🖼️ Painter'
            case 'tts': return '🔊 TTS'
            default: return stage
        }
    }

    return (
        <div className="agent-log-viewer">
            <div className="section-header">
                <span className="section-title">Agent Runs ({totalCount})</span>
                <div className="flex gap-sm">
                    <button className="btn btn-small" onClick={fetchRuns}>
                        ↻ Refresh
                    </button>
                    <button className="btn btn-small btn-danger" onClick={handleClearLogs}>
                        Clear All
                    </button>
                </div>
            </div>

            {loading ? (
                <div className="empty-state">Loading agent logs...</div>
            ) : runs.length === 0 ? (
                <div className="empty-state">No agent runs yet</div>
            ) : (
                <div className="agent-log-layout">
                    {/* Run List */}
                    <div className="agent-run-list">
                        {runs.map(run => (
                            <div
                                key={run.id}
                                className={`agent-run-item ${expandedId === run.id ? 'expanded' : ''}`}
                                onClick={() => {
                                    setExpandedId(expandedId === run.id ? null : run.id)
                                    if (expandedId !== run.id) {
                                        fetchRunDetails(run.id)
                                    }
                                }}
                            >
                                <div className="run-header">
                                    <span className={`run-status ${getStatusClass(run.status)}`}>
                                        {getStatusIcon(run.status)}
                                    </span>
                                    <span className="run-time">{formatTimestamp(run.timestamp)}</span>
                                    <span className="run-duration">{formatDuration(run.total_duration_ms)}</span>
                                </div>

                                <div className="run-message">
                                    {run.user_message?.substring(0, 100)}
                                    {run.user_message?.length > 100 ? '...' : ''}
                                </div>

                                <div className="run-stages-mini">
                                    {run.stages?.map((stage, i) => (
                                        <span
                                            key={i}
                                            className={`stage-dot ${getStatusClass(stage.status)}`}
                                            title={`${getStageName(stage.stage)}: ${stage.status}`}
                                        />
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Run Details */}
                    {selectedRun && expandedId && (
                        <div className="agent-run-details">
                            <div className="detail-header">
                                <span className={`run-status large ${getStatusClass(selectedRun.status)}`}>
                                    {getStatusIcon(selectedRun.status)} {selectedRun.status}
                                </span>
                                <span className="detail-duration">
                                    Total: {formatDuration(selectedRun.total_duration_ms)}
                                </span>
                            </div>

                            <div className="detail-section">
                                <div className="detail-label">User Message</div>
                                <div className="detail-content">{selectedRun.user_message}</div>
                            </div>

                            <div className="detail-section">
                                <div className="detail-label">Stages</div>
                                <div className="stage-timeline">
                                    {selectedRun.stages?.map((stage, i) => {
                                        return (
                                            <div key={i} className={`stage-item ${getStatusClass(stage.status)}`}>
                                                <div className="stage-header">
                                                    <span className="stage-name">{getStageName(stage.stage)}</span>
                                                    <span className="stage-status">
                                                        {getStatusIcon(stage.status)}
                                                    </span>
                                                    <span className="stage-duration">
                                                        {formatDuration(stage.duration_ms)}
                                                    </span>
                                                </div>

                                                {/* Input Content (request message structure) */}
                                                {stage.input_content && (() => {
                                                    // Try to parse as JSON for structured display
                                                    try {
                                                        const parsed = JSON.parse(stage.input_content)
                                                        return (
                                                            <details className="stage-io" open>
                                                                <summary>📥 Request Structure</summary>
                                                                <div className="request-structure">
                                                                    {parsed.llm_config && (
                                                                        <div className="request-section">
                                                                            <div className="request-label">🔧 LLM Config</div>
                                                                            <div className="request-value">
                                                                                {parsed.llm_config.name} ({parsed.llm_config.model})
                                                                            </div>
                                                                        </div>
                                                                    )}
                                                                    {parsed.preset_name && (
                                                                        <div className="request-section">
                                                                            <div className="request-label">📋 Preset</div>
                                                                            <div className="request-value">{parsed.preset_name}</div>
                                                                        </div>
                                                                    )}
                                                                    {parsed.params && Object.keys(parsed.params).length > 0 && (
                                                                        <div className="request-section">
                                                                            <div className="request-label">⚙️ Parameters</div>
                                                                            <div className="request-value">
                                                                                {Object.entries(parsed.params).map(([k, v]) => (
                                                                                    <span key={k} className="param-tag">{k}: {v}</span>
                                                                                ))}
                                                                            </div>
                                                                        </div>
                                                                    )}
                                                                    {parsed.messages && parsed.messages.map((msg, idx) => (
                                                                        <details key={idx} className="message-detail">
                                                                            <summary>
                                                                                {msg.role === 'system' ? '🤖' : '👤'} {msg.role.toUpperCase()}
                                                                                <span className="content-preview">
                                                                                    {msg.content.slice(0, 100)}...
                                                                                </span>
                                                                            </summary>
                                                                            <pre className="message-content">{msg.content}</pre>
                                                                        </details>
                                                                    ))}
                                                                </div>
                                                            </details>
                                                        )
                                                    } catch (e) {
                                                        // Not JSON, show as plain text
                                                        return (
                                                            <details className="stage-io">
                                                                <summary>📥 Input (Request)</summary>
                                                                <pre>{stage.input_content}</pre>
                                                            </details>
                                                        )
                                                    }
                                                })()}

                                                {/* Output Content */}
                                                {stage.output_content && (
                                                    <details className="stage-io">
                                                        <summary>📤 Output (Response)</summary>
                                                        <pre>{stage.output_content}</pre>
                                                    </details>
                                                )}

                                                {stage.error_message && (
                                                    <div className="stage-error">
                                                        Error: {stage.error_message}
                                                    </div>
                                                )}
                                            </div>
                                        )
                                    })}
                                </div>
                            </div>

                            {selectedRun.image_url && (
                                <div className="detail-section">
                                    <div className="detail-label">Generated Image</div>
                                    <img src={selectedRun.image_url} alt="Generated" className="detail-image" />
                                    <div className="detail-caption">{selectedRun.image_prompt}</div>
                                </div>
                            )}

                            {selectedRun.error_message && (
                                <div className="detail-section detail-error">
                                    <div className="detail-label">Error</div>
                                    <div className="detail-content">{selectedRun.error_message}</div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            <style>{`
                .agent-log-viewer {
                    height: 100%;
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                }
                
                .agent-log-layout {
                    display: flex;
                    flex-direction: column;
                    gap: 1rem;
                    flex: 1;
                    overflow: hidden;
                }
                
                .agent-run-list {
                    max-height: 200px;
                    overflow-y: auto;
                    display: flex;
                    flex-direction: column;
                    gap: 0.5rem;
                    flex-shrink: 0;
                }
                
                .agent-run-item {
                    background: var(--bg-secondary);
                    border-radius: 8px;
                    padding: 0.75rem;
                    cursor: pointer;
                    transition: all 0.2s;
                    border: 2px solid transparent;
                }
                
                .agent-run-item:hover {
                    background: var(--bg-tertiary);
                }
                
                .agent-run-item.expanded {
                    border-color: var(--primary);
                }
                
                .run-header {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    margin-bottom: 0.5rem;
                }
                
                .run-status {
                    font-weight: bold;
                }
                
                .run-status.large {
                    font-size: 1.1rem;
                }
                
                .status-success { color: #22c55e; }
                .status-warning { color: #f59e0b; }
                .status-error { color: #ef4444; }
                .status-running { color: #3b82f6; }
                .status-skipped { color: #6b7280; }
                
                .run-time {
                    font-size: 0.8rem;
                    color: var(--text-secondary);
                    flex: 1;
                }
                
                .run-duration {
                    font-size: 0.8rem;
                    color: var(--text-secondary);
                }
                
                .run-message {
                    font-size: 0.85rem;
                    color: var(--text-primary);
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                
                .run-stages-mini {
                    display: flex;
                    gap: 4px;
                    margin-top: 0.5rem;
                }
                
                .stage-dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: currentColor;
                }
                
                .agent-run-details {
                    flex: 1;
                    overflow-y: auto;
                    background: var(--bg-secondary);
                    border-radius: 8px;
                    padding: 1rem;
                }
                
                .detail-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 1rem;
                    padding-bottom: 0.5rem;
                    border-bottom: 1px solid var(--border);
                }
                
                .detail-section {
                    margin-bottom: 1rem;
                }
                
                .detail-label {
                    font-size: 0.8rem;
                    color: var(--text-secondary);
                    margin-bottom: 0.25rem;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }
                
                .detail-content {
                    background: var(--bg-tertiary);
                    padding: 0.75rem;
                    border-radius: 6px;
                    white-space: pre-wrap;
                    font-family: inherit;
                }
                
                .stage-timeline {
                    display: flex;
                    flex-direction: column;
                    gap: 0.5rem;
                }
                
                .stage-item {
                    background: var(--bg-tertiary);
                    border-radius: 6px;
                    padding: 0.75rem;
                    border-left: 3px solid currentColor;
                }
                
                .stage-header {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                }
                
                .stage-name {
                    font-weight: 500;
                    flex: 1;
                }
                
                .stage-io {
                    margin-top: 0.5rem;
                }
                
                .stage-io summary {
                    cursor: pointer;
                    font-size: 0.85rem;
                    color: var(--text-secondary);
                }
                
                .stage-io pre {
                    margin: 0.5rem 0 0;
                    padding: 0.75rem;
                    background: var(--bg-primary);
                    border-radius: 4px;
                    font-size: 0.8rem;
                    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    white-space: pre-wrap;
                    word-break: break-word;
                    line-height: 1.5;
                    max-height: 400px;
                    overflow-y: auto;
                    border: 1px solid var(--border-subtle);
                }
                
                .stage-error {
                    margin-top: 0.5rem;
                    color: #ef4444;
                    font-size: 0.85rem;
                }
                
                .detail-image {
                    max-width: 100%;
                    border-radius: 6px;
                }
                
                .detail-caption {
                    font-size: 0.85rem;
                    color: var(--text-secondary);
                    margin-top: 0.5rem;
                }
                
                .detail-error {
                    background: rgba(239, 68, 68, 0.1);
                    border-radius: 6px;
                    padding: 0.75rem;
                }
                
                .detail-error .detail-content {
                    color: #ef4444;
                }
                
                /* Request Structure Styles */
                .request-structure {
                    display: flex;
                    flex-direction: column;
                    gap: 0.75rem;
                }
                
                .request-section {
                    display: flex;
                    flex-direction: column;
                    gap: 0.25rem;
                }
                
                .request-label {
                    font-size: 0.75rem;
                    font-weight: 600;
                    color: var(--text-secondary);
                }
                
                .request-value {
                    font-size: 0.85rem;
                    color: var(--text-primary);
                    display: flex;
                    flex-wrap: wrap;
                    gap: 0.5rem;
                }
                
                .param-tag {
                    background: var(--bg-tertiary);
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 0.8rem;
                    font-family: monospace;
                }
                
                .message-detail {
                    margin-top: 0.5rem;
                    border: 1px solid var(--border-subtle);
                    border-radius: 6px;
                    overflow: hidden;
                }
                
                .message-detail summary {
                    padding: 0.5rem 0.75rem;
                    background: var(--bg-tertiary);
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    font-size: 0.85rem;
                }
                
                .content-preview {
                    font-size: 0.75rem;
                    color: var(--text-secondary);
                    margin-left: auto;
                    max-width: 300px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                }
                
                .message-content {
                    padding: 0.75rem;
                    margin: 0;
                    background: var(--bg-secondary);
                    font-size: 0.8rem;
                    white-space: pre-wrap;
                    word-break: break-word;
                    max-height: 400px;
                    overflow-y: auto;
                }
            `}</style>
        </div>
    )
}
