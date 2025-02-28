<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, viewport-fit=cover">
    <meta name="description" content="Wiskoro Chatbot - Je persoonlijke wiskunde G die je door alle sommen heen carried! 🔥">
    <title>Wiskoro Chatbot</title>
    <link rel="preconnect" href="https://rsms.me">
    <link rel="stylesheet" href="https://rsms.me/inter/inter.css">
    <style>
        :root {
            color-scheme: light dark;
            --bg-color-light: #f9f9f9;
            --bg-color-dark: #1e1e1e;
            --text-color-light: #333;
            --text-color-dark: #f5f5f5;
            --chat-bg-light: #ffffff;
            --chat-bg-dark: #2a2a2a;
            --border-color-light: #ddd;
            --border-color-dark: #444;
            --button-color-light: #007aff;
            --button-color-dark: #0a84ff;
            --button-hover-light: #005ecb;
            --button-hover-dark: #0070e6;
            --message-bg-bot-light: #f1f1f1;
            --message-bg-bot-dark: #3a3a3a;
            --focus-outline: #4a9eff;
        }

        @media (prefers-color-scheme: dark) {
            :root {
                --bg-color: var(--bg-color-dark);
                --text-color: var(--text-color-dark);
                --chat-bg: var(--chat-bg-dark);
                --border-color: var(--border-color-dark);
                --button-color: var(--button-color-dark);
                --button-hover: var(--button-hover-dark);
                --message-bg-bot: var(--message-bg-bot-dark);
            }
        }

        html, body {
            height: 100%;
            margin: 0;
            padding: 0;
            overflow: hidden;
            position: fixed;
            width: 100%;
            top: 0;
            left: 0;
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Inter', system-ui, sans-serif;
            display: flex;
            flex-direction: column;
        }

        #chat-container {
            display: flex;
            flex-direction: column;
            width: 100%;
            height: 100vh;
            background-color: var(--chat-bg);
            overflow: hidden;
        }

        #chat-box {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
            margin-bottom: 80px;
            scroll-behavior: smooth;
            -webkit-overflow-scrolling: touch;
        }

        .message {
            margin: 0.5rem 0;
            padding: 0.75rem 1rem;
            border-radius: 1rem;
            max-width: 80%;
            word-wrap: break-word;
            animation: fadeIn 0.3s ease-in-out;
            color: var(--text-color);
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(0.5rem); }
            to { opacity: 1; transform: translateY(0); }
        }

        .bot {
            background-color: var(--message-bg-bot);
            margin-right: auto;
        }

        .input-container {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            display: flex;
            justify-content: center;
            padding: 1rem;
            padding-bottom: calc(1rem + env(safe-area-inset-bottom));
            background-color: var(--chat-bg);
            box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            width: 100%;
            box-sizing: border-box;
        }

        #fact-button {
            flex: 1;
            max-width: 90%;
            padding: 1rem;
            font-size: 1rem;
            border-radius: 1rem;
            border: none;
            background-color: var(--button-color);
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.2s, transform 0.1s;
            text-align: center;
        }

        #fact-button:hover {
            background-color: var(--button-hover);
        }

        #fact-button:active {
            transform: scale(0.98);
        }

        @media (max-width: 480px) {
            .message {
                max-width: 90%;
            }

            .input-container {
                padding: 0.75rem;
                padding-bottom: calc(0.75rem + env(safe-area-inset-bottom));
            }

            #fact-button {
                padding: 0.75rem;
                font-size: 0.9rem;
            }
        }
    </style>
</head>
<body>
    <div id="chat-container">
        <div id="chat-box" role="log" aria-live="polite"></div>
        <div class="input-container">
            <button id="fact-button">Geef me nog een feitje</button>
        </div>
    </div>

    <script>
        const backendUrl = "https://api.wiskoro.nl/fact";  // ✅ FIXED ENDPOINT
        const buttonFacts = [
            "Nog een feitje", "Drop nog iets", "Gooi er nog één", 
            "Vertel me meer", "Wat nog meer?", "Hit me up", "Laat maar horen"
        ];
        const loadingMessages = [
            "Even die brain cells activeren...",
            "Matrix hacken voor je antwoord...",
            "Formules spotten zoals een echte G...",
            "Wiskunde sauce loading...",
            "Calculations on fleek incoming..."
        ];
        const errorMessages = [
            "Ey g, die server left us on read! 💀 Probeer ff opnieuw!",
            "Nah fam, connection is skeer rn. Check je wifi en probeer nog een x! 🔌",
            "Yo my g, er ging iets fout in de matrix! Refresh die pagina en we gaan door! 🔄"
        ];

        function getRandomItem(array) {
            return array[Math.floor(Math.random() * array.length)];
        }

        function updateButtonText() {
            document.getElementById("fact-button").textContent = getRandomItem(buttonFacts);
        }

        function addMessage(content, type) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}`;
            messageDiv.textContent = content;
            document.getElementById("chat-box").appendChild(messageDiv);
            document.getElementById("chat-box").scrollTop = document.getElementById("chat-box").scrollHeight;
        }

        async function fetchFact() {
            try {
                addMessage(getRandomItem(loadingMessages), 'bot');
                const response = await fetch(backendUrl);
                if (!response.ok) throw new Error('Network error');
                const data = await response.json();
                addMessage(data.response, 'bot');
            } catch (error) {
                addMessage(getRandomItem(errorMessages), 'bot');
            } finally {
                updateButtonText();
            }
        }

        document.getElementById("fact-button").addEventListener("click", fetchFact);

        // ✅ Laat direct een feitje zien bij het laden van de pagina
        document.addEventListener("DOMContentLoaded", () => {
            fetchFact();
        });
    </script>
</body>
</html>
