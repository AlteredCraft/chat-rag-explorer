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

    const modelSelect = document.getElementById('model-select');
    const loadingIndicator = document.getElementById('loading-indicator');
    const modelDetails = document.getElementById('model-details');

    const STORAGE_KEY = 'chat-rag-selected-model';
    const DEFAULT_MODEL = 'openai/gpt-3.5-turbo';

    let modelsData = [];

    // Load models on page load
    loadModels();

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

        // Group models by provider
        const grouped = {};
        models.forEach(model => {
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
            totalModels: models.length
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

        modelDetails.innerHTML = `
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

    SettingsLogger.info('Settings page initialized successfully');
});
