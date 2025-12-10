import { useState, useEffect } from 'react'

export default function RegexEditor() {
    const [scripts, setScripts] = useState([])
    const [showForm, setShowForm] = useState(false)
    const [editingId, setEditingId] = useState(null)
    const [testInput, setTestInput] = useState('')
    const [testOutput, setTestOutput] = useState('')
    const [formData, setFormData] = useState({
        name: '',
        find_regex: '',
        replace_with: '',
        flags: 'g',
        // SillyTavern-compatible options
        run_on_user_input: false,
        run_on_ai_output: true,
        run_on_edit: false,
        only_format_display: true,
        only_format_prompt: false,
        min_depth: 0,
        max_depth: -1,
        // Agent stage scope
        run_on_director_output: false,
        run_on_writer_output: true,
        run_on_paint_director_output: false,
    })

    const fetchScripts = async () => {
        const res = await fetch('/api/regex')
        if (res.ok) setScripts(await res.json())
    }

    useEffect(() => { fetchScripts() }, [])

    const resetForm = () => {
        setFormData({
            name: '', find_regex: '', replace_with: '', flags: 'g',
            run_on_user_input: false, run_on_ai_output: true, run_on_edit: false,
            only_format_display: true, only_format_prompt: false,
            min_depth: 0, max_depth: -1,
            run_on_director_output: false, run_on_writer_output: true,
            run_on_paint_director_output: false,
        })
        setEditingId(null)
        setShowForm(false)
        setTestInput('')
        setTestOutput('')
    }

    const startEdit = (script) => {
        setFormData({
            name: script.name,
            find_regex: script.find_regex,
            replace_with: script.replace_with,
            flags: script.flags,
            run_on_user_input: script.run_on_user_input,
            run_on_ai_output: script.run_on_ai_output,
            run_on_edit: script.run_on_edit ?? false,
            only_format_display: script.only_format_display,
            only_format_prompt: script.only_format_prompt,
            min_depth: script.min_depth,
            max_depth: script.max_depth,
            run_on_director_output: script.run_on_director_output ?? false,
            run_on_writer_output: script.run_on_writer_output ?? true,
            run_on_paint_director_output: script.run_on_paint_director_output ?? false,
        })
        setEditingId(script.id)
        setShowForm(true)
    }

    const handleSubmit = async () => {
        if (!formData.name || !formData.find_regex) return

        const endpoint = editingId ? `/api/regex/${editingId}` : '/api/regex'
        const method = editingId ? 'PUT' : 'POST'

        const res = await fetch(endpoint, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData),
        })

        if (res.ok) {
            await fetchScripts()
            resetForm()
        } else {
            const err = await res.json()
            alert(err.detail || 'Failed to save')
        }
    }

    const handleDelete = async (e, scriptId) => {
        e.stopPropagation()
        await fetch(`/api/regex/${scriptId}`, { method: 'DELETE' })
        await fetchScripts()
    }

    const handleToggle = async (e, scriptId) => {
        e.stopPropagation()
        await fetch(`/api/regex/${scriptId}/toggle`, { method: 'PUT' })
        await fetchScripts()
    }

    const handleTest = async () => {
        const res = await fetch('/api/regex/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                find_regex: formData.find_regex,
                replace_with: formData.replace_with,
                flags: formData.flags,
                test_text: testInput,
            }),
        })
        const data = await res.json()
        setTestOutput(data.result || '')
    }

    const handleExport = async () => {
        try {
            const res = await fetch('/api/regex/export')
            const data = await res.json()
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = 'regex_scripts.json'
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
            await fetch('/api/regex/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })
            await fetchScripts()
        } catch (err) {
            console.error('Import failed:', err)
        }
        e.target.value = ''
    }

    return (
        <div>
            <div className="section-header">
                <span className="section-title">Regex Scripts</span>
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
                    <button className="btn btn-small" onClick={handleExport} title="Export All">
                        ↑ Export
                    </button>
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
                            {editingId ? 'Edit Script' : 'New Script'}
                        </div>

                        <div className="form-group">
                            <label className="form-label">Name</label>
                            <input
                                className="input"
                                placeholder="Remove asterisks"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Find Regex</label>
                            <input
                                className="input mono"
                                placeholder="\*([^*]+)\*"
                                value={formData.find_regex}
                                onChange={(e) => setFormData({ ...formData, find_regex: e.target.value })}
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Replace With</label>
                            <input
                                className="input mono"
                                placeholder="$1 or leave empty to remove"
                                value={formData.replace_with}
                                onChange={(e) => setFormData({ ...formData, replace_with: e.target.value })}
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Flags</label>
                            <input
                                className="input mono"
                                placeholder="gim"
                                value={formData.flags}
                                onChange={(e) => setFormData({ ...formData, flags: e.target.value })}
                            />
                            <div className="text-sm text-muted mt-sm">
                                g = global, i = ignore case, m = multiline, s = dotall, u = unicode
                            </div>
                        </div>

                        {/* Run On Section - SillyTavern compatible */}
                        <div className="form-group">
                            <label className="form-label">Run On</label>
                            <div style={{
                                background: 'var(--bg-primary)',
                                padding: 'var(--space-sm)',
                                borderRadius: 'var(--radius-sm)',
                            }}>
                                <div className="flex gap-md">
                                    <label className="flex items-center gap-sm" style={{ cursor: 'pointer' }}>
                                        <input
                                            type="checkbox"
                                            checked={formData.run_on_ai_output}
                                            onChange={(e) => setFormData({ ...formData, run_on_ai_output: e.target.checked })}
                                        />
                                        <span className="text-sm">AI Output</span>
                                    </label>
                                    <label className="flex items-center gap-sm" style={{ cursor: 'pointer' }}>
                                        <input
                                            type="checkbox"
                                            checked={formData.run_on_user_input}
                                            onChange={(e) => setFormData({ ...formData, run_on_user_input: e.target.checked })}
                                        />
                                        <span className="text-sm">User Input</span>
                                    </label>
                                    <label className="flex items-center gap-sm" style={{ cursor: 'pointer' }}>
                                        <input
                                            type="checkbox"
                                            checked={formData.run_on_edit}
                                            onChange={(e) => setFormData({ ...formData, run_on_edit: e.target.checked })}
                                        />
                                        <span className="text-sm">On Edit</span>
                                    </label>
                                </div>
                                <div className="text-sm text-muted mt-xs">
                                    Which messages to apply the regex to. "On Edit" runs when editing messages.
                                </div>
                            </div>
                        </div>

                        {/* Affects Section */}
                        <div className="form-group">
                            <label className="form-label">Affects</label>
                            <div style={{
                                background: 'var(--bg-primary)',
                                padding: 'var(--space-sm)',
                                borderRadius: 'var(--radius-sm)',
                            }}>
                                <div className="flex gap-md">
                                    <label className="flex items-center gap-sm" style={{ cursor: 'pointer' }}>
                                        <input
                                            type="checkbox"
                                            checked={formData.only_format_display}
                                            onChange={(e) => setFormData({ ...formData, only_format_display: e.target.checked })}
                                        />
                                        <span className="text-sm">Display</span>
                                    </label>
                                    <label className="flex items-center gap-sm" style={{ cursor: 'pointer' }}>
                                        <input
                                            type="checkbox"
                                            checked={formData.only_format_prompt}
                                            onChange={(e) => setFormData({ ...formData, only_format_prompt: e.target.checked })}
                                        />
                                        <span className="text-sm">Prompt</span>
                                    </label>
                                </div>
                                <div className="text-sm text-muted mt-xs">
                                    Display = what you see | Prompt = what goes to LLM
                                </div>
                            </div>
                        </div>

                        {/* Agent Stage Scope */}
                        <div className="form-group">
                            <label className="form-label">Agent Stage Scope</label>
                            <div style={{
                                background: 'var(--bg-primary)',
                                padding: 'var(--space-sm)',
                                borderRadius: 'var(--radius-sm)',
                            }}>
                                <div className="flex gap-md" style={{ flexWrap: 'wrap' }}>
                                    <label className="flex items-center gap-sm" style={{ cursor: 'pointer' }}>
                                        <input
                                            type="checkbox"
                                            checked={formData.run_on_director_output}
                                            onChange={(e) => setFormData({ ...formData, run_on_director_output: e.target.checked })}
                                        />
                                        <span className="text-sm">🎬 Director</span>
                                    </label>
                                    <label className="flex items-center gap-sm" style={{ cursor: 'pointer' }}>
                                        <input
                                            type="checkbox"
                                            checked={formData.run_on_writer_output}
                                            onChange={(e) => setFormData({ ...formData, run_on_writer_output: e.target.checked })}
                                        />
                                        <span className="text-sm">✍️ Writer</span>
                                    </label>
                                    <label className="flex items-center gap-sm" style={{ cursor: 'pointer' }}>
                                        <input
                                            type="checkbox"
                                            checked={formData.run_on_paint_director_output}
                                            onChange={(e) => setFormData({ ...formData, run_on_paint_director_output: e.target.checked })}
                                        />
                                        <span className="text-sm">🎨 Paint Director</span>
                                    </label>
                                </div>
                                <div className="text-sm text-muted mt-xs">
                                    Which agent outputs to apply regex before passing to next stage
                                </div>
                            </div>
                        </div>

                        {/* Depth Section */}
                        <div className="form-group">
                            <label className="form-label">Depth Constraints</label>
                            <div style={{
                                background: 'var(--bg-primary)',
                                padding: 'var(--space-sm)',
                                borderRadius: 'var(--radius-sm)',
                            }}>
                                <div className="flex gap-md items-center">
                                    <label className="flex items-center gap-sm">
                                        <span className="text-sm">Min:</span>
                                        <input
                                            type="number"
                                            className="input"
                                            style={{ width: 60 }}
                                            value={formData.min_depth}
                                            onChange={(e) => setFormData({ ...formData, min_depth: parseInt(e.target.value) || 0 })}
                                        />
                                    </label>
                                    <label className="flex items-center gap-sm">
                                        <span className="text-sm">Max:</span>
                                        <input
                                            type="number"
                                            className="input"
                                            style={{ width: 60 }}
                                            value={formData.max_depth}
                                            onChange={(e) => setFormData({ ...formData, max_depth: parseInt(e.target.value) || -1 })}
                                        />
                                    </label>
                                </div>
                                <div className="text-sm text-muted mt-xs">
                                    0 = most recent message, -1 = no limit
                                </div>
                            </div>
                        </div>

                        {/* Test Section */}
                        <div className="form-group">
                            <label className="form-label">Test Input</label>
                            <textarea
                                className="textarea"
                                rows={2}
                                placeholder="*bold text* for testing"
                                value={testInput}
                                onChange={(e) => setTestInput(e.target.value)}
                            />
                        </div>
                        <button className="btn btn-small mb-md" onClick={handleTest}>
                            Test Regex
                        </button>
                        {testOutput && (
                            <div className="form-group">
                                <label className="form-label">Test Output</label>
                                <div className="mono text-sm" style={{
                                    padding: 'var(--space-sm)',
                                    background: 'var(--bg-primary)',
                                    borderRadius: 'var(--radius-sm)',
                                    whiteSpace: 'pre-wrap'
                                }}>
                                    {testOutput}
                                </div>
                            </div>
                        )}

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
                {scripts.map(script => (
                    <div
                        key={script.id}
                        className={`list-item ${!script.enabled ? 'text-muted' : ''}`}
                        onClick={() => startEdit(script)}
                        style={{ opacity: script.enabled ? 1 : 0.5 }}
                    >
                        <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontWeight: 500 }}>{script.name}</div>
                            <div className="text-sm mono text-muted" style={{
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis'
                            }}>
                                /{script.find_regex}/ → {script.replace_with || '(empty)'}
                            </div>
                            <div className="text-sm text-muted" style={{ marginTop: 'var(--space-xs)' }}>
                                {script.run_on_ai_output && <span className="badge" style={{ marginRight: 4, padding: '1px 4px', fontSize: 10, background: 'var(--accent-primary)', color: 'white', borderRadius: 3 }}>AI</span>}
                                {script.run_on_user_input && <span className="badge" style={{ marginRight: 4, padding: '1px 4px', fontSize: 10, background: 'var(--accent-secondary)', color: 'white', borderRadius: 3 }}>User</span>}
                                {script.run_on_director_output && <span style={{ marginRight: 4, padding: '1px 4px', fontSize: 10, background: '#9333ea', color: 'white', borderRadius: 3 }}>🎬Dir</span>}
                                {script.run_on_writer_output && <span style={{ marginRight: 4, padding: '1px 4px', fontSize: 10, background: '#0891b2', color: 'white', borderRadius: 3 }}>✍️Wri</span>}
                                {script.run_on_paint_director_output && <span style={{ marginRight: 4, padding: '1px 4px', fontSize: 10, background: '#ea580c', color: 'white', borderRadius: 3 }}>🎨Pnt</span>}
                                {script.only_format_display && <span style={{ marginRight: 4, opacity: 0.7 }}>Display</span>}
                                {script.only_format_prompt && <span style={{ marginRight: 4, opacity: 0.7 }}>Prompt</span>}
                                {(script.min_depth > 0 || script.max_depth >= 0) && (
                                    <span style={{ opacity: 0.7 }}>Depth: {script.min_depth}-{script.max_depth === -1 ? '∞' : script.max_depth}</span>
                                )}
                            </div>
                        </div>
                        <div className="flex gap-sm">
                            <button
                                className="btn btn-small"
                                onClick={(e) => handleToggle(e, script.id)}
                                title={script.enabled ? 'Disable' : 'Enable'}
                            >
                                {script.enabled ? '✓' : '○'}
                            </button>
                            <button
                                className="btn btn-small btn-danger"
                                onClick={(e) => handleDelete(e, script.id)}
                                title="Delete"
                            >
                                ✕
                            </button>
                        </div>
                    </div>
                ))}

                {scripts.length === 0 && (
                    <div className="text-muted text-sm" style={{ textAlign: 'center', padding: 'var(--space-lg)' }}>
                        No regex scripts yet.<br />
                        Click + to create one.
                    </div>
                )}
            </div>
        </div>
    )
}
