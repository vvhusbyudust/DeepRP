import { useState, useEffect } from 'react'
import { useAppStore } from '../../stores/appStore'
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
} from '@dnd-kit/core'
import {
    arrayMove,
    SortableContext,
    sortableKeyboardCoordinates,
    useSortable,
    verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

// SortableEntry component - defined outside PresetEditor to prevent re-creation on each render
function SortableEntry({ entry, idx, entriesLength, toggleEntry, deleteEntry, updateEntryContent }) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({ id: entry.id })

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.5 : 1,
        padding: 'var(--space-sm)',
        borderBottom: idx < entriesLength - 1 ? '1px solid var(--border-subtle)' : 'none',
    }

    return (
        <div ref={setNodeRef} style={style}>
            <div className="flex items-center gap-sm mb-xs">
                <span
                    {...attributes}
                    {...listeners}
                    style={{ cursor: 'grab', userSelect: 'none', padding: '4px' }}
                    title="Drag to reorder"
                >
                    ⋮⋮
                </span>
                <input
                    type="checkbox"
                    checked={entry.enabled}
                    onChange={() => toggleEntry(entry.id)}
                />
                <span className="text-sm" style={{
                    fontWeight: 500,
                    opacity: entry.enabled ? 1 : 0.5
                }}>
                    {entry.name}
                </span>
                <span className="text-sm text-muted">({entry.role})</span>
                {entry.deletable && (
                    <button
                        className="btn btn-small btn-danger"
                        onClick={() => deleteEntry(entry.id)}
                        style={{ marginLeft: 'auto' }}
                    >
                        ✕
                    </button>
                )}
            </div>
            <textarea
                className="textarea"
                rows={2}
                value={entry.content}
                onChange={(e) => updateEntryContent(entry.id, e.target.value)}
                style={{ fontSize: '12px', opacity: entry.enabled ? 1 : 0.5 }}
            />
        </div>
    )
}

export default function PresetEditor() {
    const { presets, activePreset, setActivePreset, initialize } = useAppStore()
    const [showForm, setShowForm] = useState(false)
    const [showEntriesEditor, setShowEntriesEditor] = useState(false)
    const [showAdvanced, setShowAdvanced] = useState(false)
    const [editingId, setEditingId] = useState(null)
    const [formData, setFormData] = useState({
        name: '',
        temperature: 0.9,
        max_tokens: 2048,
        top_p: 0.95,
        top_k: 40,
        frequency_penalty: 0,
        presence_penalty: 0,
        // Advanced samplers
        min_p: 0,
        repetition_penalty: 1.0,
        mirostat_mode: 0,
        mirostat_tau: 5.0,
        mirostat_eta: 0.1,
        tail_free_sampling: 1.0,
        typical_p: 1.0,
        // Features
        enable_cot: false,
    })
    const [entries, setEntries] = useState([])
    const [newEntry, setNewEntry] = useState({ name: '', content: '', role: 'system' })

    // Regex binding state
    const [availableRegexScripts, setAvailableRegexScripts] = useState([])
    const [selectedRegexIds, setSelectedRegexIds] = useState([])

    // Fetch available regex scripts on mount
    useEffect(() => {
        fetch('/api/regex')
            .then(res => res.json())
            .then(scripts => setAvailableRegexScripts(scripts))
            .catch(() => { })
    }, [])

    const resetForm = () => {
        setFormData({
            name: '', temperature: 0.9, max_tokens: 2048, top_p: 0.95,
            top_k: 40, frequency_penalty: 0, presence_penalty: 0,
            min_p: 0, repetition_penalty: 1.0, mirostat_mode: 0,
            mirostat_tau: 5.0, mirostat_eta: 0.1, tail_free_sampling: 1.0, typical_p: 1.0,
            enable_cot: false,
        })
        setEditingId(null)
        setShowForm(false)
        setShowAdvanced(false)
        setEntries([])
        setSelectedRegexIds([])
    }

    const startEdit = async (preset) => {
        setFormData({
            name: preset.name,
            temperature: preset.temperature,
            max_tokens: preset.max_tokens,
            top_p: preset.top_p,
            top_k: preset.top_k,
            frequency_penalty: preset.frequency_penalty,
            presence_penalty: preset.presence_penalty,
            min_p: preset.min_p || 0,
            repetition_penalty: preset.repetition_penalty || 1.0,
            mirostat_mode: preset.mirostat_mode || 0,
            mirostat_tau: preset.mirostat_tau || 5.0,
            mirostat_eta: preset.mirostat_eta || 0.1,
            tail_free_sampling: preset.tail_free_sampling || 1.0,
            typical_p: preset.typical_p || 1.0,
            enable_cot: preset.enable_cot || false,
        })
        setEntries(preset.prompt_entries || [])
        setSelectedRegexIds(preset.regex_script_ids || [])
        setEditingId(preset.id)
        setShowForm(true)
        // Don't auto-expand - let user click to expand to avoid scroll jumps
        setShowEntriesEditor(false)
    }

    const handleSubmit = async () => {
        if (!formData.name) return

        try {
            const endpoint = editingId ? `/api/presets/${editingId}` : '/api/presets'
            const method = editingId ? 'PUT' : 'POST'

            const payload = { ...formData }
            if (editingId) {
                payload.prompt_entries = entries
                payload.regex_script_ids = selectedRegexIds
            }

            const res = await fetch(endpoint, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            })

            if (res.ok) {
                await initialize()
                resetForm()
            }
        } catch (err) {
            console.error(err)
        }
    }

    const handleDelete = async (e, presetId) => {
        e.stopPropagation()

        try {
            await fetch(`/api/presets/${presetId}`, { method: 'DELETE' })
            await initialize()
            if (activePreset?.id === presetId) {
                setActivePreset(null)
            }
        } catch (err) {
            console.error(err)
        }
    }

    const addEntry = () => {
        if (!newEntry.name) return
        setEntries([...entries, {
            id: `entry_${Date.now()}`,
            name: newEntry.name,
            content: newEntry.content,
            role: newEntry.role,
            enabled: true,
            depth: entries.length,
            deletable: true,
        }])
        setNewEntry({ name: '', content: '', role: 'system' })
    }

    const toggleEntry = (id) => {
        setEntries(entries.map(e => e.id === id ? { ...e, enabled: !e.enabled } : e))
    }

    const deleteEntry = (id) => {
        const entry = entries.find(e => e.id === id)
        if (entry && !entry.deletable) return
        setEntries(entries.filter(e => e.id !== id))
    }

    const updateEntryContent = (id, content) => {
        setEntries(entries.map(e => e.id === id ? { ...e, content } : e))
    }

    const handleExport = async (presetId) => {
        try {
            const res = await fetch(`/api/presets/${presetId}/export`)
            const data = await res.json()
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `${data.preset_name || 'preset'}.json`
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
            await fetch('/api/presets/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            })
            await initialize()
        } catch (err) {
            console.error('Import failed:', err)
        }
        e.target.value = ''
    }

    // Drag-drop sensors
    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    )

    const handleDragEnd = (event) => {
        const { active, over } = event
        if (active.id !== over?.id) {
            const oldIndex = entries.findIndex((e) => e.id === active.id)
            const newIndex = entries.findIndex((e) => e.id === over?.id)
            setEntries(arrayMove(entries, oldIndex, newIndex))
        }
    }


    return (
        <div>
            <div className="section-header">
                <span className="section-title">Presets</span>
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
                            {editingId ? 'Edit Preset' : 'New Preset'}
                        </div>

                        <div className="form-group">
                            <label className="form-label">Name</label>
                            <input
                                className="input"
                                placeholder="My Preset"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Temperature: {formData.temperature}</label>
                            <input
                                type="range"
                                className="slider"
                                min="0"
                                max="2"
                                step="0.1"
                                value={formData.temperature}
                                onChange={(e) => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Max Tokens: {formData.max_tokens}</label>
                            <input
                                type="range"
                                className="slider"
                                min="256"
                                max="8192"
                                step="256"
                                value={formData.max_tokens}
                                onChange={(e) => setFormData({ ...formData, max_tokens: parseInt(e.target.value) })}
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Top P: {formData.top_p}</label>
                            <input
                                type="range"
                                className="slider"
                                min="0"
                                max="1"
                                step="0.05"
                                value={formData.top_p}
                                onChange={(e) => setFormData({ ...formData, top_p: parseFloat(e.target.value) })}
                            />
                        </div>

                        {/* Advanced Samplers Section */}
                        <div className="mt-md">
                            <div className="flex items-center gap-sm mb-sm">
                                <span className="form-label" style={{ margin: 0 }}>Advanced Samplers</span>
                                <button
                                    className="btn btn-small"
                                    onClick={() => setShowAdvanced(!showAdvanced)}
                                >
                                    {showAdvanced ? '▲' : '▼'}
                                </button>
                            </div>

                            {showAdvanced && (
                                <div style={{
                                    background: 'var(--bg-primary)',
                                    padding: 'var(--space-sm)',
                                    borderRadius: 'var(--radius-sm)',
                                    marginBottom: 'var(--space-md)'
                                }}>
                                    <div className="form-group">
                                        <label className="form-label">Min P: {formData.min_p}</label>
                                        <input
                                            type="range"
                                            className="slider"
                                            min="0"
                                            max="0.5"
                                            step="0.01"
                                            value={formData.min_p}
                                            onChange={(e) => setFormData({ ...formData, min_p: parseFloat(e.target.value) })}
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Repetition Penalty: {formData.repetition_penalty}</label>
                                        <input
                                            type="range"
                                            className="slider"
                                            min="1.0"
                                            max="2.0"
                                            step="0.05"
                                            value={formData.repetition_penalty}
                                            onChange={(e) => setFormData({ ...formData, repetition_penalty: parseFloat(e.target.value) })}
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Typical P: {formData.typical_p}</label>
                                        <input
                                            type="range"
                                            className="slider"
                                            min="0"
                                            max="1"
                                            step="0.05"
                                            value={formData.typical_p}
                                            onChange={(e) => setFormData({ ...formData, typical_p: parseFloat(e.target.value) })}
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Tail Free Sampling: {formData.tail_free_sampling}</label>
                                        <input
                                            type="range"
                                            className="slider"
                                            min="0"
                                            max="1"
                                            step="0.05"
                                            value={formData.tail_free_sampling}
                                            onChange={(e) => setFormData({ ...formData, tail_free_sampling: parseFloat(e.target.value) })}
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Mirostat Mode</label>
                                        <select
                                            className="select"
                                            value={formData.mirostat_mode}
                                            onChange={(e) => setFormData({ ...formData, mirostat_mode: parseInt(e.target.value) })}
                                        >
                                            <option value={0}>Disabled</option>
                                            <option value={1}>Mirostat 1</option>
                                            <option value={2}>Mirostat 2</option>
                                        </select>
                                    </div>
                                    {formData.mirostat_mode > 0 && (
                                        <>
                                            <div className="form-group">
                                                <label className="form-label">Mirostat Tau: {formData.mirostat_tau}</label>
                                                <input
                                                    type="range"
                                                    className="slider"
                                                    min="0"
                                                    max="10"
                                                    step="0.5"
                                                    value={formData.mirostat_tau}
                                                    onChange={(e) => setFormData({ ...formData, mirostat_tau: parseFloat(e.target.value) })}
                                                />
                                            </div>
                                            <div className="form-group">
                                                <label className="form-label">Mirostat Eta: {formData.mirostat_eta}</label>
                                                <input
                                                    type="range"
                                                    className="slider"
                                                    min="0"
                                                    max="1"
                                                    step="0.05"
                                                    value={formData.mirostat_eta}
                                                    onChange={(e) => setFormData({ ...formData, mirostat_eta: parseFloat(e.target.value) })}
                                                />
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Prompt Entries Section */}
                        {/* Features Section */}
                        <div className="mt-md">
                            <span className="form-label">Features</span>
                            <div style={{
                                background: 'var(--bg-primary)',
                                padding: 'var(--space-sm)',
                                borderRadius: 'var(--radius-sm)',
                                marginTop: 'var(--space-xs)'
                            }}>
                                <label className="flex items-center gap-sm" style={{ cursor: 'pointer' }}>
                                    <input
                                        type="checkbox"
                                        checked={formData.enable_cot}
                                        onChange={(e) => setFormData({ ...formData, enable_cot: e.target.checked })}
                                    />
                                    <span>Enable Chain of Thought</span>
                                    <span className="text-muted text-sm" style={{ marginLeft: 'auto' }}>
                                        (Shows thinking process from Claude/DeepSeek)
                                    </span>
                                </label>
                            </div>
                        </div>

                        {/* Regex Binding Section */}
                        {editingId && availableRegexScripts.length > 0 && (
                            <div className="mt-md">
                                <span className="form-label">Regex Binding</span>
                                <div style={{
                                    background: 'var(--bg-primary)',
                                    padding: 'var(--space-sm)',
                                    borderRadius: 'var(--radius-sm)',
                                    marginTop: 'var(--space-xs)',
                                    maxHeight: 200,
                                    overflowY: 'auto'
                                }}>
                                    {availableRegexScripts.map(script => (
                                        <label
                                            key={script.id}
                                            className="flex items-center gap-sm"
                                            style={{
                                                cursor: 'pointer',
                                                padding: '4px 0',
                                                opacity: script.enabled ? 1 : 0.5
                                            }}
                                        >
                                            <input
                                                type="checkbox"
                                                checked={selectedRegexIds.includes(script.id)}
                                                onChange={(e) => {
                                                    if (e.target.checked) {
                                                        setSelectedRegexIds([...selectedRegexIds, script.id])
                                                    } else {
                                                        setSelectedRegexIds(selectedRegexIds.filter(id => id !== script.id))
                                                    }
                                                }}
                                            />
                                            <span>{script.name}</span>
                                            <span className="text-muted text-sm" style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
                                                {script.run_on_director_output && <span style={{ padding: '1px 4px', fontSize: 10, background: '#9333ea', color: 'white', borderRadius: 3 }}>Dir</span>}
                                                {script.run_on_writer_output && <span style={{ padding: '1px 4px', fontSize: 10, background: '#0891b2', color: 'white', borderRadius: 3 }}>Wri</span>}
                                                {script.run_on_paint_director_output && <span style={{ padding: '1px 4px', fontSize: 10, background: '#ea580c', color: 'white', borderRadius: 3 }}>Pnt</span>}
                                            </span>
                                        </label>
                                    ))}
                                </div>
                                <div className="text-sm text-muted mt-xs">
                                    Selected regex scripts will be applied to this preset's outputs
                                </div>
                            </div>
                        )}

                        {editingId && (
                            <div style={{
                                marginTop: 'var(--space-lg)',
                                border: '1px solid var(--border-default)',
                                borderRadius: 'var(--radius-md)',
                                background: 'var(--bg-secondary)',
                                overflow: 'hidden'
                            }}>
                                {/* Clean Header */}
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    padding: 'var(--space-md) var(--space-lg)',
                                    background: 'var(--bg-tertiary)',
                                    borderBottom: showEntriesEditor ? '1px solid var(--border-default)' : 'none',
                                    cursor: 'pointer'
                                }} onClick={(e) => {
                                    e.preventDefault()
                                    setShowEntriesEditor(!showEntriesEditor)
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                                        <span className="form-label" style={{ margin: 0 }}>Prompt Entries</span>
                                        <span style={{
                                            background: 'var(--bg-active)',
                                            padding: '2px 8px',
                                            borderRadius: '10px',
                                            fontSize: 11,
                                            color: 'var(--text-muted)'
                                        }}>{entries.length}</span>
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                                        <button
                                            className="btn btn-small"
                                            onClick={async (e) => {
                                                e.stopPropagation()
                                                const res = await fetch(`/api/presets/${editingId}/reset-entries`, { method: 'POST' })
                                                if (res.ok) {
                                                    const updated = await res.json()
                                                    setEntries(updated.prompt_entries || [])
                                                }
                                            }}
                                            title="Reset to SillyTavern defaults"
                                        >
                                            ↻ Reset
                                        </button>
                                        <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                                            {showEntriesEditor ? '▲' : '▼'}
                                        </span>
                                    </div>
                                </div>

                                {showEntriesEditor && (
                                    <div style={{
                                        padding: 'var(--space-md)',
                                        background: 'var(--bg-primary)',
                                    }}>
                                        <DndContext
                                            sensors={sensors}
                                            collisionDetection={closestCenter}
                                            onDragEnd={handleDragEnd}
                                        >
                                            <SortableContext
                                                items={entries.map(e => e.id)}
                                                strategy={verticalListSortingStrategy}
                                            >
                                                {entries.map((entry, idx) => (
                                                    <SortableEntry
                                                        key={entry.id}
                                                        entry={entry}
                                                        idx={idx}
                                                        entriesLength={entries.length}
                                                        toggleEntry={toggleEntry}
                                                        deleteEntry={deleteEntry}
                                                        updateEntryContent={updateEntryContent}
                                                    />
                                                ))}
                                            </SortableContext>
                                        </DndContext>

                                        {/* Add new entry */}
                                        <div style={{
                                            marginTop: 'var(--space-sm)',
                                            padding: 'var(--space-sm)',
                                            borderTop: '1px solid var(--border-default)'
                                        }}>
                                            <div className="text-sm text-muted mb-xs">Add Entry</div>
                                            <div className="flex gap-sm mb-xs">
                                                <input
                                                    className="input"
                                                    placeholder="Entry name"
                                                    value={newEntry.name}
                                                    onChange={(e) => setNewEntry({ ...newEntry, name: e.target.value })}
                                                    style={{ flex: 1 }}
                                                />
                                                <select
                                                    className="select"
                                                    value={newEntry.role}
                                                    onChange={(e) => setNewEntry({ ...newEntry, role: e.target.value })}
                                                    style={{ width: 100 }}
                                                >
                                                    <option value="system">system</option>
                                                    <option value="user">user</option>
                                                    <option value="assistant">assistant</option>
                                                </select>
                                            </div>
                                            <textarea
                                                className="textarea"
                                                rows={2}
                                                placeholder="Entry content..."
                                                value={newEntry.content}
                                                onChange={(e) => setNewEntry({ ...newEntry, content: e.target.value })}
                                            />
                                            <button className="btn btn-small mt-xs" onClick={addEntry}>
                                                + Add
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        <div className="flex gap-sm" style={{ marginTop: 'var(--space-lg)' }}>
                            <button className="btn btn-primary" onClick={handleSubmit}>
                                {editingId ? 'Update' : 'Create'}
                            </button>
                            <button className="btn" onClick={resetForm}>Cancel</button>
                        </div>
                    </div>
                </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
                {presets.map(preset => (
                    <div
                        key={preset.id}
                        className={`list-item ${activePreset?.id === preset.id ? 'active' : ''}`}
                        onClick={() => setActivePreset(preset)}
                    >
                        <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: 500 }}>{preset.name}</div>
                            <div className="text-sm text-muted">
                                T:{preset.temperature} • Max:{preset.max_tokens} • Entries:{preset.prompt_entries?.length || 0}
                            </div>
                        </div>

                        <div className="flex gap-sm">
                            <button
                                className="btn btn-small"
                                onClick={(e) => {
                                    e.stopPropagation()
                                    startEdit(preset)
                                }}
                                title="Edit"
                            >
                                ✎
                            </button>
                            <button
                                className="btn btn-small"
                                onClick={(e) => {
                                    e.stopPropagation()
                                    handleExport(preset.id)
                                }}
                                title="Export SillyTavern"
                            >
                                ↑
                            </button>
                            <button
                                className="btn btn-small btn-danger"
                                onClick={(e) => handleDelete(e, preset.id)}
                                title="Delete"
                            >
                                ✕
                            </button>
                        </div>
                    </div>
                ))}

                {presets.length === 0 && (
                    <div className="text-muted text-sm" style={{ textAlign: 'center', padding: 'var(--space-lg)' }}>
                        No presets yet. Click + to create one.
                    </div>
                )}
            </div>

            {activePreset && !showForm && (
                <div className="card mt-md">
                    <div className="card-body">
                        <div className="text-sm text-muted mb-md">Active Preset</div>
                        <div style={{ fontWeight: 600, marginBottom: 'var(--space-sm)' }}>
                            {activePreset.name}
                        </div>
                        <div className="text-sm mono" style={{ color: 'var(--text-secondary)' }}>
                            temperature: {activePreset.temperature}<br />
                            max_tokens: {activePreset.max_tokens}<br />
                            prompt_entries: {activePreset.prompt_entries?.length || 0}
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
