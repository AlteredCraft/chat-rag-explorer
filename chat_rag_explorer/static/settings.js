document.addEventListener('DOMContentLoaded', () => {
    const modelSelect = document.getElementById('model-select');
    const loadingIndicator = document.getElementById('loading-indicator');
    const modelDetails = document.getElementById('model-details');

    const STORAGE_KEY = 'chat-rag-selected-model';
    const DEFAULT_MODEL = 'openai/gpt-3.5-turbo';

    let modelsData = [];

    // Load models on page load
    loadModels();

    async function loadModels() {
        loadingIndicator.classList.add('active');

        try {
            const response = await fetch('/api/models');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            modelsData = data.data || [];

            populateModelSelect(modelsData);
            restoreSelectedModel();

        } catch (error) {
            console.error('Failed to load models:', error);
            modelSelect.innerHTML = '<option value="">Failed to load models</option>';
        } finally {
            loadingIndicator.classList.remove('active');
            modelSelect.disabled = false;
        }
    }

    function populateModelSelect(models) {
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
        if (savedModel && modelSelect.querySelector(`option[value="${savedModel}"]`)) {
            modelSelect.value = savedModel;
        } else {
            // Try to select default model
            if (modelSelect.querySelector(`option[value="${DEFAULT_MODEL}"]`)) {
                modelSelect.value = DEFAULT_MODEL;
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
        if (selectedModel) {
            localStorage.setItem(STORAGE_KEY, selectedModel);
            updateModelDetails();
        }
    });
});
