import { useRef, useEffect } from 'react'
import { useAppStore } from '../../stores/appStore'
import ChatWindow from '../chat/ChatWindow'
import InputBox from '../chat/InputBox'

export default function CenterPanel() {
    const {
        activeCharacter,
        activeSession,
        sessions,
        createSession,
        agentConfig,
        agentStage
    } = useAppStore()

    const scrollRef = useRef(null)

    // Sync scroll with right panel
    const handleScroll = (e) => {
        const rightPanel = document.querySelector('.right-panel .panel-content')
        if (rightPanel) {
            rightPanel.scrollTop = e.target.scrollTop
        }
    }

    return (
        <div className="panel center-panel" style={{ height: '100%' }}>
            <div className="panel-header">
                <div className="flex items-center gap-md">
                    <span className="panel-title">
                        {activeCharacter?.data?.name || 'Chat'}
                    </span>
                    {agentStage && (
                        <span className={`agent-badge ${agentStage}`}>
                            {agentStage.toUpperCase()}
                        </span>
                    )}
                </div>

                <div className="flex gap-sm">
                    <button className="btn btn-small" onClick={createSession}>
                        + New Chat
                    </button>
                </div>
            </div>

            <div
                className="panel-content"
                ref={scrollRef}
                onScroll={handleScroll}
                style={{ padding: 0 }}
            >
                <ChatWindow />
            </div>

            <InputBox />
        </div>
    )
}
