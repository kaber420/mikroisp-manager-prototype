document.addEventListener('DOMContentLoaded', () => {
    const wsIndicator = document.getElementById('ws-indicator');
    const statusText = wsIndicator ? wsIndicator.nextElementSibling : null;

    if (!wsIndicator) {
        console.warn("WebSocket indicator element #ws-indicator not found.");
        return;
    }

    const updateIndicator = (color, title, text) => {
        wsIndicator.style.backgroundColor = color;
        wsIndicator.setAttribute('title', title);
        if (statusText) {
            statusText.textContent = text;
        }
    };

    // Initial state
    updateIndicator('#95a5a6', 'Conectando...', 'Conectando...'); // Gray

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/dashboard`;

    let ws;
    let reconnectInterval;
    const RECONNECT_DELAY = 3000; // 3 seconds

    const connectWebSocket = () => {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('WebSocket connected');
            updateIndicator('#28a745', 'Conectado', 'En Vivo'); // Green
            clearInterval(reconnectInterval); // Stop trying to reconnect
        };

        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            console.log('WebSocket message received:', message);
            // Handle incoming messages (e.g., update dashboard data)
            // Example: if (message.type === 'update') { updateDashboard(message.data); }
        };

        ws.onclose = (event) => {
            console.warn('WebSocket disconnected:', event.reason);
            updateIndicator('#dc3545', 'Desconectado. Reconectando...', 'Reconectando...'); // Red
            // Attempt to reconnect after a delay
            clearInterval(reconnectInterval); // Clear any existing interval
            reconnectInterval = setInterval(connectWebSocket, RECONNECT_DELAY);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            ws.close(); // Force close to trigger onclose and reconnection attempt
        };
    };

    connectWebSocket();
});
