import { useState, useEffect } from 'react'

const API_BASE = '/api/tts'

// Provider-specific defaults and options
const PROVIDER_CONFIGS = {
    elevenlabs: {
        label: 'ElevenLabs',
        models: [
            { id: 'eleven_multilingual_v2', name: 'Multilingual v2 (default)' },
            { id: 'eleven_turbo_v2_5', name: 'Turbo v2.5 (low latency)' },
            { id: 'eleven_flash_v2_5', name: 'Flash v2.5 (ultra-low latency)' },
            { id: 'eleven_monolingual_v1', name: 'Monolingual v1 (English)' },
        ],
        showStability: true,
        showSimilarity: true,
        showSpeed: false,
    },
    openai: {
        label: 'OpenAI',
        models: [
            { id: 'tts-1', name: 'TTS-1 (fast)' },
            { id: 'tts-1-hd', name: 'TTS-1-HD (high quality)' },
            { id: 'gpt-4o-mini-tts', name: 'GPT-4o Mini TTS (expressive)' },
        ],
        voices: [
            { id: 'alloy', name: 'Alloy' },
            { id: 'echo', name: 'Echo' },
            { id: 'fable', name: 'Fable' },
            { id: 'onyx', name: 'Onyx' },
            { id: 'nova', name: 'Nova' },
            { id: 'shimmer', name: 'Shimmer' },
        ],
        showStability: false,
        showSimilarity: false,
        showSpeed: true,
    },
}

export default function TTSConfigEditor() {
    const [configs, setConfigs] = useState([])
    const [loading, setLoading] = useState(true)
    const [testStatus, setTestStatus] = useState({})
    const [availableVoices, setAvailableVoices] = useState({})
    const [loadingVoices, setLoadingVoices] = useState({})

    const [formData, setFormData] = useState({
        name: '',
        type: 'elevenlabs',
        api_key: '',
        default_voice_id: '',
        model_id: '',
        stability: 0.5,
        similarity_boost: 0.75,
        speed: 1.0,
        dialogue_wrap_pattern: '',
    })

    useEffect(() => {
        loadConfigs()
    }, [])

    const loadConfigs = async () => {
        try {
            const res = await fetch(`${API_BASE}/configs`)
            if (res.ok) {
                setConfigs(await res.json())
            }
        } catch (err) {
            console.error('Failed to load configs:', err)
        } finally {
            setLoading(false)
        }
    }

    const resetForm = () => {
        setFormData({
            name: '',
            type: 'elevenlabs',
            api_key: '',
            default_voice_id: '',
            model_id: PROVIDER_CONFIGS.elevenlabs.models[0].id,
            stability: 0.5,
            similarity_boost: 0.75,
            speed: 1.0,
            dialogue_wrap_pattern: '',
        })
    }

    const handleTypeChange = (type) => {
        const providerConfig = PROVIDER_CONFIGS[type]
        setFormData(prev => ({
            ...prev,
            type,
            model_id: providerConfig.models[0]?.id || '',
            default_voice_id: providerConfig.voices?.[0]?.id || '',
        }))
    }

    const handleSubmit = async () => {
        if (!formData.name || !formData.api_key) {
            alert('Name and API Key are required')
            return
        }

        try {
            const res = await fetch(`${API_BASE}/configs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData),
            })
            if (res.ok) {
                await loadConfigs()
                resetForm()
            } else {
                alert('Failed to create config')
            }
        } catch (err) {
            console.error('Create error:', err)
        }
    }

    const handleDelete = async (id) => {
        if (!confirm('Delete this configuration?')) return
        try {
            await fetch(`${API_BASE}/configs/${id}`, { method: 'DELETE' })
            await loadConfigs()
        } catch (err) {
            console.error('Delete error:', err)
        }
    }

    const handleActivate = async (id) => {
        try {
            await fetch(`${API_BASE}/configs/${id}/activate`, { method: 'PUT' })
            await loadConfigs()
        } catch (err) {
            console.error('Activate error:', err)
        }
    }

    const handleTest = async (id) => {
        setTestStatus(prev => ({ ...prev, [id]: 'testing...' }))
        try {
            const res = await fetch(`${API_BASE}/configs/${id}/test`)
            const data = await res.json()
            setTestStatus(prev => ({
                ...prev,
                [id]: data.status === 'connected'
                    ? `✅ ${data.message}`
                    : `❌ ${data.message}`
            }))
        } catch (err) {
            setTestStatus(prev => ({ ...prev, [id]: `❌ ${err.message}` }))
        }
    }

    const handleFetchVoices = async (configId) => {
        setLoadingVoices(prev => ({ ...prev, [configId]: true }))
        try {
            const res = await fetch(`${API_BASE}/configs/${configId}/voices/available`)
            const data = await res.json()
            setAvailableVoices(prev => ({ ...prev, [configId]: data.voices || [] }))
        } catch (err) {
            console.error('Fetch voices error:', err)
        } finally {
            setLoadingVoices(prev => ({ ...prev, [configId]: false }))
        }
    }

    const providerConfig = PROVIDER_CONFIGS[formData.type] || PROVIDER_CONFIGS.elevenlabs

    if (loading) return <div className="loading">Loading...</div>

    return (
        <div className="settings-section">
            <h3 className="section-title">🔊 Text-to-Speech</h3>
            <p className="text-sm text-muted" style={{ marginBottom: 'var(--space-md)' }}>
                Configure TTS APIs for the Actor agent.
            </p>

            {/* Config List */}
            <div style={{ marginBottom: 'var(--space-lg)' }}>
                {configs.map(config => (
                    <div key={config.id} className={`card ${config.is_active ? 'card-active' : ''}`}
                        style={{ marginBottom: 'var(--space-sm)', padding: 'var(--space-sm)' }}>
                        <div className="flex items-center justify-between">
                            <div>
                                <div className="flex items-center gap-sm">
                                    <span style={{ fontWeight: 600 }}>{config.name}</span>
                                    <span className="badge">{PROVIDER_CONFIGS[config.type]?.label || config.type}</span>
                                    {config.is_active && <span className="badge badge-success">Active</span>}
                                </div>
                                <div className="text-xs text-muted" style={{ marginTop: 4 }}>
                                    Voice: {config.default_voice_id || '(not set)'}
                                    {config.model_id && ` • Model: ${config.model_id}`}
                                    {config.dialogue_wrap_pattern && ` • Wrap: ${config.dialogue_wrap_pattern.slice(0, 20)}...`}
                                </div>
                                {testStatus[config.id] && (
                                    <div className="text-xs" style={{ marginTop: 4 }}>{testStatus[config.id]}</div>
                                )}
                            </div>
                            <div className="flex gap-xs">
                                <button className="btn btn-small" onClick={() => handleTest(config.id)}>Test</button>
                                <button
                                    className="btn btn-small"
                                    onClick={() => handleFetchVoices(config.id)}
                                    disabled={loadingVoices[config.id]}
                                >
                                    {loadingVoices[config.id] ? '...' : 'Voices'}
                                </button>
                                {!config.is_active && (
                                    <button className="btn btn-small btn-primary" onClick={() => handleActivate(config.id)}>
                                        Activate
                                    </button>
                                )}
                                <button className="btn btn-small btn-danger" onClick={() => handleDelete(config.id)}>✕</button>
                            </div>
                        </div>

                        {/* Available voices dropdown */}
                        {availableVoices[config.id] && availableVoices[config.id].length > 0 && (
                            <div style={{
                                marginTop: 'var(--space-sm)', padding: 'var(--space-sm)',
                                background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)'
                            }}>
                                <div className="text-xs text-muted" style={{ marginBottom: 4 }}>Available Voices:</div>
                                <div style={{ maxHeight: 120, overflowY: 'auto' }}>
                                    {availableVoices[config.id].map(voice => (
                                        <div key={voice.id} className="text-sm" style={{
                                            padding: '2px 0',
                                            fontFamily: 'monospace',
                                            fontSize: 11
                                        }}>
                                            <code>{voice.id}</code> - {voice.name}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                ))}
                {configs.length === 0 && (
                    <div className="text-muted text-center" style={{ padding: 'var(--space-lg)' }}>
                        No TTS configs. Create one below.
                    </div>
                )}
            </div>

            {/* Create Form */}
            <div className="card" style={{ padding: 'var(--space-md)' }}>
                <h4 style={{ marginBottom: 'var(--space-md)' }}>Add New Config</h4>

                <div className="form-group">
                    <label className="form-label">Provider</label>
                    <select
                        className="select"
                        value={formData.type}
                        onChange={(e) => handleTypeChange(e.target.value)}
                    >
                        {Object.entries(PROVIDER_CONFIGS).map(([key, config]) => (
                            <option key={key} value={key}>{config.label}</option>
                        ))}
                    </select>
                </div>

                <div className="form-group">
                    <label className="form-label">Name</label>
                    <input
                        type="text"
                        className="input"
                        placeholder="My ElevenLabs"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    />
                </div>

                <div className="form-group">
                    <label className="form-label">API Key</label>
                    <input
                        type="password"
                        className="input"
                        placeholder="Enter API key"
                        value={formData.api_key}
                        onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                    />
                </div>

                <div className="form-group">
                    <label className="form-label">Model</label>
                    <select
                        className="select"
                        value={formData.model_id}
                        onChange={(e) => setFormData({ ...formData, model_id: e.target.value })}
                    >
                        {providerConfig.models.map(m => (
                            <option key={m.id} value={m.id}>{m.name}</option>
                        ))}
                    </select>
                </div>

                {providerConfig.voices ? (
                    <div className="form-group">
                        <label className="form-label">Default Voice</label>
                        <select
                            className="select"
                            value={formData.default_voice_id}
                            onChange={(e) => setFormData({ ...formData, default_voice_id: e.target.value })}
                        >
                            {providerConfig.voices.map(v => (
                                <option key={v.id} value={v.id}>{v.name}</option>
                            ))}
                        </select>
                    </div>
                ) : (
                    <div className="form-group">
                        <label className="form-label">Default Voice ID</label>
                        <input
                            type="text"
                            className="input"
                            placeholder="Voice ID from provider"
                            value={formData.default_voice_id}
                            onChange={(e) => setFormData({ ...formData, default_voice_id: e.target.value })}
                        />
                        <div className="text-xs text-muted" style={{ marginTop: 4 }}>
                            For ElevenLabs, use voice ID from your library. Click "Voices" on a saved config to see available IDs.
                        </div>
                    </div>
                )}

                {providerConfig.showStability && (
                    <div className="form-group">
                        <label className="form-label">Stability: {formData.stability.toFixed(2)}</label>
                        <input
                            type="range"
                            className="slider"
                            min="0"
                            max="1"
                            step="0.05"
                            value={formData.stability}
                            onChange={(e) => setFormData({ ...formData, stability: parseFloat(e.target.value) })}
                        />
                        <div className="text-xs text-muted" style={{ marginTop: 4 }}>
                            Higher = more consistent, lower = more expressive
                        </div>
                    </div>
                )}

                {providerConfig.showSimilarity && (
                    <div className="form-group">
                        <label className="form-label">Similarity Boost: {formData.similarity_boost.toFixed(2)}</label>
                        <input
                            type="range"
                            className="slider"
                            min="0"
                            max="1"
                            step="0.05"
                            value={formData.similarity_boost}
                            onChange={(e) => setFormData({ ...formData, similarity_boost: parseFloat(e.target.value) })}
                        />
                        <div className="text-xs text-muted" style={{ marginTop: 4 }}>
                            Higher = closer to original voice, lower = more natural
                        </div>
                    </div>
                )}

                {providerConfig.showSpeed && (
                    <div className="form-group">
                        <label className="form-label">Speed: {formData.speed.toFixed(2)}x</label>
                        <input
                            type="range"
                            className="slider"
                            min="0.25"
                            max="4.0"
                            step="0.25"
                            value={formData.speed}
                            onChange={(e) => setFormData({ ...formData, speed: parseFloat(e.target.value) })}
                        />
                    </div>
                )}

                <div className="form-group">
                    <label className="form-label">Dialogue Wrap Pattern (Optional)</label>
                    <input
                        type="text"
                        className="input"
                        placeholder="{text}"
                        value={formData.dialogue_wrap_pattern}
                        onChange={(e) => setFormData({ ...formData, dialogue_wrap_pattern: e.target.value })}
                    />
                    <div className="text-xs text-muted" style={{ marginTop: 4 }}>
                        Wrap dialogue before synthesis. Use <code>{'{text}'}</code> as placeholder.<br />
                        Examples: <code>「{'{text}'}」</code>, <code>&lt;speak&gt;{'{text}'}&lt;/speak&gt;</code>
                    </div>
                </div>

                <button className="btn btn-primary" onClick={handleSubmit} style={{ width: '100%' }}>
                    Create Config
                </button>
            </div>
        </div>
    )
}
