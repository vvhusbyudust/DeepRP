import { useState, useEffect } from 'react'

const API_BASE = '/api/images'

// Provider-specific defaults and options
const PROVIDER_CONFIGS = {
    openai: {
        label: 'OpenAI (DALL-E)',
        defaultUrl: 'https://api.openai.com/v1',
        models: ['dall-e-3', 'dall-e-2'],
        sizes: ['1024x1024', '1792x1024', '1024x1792', '512x512', '256x256'],
        showQuality: true,
        showAdvanced: false,
        showWorkflow: false,
    },
    novelai: {
        label: 'NovelAI',
        defaultUrl: 'https://image.novelai.net',
        models: ['nai-diffusion-3', 'nai-diffusion-4-curated-preview', 'nai-diffusion-furry-3'],
        sizes: ['1024x1024', '832x1216', '1216x832', '640x640'],
        samplers: ['k_euler', 'k_euler_ancestral', 'k_dpmpp_2s_ancestral', 'k_dpmpp_2m', 'k_dpmpp_sde', 'ddim'],
        showQuality: false,
        showAdvanced: true,
        showWorkflow: false,
    },
    comfyui: {
        label: 'ComfyUI',
        defaultUrl: 'http://127.0.0.1:8188',
        models: [],
        sizes: ['1024x1024', '1024x768', '768x1024', '512x512'],
        samplers: ['euler', 'euler_ancestral', 'dpmpp_2m', 'dpmpp_sde', 'ddim', 'uni_pc'],
        showQuality: false,
        showAdvanced: true,
        showWorkflow: true,
    },
    stable_diffusion: {
        label: 'Stable Diffusion WebUI',
        defaultUrl: 'http://127.0.0.1:7860',
        models: [],
        sizes: ['1024x1024', '768x768', '512x512', '1024x768', '768x1024'],
        samplers: ['Euler a', 'Euler', 'DPM++ 2M', 'DPM++ SDE', 'DDIM', 'UniPC'],
        showQuality: false,
        showAdvanced: true,
        showWorkflow: false,
    },
}

export default function ImageConfigEditor() {
    const [configs, setConfigs] = useState([])
    const [loading, setLoading] = useState(true)
    const [editingId, setEditingId] = useState(null)
    const [testStatus, setTestStatus] = useState({})

    const [formData, setFormData] = useState({
        name: '',
        type: 'comfyui',
        base_url: '',
        api_key: '',
        model: '',
        size: '1024x1024',
        quality: 'standard',
        negative_prompt: '',
        steps: 28,
        cfg_scale: 7.0,
        sampler: '',
        workflow_json: '',
        prompt_node_id: '',
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
            type: 'comfyui',
            base_url: PROVIDER_CONFIGS.comfyui.defaultUrl,
            api_key: '',
            model: '',
            size: '1024x1024',
            quality: 'standard',
            negative_prompt: '',
            steps: 28,
            cfg_scale: 7.0,
            sampler: '',
            workflow_json: '',
            prompt_node_id: '',
        })
        setEditingId(null)
    }

    const handleTypeChange = (type) => {
        const providerConfig = PROVIDER_CONFIGS[type]
        setFormData(prev => ({
            ...prev,
            type,
            base_url: providerConfig.defaultUrl,
            model: providerConfig.models[0] || '',
            sampler: providerConfig.samplers?.[0] || '',
        }))
    }

    const handleSubmit = async () => {
        if (!formData.name || !formData.base_url) {
            alert('Name and Base URL are required')
            return
        }

        try {
            const url = editingId
                ? `${API_BASE}/configs/${editingId}`
                : `${API_BASE}/configs`
            const method = editingId ? 'PUT' : 'POST'

            const res = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData),
            })
            if (res.ok) {
                await loadConfigs()
                resetForm()
                setEditingId(null)
            } else {
                alert(editingId ? 'Failed to update config' : 'Failed to create config')
            }
        } catch (err) {
            console.error('Save error:', err)
        }
    }

    const handleDelete = async (id) => {
        try {
            await fetch(`${API_BASE}/configs/${id}`, { method: 'DELETE' })
            await loadConfigs()
            if (editingId === id) {
                resetForm()
                setEditingId(null)
            }
        } catch (err) {
            console.error('Delete error:', err)
        }
    }

    const handleEdit = (config) => {
        setEditingId(config.id)
        setFormData({
            name: config.name,
            type: config.type,
            base_url: config.base_url,
            api_key: '',  // Don't populate masked key
            model: config.model || '',
            size: config.size || '1024x1024',
            quality: config.quality || 'standard',
            negative_prompt: config.negative_prompt || '',
            steps: config.steps || 28,
            cfg_scale: config.cfg_scale || 7.0,
            sampler: config.sampler || '',
            workflow_json: config.workflow_json || '',
            prompt_node_id: config.prompt_node_id || '',
        })
    }

    const handleCancelEdit = () => {
        setEditingId(null)
        resetForm()
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

    const providerConfig = PROVIDER_CONFIGS[formData.type] || PROVIDER_CONFIGS.comfyui

    if (loading) return <div className="loading">Loading...</div>

    return (
        <div className="settings-section">
            <h3 className="section-title">🎨 Image Generation</h3>
            <p className="text-sm text-muted" style={{ marginBottom: 'var(--space-md)' }}>
                Configure image generation APIs for the Painter agent.
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
                                    {config.base_url} • {config.size}
                                    {config.model && ` • ${config.model}`}
                                </div>
                                {testStatus[config.id] && (
                                    <div className="text-xs" style={{ marginTop: 4 }}>{testStatus[config.id]}</div>
                                )}
                            </div>
                            <div className="flex gap-xs">
                                <button className="btn btn-small" onClick={() => handleTest(config.id)}>Test</button>
                                <button className="btn btn-small" onClick={() => handleEdit(config)}>Edit</button>
                                {!config.is_active && (
                                    <button className="btn btn-small btn-primary" onClick={() => handleActivate(config.id)}>
                                        Activate
                                    </button>
                                )}
                                <button className="btn btn-small btn-danger" onClick={() => handleDelete(config.id)}>✕</button>
                            </div>
                        </div>
                    </div>
                ))}
                {configs.length === 0 && (
                    <div className="text-muted text-center" style={{ padding: 'var(--space-lg)' }}>
                        No image configs. Create one below.
                    </div>
                )}
            </div>

            {/* Create/Edit Form */}
            <div className="card" style={{ padding: 'var(--space-md)' }}>
                <div className="flex items-center justify-between" style={{ marginBottom: 'var(--space-md)' }}>
                    <h4 style={{ margin: 0 }}>{editingId ? 'Edit Config' : 'Add New Config'}</h4>
                    {editingId && (
                        <button className="btn btn-small" onClick={handleCancelEdit}>Cancel</button>
                    )}
                </div>

                <div className="form-group">
                    <label className="form-label">Provider Type</label>
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
                        placeholder="My ComfyUI"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    />
                </div>

                <div className="form-group">
                    <label className="form-label">Base URL</label>
                    <input
                        type="text"
                        className="input"
                        placeholder={providerConfig.defaultUrl}
                        value={formData.base_url}
                        onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                    />
                </div>

                <div className="form-group">
                    <label className="form-label">API Key / Token</label>
                    <input
                        type="password"
                        className="input"
                        placeholder={formData.type === 'comfyui' || formData.type === 'stable_diffusion'
                            ? '(Optional for local)'
                            : 'Enter API key'}
                        value={formData.api_key}
                        onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                    />
                </div>

                {providerConfig.models.length > 0 && (
                    <div className="form-group">
                        <label className="form-label">Model</label>
                        <select
                            className="select"
                            value={formData.model}
                            onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                        >
                            {providerConfig.models.map(m => (
                                <option key={m} value={m}>{m}</option>
                            ))}
                        </select>
                    </div>
                )}

                {formData.type === 'comfyui' && !formData.workflow_json && (
                    <div className="form-group">
                        <label className="form-label">Model / Checkpoint Name</label>
                        <input
                            type="text"
                            className="input"
                            placeholder="sd_xl_base_1.0.safetensors"
                            value={formData.model}
                            onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                        />
                        <div className="text-xs text-muted" style={{ marginTop: 4 }}>
                            Exact filename from ComfyUI models/checkpoints folder
                        </div>
                    </div>
                )}

                {!formData.workflow_json && (
                    <div className="form-group">
                        <label className="form-label">Size</label>
                        <select
                            className="select"
                            value={formData.size}
                            onChange={(e) => setFormData({ ...formData, size: e.target.value })}
                        >
                            {providerConfig.sizes.map(s => (
                                <option key={s} value={s}>{s}</option>
                            ))}
                        </select>
                    </div>
                )}

                {providerConfig.showQuality && (
                    <div className="form-group">
                        <label className="form-label">Quality</label>
                        <select
                            className="select"
                            value={formData.quality}
                            onChange={(e) => setFormData({ ...formData, quality: e.target.value })}
                        >
                            <option value="standard">Standard</option>
                            <option value="hd">HD</option>
                        </select>
                    </div>
                )}

                {providerConfig.showAdvanced && !formData.workflow_json && (
                    <>
                        <div className="form-group">
                            <label className="form-label">Steps: {formData.steps}</label>
                            <input
                                type="range"
                                className="slider"
                                min="10"
                                max="50"
                                value={formData.steps}
                                onChange={(e) => setFormData({ ...formData, steps: parseInt(e.target.value) })}
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">CFG Scale: {formData.cfg_scale}</label>
                            <input
                                type="range"
                                className="slider"
                                min="1"
                                max="20"
                                step="0.5"
                                value={formData.cfg_scale}
                                onChange={(e) => setFormData({ ...formData, cfg_scale: parseFloat(e.target.value) })}
                            />
                        </div>

                        {providerConfig.samplers && (
                            <div className="form-group">
                                <label className="form-label">Sampler</label>
                                <select
                                    className="select"
                                    value={formData.sampler}
                                    onChange={(e) => setFormData({ ...formData, sampler: e.target.value })}
                                >
                                    {providerConfig.samplers.map(s => (
                                        <option key={s} value={s}>{s}</option>
                                    ))}
                                </select>
                            </div>
                        )}

                        <div className="form-group">
                            <label className="form-label">Negative Prompt</label>
                            <textarea
                                className="textarea"
                                rows={2}
                                placeholder="bad quality, blurry, worst quality..."
                                value={formData.negative_prompt}
                                onChange={(e) => setFormData({ ...formData, negative_prompt: e.target.value })}
                            />
                        </div>
                    </>
                )}

                {providerConfig.showWorkflow && (
                    <div className="form-group">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <label className="form-label">Custom Workflow JSON (Optional)</label>
                            <label className="btn btn-sm" style={{ cursor: 'pointer', fontSize: '0.75rem', padding: '4px 8px' }}>
                                📁 Import JSON
                                <input
                                    type="file"
                                    accept=".json"
                                    style={{ display: 'none' }}
                                    onChange={(e) => {
                                        const file = e.target.files?.[0]
                                        if (file) {
                                            const reader = new FileReader()
                                            reader.onload = (evt) => {
                                                try {
                                                    // Validate JSON
                                                    JSON.parse(evt.target.result)
                                                    setFormData({ ...formData, workflow_json: evt.target.result })
                                                } catch {
                                                    alert('Invalid JSON file')
                                                }
                                            }
                                            reader.readAsText(file)
                                        }
                                        e.target.value = '' // Reset for re-import
                                    }}
                                />
                            </label>
                        </div>
                        <textarea
                            className="textarea"
                            rows={6}
                            placeholder='Paste ComfyUI API workflow JSON here (use "Save (API format)" in ComfyUI)'
                            value={formData.workflow_json}
                            onChange={(e) => setFormData({ ...formData, workflow_json: e.target.value })}
                            style={{ fontFamily: 'monospace', fontSize: '12px' }}
                        />
                        <div className="text-xs text-muted" style={{ marginTop: 4 }}>
                            Use placeholders: <code style={{ background: 'var(--bg-tertiary)', padding: '1px 4px' }}>{"{{PROMPT}}"}</code> for positive prompt,
                            <code style={{ background: 'var(--bg-tertiary)', padding: '1px 4px', marginLeft: 4 }}>{"{{NEGATIVE}}"}</code> for negative.
                            <br />Leave empty to use default txt2img workflow.
                        </div>

                        {formData.workflow_json && (
                            <div className="form-group" style={{ marginTop: '0.75rem' }}>
                                <label className="form-label">Prompt Node ID</label>
                                <input
                                    type="text"
                                    className="input"
                                    placeholder="e.g., 70"
                                    value={formData.prompt_node_id}
                                    onChange={(e) => setFormData({ ...formData, prompt_node_id: e.target.value })}
                                    style={{ width: '150px' }}
                                />
                                <div className="text-xs text-muted" style={{ marginTop: 4 }}>
                                    Node ID where the prompt should be injected (from workflow JSON)
                                </div>
                            </div>
                        )}
                    </div>
                )}

                <button className="btn btn-primary" onClick={handleSubmit} style={{ width: '100%' }}>
                    Create Config
                </button>
            </div>
        </div>
    )
}
