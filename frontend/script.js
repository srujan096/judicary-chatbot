document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const voiceBtn = document.getElementById('voice-btn');
    const voiceStatus = document.getElementById('voice-status');
    const chatMessages = document.getElementById('chat-messages');

    let recognition = null;
    let synthesis = window.speechSynthesis;

    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
        recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-IN';

        recognition.onstart = () => {
            voiceBtn.classList.add('recording');
            voiceStatus.textContent = 'Listening...';
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            chatInput.value = transcript;
            voiceStatus.textContent = 'Click microphone to start speaking';
            sendMessage();
        };

        recognition.onerror = (event) => {
            voiceStatus.textContent = 'Error occurred. Please try again.';
            voiceBtn.classList.remove('recording');
        };

        recognition.onend = () => {
            voiceBtn.classList.remove('recording');
        };
    }

    function speak(text) {
        if (synthesis.speaking) {
            synthesis.cancel();
        }

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-IN';
        utterance.rate = 1;
        utterance.pitch = 1;
        synthesis.speak(utterance);
    }

    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    if (voiceBtn) {
        voiceBtn.addEventListener('click', () => {
            if (recognition) {
                if (voiceBtn.classList.contains('recording')) {
                    recognition.stop();
                } else {
                    recognition.start();
                }
            } else {
                voiceStatus.textContent = 'Speech recognition not supported in this browser.';
            }
        });
    }

    function scrollToBottom() {
        if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    async function sendMessage() {
        const input = chatInput;
        if (!input || !input.value.trim()) return;

        const message = input.value.trim();
        input.value = '';

        // Display user message
        const userMessage = document.createElement('div');
        userMessage.className = 'message user-message';
        userMessage.textContent = message;
        chatMessages.appendChild(userMessage);
        scrollToBottom();

        // Create bot message container
        const botMessage = document.createElement('div');
        botMessage.className = 'message bot-message';
        botMessage.textContent = 'Judiciary Bot: Processing...';
        chatMessages.appendChild(botMessage);

        try {
            const response = await fetch('http://localhost:5000/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });

            if (!response.ok) throw new Error(`Network response was not ok: ${response.statusText}`);
            
            // Stream the response
            await streamResponse(response, botMessage);
            
            // Speak the response if it's not too long
            const responseText = botMessage.textContent.replace('Judiciary Bot: ', '');
            speak(responseText);

        } catch (error) {
            console.error('Error:', error);
            botMessage.textContent = `Judiciary Bot: Sorry, I am unable to process your request at the moment. (Error: ${error.message})`;
        }
        scrollToBottom();
    }

    // Helper function to stream responses
    async function streamResponse(response, botMessage) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            botMessage.textContent += chunk + " ";
            scrollToBottom();
        }
    }

// Language Toggle (unchanged)
const languageToggle = document.getElementById('language-toggle');
let isHindi = false;
languageToggle.addEventListener('click', () => {
    const language = isHindi ? 'en' : 'hi';
    fetch('/switch_language', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: language }),
    })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            isHindi = !isHindi;
            languageToggle.textContent = isHindi ? 'Switch to English' : 'Switch to Hindi';
        });
});

// Document Upload
document.getElementById('upload-btn').addEventListener('click', async () => {
    const fileInput = document.getElementById('document-input');
    const file = fileInput.files[0];
    if (!file) {
        alert('Please select a file to upload.');
        return;
    }

    const userMessage = document.createElement('div');
    userMessage.className = 'message user-message';
    userMessage.textContent = `You: Uploaded ${file.name}`;
    chatMessages.appendChild(userMessage);

    const botMessage = document.createElement('div');
    botMessage.className = 'message bot-message';
    botMessage.textContent = 'Judiciary Bot: Processing your document... ';
    chatMessages.appendChild(botMessage);

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('http://localhost:5000/upload_document', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) throw new Error(`Network response was not ok: ${response.statusText}`);
        botMessage.textContent = 'Judiciary Bot: '; // Reset for streaming
        await streamResponse(response, botMessage);
    } catch (error) {
        botMessage.textContent = `Judiciary Bot: Error processing document: ${error.message}`;
    }
    chatMessages.scrollTop = chatMessages.scrollHeight;
}); // <<< This parenthesis and semicolon correctly end the event listener.
});