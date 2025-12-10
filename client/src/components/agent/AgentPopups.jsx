import { useState, useEffect, useRef, useCallback } from 'react'
import { useAppStore } from '../../stores/appStore'

// Custom hook for drag functionality
function useDraggable(initialPosition) {
    const [position, setPosition] = useState(initialPosition)
    const [isDragging, setIsDragging] = useState(false)
    const dragRef = useRef({ startX: 0, startY: 0, startPosX: 0, startPosY: 0 })

    const handleMouseDown = useCallback((e) => {
        if (e.target.closest('.popup-close')) return // Don't drag when clicking close
        setIsDragging(true)
        dragRef.current = {
            startX: e.clientX,
            startY: e.clientY,
            startPosX: position.x,
            startPosY: position.y,
        }
        e.preventDefault()
    }, [position])

    useEffect(() => {
        if (!isDragging) return

        const handleMouseMove = (e) => {
            const deltaX = e.clientX - dragRef.current.startX
            const deltaY = e.clientY - dragRef.current.startY
            setPosition({
                x: dragRef.current.startPosX + deltaX,
                y: dragRef.current.startPosY + deltaY,
            })
        }

        const handleMouseUp = () => {
            setIsDragging(false)
        }

        document.addEventListener('mousemove', handleMouseMove)
        document.addEventListener('mouseup', handleMouseUp)

        return () => {
            document.removeEventListener('mousemove', handleMouseMove)
            document.removeEventListener('mouseup', handleMouseUp)
        }
    }, [isDragging])

    return { position, isDragging, handleMouseDown }
}

export default function AgentPopups() {
    const {
        directorOutput,
        paintDirectorOutput,
        showDirectorPopup,
        showPaintDirectorPopup,
        setShowDirectorPopup,
        setShowPaintDirectorPopup,
        agentStage,
    } = useAppStore()

    // Draggable positions - start from window dimensions
    const directorDrag = useDraggable({ x: window.innerWidth - 420, y: 80 })
    const paintDrag = useDraggable({ x: window.innerWidth - 420, y: 400 })

    // Refs for auto-scroll
    const directorRef = useRef(null)
    const paintRef = useRef(null)

    // Auto-scroll to bottom when content updates
    useEffect(() => {
        if (directorRef.current) {
            directorRef.current.scrollTop = directorRef.current.scrollHeight
        }
    }, [directorOutput])

    useEffect(() => {
        if (paintRef.current) {
            paintRef.current.scrollTop = paintRef.current.scrollHeight
        }
    }, [paintDirectorOutput])

    return (
        <>
            {/* Director Output Popup */}
            {showDirectorPopup && (
                <div
                    className="agent-popup"
                    style={{
                        left: directorDrag.position.x,
                        top: directorDrag.position.y,
                        cursor: directorDrag.isDragging ? 'grabbing' : 'default',
                    }}
                >
                    <div
                        className="popup-header"
                        onMouseDown={directorDrag.handleMouseDown}
                        style={{ cursor: directorDrag.isDragging ? 'grabbing' : 'grab' }}
                    >
                        <span className="popup-icon">🎬</span>
                        <span className="popup-title">Director</span>
                        {agentStage === 'director' && (
                            <span className="popup-streaming">● Streaming</span>
                        )}
                        <button
                            className="popup-close"
                            onClick={() => setShowDirectorPopup(false)}
                        >
                            ✕
                        </button>
                    </div>
                    <div className="popup-content" ref={directorRef}>
                        {directorOutput || (
                            <span className="text-muted">Waiting for director output...</span>
                        )}
                    </div>
                </div>
            )}

            {/* Paint Director Output Popup */}
            {showPaintDirectorPopup && (
                <div
                    className="agent-popup"
                    style={{
                        left: paintDrag.position.x,
                        top: paintDrag.position.y,
                        cursor: paintDrag.isDragging ? 'grabbing' : 'default',
                    }}
                >
                    <div
                        className="popup-header"
                        onMouseDown={paintDrag.handleMouseDown}
                        style={{ cursor: paintDrag.isDragging ? 'grabbing' : 'grab' }}
                    >
                        <span className="popup-icon">🎨</span>
                        <span className="popup-title">Paint Director</span>
                        {agentStage === 'paint_director' && (
                            <span className="popup-streaming">● Streaming</span>
                        )}
                        <button
                            className="popup-close"
                            onClick={() => setShowPaintDirectorPopup(false)}
                        >
                            ✕
                        </button>
                    </div>
                    <div className="popup-content" ref={paintRef}>
                        {paintDirectorOutput || (
                            <span className="text-muted">Waiting for image prompt...</span>
                        )}
                    </div>
                </div>
            )}

            <style>{`
                .agent-popup {
                    position: fixed;
                    width: 400px;
                    max-height: 300px;
                    background: var(--bg-secondary);
                    border: 1px solid var(--border-default);
                    border-radius: 12px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                    z-index: 1000;
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                    user-select: none;
                }

                .popup-header {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    padding: 0.75rem 1rem;
                    background: var(--bg-tertiary);
                    border-bottom: 1px solid var(--border-subtle);
                }

                .popup-icon {
                    font-size: 1.2rem;
                }

                .popup-title {
                    font-weight: 600;
                    flex: 1;
                }

                .popup-streaming {
                    font-size: 0.75rem;
                    color: #22c55e;
                    animation: pulse 1.5s infinite;
                }

                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }

                .popup-close {
                    background: none;
                    border: none;
                    color: var(--text-secondary);
                    cursor: pointer;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 1rem;
                }

                .popup-close:hover {
                    background: var(--bg-primary);
                    color: var(--text-primary);
                }

                .popup-content {
                    padding: 1rem;
                    overflow-y: auto;
                    flex: 1;
                    font-size: 0.9rem;
                    line-height: 1.6;
                    white-space: pre-wrap;
                    font-family: var(--font-sans);
                    user-select: text;
                }

                /* Responsive popup width */
                @media (max-width: 900px) {
                    .agent-popup {
                        width: 320px;
                    }
                }

                @media (max-width: 600px) {
                    .agent-popup {
                        width: 280px;
                        max-height: 250px;
                    }
                }
            `}</style>
        </>
    )
}
