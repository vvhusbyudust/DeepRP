import { useState } from 'react'
import { useAppStore } from '../../stores/appStore'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export default function LLMConfig() {
    const {
        llmConfigs,
        activeLLMConfig,
        addLLMConfig,
        setActiveLLMConfig,
        deleteLLMConfig,
        updateLLMConfig,
        settingsFormState,
        updateSettingsFormState,
        resetSettingsFormState,
    } = useAppStore()

    // Get form state from global store
    const { showForm, editingId, formData } = settingsFormState.llm

    const [loading, setLoading] = useState(false)
    const [fetchingModels, setFetchingModels] = useState(false)
    const [availableModels, setAvailableModels] = useState([])

    const setShowForm = (show) => updateSettingsFormState('llm', { showForm: show })
    const setEditingId = (id) => updateSettingsFormState('llm', { editingId: id })
    const setFormData = (data) => updateSettingsFormState('llm', { formData: data })

    const resetForm = () => {
        resetSettingsFormState('llm')
        setAvailableModels([])
    }

    const startEdit = async (config) => {
        updateSettingsFormState('llm', {
            showForm: true,
            editingId: config.id,
            formData: {
                name: config.name,
                base_url: config.base_url,
                api_key: '', // Don't show existing key
                default_model: config.default_model || '',
            }
        })
        // Load cached models if available
        try {
            const res = await fetch(`${API_BASE}/config/llm/${config.id}/cached-models`)
            if (res.ok) {
                const data = await res.json()
                if (data.models && data.models.length > 0) {
                    setAvailableModels(data.models)
                }
            }
        } catch (err) {
            console.error('Failed to load cached models:', err)
        }
    }

    const fetchModels = async () => {
        if (!editingId && !formData.base_url) {
            alert('Please save the config first before fetching models')
            return
        }

        const configId = editingId
        if (!configId) {
            alert('Please save the config first to fetch models')
            return
        }

        setFetchingModels(true)
        try {
            const res = await fetch(`${API_BASE}/config/llm/${configId}/models`)
            if (!res.ok) {
                const error = await res.json()
                throw new Error(error.detail || 'Failed to fetch models')
            }
            const data = await res.json()
            setAvailableModels(data.models || [])
            if (data.models && data.models.length > 0) {
                // If current model not in list, clear it
                if (formData.default_model && !data.models.includes(formData.default_model)) {
                    setFormData({ ...formData, default_model: data.models[0] })
                }
            }
        } catch (err) {
            console.error(err)
            alert('Failed to fetch models: ' + err.message)
        }
        setFetchingModels(false)
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!formData.name || !formData.base_url) return

        setLoading(true)
        try {
            if (editingId) {
                // Update existing config
                await updateLLMConfig(editingId, {
                    name: formData.name,
                    base_url: formData.base_url,
                    default_model: formData.default_model,
                    // Only send api_key if changed
                    ...(formData.api_key ? { api_key: formData.api_key } : {}),
                })
            } else {
                // Create new config
                if (!formData.api_key) {
                    alert('API key is required for new configs')
                    setLoading(false)
                    return
                }
                await addLLMConfig(formData)
            }
            resetForm()
        } catch (err) {
            console.error(err)
            alert('Failed to save: ' + err.message)
        }
        setLoading(false)
    }

    const handleDelete = async (e, configId) => {
        e.stopPropagation()
        try {
            await deleteLLMConfig(configId)
        } catch (err) {
            console.error(err)
        }
    }

    return (
        <div>
            <div className="section-header">
                <span className="section-title">LLM Configurations</span>
                <button className="btn btn-small" onClick={() => {
                    if (showForm) resetForm()
                    else setShowForm(true)
                }}>
                    {showForm ? '✕' : '+ Add'}
                </button>
            </div>

            {showForm && (
                <form onSubmit={handleSubmit} className="card mb-md">
                    <div className="card-body">
                        <div className="text-sm text-muted mb-md">
                            {editingId ? 'Edit Configuration' : 'New Configuration'}
                        </div>

                        <div className="form-group">
                            <label className="form-label">Name</label>
                            <input
                                className="input"
                                placeholder="e.g., OpenAI GPT-4"
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                required
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Base URL</label>
                            <input
                                className="input mono"
                                placeholder="https://api.openai.com/v1"
                                value={formData.base_url}
                                onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                                required
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">
                                API Key {editingId && <span className="text-muted">(leave empty to keep current)</span>}
                            </label>
                            <input
                                className="input input-masked"
                                type="password"
                                placeholder={editingId ? "••••••••" : "sk-..."}
                                value={formData.api_key}
                                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                                required={!editingId}
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">
                                Default Model
                                {editingId && (
                                    <button
                                        type="button"
                                        className="btn btn-small"
                                        style={{ marginLeft: '8px', fontSize: '10px' }}
                                        onClick={fetchModels}
                                        disabled={fetchingModels}
                                    >
                                        {fetchingModels ? '⏳ Fetching...' : '🔄 Fetch Models'}
                                    </button>
                                )}
                            </label>
                            {availableModels.length > 0 ? (
                                <select
                                    className="input"
                                    value={formData.default_model}
                                    onChange={(e) => setFormData({ ...formData, default_model: e.target.value })}
                                >
                                    <option value="">-- Select a model --</option>
                                    {availableModels.map(model => (
                                        <option key={model} value={model}>{model}</option>
                                    ))}
                                </select>
                            ) : (
                                <input
                                    className="input"
                                    placeholder="gpt-4"
                                    value={formData.default_model}
                                    onChange={(e) => setFormData({ ...formData, default_model: e.target.value })}
                                />
                            )}
                            {availableModels.length > 0 && (
                                <div className="text-sm text-muted" style={{ marginTop: '4px' }}>
                                    {availableModels.length} models available
                                </div>
                            )}
                        </div>

                        <div className="flex gap-sm">
                            <button className="btn btn-primary" type="submit" disabled={loading}>
                                {loading ? 'Saving...' : editingId ? 'Update' : 'Save'}
                            </button>
                            {editingId && (
                                <button type="button" className="btn" onClick={resetForm}>
                                    Cancel
                                </button>
                            )}
                        </div>
                    </div>
                </form>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
                {llmConfigs.map(config => (
                    <div
                        key={config.id}
                        className={`list-item ${activeLLMConfig?.id === config.id ? 'active' : ''}`}
                        onClick={() => setActiveLLMConfig(config.id)}
                    >
                        <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: 500 }}>{config.name}</div>
                            <div className="text-sm text-muted mono">{config.base_url}</div>
                            {config.default_model && (
                                <div className="text-sm text-accent">{config.default_model}</div>
                            )}
                        </div>

                        <div className="flex gap-sm">
                            <button
                                className="btn btn-small"
                                onClick={(e) => {
                                    e.stopPropagation()
                                    startEdit(config)
                                }}
                                title="Edit"
                            >
                                ✎
                            </button>
                            <button
                                className="btn btn-small btn-danger"
                                onClick={(e) => handleDelete(e, config.id)}
                                title="Delete"
                            >
                                ✕
                            </button>
                        </div>
                    </div>
                ))}

                {llmConfigs.length === 0 && (
                    <div className="text-muted text-sm" style={{ textAlign: 'center', padding: 'var(--space-lg)' }}>
                        No LLM configurations yet.<br />Click "+ Add" to create one.
                    </div>
                )}
            </div>
        </div>
    )
}
