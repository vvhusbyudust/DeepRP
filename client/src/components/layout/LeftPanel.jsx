import { useState } from 'react'
import { useAppStore } from '../../stores/appStore'
import LLMConfig from '../settings/LLMConfig'
import PresetEditor from '../settings/PresetEditor'
import CharacterEditor from '../settings/CharacterEditor'
import WorldBookEditor from '../settings/WorldBookEditor'
import AgentConfig from '../settings/AgentConfig'
import AgentLogViewer from '../settings/AgentLogViewer'
import SessionList from '../settings/SessionList'
import RegexEditor from '../settings/RegexEditor'
import LogViewer from '../settings/LogViewer'
import ImageConfigEditor from '../settings/ImageConfigEditor'
import TTSConfigEditor from '../settings/TTSConfigEditor'

const TABS = [
    { id: 'llm', icon: '🔧', label: 'LLM' },
    { id: 'preset', icon: '📝', label: 'Preset' },
    { id: 'character', icon: '👤', label: 'Character' },
    { id: 'worldbook', icon: '🌍', label: 'World Book' },
    { id: 'regex', icon: '📐', label: 'Regex' },
    { id: 'agent', icon: '🤖', label: 'Agent' },
    { id: 'agent-logs', icon: '📊', label: 'Agent Logs' },
    { id: 'image', icon: '🖼️', label: 'Image' },
    { id: 'tts', icon: '🔊', label: 'TTS' },
    { id: 'logs', icon: '📋', label: 'Logs' },
]

function SettingsModal({ tab, onClose }) {
    if (!tab) return null

    const tabInfo = TABS.find(t => t.id === tab)

    return (
        <div className="settings-modal-overlay" onClick={onClose}>
            <div className="settings-modal" onClick={e => e.stopPropagation()}>
                <div className="settings-modal-header">
                    <span className="settings-modal-icon">{tabInfo?.icon}</span>
                    <span className="settings-modal-title">{tabInfo?.label}</span>
                    <button className="settings-modal-close" onClick={onClose}>✕</button>
                </div>
                <div className="settings-modal-content">
                    {tab === 'llm' && <LLMConfig />}
                    {tab === 'preset' && <PresetEditor />}
                    {tab === 'character' && <CharacterEditor />}
                    {tab === 'worldbook' && <WorldBookEditor />}
                    {tab === 'regex' && <RegexEditor />}
                    {tab === 'agent' && <AgentConfig />}
                    {tab === 'agent-logs' && <AgentLogViewer />}
                    {tab === 'image' && <ImageConfigEditor />}
                    {tab === 'tts' && <TTSConfigEditor />}
                    {tab === 'logs' && <LogViewer />}
                </div>
            </div>
        </div>
    )
}

export default function LeftPanel() {
    const { agentConfig, settingsTab, setSettingsTab } = useAppStore()
    const [modalTab, setModalTab] = useState(null)

    const handleTabClick = (tabId) => {
        setSettingsTab(tabId)
        setModalTab(tabId)
    }

    return (
        <>
            <div style={{ display: 'flex', height: '100%', width: '100%' }}>
                {/* Icon Sidebar */}
                <div className="sidebar">
                    <div className="sidebar-header">
                        {agentConfig.enabled && (
                            <span className="agent-badge-small">A</span>
                        )}
                    </div>

                    <div className="sidebar-tabs">
                        {TABS.map(tab => (
                            <button
                                key={tab.id}
                                className={`sidebar-tab ${settingsTab === tab.id ? 'active' : ''}`}
                                onClick={() => handleTabClick(tab.id)}
                                title={tab.label}
                            >
                                <span className="sidebar-tab-icon">{tab.icon}</span>
                                <span className="sidebar-tab-label">{tab.label}</span>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Quick panel beside sidebar - Sessions */}
                <div className="panel left-panel" style={{ flex: 1, height: '100%' }}>
                    <div className="panel-header">
                        <span className="panel-title">Sessions</span>
                    </div>
                    <div className="panel-content">
                        <SessionList />
                    </div>
                </div>
            </div>

            {/* Settings Modal */}
            <SettingsModal tab={modalTab} onClose={() => setModalTab(null)} />
        </>
    )
}
