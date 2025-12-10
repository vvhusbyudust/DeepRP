import { useState, useRef, useEffect } from 'react'
import { useAppStore } from '../../stores/appStore'
import PromptPreviewModal from '../settings/PromptPreviewModal'

export default function InputBox() {
    const [input, setInput] = useState('')
    const [showPreview, setShowPreview] = useState(false)
    const textareaRef = useRef(null)
    const { sendMessage, isStreaming, stopStreaming, activeLLMConfig, agentConfig } = useAppStore()

    // Auto-resize textarea
    useEffect(() => {
        const textarea = textareaRef.current
        if (textarea) {
            textarea.style.height = 'auto'
            textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px'
        }
    }, [input])

    const handleSubmit = () => {
        if (!input.trim() || isStreaming) return
        sendMessage(input.trim())
        setInput('')
    }

    const handleKeyDown = (e) => {
        // Enter to send, Ctrl+Enter for newline
        if (e.key === 'Enter' && !e.ctrlKey && !e.shiftKey) {
            e.preventDefault()
            handleSubmit()
        }
    }

    return (
        <div className="chat-input-container">
            <div className="chat-input-wrapper">
                <textarea
                    ref={textareaRef}
                    className="chat-input"
                    placeholder={
                        !activeLLMConfig
                            ? "Configure an LLM first..."
                            : "Type a message... (Ctrl+Enter for newline)"
                    }
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={!activeLLMConfig}
                    rows={1}
                />

                {/* Preview button - always visible */}
                <button
                    className="btn btn-icon"
                    onClick={() => setShowPreview(true)}
                    title="Preview Agent Prompts"
                    style={{
                        background: 'var(--bg-tertiary)',
                        border: '1px solid var(--border-subtle)'
                    }}
                >
                    👁️
                </button>

                {isStreaming ? (
                    <button
                        className="btn btn-danger btn-icon"
                        onClick={stopStreaming}
                        title="Stop"
                    >
                        ⏹
                    </button>
                ) : (
                    <button
                        className="btn btn-primary btn-icon"
                        onClick={handleSubmit}
                        disabled={!input.trim() || !activeLLMConfig}
                        title="Send"
                    >
                        ➤
                    </button>
                )}
            </div>

            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginTop: 'var(--space-xs)',
                fontSize: 11,
                color: 'var(--text-muted)'
            }}>
                <span>Enter to send • Ctrl+Enter for newline</span>
                {activeLLMConfig && (
                    <span>Using: {activeLLMConfig.name}</span>
                )}
            </div>

            <PromptPreviewModal
                isOpen={showPreview}
                onClose={() => setShowPreview(false)}
            />
        </div>
    )
}
