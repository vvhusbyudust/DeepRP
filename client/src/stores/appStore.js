import { create } from 'zustand'

const API_BASE = '/api'

export const useAppStore = create((set, get) => ({
    // Loading state
    isLoading: true,

    // LLM Configs
    llmConfigs: [],
    activeLLMConfig: null,

    // Characters
    characters: [],
    activeCharacter: null,

    // World Books
    worldbooks: [],
    activeWorldbooks: [],  // Support multiple worldbooks

    // Presets
    presets: [],
    activePreset: null,

    // Image Configs
    imageConfigs: [],

    // Chat Sessions
    sessions: [],
    activeSession: null,
    messages: [],
    isStreaming: false,

    // Agent Mode
    agentConfig: { enabled: false },
    agentStage: null,

    // Agent Popups - streaming output
    directorOutput: '',
    paintDirectorOutput: '',
    showDirectorPopup: false,
    showPaintDirectorPopup: false,

    // Images for current session
    sessionImages: [],

    // Settings panel tab
    settingsTab: 'llm',

    // Settings Form State - persists across tab switches
    settingsFormState: {
        llm: { showForm: false, editingId: null, formData: { name: '', base_url: '', api_key: '', default_model: '' } },
        preset: { showForm: false, showEntriesEditor: false, editingId: null, formData: {}, entries: [] },
        character: { showForm: false, editingId: null, formData: {} },
        worldbook: { showForm: false, editingId: null, selectedWorldbook: null, selectedEntry: null },
        regex: { showForm: false, editingId: null, formData: {} },
        image: { formData: {} },
        tts: { formData: {} },
    },

    // Update settings form state for a specific settings tab
    updateSettingsFormState: (tab, updates) => set(state => ({
        settingsFormState: {
            ...state.settingsFormState,
            [tab]: { ...state.settingsFormState[tab], ...updates }
        }
    })),

    // Reset settings form state for a specific settings tab
    resetSettingsFormState: (tab) => set(state => {
        const defaults = {
            llm: { showForm: false, editingId: null, formData: { name: '', base_url: '', api_key: '', default_model: '' } },
            preset: { showForm: false, showEntriesEditor: false, editingId: null, formData: {}, entries: [] },
            character: { showForm: false, editingId: null, formData: {} },
            worldbook: { showForm: false, editingId: null, selectedWorldbook: null, selectedEntry: null },
            regex: { showForm: false, editingId: null, formData: {} },
            image: { formData: {} },
            tts: { formData: {} },
        }
        return {
            settingsFormState: {
                ...state.settingsFormState,
                [tab]: defaults[tab] || {}
            }
        }
    }),

    // Initialize app
    initialize: async () => {
        try {
            const [
                llmConfigs,
                characters,
                worldbooks,
                presets,
                sessions,
                agentConfig,
                imageConfigs
            ] = await Promise.all([
                fetch(`${API_BASE}/config/llm`).then(r => r.json()).catch(() => []),
                fetch(`${API_BASE}/characters`).then(r => r.json()).catch(() => []),
                fetch(`${API_BASE}/worldbooks`).then(r => r.json()).catch(() => []),
                fetch(`${API_BASE}/presets`).then(r => r.json()).catch(() => []),
                fetch(`${API_BASE}/chat/sessions`).then(r => r.json()).catch(() => []),
                fetch(`${API_BASE}/agent/config`).then(r => r.json()).catch(() => ({ enabled: false })),
                fetch(`${API_BASE}/images/configs`).then(r => r.json()).catch(() => []),
            ])

            const activeLLM = llmConfigs.find(c => c.is_active) || null

            set({
                llmConfigs,
                activeLLMConfig: activeLLM,
                characters,
                worldbooks,
                presets,
                sessions,
                agentConfig,
                imageConfigs,
                isLoading: false,
            })
        } catch (error) {
            console.error('Failed to initialize:', error)
            set({ isLoading: false })
        }
    },

    // Set settings tab
    setSettingsTab: (tab) => set({ settingsTab: tab }),

    // LLM Config actions
    addLLMConfig: async (config) => {
        const res = await fetch(`${API_BASE}/config/llm`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config),
        })
        const newConfig = await res.json()
        set(state => ({ llmConfigs: [...state.llmConfigs, newConfig] }))
        return newConfig
    },

    setActiveLLMConfig: async (configId) => {
        await fetch(`${API_BASE}/config/llm/${configId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_active: true }),
        })
        set(state => ({
            activeLLMConfig: state.llmConfigs.find(c => c.id === configId),
            llmConfigs: state.llmConfigs.map(c => ({
                ...c,
                is_active: c.id === configId,
            })),
        }))
    },

    deleteLLMConfig: async (configId) => {
        await fetch(`${API_BASE}/config/llm/${configId}`, { method: 'DELETE' })
        set(state => ({
            llmConfigs: state.llmConfigs.filter(c => c.id !== configId),
            activeLLMConfig: state.activeLLMConfig?.id === configId ? null : state.activeLLMConfig,
        }))
    },

    updateLLMConfig: async (configId, updates) => {
        const res = await fetch(`${API_BASE}/config/llm/${configId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates),
        })
        if (!res.ok) throw new Error('Failed to update config')
        const updated = await res.json()
        set(state => ({
            llmConfigs: state.llmConfigs.map(c => c.id === configId ? updated : c),
            activeLLMConfig: state.activeLLMConfig?.id === configId ? updated : state.activeLLMConfig,
        }))
        return updated
    },


    // Character actions
    setActiveCharacter: async (character) => {
        set({ activeCharacter: character })

        // Load bound worldbook if exists
        if (character?.extensions?.worldbook_id) {
            const wb = get().worldbooks.find(w => w.id === character.extensions.worldbook_id)
            if (wb) set({ activeWorldbooks: [wb] })
        }

        // Find most recent session for this character
        const { sessions } = get()
        const charSession = sessions
            .filter(s => s.character_id === character?.id)
            .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))[0]

        if (charSession) {
            await get().loadSession(charSession.id)
        } else if (character) {
            // No existing session - create one with first message
            await get().createSession()
        }
    },

    // Session actions
    createSession: async () => {
        const { activeCharacter, activeWorldbooks, activePreset } = get()

        const res = await fetch(`${API_BASE}/chat/sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                character_id: activeCharacter?.id,
                worldbook_ids: activeWorldbooks.map(wb => wb.id),
                preset_id: activePreset?.id,
            }),
        })
        const session = await res.json()

        // Add first message if character has one
        let messages = []
        if (activeCharacter?.data?.first_mes) {
            messages = [{
                id: 'first-mes',
                role: 'assistant',
                content: activeCharacter.data.first_mes
                    .replace(/\{\{user\}\}/g, 'User')
                    .replace(/\{\{char\}\}/g, activeCharacter.data.name),
                timestamp: new Date().toISOString(),
            }]
        }

        set(state => ({
            sessions: [...state.sessions, session],
            activeSession: session,
            messages,
            sessionImages: [],
        }))

        return session
    },

    loadSession: async (sessionId) => {
        const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}`)
        const session = await res.json()

        // Extract images from messages
        const images = session.messages
            .filter(m => m.image_url)
            .map(m => ({ url: m.image_url, messageId: m.id }))

        set({
            activeSession: session,
            messages: session.messages || [],
            sessionImages: images,
        })
    },

    deleteSession: async (sessionId) => {
        await fetch(`${API_BASE}/chat/sessions/${sessionId}`, { method: 'DELETE' })
        set(state => ({
            sessions: state.sessions.filter(s => s.id !== sessionId),
            activeSession: state.activeSession?.id === sessionId ? null : state.activeSession,
            messages: state.activeSession?.id === sessionId ? [] : state.messages,
        }))
    },

    // Send message
    sendMessage: async (content) => {
        const { activeSession, agentConfig, messages } = get()

        if (!activeSession) {
            // Create new session first
            await get().createSession()
        }

        const session = get().activeSession

        // Add user message optimistically
        const userMsg = {
            id: `temp-${Date.now()}`,
            role: 'user',
            content,
            timestamp: new Date().toISOString(),
        }

        set(state => ({
            messages: [...state.messages, userMsg],
            isStreaming: true,
        }))

        // Use agent pipeline or regular chat
        const endpoint = agentConfig.enabled
            ? `${API_BASE}/agent/generate`
            : `${API_BASE}/chat/sessions/${session.id}/messages`

        let assistantContent = ''
        let assistantMsgId = `assistant-${Date.now()}`

        // Add empty assistant message
        set(state => ({
            messages: [...state.messages, {
                id: assistantMsgId,
                role: 'assistant',
                content: '',
                timestamp: new Date().toISOString(),
            }],
        }))

        try {
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content,
                    session_id: session.id,
                    character_id: get().activeCharacter?.id,
                    worldbook_ids: get().activeWorldbooks.map(wb => wb.id),
                }),
            })

            if (!res.ok) {
                throw new Error(`Request failed: ${res.status} ${res.statusText}`)
            }

            const reader = res.body.getReader()
            const decoder = new TextDecoder()
            let buffer = '' // Buffer for partial lines

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                // Decode and add to buffer
                buffer += decoder.decode(value, { stream: true })

                // Process complete lines only
                const lines = buffer.split('\n')
                // Keep the last (possibly incomplete) line in buffer
                buffer = lines.pop() || ''

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue
                    const data = line.slice(6).trim()
                    if (data === '[DONE]' || !data) continue

                    try {
                        const event = JSON.parse(data)

                        // Handle specific event types first
                        if (event.stage) {
                            set({ agentStage: event.stage })

                            // Open popups for director and paint_director stages
                            if (event.stage === 'director') {
                                set({ showDirectorPopup: true, directorOutput: '' })
                            }
                            if (event.stage === 'paint_director') {
                                set({ showPaintDirectorPopup: true, paintDirectorOutput: '' })
                            }
                        }

                        // Director streaming chunks - accumulate in popup
                        if (event.type === 'director_chunk' && event.content) {
                            set(state => ({ directorOutput: state.directorOutput + event.content }))
                            continue  // Don't process further
                        }

                        // Director outline complete - final content (kept for backwards compatibility)
                        if (event.type === 'outline') {
                            // Outline is already accumulated via director_chunk, but set final state
                            if (event.content) {
                                set({ directorOutput: event.content })
                            }
                            continue  // Don't process as chat content
                        }

                        // Paint director streaming chunks - accumulate in popup
                        if (event.type === 'paint_chunk' && event.content) {
                            set(state => ({ paintDirectorOutput: state.paintDirectorOutput + event.content }))
                            continue  // Don't process further
                        }

                        // Paint director complete - final image prompt and URL
                        if (event.type === 'image' && event.prompt) {
                            set({ paintDirectorOutput: event.prompt })
                        }

                        // Writer content - this goes to chat
                        if (event.type === 'content' && event.content) {
                            assistantContent += event.content
                            set(state => ({
                                messages: state.messages.map(m =>
                                    m.id === assistantMsgId
                                        ? { ...m, content: assistantContent }
                                        : m
                                ),
                            }))
                        }

                        // Image event from paint director
                        if (event.type === 'image' && event.url) {
                            set(state => ({
                                sessionImages: [...state.sessionImages, { url: event.url, messageId: assistantMsgId }],
                                messages: state.messages.map(m =>
                                    m.id === assistantMsgId
                                        ? { ...m, image_url: event.url }
                                        : m
                                ),
                            }))
                        }

                        // Regex processed content event - update message with processed version
                        if (event.type === 'processed_content' && event.content) {
                            set(state => ({
                                messages: state.messages.map(m =>
                                    m.id === assistantMsgId
                                        ? { ...m, content: event.content }
                                        : m
                                ),
                            }))
                        }

                        if (event.message_id && event.message_id !== assistantMsgId) {
                            // Update the message ID in state to match server's ID
                            const oldId = assistantMsgId
                            assistantMsgId = event.message_id
                            set(state => ({
                                messages: state.messages.map(m =>
                                    m.id === oldId
                                        ? { ...m, id: assistantMsgId }
                                        : m
                                ),
                            }))
                        }

                        if (event.done) {
                            // Update with processed content if available (regex processing)
                            if (event.processed_content) {
                                set(state => ({
                                    messages: state.messages.map(m =>
                                        m.id === assistantMsgId
                                            ? { ...m, content: event.processed_content }
                                            : m
                                    ),
                                    isStreaming: false,
                                    agentStage: null,
                                }))
                            } else {
                                set({ isStreaming: false, agentStage: null })
                            }
                        }

                        if (event.error) {
                            // Show error in the assistant message
                            set(state => ({
                                messages: state.messages.map(m =>
                                    m.id === assistantMsgId
                                        ? { ...m, content: `⚠️ Error: ${event.error}`, isError: true }
                                        : m
                                ),
                                isStreaming: false,
                                agentStage: null,
                            }))
                        }
                    } catch (e) {
                        // Ignore parse errors for incomplete JSON
                    }
                }
            }
        } catch (error) {
            // Show network/fetch errors in the UI
            set(state => ({
                messages: state.messages.map(m =>
                    m.id === assistantMsgId
                        ? { ...m, content: `⚠️ Error: ${error.message}`, isError: true }
                        : m
                ),
                isStreaming: false,
                agentStage: null,
            }))
        }

        set({ isStreaming: false, agentStage: null })
    },

    // Stop streaming
    stopStreaming: () => {
        set({ isStreaming: false, agentStage: null })
    },

    // Popup controls
    setShowDirectorPopup: (show) => set({ showDirectorPopup: show }),
    setShowPaintDirectorPopup: (show) => set({ showPaintDirectorPopup: show }),

    // Regenerate last assistant message
    regenerateMessage: async (messageId) => {
        const { activeSession, messages } = get()
        if (!activeSession || !messageId) return

        // Find message index
        const msgIndex = messages.findIndex(m => m.id === messageId)
        if (msgIndex === -1) return

        set({ isStreaming: true })

        try {
            const res = await fetch(`${API_BASE}/chat/sessions/${activeSession.id}/regenerate/${messageId}`, {
                method: 'POST',
            })

            if (!res.ok) throw new Error('Regeneration failed')

            const reader = res.body.getReader()
            const decoder = new TextDecoder()

            let newContent = ''
            let newMsgId = `regen-${Date.now()}`

            // Replace the old message with an empty one
            set(state => ({
                messages: state.messages.map((m, i) =>
                    i === msgIndex ? { ...m, id: newMsgId, content: '' } : m
                ).slice(0, msgIndex + 1) // Remove any messages after
            }))

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                const text = decoder.decode(value)
                const lines = text.split('\n')

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue
                    const data = line.slice(6)
                    if (data === '[DONE]') continue

                    try {
                        const event = JSON.parse(data)

                        if (event.content) {
                            newContent += event.content
                            set(state => ({
                                messages: state.messages.map(m =>
                                    m.id === newMsgId ? { ...m, content: newContent } : m
                                )
                            }))
                        }

                        if (event.message_id) {
                            newMsgId = event.message_id
                        }

                        if (event.done) {
                            set({ isStreaming: false })
                        }

                        if (event.error) {
                            set(state => ({
                                messages: state.messages.map(m =>
                                    m.id === newMsgId
                                        ? { ...m, content: `⚠️ Error: ${event.error}`, isError: true }
                                        : m
                                ),
                                isStreaming: false,
                            }))
                        }
                    } catch (e) {
                        // Ignore parse errors
                    }
                }
            }
        } catch (error) {
            set(state => ({
                messages: state.messages.map((m, i) =>
                    i === msgIndex
                        ? { ...m, content: `⚠️ Error: ${error.message}`, isError: true }
                        : m
                ),
                isStreaming: false,
            }))
        }

        set({ isStreaming: false })
    },

    // Agent mode
    toggleAgentMode: async () => {
        const res = await fetch(`${API_BASE}/agent/toggle`, { method: 'PUT' })
        const { enabled } = await res.json()
        set(state => ({
            agentConfig: { ...state.agentConfig, enabled },
        }))
    },

    // Update agent config
    updateAgentConfig: async (config) => {
        const res = await fetch(`${API_BASE}/agent/config`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config),
        })
        if (res.ok) {
            const updated = await res.json()
            set({ agentConfig: updated })
        }
    },

    // Preset actions
    setActivePreset: (preset) => set({ activePreset: preset }),

    // Worldbook actions - toggle worldbook in active list
    toggleActiveWorldbook: (worldbook) => set(state => {
        const exists = state.activeWorldbooks.find(wb => wb.id === worldbook.id)
        if (exists) {
            return { activeWorldbooks: state.activeWorldbooks.filter(wb => wb.id !== worldbook.id) }
        } else {
            return { activeWorldbooks: [...state.activeWorldbooks, worldbook] }
        }
    }),
    setActiveWorldbooks: (worldbooks) => set({ activeWorldbooks: worldbooks }),
}))
