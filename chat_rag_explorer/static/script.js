document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatHistory = document.getElementById('chat-history');
    const submitButton = chatForm.querySelector('button');

    // Default model - could be made selectable in UI
    const currentModel = "openai/gpt-3.5-turbo";

    // Session-wide metrics
    let sessionMetrics = {
        prompt_tokens: 0,
        completion_tokens: 0,
        total_tokens: 0
    };

    // Conversation history
    let conversationHistory = [
        { role: 'system', content: 'You are a helpful assistant.' }
    ];

    // Configure marked for better chat-style breaks
    marked.setOptions({
        breaks: true,
        gfm: true
    });

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (!message) return;

        // Clear input
        messageInput.value = '';
        messageInput.disabled = true;
        submitButton.disabled = true;

        // Add user message to history
        conversationHistory.push({ role: 'user', content: message });

        // Add user message UI
        appendMessage('user', message);

        // Add empty bot message container
        const botMessageContent = appendMessage('bot', '');
        let messageBuffer = '';

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    messages: conversationHistory,
                    model: currentModel
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Handle streaming response
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                
                // Check for metadata marker
                if (chunk.startsWith('__METADATA__:')) {
                    try {
                        const metadataJson = chunk.replace('__METADATA__:', '');
                        const usageData = JSON.parse(metadataJson);
                        updateMetrics(usageData);
                    } catch (e) {
                        console.error('Failed to parse metadata', e);
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

            // Add bot message to history
            if (messageBuffer) {
                conversationHistory.push({ role: 'assistant', content: messageBuffer });
            }

        } catch (error) {
            console.error('Error:', error);
            botMessageContent.innerHTML += ` <span style="color: red;">[Error: ${error.message}]</span>`;
        } finally {
            messageInput.disabled = false;
            submitButton.disabled = false;
            messageInput.focus();
        }
    });

    function updateMetrics(data) {
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
    }

    function appendMessage(role, text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'content';
        
        if (role === 'user') {
            contentDiv.textContent = text;
        } else {
            // For bot, if there's initial text, parse it as markdown
            const html = marked.parse(text || '');
            contentDiv.innerHTML = DOMPurify.sanitize(html);
        }
        
        messageDiv.appendChild(contentDiv);
        chatHistory.appendChild(messageDiv);
        
        // Scroll to bottom
        chatHistory.scrollTop = chatHistory.scrollHeight;

        return contentDiv; // Return content div so we can append to it
    }
});
