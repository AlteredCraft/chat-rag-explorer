/**
 * Frontend Logger Utility
 * Provides structured logging with session tracking for debugging
 */
const AppLogger = {
    sessionId: localStorage.getItem('chat-rag-session-id') || (() => {
        const id = 'sess_' + Math.random().toString(36).substring(2, 10);
        localStorage.setItem('chat-rag-session-id', id);
        return id;
    })(),

    _format(level, message, data) {
        const timestamp = new Date().toISOString();
        const prefix = `[${timestamp}] [${this.sessionId}] ${level.toUpperCase()}:`;
        return { prefix, message, data };
    },

    debug(message, data = null) {
        const { prefix, message: msg, data: d } = this._format('debug', message, data);
        if (d) console.debug(prefix, msg, d);
        else console.debug(prefix, msg);
    },

    info(message, data = null) {
        const { prefix, message: msg, data: d } = this._format('info', message, data);
        if (d) console.info(prefix, msg, d);
        else console.info(prefix, msg);
    },

    warn(message, data = null) {
        const { prefix, message: msg, data: d } = this._format('warn', message, data);
        if (d) console.warn(prefix, msg, d);
        else console.warn(prefix, msg);
    },

    error(message, data = null) {
        const { prefix, message: msg, data: d } = this._format('error', message, data);
        if (d) console.error(prefix, msg, d);
        else console.error(prefix, msg);
    }
};

document.addEventListener('DOMContentLoaded', () => {
    AppLogger.info('Chat application initializing');

    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatHistory = document.getElementById('chat-history');
    const submitButton = chatForm.querySelector('button');
    // Settings link navigates directly (chat is preserved in sessionStorage)

    // API key status tracking
    let apiKeyConfigured = true; // Assume configured until we check
    const apiKeyBanner = document.getElementById('api-key-banner');
    const bannerDismiss = document.getElementById('banner-dismiss');

    /**
     * Check if the OpenRouter API key is configured and update UI accordingly.
     */
    async function checkApiKeyStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();

            apiKeyConfigured = data.api_key_configured;
            AppLogger.info('API key status checked', { configured: apiKeyConfigured });

            updateApiKeyUI();
        } catch (error) {
            AppLogger.error('Failed to check API key status', { error: error.message });
            // On error, assume it's configured to avoid blocking the user
            apiKeyConfigured = true;
            updateApiKeyUI();
        }
    }

    /**
     * Update UI elements based on API key configuration status.
     */
    function updateApiKeyUI() {
        if (!apiKeyConfigured) {
            // Show warning banner
            if (apiKeyBanner) {
                apiKeyBanner.style.display = 'block';
            }

            // Disable chat input
            messageInput.disabled = true;
            messageInput.classList.add('input-disabled');
            messageInput.placeholder = 'API key required - see banner above';
            submitButton.disabled = true;

            AppLogger.info('UI updated: API key not configured');
        } else {
            // Hide warning banner
            if (apiKeyBanner) {
                apiKeyBanner.style.display = 'none';
            }

            // Enable chat input (unless already disabled for other reasons)
            messageInput.classList.remove('input-disabled');
            messageInput.placeholder = 'Type your message...';
            // Note: Don't enable buttons here as they may be disabled during message send

            AppLogger.info('UI updated: API key configured');
        }
    }

    // Handle banner dismiss button
    if (bannerDismiss) {
        bannerDismiss.addEventListener('click', () => {
            if (apiKeyBanner) {
                apiKeyBanner.style.display = 'none';
            }
        });
    }

    // Check API key status on load
    checkApiKeyStatus();

    // Clear chat button
    const clearChatBtn = document.getElementById('clear-chat-btn');
    if (clearChatBtn) {
        clearChatBtn.addEventListener('click', () => {
            clearChat();
        });
    }

    function clearChat() {
        AppLogger.info('Clearing chat');

        // Clear UI
        chatHistory.innerHTML = '';

        // Reset conversation history (use current system prompt)
        conversationHistory = [
            { role: 'system', content: currentSystemPrompt }
        ];

        // Reset session metrics
        sessionMetrics = {
            prompt_tokens: 0,
            completion_tokens: 0,
            total_tokens: 0
        };

        // Clear sessionStorage
        clearConversationSession();

        // Update metrics display
        document.getElementById('metric-prompt-tokens').textContent = '0';
        document.getElementById('metric-completion-tokens').textContent = '0';
        document.getElementById('metric-total-tokens').textContent = '0';
        document.getElementById('total-prompt-tokens').textContent = '0';
        document.getElementById('total-completion-tokens').textContent = '0';
        document.getElementById('total-total-tokens').textContent = '0';

        messageInput.focus();
    }

    const STORAGE_KEY = 'chat-rag-selected-model';
    const DEFAULT_MODEL = 'openai/gpt-3.5-turbo';

    // Prompt selection constants
    const PROMPT_STORAGE_KEY = 'chat-rag-selected-prompt';
    const DEFAULT_PROMPT = 'default_system_prompt';
    let currentSystemPrompt = 'You are a helpful assistant.'; // Fallback (full prompt loaded from API)

    // RAG toggle state
    const RAG_ENABLED_KEY = 'chat-rag-rag-enabled';
    let ragEnabled = localStorage.getItem(RAG_ENABLED_KEY) === 'true';
    let ragConfigured = false; // Updated on load

    // Session persistence keys (survives navigation, clears on tab close)
    const SESSION_HISTORY_KEY = 'chat-rag-conversation-history';
    const SESSION_METRICS_KEY = 'chat-rag-session-metrics';
    const SESSION_METADATA_KEY = 'chat-rag-message-metadata';
    const SESSION_RETRY_MSG_KEY = 'chat-rag-retry-message';

    // Per-message metadata for details modal
    let messageMetadata = {};
    let messageIndex = 0; // Counter for message indices

    // Save conversation to sessionStorage
    function saveConversationToSession() {
        sessionStorage.setItem(SESSION_HISTORY_KEY, JSON.stringify(conversationHistory));
        sessionStorage.setItem(SESSION_METRICS_KEY, JSON.stringify(sessionMetrics));
        sessionStorage.setItem(SESSION_METADATA_KEY, JSON.stringify(messageMetadata));
    }

    // Clear conversation from sessionStorage
    function clearConversationSession() {
        sessionStorage.removeItem(SESSION_HISTORY_KEY);
        sessionStorage.removeItem(SESSION_METRICS_KEY);
        sessionStorage.removeItem(SESSION_METADATA_KEY);
        messageMetadata = {};
        messageIndex = 0;
    }

    // Save metadata for a specific message
    function saveMessageMetadata(index, data) {
        messageMetadata[index] = data;
        sessionStorage.setItem(SESSION_METADATA_KEY, JSON.stringify(messageMetadata));
    }

    // Save retry message (for restoring after navigation on error)
    function saveRetryMessage(message) {
        sessionStorage.setItem(SESSION_RETRY_MSG_KEY, message);
    }

    // Clear retry message (after successful send)
    function clearRetryMessage() {
        sessionStorage.removeItem(SESSION_RETRY_MSG_KEY);
    }

    // Restore retry message if exists
    function restoreRetryMessage() {
        const saved = sessionStorage.getItem(SESSION_RETRY_MSG_KEY);
        if (saved) {
            messageInput.value = saved;
            AppLogger.debug('Restored retry message from session');
        }
    }

    // Restore conversation from sessionStorage and re-render to DOM
    function restoreConversationFromSession() {
        const savedHistory = sessionStorage.getItem(SESSION_HISTORY_KEY);
        const savedMetrics = sessionStorage.getItem(SESSION_METRICS_KEY);
        const savedMetadata = sessionStorage.getItem(SESSION_METADATA_KEY);

        // Restore metadata first
        if (savedMetadata) {
            try {
                messageMetadata = JSON.parse(savedMetadata);

                // Restore "Last Interaction" display from the most recent message's metadata
                const indices = Object.keys(messageMetadata).map(Number);
                if (indices.length > 0) {
                    const lastIndex = Math.max(...indices);
                    const lastMetadata = messageMetadata[lastIndex];
                    if (lastMetadata && lastMetadata.tokens) {
                        document.getElementById('metric-prompt-tokens').textContent = lastMetadata.tokens.prompt_tokens || 0;
                        document.getElementById('metric-completion-tokens').textContent = lastMetadata.tokens.completion_tokens || 0;
                        document.getElementById('metric-total-tokens').textContent = lastMetadata.tokens.total_tokens || 0;
                    }
                }
            } catch (e) {
                AppLogger.error('Failed to restore metadata', { error: e.message });
            }
        }

        // Restore metrics (do this before history since history restoration may return early)
        if (savedMetrics) {
            try {
                sessionMetrics = JSON.parse(savedMetrics);
                // Update metrics display
                document.getElementById('total-prompt-tokens').textContent = sessionMetrics.prompt_tokens;
                document.getElementById('total-completion-tokens').textContent = sessionMetrics.completion_tokens;
                document.getElementById('total-total-tokens').textContent = sessionMetrics.total_tokens;
            } catch (e) {
                AppLogger.error('Failed to restore metrics', { error: e.message });
            }
        }

        if (savedHistory) {
            try {
                conversationHistory = JSON.parse(savedHistory);
                AppLogger.info('Restored conversation from session', { messages: conversationHistory.length });

                // Re-render messages to DOM (skip system message)
                // Use a display counter that matches our messageIndex pattern
                let displayIndex = 0;
                conversationHistory.forEach((msg) => {
                    if (msg.role === 'user') {
                        appendMessage('user', msg.content, displayIndex);
                        displayIndex++;
                    } else if (msg.role === 'assistant') {
                        const contentDiv = appendMessage('bot', '', displayIndex);
                        const html = marked.parse(msg.content);
                        contentDiv.innerHTML = DOMPurify.sanitize(html);

                        // Restore RAG context display if present in metadata
                        const meta = messageMetadata[displayIndex];
                        if (meta && meta.rag && meta.rag.documents_retrieved > 0) {
                            const ragContainer = document.getElementById(`rag-context-${displayIndex}`);
                            if (ragContainer) {
                                ragContainer.innerHTML = renderRagContext(meta.rag);
                            }
                        }

                        displayIndex++;
                    }
                    // Skip system messages in UI (don't increment displayIndex)
                });

                // Update message index counter to continue from where we left off
                messageIndex = displayIndex;

                return true; // Restored
            } catch (e) {
                AppLogger.error('Failed to restore conversation', { error: e.message });
            }
        }

        return false; // Nothing to restore
    }

    // Parameter controls
    const temperatureSlider = document.getElementById('temperature-slider');
    const temperatureValue = document.getElementById('temperature-value');
    const temperatureControl = document.getElementById('temperature-control');
    const temperatureHint = document.getElementById('temperature-hint');
    const topPSlider = document.getElementById('top-p-slider');
    const topPValue = document.getElementById('top-p-value');
    const topPControl = document.getElementById('top-p-control');
    const topPHint = document.getElementById('top-p-hint');

    // Track supported parameters for current model
    let supportedParams = [];

    // Get model from localStorage or use default
    function getCurrentModel() {
        const model = localStorage.getItem(STORAGE_KEY) || DEFAULT_MODEL;
        return model;
    }

    // Fetch model metadata and update parameter controls
    async function updateParameterControls() {
        const currentModel = getCurrentModel();
        AppLogger.debug('Fetching model metadata for parameter controls', { model: currentModel });

        try {
            const response = await fetch('/api/models');
            const data = await response.json();
            const models = data.data || [];
            const model = models.find(m => m.id === currentModel);

            if (model && model.supported_parameters) {
                supportedParams = model.supported_parameters;
                AppLogger.debug('Model supported parameters', { params: supportedParams });
            } else {
                supportedParams = [];
                AppLogger.debug('No supported parameters found for model');
            }

            // Update temperature control
            const tempSupported = supportedParams.includes('temperature');
            if (tempSupported) {
                temperatureControl.classList.remove('disabled');
                temperatureSlider.disabled = false;
                temperatureHint.textContent = '';
            } else {
                temperatureControl.classList.add('disabled');
                temperatureSlider.disabled = true;
                temperatureHint.textContent = 'Not supported by this model';
            }

            // Update top_p control
            const topPSupported = supportedParams.includes('top_p');
            if (topPSupported) {
                topPControl.classList.remove('disabled');
                topPSlider.disabled = false;
                topPHint.textContent = '';
            } else {
                topPControl.classList.add('disabled');
                topPSlider.disabled = true;
                topPHint.textContent = 'Not supported by this model';
            }
        } catch (error) {
            AppLogger.error('Failed to fetch model metadata', { error: error.message });
        }
    }

    // Update slider value displays
    temperatureSlider.addEventListener('input', () => {
        temperatureValue.textContent = parseFloat(temperatureSlider.value).toFixed(1);
    });

    topPSlider.addEventListener('input', () => {
        topPValue.textContent = parseFloat(topPSlider.value).toFixed(2);
    });

    // Listen for model changes from settings page
    window.addEventListener('storage', (e) => {
        if (e.key === STORAGE_KEY) {
            AppLogger.info('Model changed via storage event', { newModel: e.newValue });
            document.getElementById('metric-model').textContent = e.newValue || DEFAULT_MODEL;
            updateParameterControls();
        }
        if (e.key === PROMPT_STORAGE_KEY) {
            AppLogger.info('Prompt changed via storage event', { newPrompt: e.newValue });
            loadSystemPrompt();
        }
    });

    // ==================== RAG Toggle ====================

    const ragEnabledToggle = document.getElementById('rag-enabled-toggle');
    const ragStatus = document.getElementById('rag-status');

    /**
     * Check if RAG is configured (collection selected) and update toggle state.
     */
    async function checkRagStatus() {
        try {
            const response = await fetch('/api/rag/config');
            const data = await response.json();
            const config = data.data;

            ragConfigured = config.collection && config.collection.length > 0;

            if (ragConfigured) {
                ragStatus.textContent = config.collection;
                ragStatus.classList.remove('not-configured');
                ragStatus.classList.add('configured');
                ragEnabledToggle.disabled = false;
                ragEnabledToggle.checked = ragEnabled;
            } else {
                ragStatus.textContent = 'Not configured';
                ragStatus.classList.remove('configured');
                ragStatus.classList.add('not-configured');
                ragEnabledToggle.disabled = true;
                ragEnabledToggle.checked = false;
                ragEnabled = false;
            }

            AppLogger.info('RAG status checked', {
                configured: ragConfigured,
                collection: config.collection,
                enabled: ragEnabled
            });
        } catch (error) {
            AppLogger.error('Failed to check RAG status', { error: error.message });
            ragStatus.textContent = 'Error';
            ragEnabledToggle.disabled = true;
        }
    }

    // Handle RAG toggle changes
    if (ragEnabledToggle) {
        ragEnabledToggle.addEventListener('change', () => {
            ragEnabled = ragEnabledToggle.checked;
            localStorage.setItem(RAG_ENABLED_KEY, ragEnabled.toString());
            AppLogger.info('RAG toggle changed', { enabled: ragEnabled });
        });
    }

    // Check RAG status on load
    checkRagStatus();

    // Display current model on load
    const currentModel = getCurrentModel();
    document.getElementById('metric-model').textContent = currentModel;
    AppLogger.info('Current model loaded', { model: currentModel });

    // Initialize parameter controls
    updateParameterControls();

    // Session-wide metrics
    let sessionMetrics = {
        prompt_tokens: 0,
        completion_tokens: 0,
        total_tokens: 0
    };

    // Conversation history (initialized after loading system prompt)
    let conversationHistory = [];

    // Load system prompt from API
    async function loadSystemPrompt(skipHistoryReset = false) {
        const promptId = localStorage.getItem(PROMPT_STORAGE_KEY) || DEFAULT_PROMPT;
        AppLogger.info('Loading system prompt', { promptId });

        try {
            const response = await fetch(`/api/prompts/${promptId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            if (data.data && data.data.content) {
                currentSystemPrompt = data.data.content;
                AppLogger.info('System prompt loaded', {
                    promptId,
                    contentLength: currentSystemPrompt.length
                });
            }
        } catch (error) {
            AppLogger.warn('Failed to load system prompt, using default', { error: error.message });
            currentSystemPrompt = 'You are a helpful assistant.';
        }

        // Initialize or reset conversation with loaded prompt (skip if restoring session)
        if (!skipHistoryReset) {
            conversationHistory = [
                { role: 'system', content: currentSystemPrompt }
            ];
        }
    }

    // Try to restore session first, otherwise load fresh
    const restoredFromSession = restoreConversationFromSession();
    loadSystemPrompt(restoredFromSession); // Skip history reset if we restored

    // Restore any pending draft message (from navigation or error)
    restoreRetryMessage();

    // Save draft message when navigating away
    window.addEventListener('beforeunload', () => {
        const draft = messageInput.value.trim();
        if (draft) {
            saveRetryMessage(draft);
        } else {
            clearRetryMessage();
        }
    });

    // Configure marked for better chat-style breaks
    marked.setOptions({
        breaks: true,
        gfm: true
    });

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Don't send if API key is not configured
        if (!apiKeyConfigured) {
            AppLogger.warn('Cannot send message: API key not configured');
            if (apiKeyBanner) {
                apiKeyBanner.style.display = 'block';
            }
            return;
        }

        const message = messageInput.value.trim();
        if (!message) return;

        // Store original message for potential retry on error
        const originalMessage = message;

        const model = getCurrentModel();
        const requestStartTime = performance.now();

        AppLogger.info('Chat request initiated', {
            model: model,
            messageLength: message.length,
            conversationTurns: conversationHistory.length
        });

        // Clear input
        messageInput.value = '';
        messageInput.disabled = true;
        submitButton.disabled = true;

        // Add user message to history
        conversationHistory.push({ role: 'user', content: message });
        saveConversationToSession();

        // Track message indices
        const userMsgIndex = messageIndex++;
        const assistantMsgIndex = messageIndex++;

        // Add user message UI
        appendMessage('user', message, userMsgIndex);

        // Add empty bot message container
        const botMessageContent = appendMessage('bot', '', assistantMsgIndex);
        let messageBuffer = '';
        let chunkCount = 0;
        let firstChunkTime = null;
        let receivedMetadata = null; // Store full metadata from backend
        let errorOccurred = false;
        let errorChunk = null;

        try {
            // Build request body with optional parameters
            const requestBody = {
                messages: conversationHistory,
                model: model,
                rag_enabled: ragEnabled && ragConfigured
            };

            // Only include parameters if they're supported by the model
            if (supportedParams.includes('temperature')) {
                requestBody.temperature = parseFloat(temperatureSlider.value);
            }
            if (supportedParams.includes('top_p')) {
                requestBody.top_p = parseFloat(topPSlider.value);
            }

            AppLogger.debug('Sending POST /api/chat', {
                contextLength: conversationHistory.length,
                model: model,
                temperature: requestBody.temperature,
                top_p: requestBody.top_p,
                rag_enabled: requestBody.rag_enabled
            });

            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                AppLogger.error('Chat API returned error', { status: response.status });
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            AppLogger.debug('Stream started, processing chunks');

            // Handle streaming response
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                chunkCount++;

                // Track time to first chunk
                if (firstChunkTime === null && chunk.length > 0) {
                    firstChunkTime = performance.now();
                    const ttfc = firstChunkTime - requestStartTime;
                    AppLogger.debug('Time to first chunk', { ttfc_ms: ttfc.toFixed(2) });
                }

                // Check for error chunks from backend
                if (chunk.startsWith('Error:')) {
                    errorOccurred = true;
                    errorChunk = chunk;
                    AppLogger.error('Received error chunk from backend', { chunk });
                    continue; // Don't render error in chat
                }

                // Check for metadata marker (full entry from backend)
                if (chunk.startsWith('__METADATA__:')) {
                    try {
                        const metadataJson = chunk.replace('__METADATA__:', '');
                        receivedMetadata = JSON.parse(metadataJson);
                        AppLogger.info('Metadata received from backend', receivedMetadata);

                        // Update metrics display (only for successful responses)
                        if (receivedMetadata.tokens && !errorOccurred) {
                            updateMetrics({
                                model: receivedMetadata.model,
                                prompt_tokens: receivedMetadata.tokens.prompt_tokens,
                                completion_tokens: receivedMetadata.tokens.completion_tokens,
                                total_tokens: receivedMetadata.tokens.total_tokens
                            });
                        }
                    } catch (parseError) {
                        AppLogger.error('Failed to parse metadata', { error: parseError.message, chunk: chunk });
                    }
                    continue; // Don't render metadata in chat
                }

                messageBuffer += chunk;

                // Parse markdown and sanitize
                const html = marked.parse(messageBuffer);
                botMessageContent.innerHTML = DOMPurify.sanitize(html);

                // Auto-scroll to bottom
                chatHistory.scrollTop = chatHistory.scrollHeight;
            }

            const totalTime = performance.now() - requestStartTime;

            // Handle streaming error
            if (errorOccurred) {
                AppLogger.error('Chat streaming error detected', {
                    chunks: chunkCount,
                    totalTime_ms: totalTime.toFixed(2),
                    errorChunk: errorChunk
                });

                // Remove both user and bot messages from DOM
                const botMessage = botMessageContent.closest('.message');
                if (botMessage) {
                    const userMessage = botMessage.previousElementSibling;
                    if (userMessage && userMessage.classList.contains('message-user')) {
                        userMessage.remove();
                    }
                    botMessage.remove();
                }

                // Remove user message from conversation history
                conversationHistory.pop();
                saveConversationToSession();

                // Decrement message indices (both messages removed)
                messageIndex -= 2;

                // Restore original message to input for retry (persist for navigation)
                messageInput.value = originalMessage;
                saveRetryMessage(originalMessage);

                // Show error modal with details
                const cleanError = errorChunk.replace(/^Error:\s*/, '');
                showErrorModal(cleanError, receivedMetadata);
            } else {
                AppLogger.info('Chat response completed', {
                    chunks: chunkCount,
                    responseLength: messageBuffer.length,
                    totalTime_ms: totalTime.toFixed(2)
                });

                // Clear any pending retry message on success
                clearRetryMessage();

                // Add bot message to history
                if (messageBuffer) {
                    conversationHistory.push({ role: 'assistant', content: messageBuffer });
                    saveConversationToSession();

                    // Save assistant metadata (received from backend - DRY with chat-history.jsonl)
                    if (receivedMetadata) {
                        saveMessageMetadata(assistantMsgIndex, receivedMetadata);

                        // Display RAG context if present
                        if (receivedMetadata.rag && receivedMetadata.rag.documents_retrieved > 0) {
                            updateMessageRagContext(assistantMsgIndex, receivedMetadata.rag);
                        }
                    }
                }
            }

        } catch (error) {
            const totalTime = performance.now() - requestStartTime;
            AppLogger.error('Chat request failed', {
                error: error.message,
                totalTime_ms: totalTime.toFixed(2),
                chunksReceived: chunkCount
            });

            // Remove both user and bot messages from DOM
            const botMessage = botMessageContent.closest('.message');
            if (botMessage) {
                const userMessage = botMessage.previousElementSibling;
                if (userMessage && userMessage.classList.contains('message-user')) {
                    userMessage.remove();
                }
                botMessage.remove();
            }

            // Remove user message from conversation history
            conversationHistory.pop();
            saveConversationToSession();

            // Decrement message indices (both messages removed)
            messageIndex -= 2;

            // Restore original message to input for retry (persist for navigation)
            messageInput.value = originalMessage;
            saveRetryMessage(originalMessage);

            // Show error modal
            showErrorModal(error.message, {
                type: 'NetworkError',
                model: model,
                timing: {
                    total_ms: parseFloat(totalTime.toFixed(2))
                },
                chunksReceived: chunkCount
            });
        } finally {
            messageInput.disabled = false;
            submitButton.disabled = false;
            messageInput.focus();
        }
    });

    function updateMetrics(data) {
        AppLogger.debug('Updating metrics display', data);

        // Update Last Interaction
        if (data.model) document.getElementById('metric-model').textContent = data.model;
        if (data.prompt_tokens) document.getElementById('metric-prompt-tokens').textContent = data.prompt_tokens;
        if (data.completion_tokens) document.getElementById('metric-completion-tokens').textContent = data.completion_tokens;
        if (data.total_tokens) document.getElementById('metric-total-tokens').textContent = data.total_tokens;

        // Update Session Totals
        if (data.prompt_tokens) sessionMetrics.prompt_tokens += data.prompt_tokens;
        if (data.completion_tokens) sessionMetrics.completion_tokens += data.completion_tokens;
        if (data.total_tokens) sessionMetrics.total_tokens += data.total_tokens;

        document.getElementById('total-prompt-tokens').textContent = sessionMetrics.prompt_tokens;
        document.getElementById('total-completion-tokens').textContent = sessionMetrics.completion_tokens;
        document.getElementById('total-total-tokens').textContent = sessionMetrics.total_tokens;

        AppLogger.info('Session metrics updated', {
            sessionTotals: { ...sessionMetrics }
        });
    }

    function appendMessage(role, text, msgIndex = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        // Store message index for details lookup
        if (msgIndex !== null) {
            messageDiv.dataset.msgIndex = msgIndex;
        }

        // Add RAG context container for bot messages (populated after response)
        if (role === 'bot' && msgIndex !== null) {
            const ragContainer = document.createElement('div');
            ragContainer.className = 'rag-context-container';
            ragContainer.id = `rag-context-${msgIndex}`;
            messageDiv.appendChild(ragContainer);
        }

        const contentDiv = document.createElement('div');
        contentDiv.className = 'content';

        if (role === 'user') {
            contentDiv.textContent = text;
        } else {
            // For bot, show spinner if empty, otherwise parse markdown
            if (!text) {
                contentDiv.innerHTML = '<span class="typing-spinner"></span>';
            } else {
                const html = marked.parse(text);
                contentDiv.innerHTML = DOMPurify.sanitize(html);
            }
        }

        messageDiv.appendChild(contentDiv);

        // Add details link for assistant messages (they have the full context)
        if (role === 'bot' && msgIndex !== null) {
            const detailsLink = document.createElement('span');
            detailsLink.className = 'message-details-link';
            detailsLink.textContent = 'view details';
            detailsLink.dataset.msgIndex = msgIndex;
            detailsLink.addEventListener('click', () => showDetailsModal(msgIndex));
            messageDiv.appendChild(detailsLink);
        }

        chatHistory.appendChild(messageDiv);

        // Scroll to bottom
        chatHistory.scrollTop = chatHistory.scrollHeight;

        return contentDiv; // Return content div so we can append to it
    }

    // ==================== Details Modal ====================

    const detailsModal = document.getElementById('details-modal');
    const detailsContent = document.getElementById('details-content');
    const detailsModalClose = document.getElementById('details-modal-close');
    const detailsModalMaximize = document.getElementById('details-modal-maximize');
    const detailsModalInner = detailsModal ? detailsModal.querySelector('.details-modal') : null;

    if (detailsModalClose) {
        detailsModalClose.addEventListener('click', () => {
            detailsModal.classList.remove('visible');
            if (detailsModalInner) {
                detailsModalInner.classList.remove('maximized');
            }
        });
    }

    if (detailsModalMaximize && detailsModalInner) {
        detailsModalMaximize.addEventListener('click', () => {
            detailsModalInner.classList.toggle('maximized');
        });
    }

    if (detailsModal) {
        detailsModal.addEventListener('click', (e) => {
            if (e.target === detailsModal) {
                detailsModal.classList.remove('visible');
                if (detailsModalInner) {
                    detailsModalInner.classList.remove('maximized');
                }
            }
        });
    }

    // ==================== Error Modal ====================

    const errorModal = document.getElementById('error-modal');
    const errorMessage = document.getElementById('error-message');
    const errorDetails = document.getElementById('error-details');
    const errorDetailsContainer = document.getElementById('error-details-container');
    const errorModalClose = document.getElementById('error-modal-close');

    if (errorModalClose) {
        errorModalClose.addEventListener('click', () => {
            errorModal.classList.remove('visible');
        });
    }

    if (errorModal) {
        errorModal.addEventListener('click', (e) => {
            if (e.target === errorModal) {
                errorModal.classList.remove('visible');
            }
        });
    }

    /**
     * Extract user-friendly message from error string.
     * Tries to find 'message': '...' pattern in Python dict or JSON.
     * @param {string} errorStr - Raw error string
     * @returns {string} Extracted message or original string
     */
    function extractErrorMessage(errorStr) {
        // Try to extract 'message': '...' from Python dict syntax
        const singleQuoteMatch = errorStr.match(/'message':\s*'([^']+)'/);
        if (singleQuoteMatch) {
            return singleQuoteMatch[1];
        }

        // Try to extract "message": "..." from JSON syntax
        const doubleQuoteMatch = errorStr.match(/"message":\s*"([^"]+)"/);
        if (doubleQuoteMatch) {
            return doubleQuoteMatch[1];
        }

        // Return original if no match
        return errorStr;
    }

    /**
     * Display an error in a modal dialog.
     * @param {string} rawError - The raw error string from backend
     * @param {Object|null} metadata - Optional metadata object from backend
     */
    function showErrorModal(rawError, metadata = null) {
        AppLogger.error('Showing error modal', { rawError, hasMetadata: !!metadata });

        // Extract user-friendly message for display
        const friendlyMessage = extractErrorMessage(rawError);
        errorMessage.textContent = friendlyMessage;

        // Build details section with raw error and metadata
        let detailsText = rawError;
        if (metadata) {
            detailsText += '\n\nMETADATA:\n' + JSON.stringify(metadata, null, 2);
        }
        errorDetails.textContent = detailsText;
        errorDetailsContainer.style.display = 'block';

        errorModal.classList.add('visible');
    }

    function showDetailsModal(msgIndex) {
        const metadata = messageMetadata[msgIndex];
        if (!metadata) {
            AppLogger.warn('No metadata found for message', { msgIndex });
            return;
        }

        AppLogger.info('Showing details modal', { msgIndex, metadata });

        // Build the modal content
        let html = '';

        // Meta info section
        html += '<div class="details-meta">';
        html += `<div class="details-meta-item"><span class="details-meta-label">Model:</span><span class="details-meta-value">${escapeHtml(metadata.model || 'Unknown')}</span></div>`;

        if (metadata.params) {
            if (metadata.params.temperature !== undefined) {
                html += `<div class="details-meta-item"><span class="details-meta-label">Temperature:</span><span class="details-meta-value">${metadata.params.temperature}</span></div>`;
            }
            if (metadata.params.top_p !== undefined) {
                html += `<div class="details-meta-item"><span class="details-meta-label">Top P:</span><span class="details-meta-value">${metadata.params.top_p}</span></div>`;
            }
        }

        if (metadata.tokens) {
            html += `<div class="details-meta-item"><span class="details-meta-label">Tokens:</span><span class="details-meta-value">${metadata.tokens.prompt_tokens || 0} + ${metadata.tokens.completion_tokens || 0} → ${metadata.tokens.total_tokens || 0}</span></div>`;
        }

        if (metadata.timing) {
            const totalSec = (metadata.timing.total_ms / 1000).toFixed(2);
            const ttfcSec = metadata.timing.ttfc_ms ? (metadata.timing.ttfc_ms / 1000).toFixed(2) : '-';
            html += `<div class="details-meta-item"><span class="details-meta-label">Time:</span><span class="details-meta-value">${totalSec}s (TTFC: ${ttfcSec}s)</span></div>`;
        }
        html += '</div>';

        // RAG Documents section (if RAG was used)
        if (metadata.rag && metadata.rag.documents && metadata.rag.documents.length > 0) {
            const docCount = metadata.rag.documents.length;
            const collectionName = metadata.rag.collection || 'Unknown';
            html += '<div class="details-section">';
            html += `<div class="details-section-header">Retrieved Documents <span class="msg-count">(${docCount} from ${escapeHtml(collectionName)})</span></div>`;

            metadata.rag.documents.forEach((doc, i) => {
                const meta = metadata.rag.metadatas && metadata.rag.metadatas[i] ? metadata.rag.metadatas[i] : {};
                const distance = metadata.rag.distances && metadata.rag.distances[i] !== undefined
                    ? metadata.rag.distances[i].toFixed(4)
                    : null;

                html += '<div class="details-rag-document">';

                // Document header with metadata
                html += '<div class="details-rag-header">';
                html += `<span class="details-rag-index">#${i + 1}</span>`;
                if (meta.title) {
                    html += `<span class="details-rag-title">${escapeHtml(meta.title)}</span>`;
                }
                if (distance !== null) {
                    html += `<span class="details-rag-distance">dist: ${distance}</span>`;
                }
                html += '</div>';

                // Metadata fields (if any exist)
                const metaFields = [];
                if (meta.section_title) metaFields.push(`Section: ${meta.section_title}`);
                if (meta.section_number) metaFields.push(`#${meta.section_number}`);
                if (meta.author) metaFields.push(`Author: ${meta.author}`);
                if (meta.url) metaFields.push(`<a href="${escapeHtml(meta.url)}" target="_blank" rel="noopener">Source</a>`);

                if (metaFields.length > 0) {
                    html += `<div class="details-rag-meta">${metaFields.join(' · ')}</div>`;
                }

                // Document content (truncated preview)
                const preview = doc.length > 300 ? doc.substring(0, 300) + '...' : doc;
                html += `<div class="details-rag-content">${escapeHtml(preview)}</div>`;
                html += '</div>';
            });

            html += '</div>';
        }

        // Prompt section (messages array from backend)
        if (metadata.messages && metadata.messages.length > 0) {
            const msgCount = metadata.messages.length;
            html += '<div class="details-section">';
            html += `<div class="details-section-header">Prompt sent to LLM <span class="msg-count">(${msgCount} messages)</span></div>`;

            // Find system message, previous context, and current user message
            const systemMsg = metadata.messages.find(m => m.role === 'system');
            const previousContext = metadata.messages.filter((m, i) =>
                m.role !== 'system' && i < metadata.messages.length - 1
            );
            const currentUserMsg = metadata.messages.length > 1 ?
                metadata.messages[metadata.messages.length - 1] : null;

            // System message (always expanded)
            if (systemMsg) {
                html += '<div class="details-message system">';
                html += '<div class="details-message-header">System</div>';
                html += `<div class="details-message-content">${escapeHtml(systemMsg.content)}</div>`;
                html += '</div>';
            }

            // Previous context (collapsed if exists)
            if (previousContext.length > 0) {
                const exchangeCount = Math.floor(previousContext.length / 2);
                const previews = previousContext.slice(0, 4).map(m =>
                    `${m.role}: "${truncate(m.content, 40)}"`
                ).join(' · ');

                html += `<div class="details-context-toggle" onclick="togglePreviousContext(this)">`;
                html += `<span class="toggle-icon">▶</span>`;
                html += `<div class="details-context-summary">`;
                html += `<strong>Previous context (${exchangeCount} exchange${exchangeCount > 1 ? 's' : ''})</strong>`;
                html += `<span class="exchange-preview">${escapeHtml(previews)}</span>`;
                html += `</div>`;
                html += `</div>`;

                html += '<div class="details-context-content">';
                previousContext.forEach(msg => {
                    const roleClass = msg.role === 'user' ? 'user' : 'assistant';
                    html += `<div class="details-message ${roleClass}">`;
                    html += `<div class="details-message-header">${msg.role}</div>`;
                    html += `<div class="details-message-content">${escapeHtml(msg.content)}</div>`;
                    html += '</div>';
                });
                html += '</div>';
            }

            // Current user message (always expanded)
            if (currentUserMsg && currentUserMsg.role === 'user') {
                html += '<div class="details-message user">';
                html += '<div class="details-message-header">User (current)</div>';
                html += `<div class="details-message-content">${escapeHtml(currentUserMsg.content)}</div>`;
                html += '</div>';
            }

            html += '</div>';
        }

        // Response section
        if (metadata.response) {
            html += '<div class="details-section">';
            html += '<div class="details-section-header">Response from LLM</div>';
            html += '<div class="details-message assistant">';
            html += '<div class="details-message-header">Assistant</div>';
            html += `<div class="details-message-content">${escapeHtml(metadata.response)}</div>`;
            html += '</div>';
            html += '</div>';
        }

        detailsContent.innerHTML = html;
        detailsModal.classList.add('visible');
    }

    // Helper to escape HTML
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Helper to truncate text
    function truncate(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    // Global function to toggle previous context (called from onclick)
    window.togglePreviousContext = function(element) {
        element.classList.toggle('expanded');
        const content = element.nextElementSibling;
        if (content) {
            content.classList.toggle('expanded');
        }
    };

    // ==================== RAG Context Display ====================

    /**
     * Render RAG context as a simple label.
     * Full document content is visible in "View Details" modal.
     * @param {Object} ragData - RAG metadata from response
     * @returns {string} HTML string for the RAG context label
     */
    function renderRagContext(ragData) {
        if (!ragData || !ragData.documents || ragData.documents.length === 0) {
            return '';
        }

        const docCount = ragData.documents.length;
        const collection = escapeHtml(ragData.collection || 'knowledge base');

        return `<div class="rag-context-label">Retrieved ${docCount} document(s) from <strong>${collection}</strong></div>`;
    }

    /**
     * Update the RAG context container for a message.
     * @param {number} msgIndex - Message index
     * @param {Object} ragData - RAG metadata
     */
    function updateMessageRagContext(msgIndex, ragData) {
        const container = document.getElementById(`rag-context-${msgIndex}`);
        if (container && ragData && ragData.documents_retrieved > 0) {
            container.innerHTML = renderRagContext(ragData);
            AppLogger.debug('RAG context displayed', {
                msgIndex,
                documents: ragData.documents_retrieved
            });
        }
    }

    AppLogger.info('Chat application initialized successfully', {
        sessionId: AppLogger.sessionId,
        model: getCurrentModel()
    });
});
