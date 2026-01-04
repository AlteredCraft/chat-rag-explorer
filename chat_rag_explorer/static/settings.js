/**
 * Frontend Logger Utility (shared with script.js pattern)
 * Provides structured logging with session tracking for debugging
 */
const SettingsLogger = {
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
    SettingsLogger.info('Settings page initializing');

    // Tab navigation
    const TAB_STORAGE_KEY = 'chat-rag-settings-tab';
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');

    function switchTab(tabId) {
        tabButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });
        tabPanels.forEach(panel => {
            panel.classList.toggle('active', panel.dataset.panel === tabId);
        });
        localStorage.setItem(TAB_STORAGE_KEY, tabId);
        SettingsLogger.debug('Tab switched', { tab: tabId });
    }

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Restore last active tab
    const savedTab = localStorage.getItem(TAB_STORAGE_KEY);
    if (savedTab && document.querySelector(`[data-tab="${savedTab}"]`)) {
        switchTab(savedTab);
    }

    const modelSelect = document.getElementById('model-select');
    const loadingIndicator = document.getElementById('loading-indicator');
    const modelDetails = document.getElementById('model-details');
    const freeOnlyFilter = document.getElementById('free-only-filter');

    const STORAGE_KEY = 'chat-rag-selected-model';
    const FILTER_STORAGE_KEY = 'chat-rag-free-filter';
    const DEFAULT_MODEL = 'openai/gpt-3.5-turbo';

    // Prompt editor elements and constants
    const PROMPT_STORAGE_KEY = 'chat-rag-selected-prompt';
    const DEFAULT_PROMPT = 'default_system_prompt';
    const promptSelect = document.getElementById('prompt-select');
    const promptLoadingIndicator = document.getElementById('prompt-loading-indicator');
    const promptTitleInput = document.getElementById('prompt-title');
    const promptDescInput = document.getElementById('prompt-description');
    const promptContentInput = document.getElementById('prompt-content');
    const newPromptBtn = document.getElementById('new-prompt-btn');
    const deletePromptBtn = document.getElementById('delete-prompt-btn');
    const savePromptBtn = document.getElementById('save-prompt-btn');
    const deleteModal = document.getElementById('delete-modal');
    const deleteModalCancel = document.getElementById('delete-modal-cancel');
    const deleteModalOk = document.getElementById('delete-modal-ok');

    let isCreatingNew = false;
    let originalPromptData = null;

    function isFreeModel(model) {
        const pricing = model.pricing || {};
        const promptPrice = parseFloat(pricing.prompt) || 0;
        const completionPrice = parseFloat(pricing.completion) || 0;
        return promptPrice === 0 && completionPrice === 0;
    }

    let modelsData = [];
    let promptsData = [];

    // Restore filter state and load models
    freeOnlyFilter.checked = localStorage.getItem(FILTER_STORAGE_KEY) === 'true';
    loadModels();
    loadPrompts();

    async function loadModels() {
        SettingsLogger.info('Loading models from API');
        const startTime = performance.now();
        loadingIndicator.classList.add('active');

        try {
            const response = await fetch('/api/models');
            if (!response.ok) {
                SettingsLogger.error('Models API returned error', { status: response.status });
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            modelsData = data.data || [];

            const elapsed = performance.now() - startTime;
            SettingsLogger.info('Models loaded successfully', {
                count: modelsData.length,
                loadTime_ms: elapsed.toFixed(2)
            });

            populateModelSelect(modelsData);
            restoreSelectedModel();

        } catch (error) {
            const elapsed = performance.now() - startTime;
            SettingsLogger.error('Failed to load models', {
                error: error.message,
                loadTime_ms: elapsed.toFixed(2)
            });
            modelSelect.innerHTML = '<option value="">Failed to load models</option>';
        } finally {
            loadingIndicator.classList.remove('active');
            modelSelect.disabled = false;
        }
    }

    function populateModelSelect(models) {
        SettingsLogger.debug('Populating model select dropdown');
        modelSelect.innerHTML = '';

        // Apply free filter if enabled
        const showFreeOnly = freeOnlyFilter.checked;
        const filteredModels = showFreeOnly ? models.filter(isFreeModel) : models;

        if (filteredModels.length === 0) {
            modelSelect.innerHTML = '<option value="">No models match filter</option>';
            return;
        }

        // Group models by provider
        const grouped = {};
        filteredModels.forEach(model => {
            const provider = model.id.split('/')[0] || 'Other';
            if (!grouped[provider]) {
                grouped[provider] = [];
            }
            grouped[provider].push(model);
        });

        // Sort providers alphabetically
        const sortedProviders = Object.keys(grouped).sort();

        sortedProviders.forEach(provider => {
            const optgroup = document.createElement('optgroup');
            optgroup.label = formatProviderName(provider);

            grouped[provider].forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = model.name || model.id;
                option.dataset.contextLength = model.context_length || 0;
                option.dataset.pricing = JSON.stringify(model.pricing || {});
                optgroup.appendChild(option);
            });

            modelSelect.appendChild(optgroup);
        });

        SettingsLogger.debug('Model select populated', {
            providers: sortedProviders.length,
            totalModels: filteredModels.length,
            filtered: showFreeOnly
        });
    }

    function formatProviderName(provider) {
        // Capitalize and clean up provider names
        const nameMap = {
            'openai': 'OpenAI',
            'anthropic': 'Anthropic',
            'google': 'Google',
            'meta-llama': 'Meta Llama',
            'mistralai': 'Mistral AI',
            'cohere': 'Cohere',
            'deepseek': 'DeepSeek',
            'qwen': 'Qwen'
        };
        return nameMap[provider] || provider.charAt(0).toUpperCase() + provider.slice(1);
    }

    function restoreSelectedModel() {
        const savedModel = localStorage.getItem(STORAGE_KEY);
        SettingsLogger.debug('Restoring selected model', { savedModel: savedModel || '(none)' });

        if (savedModel && modelSelect.querySelector(`option[value="${savedModel}"]`)) {
            modelSelect.value = savedModel;
            SettingsLogger.info('Restored previously saved model', { model: savedModel });
        } else {
            // Try to select default model
            if (modelSelect.querySelector(`option[value="${DEFAULT_MODEL}"]`)) {
                modelSelect.value = DEFAULT_MODEL;
                SettingsLogger.info('Using default model (no saved selection)', { model: DEFAULT_MODEL });
            } else {
                SettingsLogger.warn('Default model not available in model list', { defaultModel: DEFAULT_MODEL });
            }
        }
        updateModelDetails();
    }

    function updateModelDetails() {
        const selectedOption = modelSelect.options[modelSelect.selectedIndex];
        if (!selectedOption || !selectedOption.value) {
            modelDetails.classList.remove('visible');
            return;
        }

        const model = modelsData.find(m => m.id === selectedOption.value);
        if (!model) {
            modelDetails.classList.remove('visible');
            return;
        }

        const contextLength = model.context_length || 'N/A';
        const pricing = model.pricing || {};
        const promptPrice = pricing.prompt ? `$${(parseFloat(pricing.prompt) * 1000000).toFixed(2)}/M tokens` : 'N/A';
        const completionPrice = pricing.completion ? `$${(parseFloat(pricing.completion) * 1000000).toFixed(2)}/M tokens` : 'N/A';

        const description = model.description || '';
        const architecture = model.architecture || {};
        const inputModalities = architecture.input_modalities || [];
        const outputModalities = architecture.output_modalities || [];
        const supportedParams = model.supported_parameters || [];

        modelDetails.innerHTML = `
            ${description ? `<div class="detail-row description"><span class="detail-value">${description}</span></div>` : ''}
            <div class="detail-row">
                <span class="detail-label">Model ID:</span>
                <span class="detail-value">${model.id}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Context Length:</span>
                <span class="detail-value">${contextLength.toLocaleString()} tokens</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Prompt Pricing:</span>
                <span class="detail-value">${promptPrice}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Completion Pricing:</span>
                <span class="detail-value">${completionPrice}</span>
            </div>
            ${inputModalities.length ? `<div class="detail-row"><span class="detail-label">Modality-in:</span><div class="tags">${inputModalities.map(m => `<span class="tag">${m}</span>`).join('')}</div></div>` : ''}
            ${outputModalities.length ? `<div class="detail-row"><span class="detail-label">Modality-out:</span><div class="tags">${outputModalities.map(m => `<span class="tag">${m}</span>`).join('')}</div></div>` : ''}
            ${supportedParams.length ? `<div class="detail-row"><span class="detail-label">Parameters:</span><div class="tags">${supportedParams.map(p => `<span class="tag">${p}</span>`).join('')}</div></div>` : ''}
        `;
        modelDetails.classList.add('visible');
    }

    modelSelect.addEventListener('change', () => {
        const selectedModel = modelSelect.value;
        const previousModel = localStorage.getItem(STORAGE_KEY);

        if (selectedModel) {
            localStorage.setItem(STORAGE_KEY, selectedModel);
            SettingsLogger.info('Model selection changed', {
                previousModel: previousModel || '(none)',
                newModel: selectedModel
            });
            updateModelDetails();
        }
    });

    freeOnlyFilter.addEventListener('change', () => {
        localStorage.setItem(FILTER_STORAGE_KEY, freeOnlyFilter.checked);
        SettingsLogger.info('Free filter toggled', { enabled: freeOnlyFilter.checked });
        populateModelSelect(modelsData);
        restoreSelectedModel();
    });

    // ===== Prompt Editor Functions =====

    async function loadPrompts() {
        SettingsLogger.info('Loading prompts from API');
        const startTime = performance.now();
        promptLoadingIndicator.classList.add('active');

        try {
            const response = await fetch('/api/prompts');
            if (!response.ok) {
                SettingsLogger.error('Prompts API returned error', { status: response.status });
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            promptsData = data.data || [];

            const elapsed = performance.now() - startTime;
            SettingsLogger.info('Prompts loaded successfully', {
                count: promptsData.length,
                loadTime_ms: elapsed.toFixed(2)
            });

            populatePromptSelect(promptsData);
            restoreSelectedPrompt();
            updateDeleteButtonState();

        } catch (error) {
            const elapsed = performance.now() - startTime;
            SettingsLogger.error('Failed to load prompts', {
                error: error.message,
                loadTime_ms: elapsed.toFixed(2)
            });
            promptSelect.innerHTML = '<option value="">Failed to load prompts</option>';
        } finally {
            promptLoadingIndicator.classList.remove('active');
            promptSelect.disabled = false;
        }
    }

    function populatePromptSelect(prompts) {
        SettingsLogger.debug('Populating prompt select dropdown');
        promptSelect.innerHTML = '';

        if (prompts.length === 0) {
            promptSelect.innerHTML = '<option value="">No prompts available</option>';
            return;
        }

        prompts.forEach(prompt => {
            const option = document.createElement('option');
            option.value = prompt.id;
            option.textContent = prompt.title || prompt.id;
            promptSelect.appendChild(option);
        });

        SettingsLogger.debug('Prompt select populated', { totalPrompts: prompts.length });
    }

    function restoreSelectedPrompt() {
        const savedPrompt = localStorage.getItem(PROMPT_STORAGE_KEY);
        SettingsLogger.debug('Restoring selected prompt', { savedPrompt: savedPrompt || '(none)' });

        if (savedPrompt && promptSelect.querySelector(`option[value="${savedPrompt}"]`)) {
            promptSelect.value = savedPrompt;
            SettingsLogger.info('Restored previously saved prompt', { prompt: savedPrompt });
        } else if (promptSelect.querySelector(`option[value="${DEFAULT_PROMPT}"]`)) {
            promptSelect.value = DEFAULT_PROMPT;
            localStorage.setItem(PROMPT_STORAGE_KEY, DEFAULT_PROMPT);
            SettingsLogger.info('Using default prompt (no saved selection)', { prompt: DEFAULT_PROMPT });
        }
        loadPromptIntoForm();
    }

    function loadPromptIntoForm() {
        const selectedPrompt = promptsData.find(p => p.id === promptSelect.value);
        if (!selectedPrompt) {
            clearForm();
            return;
        }

        isCreatingNew = false;
        originalPromptData = { ...selectedPrompt };
        promptTitleInput.value = selectedPrompt.title || '';
        promptDescInput.value = selectedPrompt.description || '';
        promptContentInput.value = selectedPrompt.content || '';

        // Disable form fields for protected prompts
        const isProtected = selectedPrompt.protected === true;
        promptTitleInput.disabled = isProtected;
        promptDescInput.disabled = isProtected;
        promptContentInput.disabled = isProtected;

        updateSaveButtonState();
        updateDeleteButtonState();
    }

    function clearForm() {
        promptTitleInput.value = '';
        promptDescInput.value = '';
        promptContentInput.value = '';
        promptTitleInput.disabled = false;
        promptDescInput.disabled = false;
        promptContentInput.disabled = false;
        originalPromptData = null;
        updateSaveButtonState();
    }

    function updateDeleteButtonState() {
        // Disable delete if creating new or prompt is protected
        const selectedPrompt = promptsData.find(p => p.id === promptSelect.value);
        const isProtected = selectedPrompt?.protected === true;
        deletePromptBtn.disabled = isCreatingNew || isProtected;
    }

    function updateSaveButtonState() {
        if (isCreatingNew) {
            // For new prompts, enable save if title is filled
            savePromptBtn.disabled = !promptTitleInput.value.trim();
        } else if (originalPromptData) {
            // Protected prompts cannot be saved
            if (originalPromptData.protected) {
                savePromptBtn.disabled = true;
                return;
            }
            // For existing prompts, enable save if anything changed
            const hasChanges =
                promptTitleInput.value !== originalPromptData.title ||
                promptDescInput.value !== (originalPromptData.description || '') ||
                promptContentInput.value !== (originalPromptData.content || '');
            savePromptBtn.disabled = !hasChanges || !promptTitleInput.value.trim();
        } else {
            savePromptBtn.disabled = true;
        }
    }

    function generatePromptId(title) {
        return title.toLowerCase()
            .replace(/[^a-z0-9\s]/g, '')
            .replace(/\s+/g, '_')
            .substring(0, 50);
    }

    async function savePrompt() {
        const title = promptTitleInput.value.trim();
        const description = promptDescInput.value.trim();
        const content = promptContentInput.value.trim();

        if (!title) {
            SettingsLogger.warn('Save failed: title is required');
            return;
        }

        savePromptBtn.disabled = true;
        savePromptBtn.textContent = 'Saving...';

        try {
            let response;
            let promptId;

            if (isCreatingNew) {
                promptId = generatePromptId(title);
                SettingsLogger.info('Creating new prompt', { id: promptId });
                response = await fetch('/api/prompts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: promptId, title, description, content })
                });
            } else {
                promptId = promptSelect.value;
                SettingsLogger.info('Updating prompt', { id: promptId });
                response = await fetch(`/api/prompts/${promptId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, description, content })
                });
            }

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to save prompt');
            }

            SettingsLogger.info('Prompt saved successfully', { id: promptId });

            // Reload prompts and select the saved one
            await loadPrompts();
            promptSelect.value = promptId;
            localStorage.setItem(PROMPT_STORAGE_KEY, promptId);
            loadPromptIntoForm();

        } catch (error) {
            SettingsLogger.error('Failed to save prompt', { error: error.message });
            alert('Failed to save: ' + error.message);
        } finally {
            savePromptBtn.textContent = 'Save Changes';
            updateSaveButtonState();
        }
    }

    function startNewPrompt() {
        isCreatingNew = true;
        promptSelect.value = '';
        clearForm();
        promptTitleInput.focus();
        updateDeleteButtonState();
        SettingsLogger.info('Starting new prompt creation');
    }

    function showDeleteModal() {
        deleteModal.classList.add('visible');
    }

    function hideDeleteModal() {
        deleteModal.classList.remove('visible');
    }

    async function deletePrompt() {
        const promptId = promptSelect.value;
        if (!promptId || promptsData.length <= 1) return;

        hideDeleteModal();
        SettingsLogger.info('Deleting prompt', { id: promptId });

        try {
            const response = await fetch(`/api/prompts/${promptId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to delete prompt');
            }

            SettingsLogger.info('Prompt deleted successfully', { id: promptId });

            // Clear from localStorage if it was selected
            if (localStorage.getItem(PROMPT_STORAGE_KEY) === promptId) {
                localStorage.removeItem(PROMPT_STORAGE_KEY);
            }

            // Reload prompts
            await loadPrompts();

        } catch (error) {
            SettingsLogger.error('Failed to delete prompt', { error: error.message });
            alert('Failed to delete: ' + error.message);
        }
    }

    // Prompt event listeners
    promptSelect.addEventListener('change', () => {
        const selectedPrompt = promptSelect.value;
        if (selectedPrompt) {
            isCreatingNew = false;
            localStorage.setItem(PROMPT_STORAGE_KEY, selectedPrompt);
            SettingsLogger.info('Prompt selection changed', { prompt: selectedPrompt });
            loadPromptIntoForm();
        }
    });

    promptTitleInput.addEventListener('input', updateSaveButtonState);
    promptDescInput.addEventListener('input', updateSaveButtonState);
    promptContentInput.addEventListener('input', updateSaveButtonState);

    newPromptBtn.addEventListener('click', startNewPrompt);
    savePromptBtn.addEventListener('click', savePrompt);
    deletePromptBtn.addEventListener('click', showDeleteModal);
    deleteModalCancel.addEventListener('click', hideDeleteModal);
    deleteModalOk.addEventListener('click', deletePrompt);

    // ===== RAG Settings Functions =====

    const RAG_CONFIG_KEY = 'chat-rag-rag-config';

    // DOM Elements
    const ragModeRadios = document.querySelectorAll('input[name="rag-mode"]');
    const ragLocalSettings = document.getElementById('rag-local-settings');
    const ragServerSettings = document.getElementById('rag-server-settings');
    const ragCloudSettings = document.getElementById('rag-cloud-settings');
    const ragLocalPath = document.getElementById('rag-local-path');
    const ragPathStatus = document.getElementById('rag-path-status');
    const ragServerHost = document.getElementById('rag-server-host');
    const ragServerPort = document.getElementById('rag-server-port');
    const ragTenantId = document.getElementById('rag-tenant-id');
    const ragDatabase = document.getElementById('rag-database');
    const ragApiKeyStatus = document.getElementById('rag-api-key-status');
    const ragTestBtn = document.getElementById('rag-test-btn');
    const ragSaveBtn = document.getElementById('rag-save-btn');
    const ragTestResult = document.getElementById('rag-test-result');
    const ragCollectionSection = document.getElementById('rag-collection-section');
    const ragCollectionSelect = document.getElementById('rag-collection-select');
    const ragSampleBtn = document.getElementById('rag-sample-btn');
    const ragSampleSection = document.getElementById('rag-sample-section');
    const ragSampleCount = document.getElementById('rag-sample-count');
    const ragSampleRecords = document.getElementById('rag-sample-records');

    let originalRagConfig = null;
    let pathValidateTimeout = null;
    let availableCollections = [];

    function getSelectedRagMode() {
        const selected = document.querySelector('input[name="rag-mode"]:checked');
        return selected ? selected.value : 'local';
    }

    function toggleRagMode() {
        const mode = getSelectedRagMode();
        ragLocalSettings.style.display = mode === 'local' ? 'block' : 'none';
        ragServerSettings.style.display = mode === 'server' ? 'block' : 'none';
        ragCloudSettings.style.display = mode === 'cloud' ? 'block' : 'none';

        // Hide collection section when switching modes (connection needs to be re-tested)
        ragCollectionSection.style.display = 'none';
        ragTestResult.innerHTML = '';

        // Load API key status when switching to cloud mode
        if (mode === 'cloud') {
            loadApiKeyStatus();
        }

        updateRagSaveButtonState();
        SettingsLogger.debug('RAG mode toggled', { mode });
    }

    async function loadRagConfig() {
        SettingsLogger.info('Loading RAG configuration');
        try {
            const response = await fetch('/api/rag/config');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            originalRagConfig = data.data;

            // Populate form
            const modeRadio = document.querySelector(`input[name="rag-mode"][value="${originalRagConfig.mode}"]`);
            if (modeRadio) modeRadio.checked = true;

            ragLocalPath.value = originalRagConfig.local_path || '';
            ragServerHost.value = originalRagConfig.server_host || 'localhost';
            ragServerPort.value = originalRagConfig.server_port || 8000;
            ragTenantId.value = originalRagConfig.cloud_tenant || '';
            ragDatabase.value = originalRagConfig.cloud_database || '';

            toggleRagMode();

            SettingsLogger.info('RAG config loaded', originalRagConfig);
        } catch (error) {
            SettingsLogger.error('Failed to load RAG config', { error: error.message });
        }
    }

    async function loadApiKeyStatus() {
        try {
            const response = await fetch('/api/rag/api-key-status');
            const data = await response.json();

            if (data.configured) {
                ragApiKeyStatus.innerHTML = `
                    <span class="status-ok">Configured</span>
                    <code>${data.masked}</code>
                `;
                ragApiKeyStatus.classList.remove('error');
            } else {
                ragApiKeyStatus.innerHTML = `
                    <span class="status-error">Not configured</span>
                    <span class="field-hint">Add CHROMADB_API_KEY to your .env file</span>
                `;
                ragApiKeyStatus.classList.add('error');
            }
        } catch (error) {
            SettingsLogger.error('Failed to check API key status', { error: error.message });
            ragApiKeyStatus.innerHTML = '<span class="status-error">Error checking status</span>';
        }
    }

    async function validateLocalPath(path) {
        if (!path.trim()) {
            ragPathStatus.innerHTML = '';
            return;
        }

        ragPathStatus.innerHTML = '<span class="validating">Validating...</span>';

        try {
            const response = await fetch('/api/rag/validate-path', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path })
            });

            const data = await response.json();

            if (data.valid) {
                ragPathStatus.innerHTML = `<span class="status-ok">${data.message}</span>`;
            } else {
                ragPathStatus.innerHTML = `<span class="status-error">${data.message}</span>`;
            }
        } catch (error) {
            ragPathStatus.innerHTML = '<span class="status-error">Validation failed</span>';
        }
    }

    async function testRagConnection() {
        ragTestBtn.disabled = true;
        ragTestBtn.textContent = 'Testing...';
        ragTestResult.innerHTML = '<div class="testing">Testing connection...</div>';
        ragCollectionSection.style.display = 'none';

        const config = getCurrentRagConfig();

        try {
            const response = await fetch('/api/rag/test-connection', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });

            const data = await response.json();

            if (data.success) {
                let html = `<div class="test-success">
                    <strong>Connection successful!</strong>
                    <p>${data.message}</p>`;
                if (data.collections && data.collections.length > 0) {
                    html += `<p>Found ${data.collections.length} collection(s)</p>`;
                } else {
                    html += '<p>No collections found (empty database)</p>';
                }
                html += '</div>';
                ragTestResult.innerHTML = html;

                // Populate and show collection selector
                availableCollections = data.collections || [];
                populateCollectionSelect(availableCollections);
                ragCollectionSection.style.display = 'block';
            } else {
                ragTestResult.innerHTML = `
                    <div class="test-error">
                        <strong>Connection failed</strong>
                        <p>${data.message}</p>
                    </div>`;
                ragCollectionSection.style.display = 'none';
            }
        } catch (error) {
            ragTestResult.innerHTML = `
                <div class="test-error">
                    <strong>Test failed</strong>
                    <p>${error.message}</p>
                </div>`;
            ragCollectionSection.style.display = 'none';
        } finally {
            ragTestBtn.disabled = false;
            ragTestBtn.textContent = 'Test Connection';
        }
    }

    function populateCollectionSelect(collections) {
        ragCollectionSelect.innerHTML = '<option value="">Select a collection...</option>';

        collections.forEach(name => {
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            ragCollectionSelect.appendChild(option);
        });

        // Restore previously selected collection if available
        const savedCollection = originalRagConfig?.collection;
        if (savedCollection && collections.includes(savedCollection)) {
            ragCollectionSelect.value = savedCollection;
        }

        SettingsLogger.debug('Collection select populated', { count: collections.length });
    }

    function getCurrentRagConfig() {
        return {
            mode: getSelectedRagMode(),
            local_path: ragLocalPath.value.trim(),
            server_host: ragServerHost.value.trim(),
            server_port: parseInt(ragServerPort.value) || 8000,
            cloud_tenant: ragTenantId.value.trim(),
            cloud_database: ragDatabase.value.trim(),
            collection: ragCollectionSelect.value
        };
    }

    function hasRagConfigChanges() {
        if (!originalRagConfig) return false;
        const current = getCurrentRagConfig();
        return current.mode !== originalRagConfig.mode ||
               current.local_path !== (originalRagConfig.local_path || '') ||
               current.server_host !== (originalRagConfig.server_host || 'localhost') ||
               current.server_port !== (originalRagConfig.server_port || 8000) ||
               current.cloud_tenant !== (originalRagConfig.cloud_tenant || '') ||
               current.cloud_database !== (originalRagConfig.cloud_database || '') ||
               current.collection !== (originalRagConfig.collection || '');
    }

    function validateRagForm() {
        const mode = getSelectedRagMode();
        if (mode === 'local') {
            return ragLocalPath.value.trim().length > 0;
        } else if (mode === 'server') {
            return ragServerHost.value.trim().length > 0 && ragServerPort.value;
        } else if (mode === 'cloud') {
            return ragTenantId.value.trim().length > 0 && ragDatabase.value.trim().length > 0;
        }
        return false;
    }

    function updateRagSaveButtonState() {
        const hasChanges = hasRagConfigChanges();
        const isValid = validateRagForm();
        ragSaveBtn.disabled = !hasChanges || !isValid;
    }

    async function saveRagConfig() {
        ragSaveBtn.disabled = true;
        ragSaveBtn.textContent = 'Saving...';

        const config = getCurrentRagConfig();

        try {
            const response = await fetch('/api/rag/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to save');
            }

            originalRagConfig = config;
            SettingsLogger.info('RAG config saved', config);

            // Clear test result on successful save
            ragTestResult.innerHTML = '';

        } catch (error) {
            SettingsLogger.error('Failed to save RAG config', { error: error.message });
            alert('Failed to save: ' + error.message);
        } finally {
            ragSaveBtn.textContent = 'Save Settings';
            updateRagSaveButtonState();
        }
    }

    // ===== Sample Records Functions =====

    function updateSampleButtonVisibility() {
        const hasCollection = ragCollectionSelect.value !== '';
        ragSampleBtn.style.display = hasCollection ? 'inline-block' : 'none';
        // Hide sample section when collection changes
        if (!hasCollection) {
            ragSampleSection.style.display = 'none';
        }
    }

    async function fetchSampleRecords() {
        const collection = ragCollectionSelect.value;
        if (!collection) return;

        ragSampleBtn.disabled = true;
        ragSampleBtn.textContent = 'Loading...';

        const config = getCurrentRagConfig();

        try {
            const response = await fetch('/api/rag/sample', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...config,
                    collection: collection
                })
            });

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.message || 'Failed to fetch samples');
            }

            renderSampleRecords(result.records);
            ragSampleCount.textContent = `(${result.count})`;
            ragSampleSection.style.display = 'block';

            SettingsLogger.info('Sample records fetched', { collection, count: result.count });
        } catch (error) {
            SettingsLogger.error('Failed to fetch sample records', { error: error.message });
            ragSampleRecords.innerHTML = `<div class="sample-error">Error: ${error.message}</div>`;
            ragSampleCount.textContent = '';
            ragSampleSection.style.display = 'block';
        } finally {
            ragSampleBtn.disabled = false;
            ragSampleBtn.textContent = 'Sample';
        }
    }

    function renderSampleRecords(records) {
        if (!records || records.length === 0) {
            ragSampleRecords.innerHTML = '<div class="sample-empty">No records found in this collection.</div>';
            return;
        }

        const TRUNCATE_LENGTH = 200;

        const html = records.map((record, index) => {
            const doc = record.document || '(no document content)';
            const needsTruncation = doc.length > TRUNCATE_LENGTH;
            const truncatedDoc = needsTruncation ? doc.substring(0, TRUNCATE_LENGTH) + '...' : doc;
            const metadata = record.metadata ? JSON.stringify(record.metadata, null, 2) : null;

            return `
                <div class="sample-record" data-index="${index}">
                    <div class="sample-record-id">${escapeHtml(record.id)}</div>
                    <div class="sample-record-document">
                        <span class="doc-truncated">${escapeHtml(truncatedDoc)}</span>
                        ${needsTruncation ? `<span class="doc-full" style="display: none;">${escapeHtml(doc)}</span>` : ''}
                        ${needsTruncation ? `<button class="doc-toggle" onclick="toggleRecordExpand(this)">[show more]</button>` : ''}
                    </div>
                    ${metadata ? `
                        <details class="sample-record-metadata">
                            <summary>metadata</summary>
                            <pre>${escapeHtml(metadata)}</pre>
                        </details>
                    ` : ''}
                </div>
            `;
        }).join('');

        ragSampleRecords.innerHTML = html;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Global function for onclick handler
    window.toggleRecordExpand = function(btn) {
        const recordDiv = btn.closest('.sample-record-document');
        const truncated = recordDiv.querySelector('.doc-truncated');
        const full = recordDiv.querySelector('.doc-full');

        if (truncated.style.display !== 'none') {
            truncated.style.display = 'none';
            full.style.display = 'inline';
            btn.textContent = '[show less]';
        } else {
            truncated.style.display = 'inline';
            full.style.display = 'none';
            btn.textContent = '[show more]';
        }
    };

    // RAG Event listeners
    ragModeRadios.forEach(radio => {
        radio.addEventListener('change', toggleRagMode);
    });

    function onConnectionParamChange() {
        // Hide collection section when connection parameters change
        ragCollectionSection.style.display = 'none';
        ragSampleSection.style.display = 'none';
        ragSampleBtn.style.display = 'none';
        ragTestResult.innerHTML = '';
        updateRagSaveButtonState();
    }

    ragLocalPath.addEventListener('input', () => {
        onConnectionParamChange();
        // Debounce path validation
        clearTimeout(pathValidateTimeout);
        pathValidateTimeout = setTimeout(() => {
            validateLocalPath(ragLocalPath.value);
        }, 500);
    });

    ragServerHost.addEventListener('input', onConnectionParamChange);
    ragServerPort.addEventListener('input', onConnectionParamChange);
    ragTenantId.addEventListener('input', onConnectionParamChange);
    ragDatabase.addEventListener('input', onConnectionParamChange);
    ragCollectionSelect.addEventListener('change', () => {
        updateRagSaveButtonState();
        updateSampleButtonVisibility();
    });

    ragTestBtn.addEventListener('click', testRagConnection);
    ragSaveBtn.addEventListener('click', saveRagConfig);
    ragSampleBtn.addEventListener('click', fetchSampleRecords);

    // Load RAG config on page load
    loadRagConfig();

    SettingsLogger.info('Settings page initialized successfully');
});
