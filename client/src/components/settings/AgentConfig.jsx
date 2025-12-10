import { useState, useEffect } from 'react'
import { useAppStore } from '../../stores/appStore'

export default function AgentConfig() {
    const {
        agentConfig,
        toggleAgentMode,
        updateAgentConfig,
        llmConfigs,
        presets,
        imageConfigs
    } = useAppStore()

    // Test connection states
    const [testingTTS, setTestingTTS] = useState(false)
    const [ttsTestResult, setTTSTestResult] = useState(null)
    const [testingImage, setTestingImage] = useState(false)
    const [imageTestResult, setImageTestResult] = useState(null)

    const [config, setConfig] = useState({
        director_llm_config_id: '',
        director_preset_id: '',
        writer_llm_config_id: '',
        writer_preset_id: '',
        painter_llm_config_id: '',
        painter_preset_id: '',
        image_config_id: '',
        tts_config_id: '',
        tts_llm_config_id: '',
        tts_preset_id: '',
        enable_paint: true,
        enable_tts: true,
    })

    useEffect(() => {
        if (agentConfig) {
            setConfig({
                director_llm_config_id: agentConfig.director_llm_config_id || '',
                director_preset_id: agentConfig.director_preset_id || '',
                writer_llm_config_id: agentConfig.writer_llm_config_id || '',
                writer_preset_id: agentConfig.writer_preset_id || '',
                painter_llm_config_id: agentConfig.painter_llm_config_id || '',
                painter_preset_id: agentConfig.painter_preset_id || '',
                image_config_id: agentConfig.image_config_id || '',
                tts_config_id: agentConfig.tts_config_id || '',
                tts_llm_config_id: agentConfig.tts_llm_config_id || '',
                tts_preset_id: agentConfig.tts_preset_id || '',
                enable_paint: agentConfig.enable_paint !== false,
                enable_tts: agentConfig.enable_tts !== false,
            })
        }
    }, [agentConfig])

    const handleChange = async (field, value) => {
        const newConfig = { ...config, [field]: value }
        setConfig(newConfig)
        await updateAgentConfig({ ...agentConfig, ...newConfig })
    }

    const testTTSConnection = async () => {
        if (!config.tts_config_id) {
            setTTSTestResult({ status: 'error', message: 'No TTS config ID set' })
            return
        }
        setTestingTTS(true)
        setTTSTestResult(null)
        try {
            const res = await fetch(`/api/tts/configs/${config.tts_config_id}/test`)
            const result = await res.json()
            setTTSTestResult(result)
        } catch (err) {
            setTTSTestResult({ status: 'error', message: err.message })
        }
        setTestingTTS(false)
    }

    const testImageConnection = async () => {
        if (!config.image_config_id) {
            setImageTestResult({ status: 'error', message: 'No Image config ID set' })
            return
        }
        setTestingImage(true)
        setImageTestResult(null)
        try {
            const res = await fetch(`/api/images/configs/${config.image_config_id}/test`)
            const result = await res.json()
            setImageTestResult(result)
        } catch (err) {
            setImageTestResult({ status: 'error', message: err.message })
        }
        setTestingImage(false)
    }

    const AgentRow = ({ badge, label, llmField, presetField }) => (
        <div className="card mb-md">
            <div className="card-header">
                <span className={`agent-badge ${badge}`}>{label}</span>
            </div>
            <div className="card-body">
                <div className="form-group">
                    <label className="form-label">LLM Config</label>
                    <select
                        className="select"
                        value={config[llmField] || ''}
                        onChange={(e) => handleChange(llmField, e.target.value)}
                    >
                        <option value="">Select LLM...</option>
                        {llmConfigs.map(c => (
                            <option key={c.id} value={c.id}>{c.name}</option>
                        ))}
                    </select>
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                    <label className="form-label">Generation Preset</label>
                    <select
                        className="select"
                        value={config[presetField] || ''}
                        onChange={(e) => handleChange(presetField, e.target.value)}
                    >
                        <option value="">Default parameters</option>
                        {presets.map(p => (
                            <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                    </select>
                </div>
            </div>
        </div>
    )

    return (
        <div>
            <div className="section-header">
                <span className="section-title">Agent Mode</span>
                <div
                    className={`toggle ${agentConfig.enabled ? 'active' : ''}`}
                    onClick={toggleAgentMode}
                />
            </div>

            <div className="card mb-md">
                <div className="card-body">
                    <p className="text-sm text-muted" style={{ marginBottom: 'var(--space-md)' }}>
                        When enabled, messages go through the Director → Writer → Paint Director → TTS pipeline
                        for enhanced roleplay with images and voice.
                    </p>

                    {/* Stage Toggle Switches */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)', marginTop: 'var(--space-md)', paddingTop: 'var(--space-md)', borderTop: '1px solid var(--border-default)' }}>
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-sm">
                                <span className="agent-badge painter" style={{ fontSize: '0.7rem', padding: '2px 6px' }}>🎨</span>
                                <span className="text-sm">Paint Director + Painter</span>
                            </div>
                            <div
                                className={`toggle ${config.enable_paint ? 'active' : ''}`}
                                onClick={() => handleChange('enable_paint', !config.enable_paint)}
                            />
                        </div>
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-sm">
                                <span className="agent-badge tts" style={{ fontSize: '0.7rem', padding: '2px 6px' }}>🔊</span>
                                <span className="text-sm">TTS Actor</span>
                            </div>
                            <div
                                className={`toggle ${config.enable_tts ? 'active' : ''}`}
                                onClick={() => handleChange('enable_tts', !config.enable_tts)}
                            />
                        </div>
                    </div>
                </div>
            </div>

            {agentConfig.enabled && (
                <>
                    <AgentRow
                        badge="director"
                        label="Director"
                        llmField="director_llm_config_id"
                        presetField="director_preset_id"
                    />
                    <AgentRow
                        badge="writer"
                        label="Writer"
                        llmField="writer_llm_config_id"
                        presetField="writer_preset_id"
                    />
                    <AgentRow
                        badge="painter"
                        label="Paint Director"
                        llmField="painter_llm_config_id"
                        presetField="painter_preset_id"
                    />

                    {/* Image API Configuration */}
                    <div className="card mb-md">
                        <div className="card-header">
                            <span className="agent-badge painter" style={{ fontSize: '0.7rem', padding: '2px 6px' }}>🎨</span>
                            <span style={{ marginLeft: '0.5rem' }}>Image Generation API</span>
                        </div>
                        <div className="card-body">
                            <div className="form-group" style={{ marginBottom: 0 }}>
                                <label className="form-label">Image API Config</label>
                                <div className="flex gap-sm">
                                    <select
                                        className="select"
                                        style={{ flex: 1 }}
                                        value={config.image_config_id || ''}
                                        onChange={(e) => handleChange('image_config_id', e.target.value)}
                                    >
                                        <option value="">Select Image API...</option>
                                        {imageConfigs.map(c => (
                                            <option key={c.id} value={c.id}>{c.name} ({c.type})</option>
                                        ))}
                                    </select>
                                    <button
                                        className="btn btn-primary"
                                        onClick={testImageConnection}
                                        disabled={testingImage || !config.image_config_id}
                                    >
                                        {testingImage ? '...' : 'Test'}
                                    </button>
                                </div>
                                {imageTestResult && (
                                    <div className={`text-sm mt-sm ${imageTestResult.status === 'connected' ? 'text-success' : 'text-error'}`}>
                                        {imageTestResult.status === 'connected' ? '✓' : '✗'} {imageTestResult.message}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* TTS Configuration */}
                    <div className="card mb-md">
                        <div className="card-header">
                            <span className="agent-badge tts">TTS Actor</span>
                        </div>
                        <div className="card-body">
                            <div className="form-group">
                                <label className="form-label">TTS API Config ID</label>
                                <div className="flex gap-sm">
                                    <input
                                        type="text"
                                        className="input"
                                        style={{ flex: 1 }}
                                        placeholder="TTS configuration ID..."
                                        value={config.tts_config_id || ''}
                                        onChange={(e) => handleChange('tts_config_id', e.target.value)}
                                    />
                                    <button
                                        className="btn btn-primary"
                                        onClick={testTTSConnection}
                                        disabled={testingTTS || !config.tts_config_id}
                                    >
                                        {testingTTS ? '...' : 'Test'}
                                    </button>
                                </div>
                                {ttsTestResult && (
                                    <div className={`text-sm mt-sm ${ttsTestResult.status === 'connected' ? 'text-success' : 'text-error'}`}>
                                        {ttsTestResult.status === 'connected' ? '✓' : '✗'} {ttsTestResult.message}
                                    </div>
                                )}
                            </div>
                            <div className="form-group">
                                <label className="form-label">Actor LLM (emotion detection)</label>
                                <select
                                    className="select"
                                    value={config.tts_llm_config_id || ''}
                                    onChange={(e) => handleChange('tts_llm_config_id', e.target.value)}
                                >
                                    <option value="">No emotion detection</option>
                                    {llmConfigs.map(c => (
                                        <option key={c.id} value={c.id}>{c.name}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="form-group" style={{ marginBottom: 0 }}>
                                <label className="form-label">Actor Preset</label>
                                <select
                                    className="select"
                                    value={config.tts_preset_id || ''}
                                    onChange={(e) => handleChange('tts_preset_id', e.target.value)}
                                >
                                    <option value="">Default parameters</option>
                                    {presets.map(p => (
                                        <option key={p.id} value={p.id}>{p.name}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* Painter (Image Backend) */}
                    <div className="card mb-md">
                        <div className="card-header">
                            <span className="agent-badge painter">Painter</span>
                        </div>
                        <div className="card-body">
                            <div className="form-group" style={{ marginBottom: 0 }}>
                                <label className="form-label">Image Backend Config ID</label>
                                <div className="flex gap-sm">
                                    <input
                                        type="text"
                                        className="input"
                                        style={{ flex: 1 }}
                                        placeholder="ComfyUI, DALL-E, or other image API..."
                                        value={config.image_config_id || ''}
                                        onChange={(e) => handleChange('image_config_id', e.target.value)}
                                    />
                                    <button
                                        className="btn btn-primary"
                                        onClick={testImageConnection}
                                        disabled={testingImage || !config.image_config_id}
                                    >
                                        {testingImage ? '...' : 'Test'}
                                    </button>
                                </div>
                                {imageTestResult && (
                                    <div className={`text-sm mt-sm ${imageTestResult.status === 'connected' ? 'text-success' : 'text-error'}`}>
                                        {imageTestResult.status === 'connected' ? '✓' : '✗'} {imageTestResult.message}
                                    </div>
                                )}
                                <div className="text-sm text-muted mt-sm">
                                    Painter generates images from prompts created by Paint Director
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Pipeline Preview */}
                    <div className="card">
                        <div className="card-body">
                            <div className="text-sm text-muted mb-md">Pipeline Preview</div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                <div className="flex items-center gap-sm">
                                    <span className="agent-badge director">1</span>
                                    <span className="text-sm">Director creates scene outline</span>
                                </div>
                                <div style={{ width: 1, height: 16, background: 'var(--border-default)', marginLeft: 11 }} />
                                <div className="flex items-center gap-sm">
                                    <span className="agent-badge writer">2</span>
                                    <span className="text-sm">Writer generates narrative</span>
                                </div>
                                <div style={{ width: 1, height: 16, background: 'var(--border-default)', marginLeft: 11 }} />
                                <div className="flex items-center gap-sm">
                                    <span className="agent-badge painter">3</span>
                                    <span className="text-sm">Paint Director creates image prompt</span>
                                </div>
                                <div style={{ width: 1, height: 16, background: 'var(--border-default)', marginLeft: 11 }} />
                                <div className="flex items-center gap-sm">
                                    <span className="agent-badge painter">4</span>
                                    <span className="text-sm">Painter generates image</span>
                                </div>
                                <div style={{ width: 1, height: 16, background: 'var(--border-default)', marginLeft: 11 }} />
                                <div className="flex items-center gap-sm">
                                    <span className="agent-badge tts">5</span>
                                    <span className="text-sm">Actor synthesizes dialogue audio</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    )
}
