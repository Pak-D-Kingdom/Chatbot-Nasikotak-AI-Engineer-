/**
 * Ayam Bakar Pak D - AI Sales Chatbot Embeddable Widget
 * 
 * Penggunaan di WordPress / Website:
 * <script src="https://api-chatbot.domainanda.com/static/widget.js" defer></script>
 */

(function () {
    'use strict';

    // 1. Tentukan API Base URL secara otomatis dari lokasi script dimuat
    let apiBaseUrl = window.AYAMBAKAR_CHATBOT_API_URL || '';
    if (!apiBaseUrl) {
        const currentScript = document.currentScript || (function () {
            const scripts = document.getElementsByTagName('script');
            for (let i = scripts.length - 1; i >= 0; i--) {
                if (scripts[i].src && scripts[i].src.includes('widget.js')) {
                    return scripts[i];
                }
            }
            return null;
        })();

        if (currentScript && currentScript.src) {
            try {
                const url = new URL(currentScript.src);
                apiBaseUrl = `${url.protocol}//${url.host}`;
            } catch (e) {
                apiBaseUrl = window.location.origin;
            }
        } else {
            apiBaseUrl = window.location.origin;
        }
    }

    // 2. Inject External Font & Icons (Outfit & FontAwesome)
    function injectHeadDependencies() {
        if (!document.getElementById('abpd-font-outfit')) {
            const linkOutfit = document.createElement('link');
            linkOutfit.id = 'abpd-font-outfit';
            linkOutfit.rel = 'stylesheet';
            linkOutfit.href = 'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap';
            document.head.appendChild(linkOutfit);
        }

        if (!document.getElementById('abpd-font-awesome')) {
            const linkFA = document.createElement('link');
            linkFA.id = 'abpd-font-awesome';
            linkFA.rel = 'stylesheet';
            linkFA.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css';
            document.head.appendChild(linkFA);
        }
    }

    // 3. Inject Scoped CSS (Khusus untuk Chatbot agar tidak bentrok dengan tema WordPress)
    function injectScopedCSS() {
        if (document.getElementById('abpd-widget-styles')) return;

        const style = document.createElement('style');
        style.id = 'abpd-widget-styles';
        style.textContent = `
            #abpd-widget-root {
                font-family: 'Outfit', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                font-size: 16px;
                color: #2D3748;
                line-height: 1.5;
            }

            #abpd-widget-root * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }

            /* Tombol Floating Toggle */
            #abpd-toggle-btn {
                position: fixed;
                bottom: 25px;
                right: 25px;
                width: 62px;
                height: 62px;
                border-radius: 50%;
                background: linear-gradient(135deg, #FF8A00 0%, #FF5C00 100%);
                color: #ffffff;
                border: none;
                font-size: 26px;
                cursor: pointer;
                box-shadow: 0 10px 25px rgba(255, 107, 0, 0.35);
                z-index: 999998;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.3s ease;
                outline: none;
            }

            #abpd-toggle-btn:hover {
                transform: scale(1.08);
                box-shadow: 0 12px 30px rgba(255, 107, 0, 0.45);
            }

            #abpd-toggle-btn.abpd-hidden {
                display: none !important;
            }

            /* Container Chat Popup */
            #abpd-chat-container {
                position: fixed;
                bottom: 95px;
                right: 25px;
                width: 390px;
                height: 620px;
                max-height: calc(100vh - 110px);
                background: #FFFFFF;
                border-radius: 20px;
                box-shadow: 0 15px 40px rgba(0, 0, 0, 0.16);
                display: flex;
                flex-direction: column;
                z-index: 999999;
                transition: opacity 0.28s ease, transform 0.28s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                transform-origin: bottom right;
                border: 1px solid rgba(0, 0, 0, 0.08);
                overflow: hidden;
            }

            #abpd-chat-container.abpd-hidden {
                opacity: 0;
                pointer-events: none;
                transform: scale(0.85) translateY(40px);
            }

            /* Header */
            .abpd-chat-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 16px 20px;
                background: linear-gradient(135deg, #FF8A00 0%, #FF5C00 100%);
                color: #ffffff;
            }

            .abpd-header-info {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .abpd-avatar {
                position: relative;
            }

            .abpd-avatar img {
                width: 42px;
                height: 42px;
                border-radius: 50%;
                border: 2px solid #ffffff;
                display: block;
            }

            .abpd-online-indicator {
                position: absolute;
                bottom: 1px;
                right: 1px;
                width: 11px;
                height: 11px;
                background-color: #22c55e;
                border-radius: 50%;
                border: 2px solid #ffffff;
            }

            .abpd-header-text h3 {
                font-size: 1.05rem;
                font-weight: 600;
                margin: 0;
                color: #ffffff;
                line-height: 1.2;
            }

            .abpd-header-text p {
                font-size: 0.82rem;
                opacity: 0.92;
                margin: 3px 0 0 0;
                color: #ffffff;
            }

            .abpd-close-btn {
                background: transparent;
                border: none;
                color: #ffffff;
                font-size: 1.3rem;
                cursor: pointer;
                opacity: 0.85;
                padding: 4px;
                transition: opacity 0.2s;
                outline: none;
            }

            .abpd-close-btn:hover {
                opacity: 1;
            }

            /* Pre-Chat Form */
            .abpd-prechat-form {
                flex: 1;
                display: flex;
                flex-direction: column;
                padding: 30px 24px;
                background: #ffffff;
                justify-content: center;
                gap: 18px;
            }

            .abpd-prechat-greeting {
                text-align: center;
                margin-bottom: 8px;
            }

            .abpd-prechat-greeting h4 {
                font-size: 1.35rem;
                color: #FF6B00;
                margin-bottom: 6px;
                font-weight: 700;
            }

            .abpd-prechat-greeting p {
                font-size: 0.9rem;
                color: #718096;
            }

            .abpd-form-group {
                display: flex;
                flex-direction: column;
            }

            .abpd-form-group input {
                padding: 13px 16px;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                font-family: inherit;
                font-size: 0.95rem;
                transition: border-color 0.2s, box-shadow 0.2s;
                outline: none;
                width: 100%;
                background: #fdfdfd;
            }

            .abpd-form-group input:focus {
                border-color: #FF6B00;
                box-shadow: 0 0 0 3px rgba(255, 107, 0, 0.12);
                background: #ffffff;
            }

            .abpd-start-btn {
                background: linear-gradient(135deg, #FF8A00 0%, #FF5C00 100%);
                color: #ffffff;
                border: none;
                padding: 14px;
                border-radius: 12px;
                font-family: inherit;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
                box-shadow: 0 4px 12px rgba(255, 107, 0, 0.25);
                margin-top: 6px;
                outline: none;
            }

            .abpd-start-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(255, 107, 0, 0.35);
            }

            .abpd-start-btn:disabled {
                opacity: 0.65;
                cursor: not-allowed;
                transform: none;
            }

            /* Chat Body */
            .abpd-chat-body {
                flex: 1;
                padding: 18px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 14px;
                background-color: #fafafa;
                scroll-behavior: smooth;
            }

            .abpd-chat-body::-webkit-scrollbar {
                width: 5px;
            }

            .abpd-chat-body::-webkit-scrollbar-thumb {
                background: #CBD5E0;
                border-radius: 10px;
            }

            /* Messages */
            .abpd-msg {
                max-width: 85%;
                display: flex;
                flex-direction: column;
                animation: abpdFadeIn 0.25s ease;
            }

            @keyframes abpdFadeIn {
                from { opacity: 0; transform: translateY(8px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .abpd-msg-bot {
                align-self: flex-start;
            }

            .abpd-msg-user {
                align-self: flex-end;
            }

            .abpd-bubble {
                padding: 12px 16px;
                font-size: 0.93rem;
                line-height: 1.5;
                word-wrap: break-word;
            }

            .abpd-msg-bot .abpd-bubble {
                background-color: #FFFFFF;
                color: #2D3748;
                border-radius: 14px 14px 14px 4px;
                border: 1px solid #edf2f7;
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.04);
            }

            .abpd-msg-user .abpd-bubble {
                background: linear-gradient(135deg, #FF8A00 0%, #FF5C00 100%);
                color: #ffffff;
                border-radius: 14px 14px 4px 14px;
                box-shadow: 0 4px 12px rgba(255, 107, 0, 0.2);
            }

            .abpd-time {
                font-size: 0.68rem;
                color: #A0AEC0;
                margin-top: 4px;
            }

            .abpd-msg-bot .abpd-time { align-self: flex-start; }
            .abpd-msg-user .abpd-time { align-self: flex-end; }

            .abpd-bubble img {
                max-width: 100%;
                height: auto;
                border-radius: 8px;
                margin-top: 8px;
                margin-bottom: 8px;
                display: block;
                box-shadow: 0 2px 6px rgba(0,0,0,0.08);
            }

            /* WhatsApp Action Button */
            .abpd-wa-btn {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background-color: #25D366;
                color: #ffffff !important;
                padding: 10px 16px;
                border-radius: 10px;
                text-decoration: none !important;
                font-weight: 600;
                font-size: 0.88rem;
                margin-top: 10px;
                transition: transform 0.2s, box-shadow 0.2s;
                box-shadow: 0 4px 8px rgba(37, 211, 102, 0.25);
            }

            .abpd-wa-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 14px rgba(37, 211, 102, 0.35);
            }

            /* Suggested Outlets Buttons */
            .abpd-outlets-container {
                margin-top: 10px;
                display: flex;
                flex-direction: column;
                gap: 6px;
            }

            .abpd-outlet-btn {
                background: #ffffff;
                color: #d84315;
                border: 1.5px solid #ffab91;
                padding: 8px 12px;
                border-radius: 8px;
                font-size: 0.84rem;
                font-weight: 500;
                cursor: pointer;
                text-align: left;
                transition: all 0.2s ease;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 2px 4px rgba(0,0,0,0.04);
                outline: none;
            }

            .abpd-outlet-btn:hover {
                background: #fbe9e7;
                border-color: #d84315;
                transform: translateY(-1px);
            }

            .abpd-outlet-btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }

            /* Quick Replies */
            .abpd-quick-replies {
                padding: 8px 16px;
                display: flex;
                gap: 8px;
                overflow-x: auto;
                scrollbar-width: none;
                white-space: nowrap;
                background: #fafafa;
                border-top: 1px solid #edf2f7;
            }

            .abpd-quick-replies::-webkit-scrollbar {
                display: none;
            }

            .abpd-qr-btn {
                background: #ffffff;
                border: 1px solid #FF8A00;
                color: #FF6B00;
                padding: 6px 13px;
                border-radius: 16px;
                font-size: 0.82rem;
                font-family: inherit;
                cursor: pointer;
                transition: all 0.2s;
                flex-shrink: 0;
                outline: none;
            }

            .abpd-qr-btn:hover {
                background: #FF6B00;
                color: #ffffff;
            }

            /* Chat Footer */
            .abpd-chat-footer {
                padding: 14px 18px;
                background: #ffffff;
                border-top: 1px solid #E2E8F0;
            }

            .abpd-input-container {
                display: flex;
                gap: 8px;
                background: #F8F9FA;
                padding: 6px 8px;
                border-radius: 24px;
                border: 1px solid #E2E8F0;
                transition: border-color 0.2s;
            }

            .abpd-input-container:focus-within {
                border-color: #FF6B00;
                background: #ffffff;
            }

            #abpd-input {
                flex: 1;
                border: none;
                background: transparent;
                padding: 8px 12px;
                font-family: inherit;
                font-size: 0.92rem;
                color: #2D3748;
                outline: none;
            }

            .abpd-send-btn {
                background: linear-gradient(135deg, #FF8A00 0%, #FF5C00 100%);
                color: #ffffff;
                border: none;
                width: 38px;
                height: 38px;
                border-radius: 50%;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: transform 0.2s;
                outline: none;
                flex-shrink: 0;
            }

            .abpd-send-btn:hover {
                transform: scale(1.06);
            }

            .abpd-send-btn:disabled {
                background: #CBD5E0;
                cursor: not-allowed;
                transform: none;
            }

            .abpd-branding {
                text-align: center;
                margin-top: 8px;
                font-size: 0.68rem;
                color: #A0AEC0;
            }

            /* Typing Indicator */
            .abpd-typing {
                display: flex;
                gap: 5px;
                padding: 12px 16px;
                background-color: #FFFFFF;
                border-radius: 14px 14px 14px 4px;
                align-self: flex-start;
                margin-bottom: 4px;
                border: 1px solid #edf2f7;
            }

            .abpd-dot {
                width: 6px;
                height: 6px;
                background-color: #A0AEC0;
                border-radius: 50%;
                animation: abpdTyping 1.4s infinite ease-in-out;
            }

            .abpd-dot:nth-child(1) { animation-delay: 0s; }
            .abpd-dot:nth-child(2) { animation-delay: 0.2s; }
            .abpd-dot:nth-child(3) { animation-delay: 0.4s; }

            @keyframes abpdTyping {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-4px); }
            }

            .abpd-hidden {
                display: none !important;
            }

            /* Mobile Responsive */
            @media (max-width: 480px) {
                #abpd-chat-container {
                    width: 100% !important;
                    height: 100% !important;
                    max-height: 100vh !important;
                    bottom: 0 !important;
                    right: 0 !important;
                    border-radius: 0 !important;
                }
                .abpd-chat-footer {
                    padding-bottom: 24px;
                }
            }
        `;
        document.head.appendChild(style);
    }

    // 4. Inject Markup HTML Widget ke dalam Body
    function injectWidgetHTML() {
        if (document.getElementById('abpd-widget-root')) return;

        const root = document.createElement('div');
        root.id = 'abpd-widget-root';
        root.innerHTML = `
            <!-- Tombol Toggle Chat -->
            <button id="abpd-toggle-btn" aria-label="Buka Chat AI Ayam Bakar Pak D">
                <i class="fas fa-comment-dots"></i>
            </button>

            <!-- Container Chat Widget -->
            <div id="abpd-chat-container" class="abpd-hidden">
                <!-- Header -->
                <div class="abpd-chat-header">
                    <div class="abpd-header-info">
                        <div class="abpd-avatar">
                            <img src="https://ui-avatars.com/api/?name=AI&background=FF8A00&color=fff" alt="AI Avatar">
                            <div class="abpd-online-indicator"></div>
                        </div>
                        <div class="abpd-header-text">
                            <h3>AI Sales Assistant</h3>
                            <p>Ayam Bakar Pak D</p>
                        </div>
                    </div>
                    <button id="abpd-close-btn" class="abpd-close-btn" aria-label="Tutup Chat">
                        <i class="fas fa-times"></i>
                    </button>
                </div>

                <!-- Pre-Chat Form -->
                <div id="abpd-prechat" class="abpd-prechat-form">
                    <div class="abpd-prechat-greeting">
                        <h4>Selamat Datang!</h4>
                        <p>Silakan isi data diri Anda untuk memulai pesanan atau bertanya info catering.</p>
                    </div>
                    <div class="abpd-form-group">
                        <input type="text" id="abpd-user-name" placeholder="Nama Anda" required autocomplete="name">
                    </div>
                    <div class="abpd-form-group">
                        <input type="tel" id="abpd-user-phone" placeholder="No. Telepon / WhatsApp" required autocomplete="tel">
                    </div>
                    <button id="abpd-start-btn" class="abpd-start-btn">Mulai Chat</button>
                </div>

                <!-- Chat Body -->
                <div id="abpd-chat-body" class="abpd-chat-body abpd-hidden"></div>

                <!-- Quick Replies -->
                <div id="abpd-quick-replies" class="abpd-quick-replies abpd-hidden">
                    <button class="abpd-qr-btn" data-text="Ada paket catering apa saja?">Lihat Paket</button>
                    <button class="abpd-qr-btn" data-text="Apakah ada promo saat ini?">Promo</button>
                    <button class="abpd-qr-btn" data-text="Saya punya budget 25rb per box">Budget 25rb</button>
                </div>

                <!-- Chat Footer -->
                <div id="abpd-chat-footer" class="abpd-chat-footer abpd-hidden">
                    <div class="abpd-input-container">
                        <input type="text" id="abpd-input" placeholder="Tulis pesan..." autocomplete="off">
                        <button id="abpd-send-btn" class="abpd-send-btn" aria-label="Kirim Pesan">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    </div>
                    <div class="abpd-branding">
                        <span>AI Assistant Ayam Bakar Pak D</span>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(root);
    }

    // 5. Inisialisasi Logika & Event Handler Chatbot
    function initChatLogic() {
        const toggleBtn = document.getElementById('abpd-toggle-btn');
        const container = document.getElementById('abpd-chat-container');
        const closeBtn = document.getElementById('abpd-close-btn');
        const prechatForm = document.getElementById('abpd-prechat');
        const nameInput = document.getElementById('abpd-user-name');
        const phoneInput = document.getElementById('abpd-user-phone');
        const startBtn = document.getElementById('abpd-start-btn');
        const chatBody = document.getElementById('abpd-chat-body');
        const quickReplies = document.getElementById('abpd-quick-replies');
        const chatFooter = document.getElementById('abpd-chat-footer');
        const chatInput = document.getElementById('abpd-input');
        const sendBtn = document.getElementById('abpd-send-btn');

        let isWaiting = false;

        function escapeHtml(str) {
            return str
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function stripMarkdownBold(str) {
            return str.replace(/\*\*(.*?)\*\*/g, '$1');
        }

        function linkify(str) {
            const urlRegex = /(https?:\/\/[^\s<]+)/g;
            return str.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer" style="color: #e65100; font-weight: bold; text-decoration: underline;">$1</a>');
        }

        // Render konten bot (gambar diproses dan otomatis menggunakan apiBaseUrl)
        function renderBotContent(content) {
            content = stripMarkdownBold(content);

            const imageRegex = /!\[([^\]]*)\]\(([^)\s]+)\)/g;
            let lastIndex = 0;
            let html = '';
            let match;

            while ((match = imageRegex.exec(content)) !== null) {
                const textBefore = content.slice(lastIndex, match.index);
                html += linkify(escapeHtml(textBefore)).replace(/\n/g, '<br>');

                const alt = escapeHtml(match[1]);
                let url = escapeHtml(match[2]);

                // Pastikan gambar produk mengarah ke backend FastAPI
                if (url.startsWith('/image') || url.startsWith('/static')) {
                    url = apiBaseUrl + url;
                }

                html += `<img src="${url}" alt="${alt}" loading="lazy">`;
                lastIndex = imageRegex.lastIndex;
            }

            const textAfter = content.slice(lastIndex);
            html += linkify(escapeHtml(textAfter)).replace(/\n/g, '<br>');
            return html;
        }

        function scrollToBottom() {
            chatBody.scrollTop = chatBody.scrollHeight;
        }

        function getCurrentTime() {
            const now = new Date();
            return now.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
        }

        function showChatUI(customerName) {
            prechatForm.classList.add('abpd-hidden');
            chatBody.classList.remove('abpd-hidden');
            chatFooter.classList.remove('abpd-hidden');
            if (quickReplies) quickReplies.classList.remove('abpd-hidden');

            setTimeout(() => {
                if (chatBody.children.length === 0) {
                    const greetingName = customerName ? customerName : 'Kak';
                    addMessage(`Halo kak ${greetingName}! 👋 Saya Asisten AI Ayam Bakar Pak D. Ada yang bisa dibantu soal pesanan catering untuk acara kakak?`, 'bot');
                }
            }, 400);
        }

        async function toggleChat() {
            container.classList.toggle('abpd-hidden');
            if (!container.classList.contains('abpd-hidden')) {
                toggleBtn.classList.add('abpd-hidden');

                const sessionId = sessionStorage.getItem('nasikotak_session') || '';
                if (!sessionId) {
                    prechatForm.classList.remove('abpd-hidden');
                    chatBody.classList.add('abpd-hidden');
                    chatFooter.classList.add('abpd-hidden');
                    return;
                }

                try {
                    const res = await fetch(`${apiBaseUrl}/api/session`, {
                        headers: { 'X-Session-ID': sessionId }
                    });
                    const data = await res.json();

                    if (data.authenticated) {
                        showChatUI(data.user.name);
                        chatInput.focus();
                        scrollToBottom();
                    } else {
                        prechatForm.classList.remove('abpd-hidden');
                        chatBody.classList.add('abpd-hidden');
                        chatFooter.classList.add('abpd-hidden');
                    }
                } catch (e) {
                    prechatForm.classList.remove('abpd-hidden');
                    chatBody.classList.add('abpd-hidden');
                    chatFooter.classList.add('abpd-hidden');
                }
            } else {
                toggleBtn.classList.remove('abpd-hidden');
            }
        }

        toggleBtn.addEventListener('click', toggleChat);
        closeBtn.addEventListener('click', toggleChat);

        // Pre-chat form submit
        startBtn.addEventListener('click', async () => {
            const name = nameInput.value.trim();
            const phone = phoneInput.value.trim();

            if (!name || !phone) {
                alert('Mohon isi nama dan nomor telepon Anda terlebih dahulu.');
                return;
            }

            startBtn.disabled = true;
            startBtn.textContent = 'Memulai...';

            try {
                const res = await fetch(`${apiBaseUrl}/api/session/new`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ customer_name: name, customer_phone: phone })
                });

                if (!res.ok) throw new Error('Gagal inisialisasi sesi');
                const data = await res.json();

                if (data.session_id) {
                    sessionStorage.setItem('nasikotak_session', data.session_id);
                }

                showChatUI(name);
            } catch (e) {
                console.error("Gagal membuat sesi:", e);
                alert('Gagal menghubungkan ke server chatbot. Silakan coba lagi.');
            } finally {
                startBtn.disabled = false;
                startBtn.textContent = 'Mulai Chat';
            }
        });

        function addMessage(content, sender, whatsappLink = null, suggestedOutlets = null) {
            const msgDiv = document.createElement('div');
            msgDiv.className = `abpd-msg abpd-msg-${sender}`;

            const bubbleDiv = document.createElement('div');
            bubbleDiv.className = 'abpd-bubble';

            if (sender === 'bot') {
                bubbleDiv.innerHTML = renderBotContent(content);
            } else {
                bubbleDiv.innerHTML = escapeHtml(content).replace(/\n/g, '<br>');
            }

            msgDiv.appendChild(bubbleDiv);

            // Suggested Outlets Buttons
            if (sender === 'bot' && suggestedOutlets && suggestedOutlets.length > 0) {
                const outletsContainer = document.createElement('div');
                outletsContainer.className = 'abpd-outlets-container';

                suggestedOutlets.forEach((outlet) => {
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'abpd-outlet-btn';
                    btn.innerHTML = `<span>📍 <strong>${escapeHtml(outlet.name)}</strong></span> <span style="font-size: 0.8em; opacity: 0.85;">± ${outlet.distance_km} km</span>`;
                    btn.addEventListener('click', () => {
                        outletsContainer.querySelectorAll('button').forEach(b => {
                            b.disabled = true;
                            b.style.pointerEvents = 'none';
                        });
                        sendMessage(`Saya pilih ${outlet.name}`);
                    });
                    outletsContainer.appendChild(btn);
                });
                bubbleDiv.appendChild(outletsContainer);
            }

            // WhatsApp Action Button
            if (sender === 'bot' && whatsappLink) {
                const btnContainer = document.createElement('div');
                btnContainer.style.marginTop = '10px';
                const waBtn = document.createElement('a');
                waBtn.href = whatsappLink;
                waBtn.target = '_blank';
                waBtn.rel = 'noopener noreferrer';
                waBtn.className = 'abpd-wa-btn';

                if (content.includes("Ringkasan Reservasi")) {
                    waBtn.innerHTML = '<i class="fab fa-whatsapp"></i> Konfirmasi Reservasi (WhatsApp)';
                } else if (content.includes("Ringkasan Pesanan")) {
                    waBtn.innerHTML = '<i class="fab fa-whatsapp"></i> Kirim Pesanan (WhatsApp)';
                } else {
                    waBtn.innerHTML = '<i class="fab fa-whatsapp"></i> Hubungi Admin';
                }

                btnContainer.appendChild(waBtn);
                bubbleDiv.appendChild(btnContainer);
            }

            const timeDiv = document.createElement('div');
            timeDiv.className = 'abpd-time';
            timeDiv.textContent = getCurrentTime();
            msgDiv.appendChild(timeDiv);

            chatBody.appendChild(msgDiv);
            scrollToBottom();

            // Auto-scroll ulang saat gambar bot selesai dimuat
            msgDiv.querySelectorAll('img').forEach(img => {
                img.addEventListener('load', () => scrollToBottom());
            });
        }

        function showTyping() {
            isWaiting = true;
            sendBtn.disabled = true;

            const typingDiv = document.createElement('div');
            typingDiv.className = 'abpd-typing';
            typingDiv.id = 'abpd-typing-indicator';

            for (let i = 0; i < 3; i++) {
                const dot = document.createElement('div');
                dot.className = 'abpd-dot';
                typingDiv.appendChild(dot);
            }

            chatBody.appendChild(typingDiv);
            scrollToBottom();
        }

        function removeTyping() {
            isWaiting = false;
            sendBtn.disabled = false;
            const typing = document.getElementById('abpd-typing-indicator');
            if (typing) typing.remove();
        }

        async function sendMessage(text) {
            if (!text || !text.trim() || isWaiting) return;

            chatInput.value = '';
            addMessage(text, 'user');

            if (quickReplies) quickReplies.style.display = 'none';
            showTyping();

            try {
                const response = await fetch(`${apiBaseUrl}/api/chat`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Session-ID': sessionStorage.getItem('nasikotak_session') || ''
                    },
                    body: JSON.stringify({ message: text })
                });

                if (!response.ok) throw new Error('Respon server gagal');

                const data = await response.json();
                removeTyping();
                addMessage(data.reply, 'bot', data.whatsapp_link, data.suggested_outlets);
            } catch (err) {
                console.error("Chatbot Error:", err);
                removeTyping();
                addMessage("Maaf kak, sistem kami sedang sibuk atau terjadi gangguan koneksi. Bisa dicoba lagi sebentar ya 🙏", 'bot');
            } finally {
                removeTyping();
                chatInput.focus();
            }
        }

        sendBtn.addEventListener('click', () => sendMessage(chatInput.value));

        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage(chatInput.value);
            }
        });

        // Quick Replies Click
        document.querySelectorAll('.abpd-qr-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const text = btn.getAttribute('data-text');
                sendMessage(text);
            });
        });
    }

    // Inisialisasi saat DOM siap
    function init() {
        injectHeadDependencies();
        injectScopedCSS();
        injectWidgetHTML();
        initChatLogic();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
