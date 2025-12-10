import { useRef, useEffect, useState } from 'react'
import { useAppStore } from '../../stores/appStore'
import MessageBubble from './MessageBubble'

export default function ChatWindow() {
    const { messages, isStreaming, activeCharacter, activeSession, regenerateMessage } = useAppStore()
    const bottomRef = useRef(null)
    const [greetingIndex, setGreetingIndex] = useState(0)

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    // Reset greeting index when character changes
    useEffect(() => {
        setGreetingIndex(0)
    }, [activeCharacter?.id])

    // Calculate greeting count from character's alternate_greetings
    const greetings = activeCharacter?.data?.alternate_greetings || []
    const allGreetings = activeCharacter?.data?.first_mes
        ? [activeCharacter.data.first_mes, ...greetings]
        : greetings
    const greetingCount = allGreetings.length

    const handleSwipeGreeting = (direction) => {
        const newIndex = greetingIndex + direction
        if (newIndex >= 0 && newIndex < greetingCount) {
            setGreetingIndex(newIndex)
            // Update the first message content
            const newGreeting = allGreetings[newIndex] || ''
            useAppStore.setState(state => ({
                messages: state.messages.map((m, i) =>
                    i === 0 && m.role === 'assistant'
                        ? {
                            ...m,
                            content: newGreeting
                                .replace(/\{\{user\}\}/g, 'User')
                                .replace(/\{\{char\}\}/g, activeCharacter?.data?.name || 'Assistant')
                        }
                        : m
                )
            }))
        }
    }

    const handleRegenerate = (messageId) => {
        if (regenerateMessage) {
            regenerateMessage(messageId)
        }
    }

    if (!activeSession && !activeCharacter) {
        return (
            <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: 'var(--text-muted)',
                padding: 'var(--space-2xl)'
            }}>
                <div style={{ fontSize: 48, marginBottom: 'var(--space-lg)' }}>💬</div>
                <div style={{ fontSize: 16, marginBottom: 'var(--space-sm)' }}>Welcome to DeepRP</div>
                <div className="text-sm" style={{ textAlign: 'center' }}>
                    Select a character from the left panel to start chatting,<br />
                    or create a new chat session.
                </div>
            </div>
        )
    }

    // Find the last assistant message that can be regenerated
    const lastAssistantIndex = messages.reduceRight((acc, m, i) =>
        acc === -1 && m.role === 'assistant' && m.id !== 'first-mes' ? i : acc, -1)

    return (
        <div style={{ padding: 'var(--space-lg)' }}>
            {messages.map((message, index) => {
                const isFirstMessage = index === 0 && message.role === 'assistant'
                const isLastAssistant = index === lastAssistantIndex

                return (
                    <MessageBubble
                        key={message.id || index}
                        message={message}
                        isStreaming={isStreaming && index === messages.length - 1 && message.role === 'assistant'}
                        isLast={isLastAssistant}
                        onRegenerate={isLastAssistant ? () => handleRegenerate(message.id) : undefined}
                        greetingIndex={isFirstMessage ? greetingIndex : 0}
                        greetingCount={isFirstMessage ? greetingCount : 1}
                        onSwipeGreeting={isFirstMessage && greetingCount > 1 ? handleSwipeGreeting : undefined}
                    />
                )
            })}
            <div ref={bottomRef} />
        </div>
    )
}
