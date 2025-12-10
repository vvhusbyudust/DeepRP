import { useState, useEffect } from 'react'
import { PanelGroup, Panel, PanelResizeHandle } from 'react-resizable-panels'
import LeftPanel from './components/layout/LeftPanel'
import CenterPanel from './components/layout/CenterPanel'
import RightPanel from './components/layout/RightPanel'
import AgentPopups from './components/agent/AgentPopups'
import { useAppStore } from './stores/appStore'

function App() {
    const { initialize, isLoading } = useAppStore()

    useEffect(() => {
        initialize()
    }, [])

    if (isLoading) {
        return (
            <div className="app-container" style={{
                alignItems: 'center',
                justifyContent: 'center',
                flexDirection: 'column',
                gap: 'var(--space-lg)'
            }}>
                <div className="spinner" style={{ width: 40, height: 40 }}></div>
                <div style={{ color: 'var(--text-secondary)' }}>Loading DeepRP...</div>
            </div>
        )
    }

    return (
        <div className="app-container">
            <PanelGroup direction="horizontal" autoSaveId="deeprp-panels" style={{ width: '100%', height: '100%' }}>
                <Panel defaultSize={25} minSize={15} maxSize={40}>
                    <LeftPanel />
                </Panel>

                <PanelResizeHandle className="resize-handle" />

                <Panel defaultSize={50} minSize={30}>
                    <CenterPanel />
                </Panel>

                <PanelResizeHandle className="resize-handle" />

                <Panel defaultSize={25} minSize={15} maxSize={40}>
                    <RightPanel />
                </Panel>
            </PanelGroup>
            <AgentPopups />
        </div>
    )
}

export default App
