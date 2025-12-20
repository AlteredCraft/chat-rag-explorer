document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatHistory = document.getElementById('chat-history');
    const submitButton = chatForm.querySelector('button');

    // Default model - could be made selectable in UI
    const currentModel = "openai/gpt-3.5-turbo";

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

        // Add user message
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
                    message: message,
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
                messageBuffer += chunk;
                
                // Parse markdown and sanitize
                const html = marked.parse(messageBuffer);
                botMessageContent.innerHTML = DOMPurify.sanitize(html);
                
                // Auto-scroll to bottom
                chatHistory.scrollTop = chatHistory.scrollHeight;
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
