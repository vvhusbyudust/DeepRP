import { useAppStore } from '../../stores/appStore'

export default function RightPanel() {
    const { sessionImages, agentConfig } = useAppStore()

    // Sync scroll with center panel
    const handleScroll = (e) => {
        const centerPanel = document.querySelector('.center-panel .panel-content')
        if (centerPanel) {
            centerPanel.scrollTop = e.target.scrollTop
        }
    }

    return (
        <div className="panel right-panel" style={{ height: '100%' }}>
            <div className="panel-header">
                <span className="panel-title">Images</span>
                {agentConfig.enabled && (
                    <span className="text-sm text-muted">Agent Mode</span>
                )}
            </div>

            <div className="panel-content" onScroll={handleScroll}>
                {sessionImages.length === 0 ? (
                    <div style={{
                        textAlign: 'center',
                        padding: 'var(--space-2xl)',
                        color: 'var(--text-muted)'
                    }}>
                        <div style={{ fontSize: 32, marginBottom: 'var(--space-md)' }}>🎨</div>
                        <div className="text-sm">
                            {agentConfig.enabled
                                ? 'Images will appear here when Agent mode generates them'
                                : 'Enable Agent mode to generate images automatically'
                            }
                        </div>
                    </div>
                ) : (
                    <div className="image-gallery">
                        {sessionImages.map((img, index) => (
                            <div key={index} className="gallery-item">
                                <img
                                    src={img.url}
                                    alt={`Generated image ${index + 1}`}
                                    loading="lazy"
                                />
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}
