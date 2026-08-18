document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const chatToggleBtn = document.getElementById('chat-toggle-btn');
    const chatContainer = document.getElementById('chat-container');
    const chatCloseBtn = document.getElementById('chat-close-btn');
    const chatBody = document.getElementById('chat-body');
    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('chat-send-btn');
    const quickReplies = document.querySelectorAll('.quick-reply-btn');
    const preChatForm = document.getElementById('pre-chat-form');
    const userNameInput = document.getElementById('user-name');
    const userPhoneInput = document.getElementById('user-phone');
    const startChatBtn = document.getElementById('start-chat-btn');
    const chatFooter = document.getElementById('chat-footer');

    // State
    let isWaiting = false;

    // Initialize Markdown options
    marked.setOptions({
        breaks: true,
        gfm: true
    });

    // Start Chat after form submit
    startChatBtn.addEventListener('click', async () => {
        const name = userNameInput.value.trim();
        const phone = userPhoneInput.value.trim();

        if (!name || !phone) {
            alert('Mohon isi nama dan nomor telepon Anda.');
            return;
        }

        startChatBtn.disabled = true;
        startChatBtn.textContent = 'Memulai...';

        try {
            const res = await fetch('/api/session/new', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ customer_name: name, customer_phone: phone })
            });
            const data = await res.json();
            
            if (data.session_id) {
                sessionStorage.setItem('nasikotak_session', data.session_id);
            }
            
            showChatUI(name);
        } catch (e) {
            console.error("Gagal membuat session:", e);
            alert('Gagal memulai chat. Silakan coba lagi.');
            startChatBtn.disabled = false;
            startChatBtn.textContent = 'Mulai Chat';
        }
    });

    function showChatUI(customerName) {
        preChatForm.classList.add('hidden');
        chatBody.classList.remove('hidden');
        chatFooter.classList.remove('hidden');
        const qrContainer = document.getElementById('quick-replies');
        if (qrContainer) qrContainer.classList.remove('hidden');

        // Initial greeting
        setTimeout(() => {
            if (chatBody.children.length === 0) {
                const greetingName = customerName ? customerName : 'Kak';
                addMessage(`Halo kak ${greetingName}! 👋 Saya Asisten AI Ayam Bakar Pak D. Ada yang bisa dibantu soal pesanan nasi kotak untuk acara kakak?`, 'bot');
            }
        }, 500);
    }

    // Toggle Chat Widget
    async function toggleChat() {
        chatContainer.classList.toggle('hidden');
        if (!chatContainer.classList.contains('hidden')) {
            chatToggleBtn.classList.add('hidden');
            
            try {
                const res = await fetch('/api/session', {
                    headers: {
                        'X-Session-ID': sessionStorage.getItem('nasikotak_session') || ''
                    }
                });
                const data = await res.json();
                
                if (data.authenticated) {
                    showChatUI(data.user.name);
                    chatInput.focus();
                    scrollToBottom();
                } else {
                    preChatForm.classList.remove('hidden');
                    chatBody.classList.add('hidden');
                    chatFooter.classList.add('hidden');
                }
            } catch (e) {
                console.error("Error checking session:", e);
                preChatForm.classList.remove('hidden');
                chatBody.classList.add('hidden');
                chatFooter.classList.add('hidden');
            }
        } else {
            chatToggleBtn.classList.remove('hidden');
        }
    }

    chatToggleBtn.addEventListener('click', toggleChat);
    chatCloseBtn.addEventListener('click', toggleChat);

    // Auto scroll to bottom
    function scrollToBottom() {
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    // Format Time
    function getCurrentTime() {
        const now = new Date();
        return now.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
    }

    // Add Message to DOM
    function addMessage(content, sender, isMarkdown = false, whatsappLink = null) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message message-${sender}`;

        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';
        
        if (isMarkdown && sender === 'bot') {
            bubbleDiv.innerHTML = marked.parse(content);
        } else {
            // For simple text, replace newlines with <br>
            bubbleDiv.innerHTML = content.replace(/\n/g, '<br>');
        }

        msgDiv.appendChild(bubbleDiv);

        // If bot sends a whatsapp link, append a CTA button
        if (sender === 'bot' && whatsappLink) {
            const btnContainer = document.createElement('div');
            btnContainer.style.marginTop = '10px';
            const waBtn = document.createElement('a');
            waBtn.href = whatsappLink;
            waBtn.target = '_blank';
            waBtn.className = 'action-btn';
            waBtn.innerHTML = '<i class="fab fa-whatsapp"></i> Hubungi Admin';
            btnContainer.appendChild(waBtn);
            bubbleDiv.appendChild(btnContainer);
        }

        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = getCurrentTime();
        msgDiv.appendChild(timeDiv);

        chatBody.appendChild(msgDiv);
        scrollToBottom();
    }

    // Show/Hide Typing Indicator
    function showTyping() {
        isWaiting = true;
        chatSendBtn.disabled = true;
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.id = 'typing-indicator';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.className = 'typing-dot';
            typingDiv.appendChild(dot);
        }
        
        chatBody.appendChild(typingDiv);
        scrollToBottom();
    }

    function removeTyping() {
        isWaiting = false;
        chatSendBtn.disabled = false;
        const typingDiv = document.getElementById('typing-indicator');
        if (typingDiv) {
            typingDiv.remove();
        }
    }

    // Send Message API Call
    async function sendMessage(text) {
        if (!text.trim() || isWaiting) return;

        // Clear input
        chatInput.value = '';
        
        // Add user message to UI
        addMessage(text, 'user');
        
        // Hide quick replies after first message
        const qrContainer = document.getElementById('quick-replies');
        if (qrContainer) qrContainer.style.display = 'none';

        // Show typing
        showTyping();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': sessionStorage.getItem('nasikotak_session') || ''
                },
                body: JSON.stringify({
                    message: text
                })
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            
            // Remove typing and add bot response
            removeTyping();
            addMessage(data.reply, 'bot', true, data.whatsapp_link);

        } catch (error) {
            console.error('Error:', error);
            removeTyping();
            addMessage("Maaf kak, sistem kami sedang sibuk. Bisa dicoba lagi sebentar ya 🙏", 'bot');
        }
    }

    // Event Listeners
    chatSendBtn.addEventListener('click', () => {
        sendMessage(chatInput.value);
    });

    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage(chatInput.value);
        }
    });

    // Quick Replies Listeners
    quickReplies.forEach(btn => {
        btn.addEventListener('click', () => {
            const text = btn.getAttribute('data-text');
            sendMessage(text);
        });
    });
});
