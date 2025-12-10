import { useState, useRef } from 'react'
import { useAppStore } from '../../stores/appStore'

export default function CharacterEditor() {
    const { characters, activeCharacter, setActiveCharacter, initialize } = useAppStore()
    const fileInputRef = useRef(null)
    const [importing, setImporting] = useState(false)
    const [showForm, setShowForm] = useState(false)
    const [editingId, setEditingId] = useState(null)
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        personality: '',
        scenario: '',
        first_mes: '',
        mes_example: '',
        system_prompt: '',
        alternate_greetings: [],
        tags: [],
    })

    const resetForm = () => {
        setFormData({
            name: '', description: '', personality: '', scenario: '',
            first_mes: '', mes_example: '', system_prompt: '',
            alternate_greetings: [], tags: [],
        })
        setEditingId(null)
        setShowForm(false)
    }

    const startEdit = (char) => {
        setFormData({
            name: char.data.name,
            description: char.data.description || '',
            personality: char.data.personality || '',
            scenario: char.data.scenario || '',
            first_mes: char.data.first_mes || '',
            mes_example: char.data.mes_example || '',
            system_prompt: char.data.system_prompt || '',
            alternate_greetings: char.data.alternate_greetings || [],
            tags: char.data.tags || [],
        })
        setEditingId(char.id)
        setShowForm(true)
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!formData.name) return

        try {
            const endpoint = editingId
                ? `/api/characters/${editingId}`
                : '/api/characters'
            const method = editingId ? 'PUT' : 'POST'

            const res = await fetch(endpoint, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData),
            })

            if (res.ok) {
                await initialize()
                resetForm()
            } else {
                throw new Error('Failed to save')
            }
        } catch (err) {
            console.error(err)
            alert('Failed to save character')
        }
    }

    const handleDelete = async (e, charId) => {
        e.stopPropagation()

        try {
            await fetch(`/api/characters/${charId}`, { method: 'DELETE' })
            await initialize()
            if (activeCharacter?.id === charId) {
                setActiveCharacter(null)
            }
        } catch (err) {
            console.error(err)
        }
    }

    const handleImport = async (e) => {
        const file = e.target.files?.[0]
        if (!file) return

        setImporting(true)
        try {
            const formData = new FormData()
            formData.append('file', file)

            const res = await fetch('/api/characters/import', {
                method: 'POST',
                body: formData,
            })

            if (res.ok) {
                await initialize()
            }
        } catch (err) {
            console.error('Import failed:', err)
        }
        setImporting(false)
        e.target.value = ''
    }

    const handleExport = async (e, charId, format) => {
        e.stopPropagation()
        window.open(`/api/characters/${charId}/export?format=${format}`, '_blank')
    }

    return (
        <div>
            <div className="section-header">
                <span className="section-title">Characters</span>
                <div className="flex gap-sm">
                    <button
                        className="btn btn-small"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={importing}
                    >
                        {importing ? '...' : '📥'}
                    </button>
                    <button
                        className="btn btn-small"
                        onClick={() => {
                            if (showForm) resetForm()
                            else setShowForm(true)
                        }}
                    >
                        {showForm ? '✕' : '+'}
                    </button>
                </div>
            </div>

            <input
                ref={fileInputRef}
                type="file"
                accept=".png,.json"
                style={{ display: 'none' }}
                onChange={handleImport}
            />

            {showForm && (
                <form onSubmit={handleSubmit} className="card mb-md">
                    <div className="card-body">
                        <div className="text-sm text-muted mb-md">
                            {editingId ? 'Edit Character' : 'New Character'}
                        </div>

                        <div className="form-group">
                            <label className="form-label">Name *</label>
                            <input
                                className="input"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                required
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Description</label>
                            <textarea
                                className="textarea"
                                rows={3}
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                placeholder="Character description..."
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Personality</label>
                            <textarea
                                className="textarea"
                                rows={2}
                                value={formData.personality}
                                onChange={(e) => setFormData({ ...formData, personality: e.target.value })}
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">First Message</label>
                            <textarea
                                className="textarea"
                                rows={3}
                                value={formData.first_mes}
                                onChange={(e) => setFormData({ ...formData, first_mes: e.target.value })}
                                placeholder="*{{char}} waves* Hello there!"
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Scenario</label>
                            <textarea
                                className="textarea"
                                rows={2}
                                value={formData.scenario}
                                onChange={(e) => setFormData({ ...formData, scenario: e.target.value })}
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">System Prompt</label>
                            <textarea
                                className="textarea"
                                rows={2}
                                value={formData.system_prompt}
                                onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Tags (comma-separated)</label>
                            <input
                                className="input"
                                value={formData.tags.join(', ')}
                                onChange={(e) => setFormData({
                                    ...formData,
                                    tags: e.target.value.split(',').map(t => t.trim()).filter(Boolean)
                                })}
                                placeholder="fantasy, adventure"
                            />
                        </div>

                        <div className="flex gap-sm">
                            <button className="btn btn-primary" type="submit">
                                {editingId ? 'Update' : 'Create'}
                            </button>
                            <button type="button" className="btn" onClick={resetForm}>
                                Cancel
                            </button>
                        </div>
                    </div>
                </form>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
                {characters.map(char => (
                    <div
                        key={char.id}
                        className={`list-item ${activeCharacter?.id === char.id ? 'active' : ''}`}
                        onClick={() => setActiveCharacter(char)}
                    >
                        {char.avatar_url ? (
                            <img
                                src={char.avatar_url}
                                alt={char.data.name}
                                style={{
                                    width: 40,
                                    height: 40,
                                    borderRadius: 'var(--radius-md)',
                                    objectFit: 'cover'
                                }}
                            />
                        ) : (
                            <div
                                className="message-avatar"
                                style={{
                                    width: 40,
                                    height: 40,
                                    backgroundColor: 'var(--accent-secondary)',
                                    color: 'white'
                                }}
                            >
                                {char.data.name.charAt(0).toUpperCase()}
                            </div>
                        )}

                        <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: 500 }}>{char.data.name}</div>
                            {char.data.tags?.length > 0 && (
                                <div className="text-sm text-muted">
                                    {char.data.tags.slice(0, 3).join(', ')}
                                </div>
                            )}
                        </div>

                        <div className="flex gap-sm">
                            <button
                                className="btn btn-small"
                                onClick={(e) => {
                                    e.stopPropagation()
                                    startEdit(char)
                                }}
                                title="Edit"
                            >
                                ✎
                            </button>
                            <button
                                className="btn btn-small"
                                onClick={(e) => handleExport(e, char.id, 'json')}
                                title="Export JSON"
                            >
                                📤
                            </button>
                            <button
                                className="btn btn-small btn-danger"
                                onClick={(e) => handleDelete(e, char.id)}
                                title="Delete"
                            >
                                ✕
                            </button>
                        </div>
                    </div>
                ))}

                {characters.length === 0 && (
                    <div className="text-muted text-sm" style={{ textAlign: 'center', padding: 'var(--space-lg)' }}>
                        No characters yet.<br />
                        Click + to create or 📥 to import.
                    </div>
                )}
            </div>

            {activeCharacter && !showForm && (
                <div className="card mt-md">
                    <div className="card-body">
                        <div className="text-sm text-muted mb-md">Selected Character</div>
                        <div style={{ fontWeight: 600, marginBottom: 'var(--space-sm)' }}>
                            {activeCharacter.data.name}
                        </div>
                        <div className="text-sm" style={{
                            maxHeight: 100,
                            overflow: 'auto',
                            color: 'var(--text-secondary)'
                        }}>
                            {activeCharacter.data.description?.slice(0, 300)}
                            {activeCharacter.data.description?.length > 300 && '...'}
                        </div>
                        {activeCharacter.data.first_mes && (
                            <div className="text-sm mt-md" style={{ color: 'var(--text-muted)' }}>
                                <strong>First message:</strong> {activeCharacter.data.first_mes.slice(0, 100)}...
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
