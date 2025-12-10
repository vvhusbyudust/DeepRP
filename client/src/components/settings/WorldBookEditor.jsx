import { useState } from 'react'
import { useAppStore } from '../../stores/appStore'

export default function WorldBookEditor() {
    // activeWorldbook = for editing, activeWorldbooks = for chat selection
    const { worldbooks, activeWorldbooks, toggleActiveWorldbook, initialize } = useAppStore()
    const [activeWorldbook, setActiveWorldbook] = useState(null)
    const [showForm, setShowForm] = useState(false)
    const [editingId, setEditingId] = useState(null)
    const [editingEntryId, setEditingEntryId] = useState(null)
    const [formData, setFormData] = useState({ name: '', description: '' })
    const [entryFormData, setEntryFormData] = useState({
        key: [],
        secondary_key: [],
        content: '',
        enabled: true,
        constant: false,
        scan_depth: 5,
        order: 100,
        position: 'before_char',  // before_char, after_char, at_depth
        depth: 0,  // For at_depth position: N messages from bottom
        role: 'system',  // system, user, assistant
        recursive: false,
        inclusion_group: '',
        // SillyTavern compatibility fields
        case_sensitive: false,
        match_whole_words: false,
        probability: 100,
        use_probability: false,
        selective_logic: 'and',  // and, or, not
        comment: '',
    })

    const resetForm = () => {
        setFormData({ name: '', description: '' })
        setEditingId(null)
        setShowForm(false)
    }

    const resetEntryForm = () => {
        setEntryFormData({
            key: [], secondary_key: [], content: '', enabled: true, constant: false,
            scan_depth: 5, order: 100, position: 'before_char', depth: 0, role: 'system',
            recursive: false, inclusion_group: '',
            case_sensitive: false, match_whole_words: false, probability: 100,
            use_probability: false, selective_logic: 'and', comment: '',
        })
        setEditingEntryId(null)
    }

    const startEdit = (wb) => {
        setFormData({ name: wb.name, description: wb.description || '' })
        setEditingId(wb.id)
        setShowForm(true)
    }

    const startEditEntry = (entry) => {
        setEntryFormData({
            key: entry.key || [],
            secondary_key: entry.secondary_key || [],
            content: entry.content || '',
            enabled: entry.enabled !== false,
            constant: entry.constant || false,
            scan_depth: entry.scan_depth || 5,
            order: entry.order || 100,
            position: entry.position || 'before_char',
            depth: entry.depth || 0,
            role: entry.role || 'system',
            recursive: entry.recursive || false,
            inclusion_group: entry.inclusion_group || '',
            // SillyTavern compatibility fields
            case_sensitive: entry.case_sensitive || false,
            match_whole_words: entry.match_whole_words || false,
            probability: entry.probability ?? 100,
            use_probability: entry.use_probability || false,
            selective_logic: entry.selective_logic || 'and',
            comment: entry.comment || '',
        })
        setEditingEntryId(entry.id)
    }

    const handleSubmit = async () => {
        if (!formData.name) return

        try {
            const endpoint = editingId ? `/api/worldbooks/${editingId}` : '/api/worldbooks'
            const method = editingId ? 'PUT' : 'POST'

            const res = await fetch(endpoint, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData),
            })

            if (res.ok) {
                await initialize()
                resetForm()
            }
        } catch (err) {
            console.error(err)
        }
    }

    const handleDelete = async (e, wbId) => {
        e.stopPropagation()

        try {
            await fetch(`/api/worldbooks/${wbId}`, { method: 'DELETE' })
            await initialize()
            if (activeWorldbook?.id === wbId) {
                setActiveWorldbook(null)
            }
        } catch (err) {
            console.error(err)
        }
    }

    const handleAddEntry = async () => {
        if (!activeWorldbook || !entryFormData.content) return

        try {
            const res = await fetch(`/api/worldbooks/${activeWorldbook.id}/entries`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(entryFormData),
            })

            if (res.ok) {
                await initialize()
                resetEntryForm()
            }
        } catch (err) {
            console.error(err)
        }
    }

    const handleUpdateEntry = async () => {
        if (!activeWorldbook || !editingEntryId) return

        try {
            const res = await fetch(`/api/worldbooks/${activeWorldbook.id}/entries/${editingEntryId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(entryFormData),
            })

            if (res.ok) {
                await initialize()
                resetEntryForm()
            }
        } catch (err) {
            console.error(err)
        }
    }

    const handleDeleteEntry = async (entryId) => {
        if (!activeWorldbook) return

        try {
            await fetch(`/api/worldbooks/${activeWorldbook.id}/entries/${entryId}`, { method: 'DELETE' })
            await initialize()
        } catch (err) {
            console.error(err)
        }
    }

    const handleExport = async (wbId) => {
        try {
            const res = await fetch(`/api/worldbooks/${wbId}/export`)
            const data = await res.json()
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `${data.name || 'worldbook'}.json`
            a.click()
            URL.revokeObjectURL(url)
        } catch (err) {
            console.error('Export failed:', err)
        }
    }

    const handleImport = async (e) => {
        const file = e.target.files?.[0]
        if (!file) return

        try {
            const text = await file.text()
            const data = JSON.parse(text)
            await fetch('/api/worldbooks/import-new', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })
            await initialize()
        } catch (err) {
            console.error('Import failed:', err)
        }
        e.target.value = ''  // Reset input
    }

    return (
        <div>
            <div className="section-header">
                <span className="section-title">World Books</span>
                <div className="flex gap-sm">
                    <label className="btn btn-small" style={{ cursor: 'pointer' }}>
                        ↓ Import
                        <input
                            type="file"
                            accept=".json"
                            onChange={handleImport}
                            style={{ display: 'none' }}
                        />
                    </label>
                    <button className="btn btn-small" onClick={() => {
                        if (showForm) resetForm()
                        else setShowForm(true)
                    }}>
                        {showForm ? '✕' : '+'}
                    </button>
                </div>
            </div>

            {showForm && (
                <div className="card mb-md">
                    <div className="card-body">
                        <div className="text-sm text-muted mb-md">
                            {editingId ? 'Edit World Book' : 'New World Book'}
                        </div>

                        <div className="form-group">
                            <label className="form-label">Name</label>
                            <input
                                className="input"
                                placeholder="Fantasy World"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Description</label>
                            <textarea
                                className="textarea"
                                placeholder="A brief description..."
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            />
                        </div>

                        <div className="flex gap-sm">
                            <button className="btn btn-primary" onClick={handleSubmit}>
                                {editingId ? 'Update' : 'Create'}
                            </button>
                            <button className="btn" onClick={resetForm}>Cancel</button>
                        </div>
                    </div>
                </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
                {worldbooks.map(wb => (
                    <div
                        key={wb.id}
                        className={`list-item ${activeWorldbook?.id === wb.id ? 'active' : ''}`}
                        onClick={() => setActiveWorldbook(wb)}
                    >
                        {/* Checkbox for activating worldbook in chat */}
                        <input
                            type="checkbox"
                            checked={activeWorldbooks?.some(awb => awb.id === wb.id) || false}
                            onChange={(e) => {
                                e.stopPropagation()
                                toggleActiveWorldbook(wb)
                            }}
                            onClick={(e) => e.stopPropagation()}
                            title="Use in chat"
                            style={{ marginRight: 'var(--space-sm)' }}
                        />
                        <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: 500 }}>{wb.name}</div>
                            <div className="text-sm text-muted">
                                {wb.entries?.length || 0} entries
                            </div>
                        </div>

                        <div className="flex gap-sm">
                            <button
                                className="btn btn-small"
                                onClick={(e) => {
                                    e.stopPropagation()
                                    startEdit(wb)
                                }}
                                title="Edit"
                            >
                                ✎
                            </button>
                            <button
                                className="btn btn-small"
                                onClick={(e) => {
                                    e.stopPropagation()
                                    handleExport(wb.id)
                                }}
                                title="Export SillyTavern"
                            >
                                ↑
                            </button>
                            <button
                                className="btn btn-small btn-danger"
                                onClick={(e) => handleDelete(e, wb.id)}
                                title="Delete"
                            >
                                ✕
                            </button>
                        </div>
                    </div>
                ))}

                {worldbooks.length === 0 && (
                    <div className="text-muted text-sm" style={{ textAlign: 'center', padding: 'var(--space-lg)' }}>
                        No world books yet.
                    </div>
                )}
            </div>

            {activeWorldbook && (
                <div className="card mt-md">
                    <div className="card-body">
                        <div className="section-header" style={{ marginBottom: 'var(--space-md)' }}>
                            <span className="text-sm text-muted">{activeWorldbook.name} Entries</span>
                            <button
                                className="btn btn-small"
                                onClick={() => {
                                    resetEntryForm()
                                    setEditingEntryId('new')
                                }}
                            >
                                + Entry
                            </button>
                        </div>

                        {editingEntryId && (
                            <div style={{
                                background: 'var(--bg-primary)',
                                padding: 'var(--space-md)',
                                borderRadius: 'var(--radius-md)',
                                marginBottom: 'var(--space-md)'
                            }}>
                                <div className="form-group">
                                    <label className="form-label">Keywords (comma-separated)</label>
                                    <input
                                        className="input"
                                        value={entryFormData.key.join(', ')}
                                        onChange={(e) => setEntryFormData({
                                            ...entryFormData,
                                            key: e.target.value.split(',').map(k => k.trim()).filter(Boolean)
                                        })}
                                        placeholder="dragon, wyrm"
                                    />
                                </div>

                                <div className="form-group">
                                    <label className="form-label">Content</label>
                                    <textarea
                                        className="textarea"
                                        rows={3}
                                        value={entryFormData.content}
                                        onChange={(e) => setEntryFormData({ ...entryFormData, content: e.target.value })}
                                        placeholder="Dragons are ancient creatures..."
                                    />
                                </div>

                                <div className="form-group">
                                    <label className="form-label">Secondary Keywords (AND logic, comma-separated)</label>
                                    <input
                                        className="input"
                                        value={entryFormData.secondary_key.join(', ')}
                                        onChange={(e) => setEntryFormData({
                                            ...entryFormData,
                                            secondary_key: e.target.value.split(',').map(k => k.trim()).filter(Boolean)
                                        })}
                                        placeholder="all these must match"
                                    />
                                </div>

                                <div className="flex gap-md mb-md flex-wrap">
                                    <label className="flex items-center gap-sm" style={{ fontSize: 12 }}>
                                        <input
                                            type="checkbox"
                                            checked={entryFormData.enabled}
                                            onChange={(e) => setEntryFormData({ ...entryFormData, enabled: e.target.checked })}
                                        />
                                        Enabled
                                    </label>
                                    <label className="flex items-center gap-sm" style={{ fontSize: 12 }}>
                                        <input
                                            type="checkbox"
                                            checked={entryFormData.constant}
                                            onChange={(e) => setEntryFormData({ ...entryFormData, constant: e.target.checked })}
                                        />
                                        Always Active
                                    </label>
                                    <label className="flex items-center gap-sm" style={{ fontSize: 12 }}>
                                        <input
                                            type="checkbox"
                                            checked={entryFormData.recursive}
                                            onChange={(e) => setEntryFormData({ ...entryFormData, recursive: e.target.checked })}
                                        />
                                        Recursive
                                    </label>
                                    <label className="flex items-center gap-sm" style={{ fontSize: 12 }}>
                                        <input
                                            type="checkbox"
                                            checked={entryFormData.case_sensitive}
                                            onChange={(e) => setEntryFormData({ ...entryFormData, case_sensitive: e.target.checked })}
                                        />
                                        Case Sensitive
                                    </label>
                                    <label className="flex items-center gap-sm" style={{ fontSize: 12 }}>
                                        <input
                                            type="checkbox"
                                            checked={entryFormData.match_whole_words}
                                            onChange={(e) => setEntryFormData({ ...entryFormData, match_whole_words: e.target.checked })}
                                        />
                                        Match Whole Words
                                    </label>
                                </div>

                                {/* Selective Logic for secondary keys */}
                                <div className="form-group">
                                    <label className="form-label">Secondary Key Logic</label>
                                    <select
                                        className="select"
                                        value={entryFormData.selective_logic}
                                        onChange={(e) => setEntryFormData({ ...entryFormData, selective_logic: e.target.value })}
                                    >
                                        <option value="and">AND (all secondary keys must match)</option>
                                        <option value="or">OR (any secondary key can match)</option>
                                        <option value="not">NOT (none of secondary keys can match)</option>
                                    </select>
                                    <div className="text-xs text-muted" style={{ marginTop: 4 }}>
                                        Controls how secondary keywords are evaluated against the chat.
                                    </div>
                                </div>

                                {/* Probability settings */}
                                <div className="flex gap-md items-end">
                                    <label className="flex items-center gap-sm" style={{ fontSize: 12 }}>
                                        <input
                                            type="checkbox"
                                            checked={entryFormData.use_probability}
                                            onChange={(e) => setEntryFormData({ ...entryFormData, use_probability: e.target.checked })}
                                        />
                                        Use Probability
                                    </label>
                                    {entryFormData.use_probability && (
                                        <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
                                            <label className="form-label">Trigger Chance: {entryFormData.probability}%</label>
                                            <input
                                                type="range"
                                                className="slider"
                                                min="0"
                                                max="100"
                                                value={entryFormData.probability}
                                                onChange={(e) => setEntryFormData({ ...entryFormData, probability: parseInt(e.target.value) })}
                                            />
                                        </div>
                                    )}
                                </div>

                                <div className="form-group">
                                    <label className="form-label">Inclusion Group (mutual exclusivity)</label>
                                    <input
                                        className="input"
                                        value={entryFormData.inclusion_group}
                                        onChange={(e) => setEntryFormData({ ...entryFormData, inclusion_group: e.target.value })}
                                        placeholder="e.g. location, character_mood"
                                    />
                                </div>

                                <div className="form-group">
                                    <label className="form-label">Comment / Note (not sent to AI)</label>
                                    <input
                                        className="input"
                                        value={entryFormData.comment}
                                        onChange={(e) => setEntryFormData({ ...entryFormData, comment: e.target.value })}
                                        placeholder="Internal note about this entry"
                                    />
                                </div>

                                <div className="form-group">
                                    <label className="form-label">Scan Depth: {entryFormData.scan_depth}</label>
                                    <input
                                        type="range"
                                        className="slider"
                                        min="0"
                                        max="10"
                                        value={entryFormData.scan_depth}
                                        onChange={(e) => setEntryFormData({ ...entryFormData, scan_depth: parseInt(e.target.value) })}
                                    />
                                </div>

                                <div className="form-group">
                                    <label className="form-label">Order / Priority (higher = closer to AI response)</label>
                                    <input
                                        type="number"
                                        className="input"
                                        value={entryFormData.order}
                                        onChange={(e) => setEntryFormData({ ...entryFormData, order: parseInt(e.target.value) || 0 })}
                                        placeholder="100"
                                    />
                                    <div className="text-xs text-muted" style={{ marginTop: 4 }}>
                                        SillyTavern calls this "Insertion Order". 0 = top of context, higher = closer to bottom/AI reply.
                                    </div>
                                </div>

                                <div className="form-group">
                                    <label className="form-label">Position</label>
                                    <select
                                        className="select"
                                        value={entryFormData.position}
                                        onChange={(e) => setEntryFormData({ ...entryFormData, position: e.target.value })}
                                    >
                                        <option value="before_char">Before Character</option>
                                        <option value="after_char">After Character</option>
                                        <option value="at_depth">@ Depth (in chat history)</option>
                                    </select>
                                </div>

                                {entryFormData.position === 'at_depth' && (
                                    <div className="flex gap-md">
                                        <div className="form-group" style={{ flex: 1 }}>
                                            <label className="form-label">Depth (from bottom): {entryFormData.depth}</label>
                                            <input
                                                type="range"
                                                className="slider"
                                                min="0"
                                                max="20"
                                                value={entryFormData.depth}
                                                onChange={(e) => setEntryFormData({ ...entryFormData, depth: parseInt(e.target.value) })}
                                            />
                                        </div>
                                        <div className="form-group" style={{ flex: 1 }}>
                                            <label className="form-label">Role</label>
                                            <select
                                                className="select"
                                                value={entryFormData.role}
                                                onChange={(e) => setEntryFormData({ ...entryFormData, role: e.target.value })}
                                            >
                                                <option value="system">System</option>
                                                <option value="user">User</option>
                                                <option value="assistant">Assistant</option>
                                            </select>
                                        </div>
                                    </div>
                                )}

                                <div className="flex gap-sm">
                                    <button
                                        className="btn btn-primary btn-small"
                                        onClick={editingEntryId === 'new' ? handleAddEntry : handleUpdateEntry}
                                    >
                                        {editingEntryId === 'new' ? 'Add' : 'Update'}
                                    </button>
                                    <button className="btn btn-small" onClick={resetEntryForm}>
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        )}

                        {activeWorldbook.entries?.map((entry, i) => (
                            <div key={entry.id || i} style={{
                                padding: 'var(--space-sm)',
                                background: 'var(--bg-primary)',
                                borderRadius: 'var(--radius-sm)',
                                marginBottom: 'var(--space-xs)',
                                opacity: entry.enabled === false ? 0.5 : 1,
                            }}>
                                <div className="flex items-center justify-between">
                                    <div className="text-sm" style={{ fontWeight: 500 }}>
                                        <span style={{ color: 'var(--accent)', marginRight: 6, fontFamily: 'monospace', fontSize: 11 }}>
                                            #{entry.order || 100}
                                        </span>
                                        {entry.key?.join(', ') || 'No keywords'}
                                        {entry.constant && <span className="text-accent"> (const)</span>}
                                        {entry.recursive && <span style={{ color: 'var(--accent-secondary)' }}> (⟳)</span>}
                                        {entry.inclusion_group && <span className="text-muted"> [{entry.inclusion_group}]</span>}
                                    </div>
                                    <div className="flex gap-sm">
                                        <button
                                            className="btn btn-small"
                                            onClick={() => startEditEntry(entry)}
                                            title="Edit"
                                        >
                                            ✎
                                        </button>
                                        <button
                                            className="btn btn-small btn-danger"
                                            onClick={() => handleDeleteEntry(entry.id)}
                                            title="Delete"
                                        >
                                            ✕
                                        </button>
                                    </div>
                                </div>
                                <div className="text-sm text-muted" style={{
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap'
                                }}>
                                    {entry.content?.slice(0, 80)}...
                                </div>
                                <div className="text-xs" style={{ marginTop: 4, color: 'var(--text-tertiary)' }}>
                                    {entry.position === 'at_depth'
                                        ? `@ Depth ${entry.depth || 0} (${entry.role || 'system'})`
                                        : entry.position === 'after_char' ? 'After Char' : 'Before Char'
                                    }
                                    {entry.scan_depth !== undefined && entry.scan_depth !== 5 && ` | Scan: ${entry.scan_depth}`}
                                </div>
                            </div>
                        ))}

                        {(!activeWorldbook.entries || activeWorldbook.entries.length === 0) && !editingEntryId && (
                            <div className="text-sm text-muted" style={{ textAlign: 'center', padding: 'var(--space-md)' }}>
                                No entries. Click "+ Entry" to add one.
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
