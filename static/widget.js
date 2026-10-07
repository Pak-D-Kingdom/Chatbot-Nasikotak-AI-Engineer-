/**
 * Ayam Bakar Pak D - AI Sales Chatbot Embeddable Widget
 * 
 * Penggunaan di WordPress / Website Eksternal:
 * <script>
 *   window.AYAMBAKAR_CHATBOT_API_URL = "https://domain-backend-anda.com"; // Opsional jika backend beda domain
 * </script>
 * <script src="https://domain-backend-anda.com/static/widget.js" defer></script>
 */

(function () {
    'use strict';

    // Cegah double injection
    if (window.__ABPD_WIDGET_INITIALIZED__) return;
    window.__ABPD_WIDGET_INITIALIZED__ = true;

    // 1. Tentukan API Base URL secara dinamis
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
    apiBaseUrl = apiBaseUrl.replace(/\/+$/, '');

    // 2. Inject External Font & Icons ke Document Head
    function injectGlobalDependencies() {
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
    injectGlobalDependencies();

    // 3. Inisialisasi Shadow Host
    const hostElement = document.createElement('div');
    hostElement.id = 'abpd-chatbot-widget-host';
    hostElement.style.position = 'fixed';
    hostElement.style.bottom = '0';
    hostElement.style.right = '0';
    hostElement.style.zIndex = '2147483647';
    hostElement.style.pointerEvents = 'none';

    document.body.appendChild(hostElement);

    const shadow = hostElement.attachShadow({ mode: 'open' });

    // Inject FontAwesome & Outfit langsung ke dalam Shadow DOM
    const linkOutfitShadow = document.createElement('link');
    linkOutfitShadow.rel = 'stylesheet';
    linkOutfitShadow.href = 'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap';
    shadow.appendChild(linkOutfitShadow);

    const linkFAShadow = document.createElement('link');
    linkFAShadow.rel = 'stylesheet';
    linkFAShadow.href = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css';
    shadow.appendChild(linkFAShadow);

    // 4. Inject Stylesheet ke dalam Shadow DOM
    const style = document.createElement('style');
    style.textContent = `
        :host {
            --primary-color: #FF6B00;
            --primary-gradient: linear-gradient(135deg, #FF8A00 0%, #FF5C00 100%);
            --bg-color: #F8F9FA;
            --chat-bg: #FFFFFF;
            --text-main: #2D3748;
            --text-muted: #718096;
            --bot-msg-bg: #F1F3F5;
            --user-msg-bg: var(--primary-color);
            --user-msg-text: #FFFFFF;
            --shadow-sm: 0 4px 6px rgba(0, 0, 0, 0.05);
            --shadow-lg: 0 10px 25px rgba(255, 107, 0, 0.15);
            --border-radius-lg: 20px;
            --border-radius-sm: 12px;
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-size: 16px;
            color: var(--text-main);
            box-sizing: border-box;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: inherit;
        }

        /* Floating Button Group (WhatsApp, Instagram, Chatbot AI) */
        .floating-btn-group {
            position: fixed;
            bottom: 30px;
            right: 30px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
            z-index: 1000;
            pointer-events: auto;
            transition: opacity 0.3s ease, transform 0.3s ease;
        }

        .floating-btn-group.hidden {
            display: none !important;
        }

        .floating-btn {
            width: 46px;
            height: 46px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            text-decoration: none;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
            border: 2px solid #ffffff;
            transition: transform 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.25s ease;
            cursor: pointer;
            outline: none;
        }

        .floating-btn:hover {
            transform: scale(1.12);
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.25);
        }

        .btn-instagram {
            background: radial-gradient(circle at 30% 107%, #fdf497 0%, #fdf497 5%, #fd5949 45%, #d6249f 60%, #285AEB 90%);
            font-size: 22px;
        }

        .btn-whatsapp {
            background: #25D366;
            font-size: 24px;
        }

        /* Tombol Floating Chat (Toggle) */
        .chat-toggle-btn {
            position: relative;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: var(--primary-gradient);
            color: white;
            border: 2.5px solid #ffffff;
            font-size: 24px;
            cursor: pointer;
            box-shadow: var(--shadow-lg);
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            display: flex;
            align-items: center;
            justify-content: center;
            outline: none;
        }

        .chat-toggle-btn:hover {
            transform: scale(1.1);
        }

        .chatbot-badge {
            position: absolute;
            top: -4px;
            right: -4px;
            min-width: 22px;
            height: 22px;
            padding: 0 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            background: #ffffff;
            color: var(--primary-color, #FF6B00);
            border: 2px solid var(--primary-color, #FF6B00);
            font-size: 10px;
            font-weight: 800;
            line-height: 1;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.15);
            pointer-events: none;
        }

        .chat-toggle-btn.hidden {
            display: none !important;
        }

        /* Container Chat Popup */
        .chat-container {
            position: fixed;
            bottom: 100px;
            right: 30px;
            width: 380px;
            height: 600px;
            max-height: calc(100vh - 120px);
            background: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(10px);
            border-radius: var(--border-radius-lg);
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.15);
            display: flex;
            flex-direction: column;
            transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            transform-origin: bottom right;
            border: 1px solid rgba(226, 232, 240, 0.8);
            overflow: hidden;
            pointer-events: auto;
        }

        .chat-container.hidden {
            opacity: 0;
            pointer-events: none;
            transform: scale(0.8) translateY(50px);
        }

        /* Header Chat */
        .chat-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px;
            background: var(--primary-gradient);
            color: white;
            border-top-left-radius: var(--border-radius-lg);
            border-top-right-radius: var(--border-radius-lg);
            flex-shrink: 0;
        }

        .header-info {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .avatar {
            position: relative;
            width: 40px;
            height: 40px;
        }

        .avatar img {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            border: 2px solid white;
            object-fit: cover;
            display: block;
        }

        .online-indicator {
            position: absolute;
            bottom: 2px;
            right: 2px;
            width: 10px;
            height: 10px;
            background-color: #4CAF50;
            border-radius: 50%;
            border: 2px solid white;
        }

        .header-text h3 {
            font-size: 1rem;
            font-weight: 600;
            margin: 0;
            color: white;
            line-height: 1.2;
        }

        .header-text p {
            font-size: 0.8rem;
            opacity: 0.9;
            margin: 2px 0 0 0;
            color: white;
            line-height: 1.2;
        }

        .chat-close-btn {
            background: transparent;
            border: none;
            color: white;
            font-size: 1.2rem;
            cursor: pointer;
            opacity: 0.8;
            transition: opacity 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 4px;
            outline: none;
        }

        .chat-close-btn:hover {
            opacity: 1;
        }

        /* Chat Body */
        .chat-body {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 16px;
            scroll-behavior: smooth;
            background: #FFFFFF;
        }

        .chat-body::-webkit-scrollbar {
            width: 6px;
        }

        .chat-body::-webkit-scrollbar-track {
            background: transparent;
        }

        .chat-body::-webkit-scrollbar-thumb {
            background: #E2E8F0;
            border-radius: 10px;
        }

        /* Balon Pesan */
        .message {
            max-width: 85%;
            display: flex;
            flex-direction: column;
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message-bubble {
            padding: 12px 16px;
            font-size: 0.95rem;
            line-height: 1.5;
            word-wrap: break-word;
        }

        .message-bot {
            align-self: flex-start;
        }

        .message-bot .message-bubble {
            background-color: var(--bot-msg-bg);
            color: var(--text-main);
            border-radius: var(--border-radius-sm) var(--border-radius-sm) var(--border-radius-sm) 4px;
        }

        .message-user {
            align-self: flex-end;
        }

        .message-user .message-bubble {
            background: var(--primary-gradient);
            color: var(--user-msg-text);
            border-radius: var(--border-radius-sm) var(--border-radius-sm) 4px var(--border-radius-sm);
            box-shadow: 0 4px 10px rgba(255, 107, 0, 0.2);
        }

        .message-time {
            font-size: 0.7rem;
            color: var(--text-muted);
            margin-top: 4px;
            align-self: flex-end;
        }

        .message-bot .message-time {
            align-self: flex-start;
        }

        /* Format Konten Pesan Bot */
        .message-bot .message-bubble p {
            margin-bottom: 8px;
        }
        .message-bot .message-bubble p:last-child {
            margin-bottom: 0;
        }
        .message-bot .message-bubble ul, .message-bot .message-bubble ol {
            margin-left: 20px;
            margin-bottom: 8px;
        }
        .message-bot .message-bubble strong {
            font-weight: 600;
        }
        .message-bot .message-bubble img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            margin-top: 8px;
            margin-bottom: 8px;
            display: block;
        }

        /* Tombol Konfirmasi WhatsApp */
        .action-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background-color: #25D366;
            color: white !important;
            padding: 10px 16px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            margin-top: 10px;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 4px 6px rgba(37, 211, 102, 0.2);
        }

        .action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(37, 211, 102, 0.3);
        }

        /* Tombol Pilihan 5 Outlet Terdekat */
        .suggested-outlets-container {
            margin-top: 12px;
            display: flex;
            flex-direction: column;
            gap: 7px;
        }

        .outlet-select-btn {
            background: #ffffff;
            color: #d84315;
            border: 1.5px solid #ffab91;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 0.85rem;
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

        .outlet-select-btn:hover {
            background: #fbe9e7;
            border-color: #d84315;
            transform: translateY(-1px);
            box-shadow: 0 3px 6px rgba(216, 67, 21, 0.15);
        }

        .outlet-select-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        /* Quick Replies */
        .quick-replies {
            padding: 0 20px 10px;
            display: flex;
            gap: 8px;
            overflow-x: auto;
            scrollbar-width: none;
            white-space: nowrap;
            background: #FFFFFF;
            flex-shrink: 0;
        }

        .quick-replies::-webkit-scrollbar {
            display: none;
        }

        .quick-reply-btn {
            background: white;
            border: 1px solid var(--primary-color);
            color: var(--primary-color);
            padding: 6px 12px;
            border-radius: 16px;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
            flex-shrink: 0;
            outline: none;
        }

        .quick-reply-btn:hover {
            background: var(--primary-color);
            color: white;
        }

        /* Chat Footer & Input */
        .chat-footer {
            padding: 16px 20px;
            background: white;
            border-top: 1px solid #E2E8F0;
            border-bottom-left-radius: var(--border-radius-lg);
            border-bottom-right-radius: var(--border-radius-lg);
            flex-shrink: 0;
        }

        .input-container {
            display: flex;
            gap: 10px;
            background: #F8F9FA;
            padding: 8px;
            border-radius: 24px;
            border: 1px solid #E2E8F0;
            transition: border-color 0.2s;
        }

        .input-container:focus-within {
            border-color: var(--primary-color);
            background: white;
        }

        .chat-input {
            flex: 1;
            border: none;
            background: transparent;
            padding: 8px 12px;
            font-size: 0.95rem;
            color: var(--text-main);
            outline: none;
        }

        .chat-send-btn {
            background: var(--primary-gradient);
            color: white;
            border: none;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.2s;
            outline: none;
            font-size: 14px;
        }

        .chat-send-btn:hover {
            transform: scale(1.05);
        }

        .chat-send-btn:disabled {
            background: #CBD5E0;
            cursor: not-allowed;
            transform: none;
        }

        .footer-branding {
            text-align: center;
            margin-top: 10px;
            font-size: 0.7rem;
            color: var(--text-muted);
        }

        /* Typing Indicator */
        .typing-indicator {
            display: flex;
            gap: 4px;
            padding: 12px 16px;
            background-color: var(--bot-msg-bg);
            border-radius: var(--border-radius-sm) var(--border-radius-sm) var(--border-radius-sm) 4px;
            align-self: flex-start;
            margin-bottom: 16px;
        }

        .typing-dot {
            width: 6px;
            height: 6px;
            background-color: var(--text-muted);
            border-radius: 50%;
            animation: typing 1.4s infinite ease-in-out;
        }

        .typing-dot:nth-child(1) { animation-delay: 0s; }
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }

        @keyframes typing {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-4px); }
        }

        /* Pre-Chat Registration Form */
        .pre-chat-form {
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 30px 20px;
            background: white;
            justify-content: center;
            gap: 20px;
            animation: fadeIn 0.3s ease;
        }

        .pre-chat-greeting {
            text-align: center;
            margin-bottom: 10px;
        }

        .pre-chat-greeting h4 {
            font-size: 1.4rem;
            color: var(--primary-color);
            margin-bottom: 8px;
            font-weight: 700;
        }

        .pre-chat-greeting p {
            font-size: 0.9rem;
            color: var(--text-muted);
        }

        .form-group {
            display: flex;
            flex-direction: column;
        }

        .form-group input {
            padding: 12px 16px;
            border: 1px solid #E2E8F0;
            border-radius: var(--border-radius-sm);
            font-size: 0.95rem;
            transition: border-color 0.2s, box-shadow 0.2s;
            outline: none;
            color: var(--text-main);
            background: white;
        }

        .form-group input:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(255, 107, 0, 0.1);
        }

        .form-group input.input-error {
            border-color: #E53E3E !important;
            background-color: #FFF5F5 !important;
        }

        .form-group input.input-error:focus {
            box-shadow: 0 0 0 3px rgba(229, 62, 62, 0.2) !important;
        }

        .error-text {
            color: #E53E3E;
            font-size: 0.8rem;
            margin-top: 4px;
            line-height: 1.3;
        }

        .start-chat-btn {
            background: var(--primary-gradient);
            color: white;
            border: none;
            padding: 14px;
            border-radius: var(--border-radius-sm);
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 4px 10px rgba(255, 107, 0, 0.2);
            margin-top: 10px;
            outline: none;
        }

        .start-chat-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(255, 107, 0, 0.3);
        }

        .hidden {
            display: none !important;
        }

        /* Mobile Viewport */
        @media (max-width: 480px) {
            .chat-container {
                width: 100vw;
                height: 100vh;
                max-height: 100vh;
                bottom: 0;
                right: 0;
                border-radius: 0;
                transform-origin: bottom center;
            }

            .chat-header {
                border-radius: 0;
            }

            .chat-footer {
                border-radius: 0;
                padding-bottom: 24px;
            }

            .chat-toggle-btn.hidden {
                transform: translateY(100px);
            }
        }
    `;

    shadow.appendChild(style);

    // 5. Inject HTML Widget persis seperti index.html
    const widgetHTML = `
        <!-- Floating Action Button Stack (Instagram, WhatsApp, AI Chat) -->
        <div id="floating-btn-group" class="floating-btn-group">
            <!-- Instagram Button -->
            <a href="https://www.instagram.com/ayambakarpakd?utm_source=ig_web_button_share_sheet&igsh=ZDNlZDc0MzIxNw%3D%3D" target="_blank" rel="noopener noreferrer" class="floating-btn btn-instagram" aria-label="Instagram Ayam Bakar Pak D" title="Instagram @ayambakarpakd">
                <i class="fab fa-instagram"></i>
            </a>

            <!-- WhatsApp Button -->
            <a href="https://api.whatsapp.com/send?phone=628881111158" target="_blank" rel="noopener noreferrer" class="floating-btn btn-whatsapp" aria-label="WhatsApp Ayam Bakar Pak D" title="WhatsApp Customer Service">
                <i class="fab fa-whatsapp"></i>
            </a>

            <!-- Floating Chat Toggle Button -->
            <button id="chat-toggle-btn" class="chat-toggle-btn" aria-label="Buka Chat AI Ayam Bakar Pak D" title="Chat dengan AI Assistant">
                <i class="fas fa-comment-dots"></i>
            </button>
        </div>

        <!-- Chat Container Window -->
        <div id="chat-container" class="chat-container hidden">
            <!-- Header -->
            <div class="chat-header">
                <div class="header-info">
                    <div class="avatar">
                        <img src="https://ui-avatars.com/api/?name=AI&background=FF8A00&color=fff" alt="AI Avatar">
                        <div class="online-indicator"></div>
                    </div>
                    <div class="header-text">
                        <h3>AI Sales Assistant</h3>
                        <p>Ayam Bakar Pak D</p>
                    </div>
                </div>
                <button id="chat-close-btn" class="chat-close-btn" aria-label="Tutup Chat">
                    <i class="fas fa-times"></i>
                </button>
            </div>

            <!-- Pre-Chat Registration Form -->
            <div id="pre-chat-form" class="pre-chat-form">
                <div class="pre-chat-greeting">
                    <h4>Selamat Datang!</h4>
                    <p>Silakan isi data diri Anda untuk memulai.</p>
                </div>
                <div class="form-group">
                    <input type="text" id="user-name" placeholder="Nama Anda" required autocomplete="off">
                    <span id="name-error" class="error-text hidden"></span>
                </div>
                <div class="form-group">
                    <input type="tel" id="user-phone" placeholder="No. WhatsApp (contoh: 08123456789)" required autocomplete="off">
                    <span id="phone-error" class="error-text hidden"></span>
                </div>
                <button id="start-chat-btn" class="start-chat-btn">Mulai Chat</button>
            </div>

            <!-- Chat Message Body -->
            <div id="chat-body" class="chat-body hidden"></div>

            <!-- Quick Reply Chips -->
            <div id="quick-replies" class="quick-replies hidden">
                <button class="quick-reply-btn" data-text="Ada paket catering apa saja?">Lihat Paket</button>
                <button class="quick-reply-btn" data-text="Apakah ada promo saat ini?">Promo</button>
                <button class="quick-reply-btn" data-text="Saya punya budget 25rb per box">Budget 25rb</button>
            </div>

            <!-- Chat Footer Input -->
            <div id="chat-footer" class="chat-footer hidden">
                <div class="input-container">
                    <input type="text" id="chat-input" class="chat-input" placeholder="Tulis pesan..." autocomplete="off">
                    <button id="chat-send-btn" class="chat-send-btn" aria-label="Kirim Pesan">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
                <div class="footer-branding">
                    <span>AI Chatbot Ayam Bakar Pak D</span>
                </div>
            </div>
        </div>
    `;

    const widgetWrapper = document.createElement('div');
    widgetWrapper.innerHTML = widgetHTML;
    shadow.appendChild(widgetWrapper);

    // 6. Query Elemen-Elemen dari Shadow DOM
    const floatingBtnGroup = shadow.getElementById('floating-btn-group');
    const chatToggleBtn = shadow.getElementById('chat-toggle-btn');
    const chatContainer = shadow.getElementById('chat-container');
    const chatCloseBtn = shadow.getElementById('chat-close-btn');
    const chatBody = shadow.getElementById('chat-body');
    const chatInput = shadow.getElementById('chat-input');
    const chatSendBtn = shadow.getElementById('chat-send-btn');
    const quickReplies = shadow.querySelectorAll('.quick-reply-btn');
    const preChatForm = shadow.getElementById('pre-chat-form');
    const userNameInput = shadow.getElementById('user-name');
    const userPhoneInput = shadow.getElementById('user-phone');
    const nameError = shadow.getElementById('name-error');
    const phoneError = shadow.getElementById('phone-error');
    const startChatBtn = shadow.getElementById('start-chat-btn');
    const chatFooter = shadow.getElementById('chat-footer');
    const quickRepliesContainer = shadow.getElementById('quick-replies');

    let isWaiting = false;

    function showError(inputEl, errorEl, message) {
        if (inputEl) inputEl.classList.add('input-error');
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.classList.remove('hidden');
        }
    }

    function clearError(inputEl, errorEl) {
        if (inputEl) inputEl.classList.remove('input-error');
        if (errorEl) {
            errorEl.textContent = '';
            errorEl.classList.add('hidden');
        }
    }

    if (userNameInput) {
        userNameInput.addEventListener('input', () => clearError(userNameInput, nameError));
        userNameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') userPhoneInput ? userPhoneInput.focus() : startChatBtn.click();
        });
    }

    if (userPhoneInput) {
        userPhoneInput.addEventListener('input', () => {
            clearError(userPhoneInput, phoneError);
            userPhoneInput.value = userPhoneInput.value.replace(/[^0-9+\-\s]/g, '');
        });
        userPhoneInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') startChatBtn.click();
        });
    }

    // 7. Helper Functions (Text escaping, Linkify, Markdown Parsing)
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
            const url = escapeHtml(match[2]);
            html += `<img src="${url}" alt="${alt}" loading="lazy">`;

            lastIndex = imageRegex.lastIndex;
        }

        const textAfter = content.slice(lastIndex);
        html += linkify(escapeHtml(textAfter)).replace(/\n/g, '<br>');

        return html;
    }

    function playNotificationSound() {
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            const ctx = new AudioContext();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(587.33, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.12);
            gain.gain.setValueAtTime(0.08, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 0.2);
        } catch (e) {
            // Audio context mungkin diblokir browser sebelum ada interaksi user
        }
    }

    function formatAndValidatePhone(phone) {
        let cleaned = phone.replace(/[\s\-\(\)\.]+/g, '');
        if (cleaned.startsWith('+62')) {
            cleaned = cleaned.slice(3);
            if (cleaned.startsWith('0')) cleaned = cleaned.slice(1);
            cleaned = '0' + cleaned;
        } else if (cleaned.startsWith('62')) {
            cleaned = cleaned.slice(2);
            if (cleaned.startsWith('0')) cleaned = cleaned.slice(1);
            cleaned = '0' + cleaned;
        } else if (cleaned.startsWith('8')) {
            cleaned = '0' + cleaned;
        }

        // Format valid: diawali 08, minimal 10 digit, maksimal 14 digit
        const phoneRegex = /^08[1-9][0-9]{7,11}$/;
        if (!phoneRegex.test(cleaned)) {
            return null;
        }
        return cleaned;
    }

    // 8. Event Handlers & Logika Chat
    startChatBtn.addEventListener('click', async () => {
        clearError(userNameInput, nameError);
        clearError(userPhoneInput, phoneError);

        const name = userNameInput.value.trim();
        const rawPhone = userPhoneInput.value.trim();

        let hasError = false;

        if (!name) {
            showError(userNameInput, nameError, 'Nama wajib diisi.');
            userNameInput.focus();
            hasError = true;
        }

        if (!rawPhone) {
            showError(userPhoneInput, phoneError, 'Nomor WhatsApp wajib diisi.');
            if (!hasError) userPhoneInput.focus();
            hasError = true;
        }

        if (hasError) return;

        const validPhone = formatAndValidatePhone(rawPhone);
        if (!validPhone) {
            showError(userPhoneInput, phoneError, 'Format salah! Wajib nomor WhatsApp (diawali 08... / +62 / 62, minimal 10 digit). Contoh: 08123456789');
            userPhoneInput.focus();
            return;
        }

        // Update input tampilan ke format standar 08...
        userPhoneInput.value = validPhone;

        startChatBtn.disabled = true;
        startChatBtn.textContent = 'Memulai...';

        try {
            const res = await fetch(`${apiBaseUrl}/api/session/new`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ customer_name: name, customer_phone: validPhone })
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || 'Gagal memulai chat.');
            }

            const data = await res.json();

            if (data.session_id) {
                sessionStorage.setItem('nasikotak_session', data.session_id);
            }

            showChatUI(name);
        } catch (e) {
            console.error("Gagal membuat session:", e);
            showError(userPhoneInput, phoneError, e.message || 'Gagal memulai chat. Silakan coba lagi.');
            startChatBtn.disabled = false;
            startChatBtn.textContent = 'Mulai Chat';
        }
    });

    function showChatUI(customerName) {
        preChatForm.classList.add('hidden');
        chatBody.classList.remove('hidden');
        chatFooter.classList.remove('hidden');
        if (quickRepliesContainer) quickRepliesContainer.classList.remove('hidden');

        setTimeout(() => {
            if (chatBody.children.length === 0) {
                const greetingName = customerName ? customerName : 'Kak';
                addMessage(`Halo kak ${greetingName}! 👋 Saya Asisten AI Ayam Bakar Pak D. Ada yang bisa dibantu soal pesanan catering atau reservasi meja?`, 'bot');
            }
        }, 500);
    }

    async function toggleChat() {
        chatContainer.classList.toggle('hidden');
        if (!chatContainer.classList.contains('hidden')) {
            if (floatingBtnGroup) floatingBtnGroup.classList.add('hidden');
            else chatToggleBtn.classList.add('hidden');

            try {
                const res = await fetch(`${apiBaseUrl}/api/session`, {
                    headers: {
                        'X-Session-ID': sessionStorage.getItem('nasikotak_session') || ''
                    }
                });
                const data = await res.json();

                if (data.authenticated) {
                    showChatUI(data.customer_name);
                } else {
                    preChatForm.classList.remove('hidden');
                    chatBody.classList.add('hidden');
                    chatFooter.classList.add('hidden');
                    if (quickRepliesContainer) quickRepliesContainer.classList.add('hidden');
                }
            } catch (e) {
                console.error("Gagal memeriksa sesi:", e);
                preChatForm.classList.remove('hidden');
                chatBody.classList.add('hidden');
                chatFooter.classList.add('hidden');
                if (quickRepliesContainer) quickRepliesContainer.classList.add('hidden');
            }
        } else {
            if (floatingBtnGroup) floatingBtnGroup.classList.remove('hidden');
            else chatToggleBtn.classList.remove('hidden');
        }
    }

    chatToggleBtn.addEventListener('click', toggleChat);
    chatCloseBtn.addEventListener('click', toggleChat);

    quickReplies.forEach(btn => {
        btn.addEventListener('click', () => {
            const text = btn.getAttribute('data-text');
            chatInput.value = text;
            sendMessage();
        });
    });

    chatSendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text || isWaiting) return;

        addMessage(text, 'user');
        chatInput.value = '';

        const typingIndicator = showTypingIndicator();
        isWaiting = true;
        chatSendBtn.disabled = true;

        try {
            const res = await fetch(`${apiBaseUrl}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': sessionStorage.getItem('nasikotak_session') || ''
                },
                body: JSON.stringify({ message: text })
            });

            if (!res.ok) {
                if (res.status === 401) {
                    removeTypingIndicator(typingIndicator);
                    sessionStorage.removeItem('nasikotak_session');
                    preChatForm.classList.remove('hidden');
                    chatBody.classList.add('hidden');
                    chatFooter.classList.add('hidden');
                    if (quickRepliesContainer) quickRepliesContainer.classList.add('hidden');
                    alert('Sesi telah berakhir. Silakan isi form kembali.');
                    return;
                }
                throw new Error(`HTTP error! status: ${res.status}`);
            }

            const data = await res.json();
            removeTypingIndicator(typingIndicator);

            if (data.session_id) {
                sessionStorage.setItem('nasikotak_session', data.session_id);
            }

            addMessage(data.reply, 'bot', data.whatsapp_link, data.suggested_outlets);

        } catch (e) {
            console.error("Error sending message:", e);
            removeTypingIndicator(typingIndicator);
            addMessage("Maaf kak, terjadi kendala teknis. Mohon dicoba lagi sebentar ya 🙏", 'bot');
        } finally {
            isWaiting = false;
            chatSendBtn.disabled = false;
            chatInput.focus();
        }
    }

    function addMessage(text, sender, whatsappLink = null, suggestedOutlets = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${sender}`;

        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';

        if (sender === 'bot') {
            bubbleDiv.innerHTML = renderBotContent(text);

            // Tombol Interaktif Pilihan Outlet Terdekat
            if (suggestedOutlets && suggestedOutlets.length > 0) {
                const outletsContainer = document.createElement('div');
                outletsContainer.className = 'suggested-outlets-container';

                suggestedOutlets.forEach(outlet => {
                    const btn = document.createElement('button');
                    btn.className = 'outlet-select-btn';
                    btn.innerHTML = `<span>📍 ${escapeHtml(outlet.name)}</span> <span style="font-size: 0.8rem; color: #ff5722;">Pilih &rarr;</span>`;
                    btn.onclick = () => {
                        outletsContainer.querySelectorAll('button').forEach(b => b.disabled = true);
                        chatInput.value = `Saya pilih ${outlet.name}`;
                        sendMessage();
                    };
                    outletsContainer.appendChild(btn);
                });

                bubbleDiv.appendChild(outletsContainer);
            }

            // Tombol Konfirmasi WhatsApp
            if (whatsappLink) {
                const waBtn = document.createElement('a');
                waBtn.href = whatsappLink;
                waBtn.target = '_blank';
                waBtn.rel = 'noopener noreferrer';
                waBtn.className = 'action-btn';

                const isReservation = text.includes('Ringkasan Reservasi') || whatsappLink.includes('reservasi');
                const btnLabel = isReservation ? 'Konfirmasi Reservasi (WhatsApp)' : 'Hubungi Admin (WhatsApp)';

                waBtn.innerHTML = `
                    <i class="fab fa-whatsapp" style="font-size: 1.15rem;"></i>
                    <span>${btnLabel}</span>
                `;
                bubbleDiv.appendChild(waBtn);
            }
        } else {
            bubbleDiv.textContent = text;
        }

        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        const now = new Date();
        timeDiv.textContent = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

        messageDiv.appendChild(bubbleDiv);
        messageDiv.appendChild(timeDiv);

        chatBody.appendChild(messageDiv);
        chatBody.scrollTop = chatBody.scrollHeight;

        if (sender === 'bot') {
            playNotificationSound();
        }
    }

    function showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator';
        indicator.innerHTML = `
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        `;
        chatBody.appendChild(indicator);
        chatBody.scrollTop = chatBody.scrollHeight;
        return indicator;
    }

    function removeTypingIndicator(indicator) {
        if (indicator && indicator.parentNode) {
            indicator.parentNode.removeChild(indicator);
        }
    }

})();
