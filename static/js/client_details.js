document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;
    const clientId = window.location.pathname.split('/').pop();
    let clientData = null;

    // --- Lógica de Pestañas ---
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabPanels = document.querySelectorAll('.tab-panel');
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            const tabName = button.getAttribute('data-tab');
            tabPanels.forEach(panel => {
                panel.classList.toggle('active', panel.id === `tab-${tabName}`);
            });
        });
    });

    // --- Funciones de Utilidad ---
    async function fetchJSON(url, options = {}) {
        const getUrl = new URL(url, API_BASE_URL);
        if (!options.method || options.method === 'GET') {
            getUrl.searchParams.append('_', new Date().getTime());
        }
        const response = await fetch(getUrl.toString(), options);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || 'API Request Failed');
        }
        return response.status === 204 ? null : response.json();
    }

    function formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 Bytes';
        const bytesNum = parseInt(bytes, 10);
        if (isNaN(bytesNum)) return 'N/A';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytesNum) / Math.log(k));
        return parseFloat((bytesNum / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // --- Funciones de Carga y Renderizado ---
    function renderClientInfo(client) {
        const container = document.getElementById('client-info-container');
        const coordsLink = client.coordinates ? `<a href="http://maps.google.com/maps?q=${client.coordinates}" target="_blank" class="font-semibold text-primary hover:underline">${client.coordinates}</a>` : '<span class="font-semibold">N/A</span>';
        container.innerHTML = `
            <div class="flex justify-between"><span>Phone:</span> <span class="font-semibold">${client.phone_number || 'N/A'}</span></div>
            <div class="flex justify-between"><span>WhatsApp:</span> <span class="font-semibold">${client.whatsapp_number || 'N/A'}</span></div>
            <div class="flex justify-between"><span>Email:</span> <span class="font-semibold">${client.email || 'N/A'}</span></div>
            <div class="flex justify-between"><span>Address:</span> <span class="font-semibold text-right">${client.address || 'N/A'}</span></div>
            <div class="flex justify-between"><span>Coordinates:</span> ${coordsLink}</div>
        `;
    }

    async function loadServiceStatus() {
        const container = document.getElementById('service-status-container');
        container.innerHTML = '<p class="text-text-secondary text-center">Loading service status...</p>';
        try {
            const services = await fetchJSON(`/api/clients/${clientId}/services`);
            if (!services || services.length === 0) {
                container.innerHTML = '<p class="text-text-secondary text-center font-semibold">This client has no network services configured.</p>';
                return;
            }
            
            const pppoeService = services.find(s => s.service_type === 'pppoe');
            if (!pppoeService) {
                 container.innerHTML = '<p class="text-text-secondary text-center font-semibold">Service is not PPPoE.</p>';
                 return;
            }

            const username = pppoeService.pppoe_username;
            const routerHost = pppoeService.router_host;
            
            const secretData = await fetchJSON(`/api/routers/${routerHost}/pppoe/secrets?name=${encodeURIComponent(username)}`);
            
            let statusHtml = '';
            if (!secretData || secretData.length === 0) {
                statusHtml = `
                    <div class="flex justify-between"><span class="text-text-secondary">Status:</span> <span class="font-semibold text-danger">User Not Found on Router</span></div>
                    <div class="flex justify-between"><span class="text-text-secondary">PPPoE User:</span> <span class="font-mono">${username}</span></div>
                    <div class="flex justify-between"><span class="text-text-secondary">Router:</span> <span class="font-mono">${routerHost}</span></div>
                `;
            } else {
                const secret = secretData[0];
                const isDisabled = secret.disabled === 'true'; 
                const statusClass = isDisabled ? 'text-danger' : 'text-success';
                const statusText = isDisabled ? 'Suspended' : 'Active';

                const activeConnections = await fetchJSON(`/api/routers/${routerHost}/pppoe/active?name=${encodeURIComponent(username)}`);
                const isOnline = activeConnections && activeConnections.length > 0;
                const onlineText = isOnline ? `Online (<span class="text-success">${activeConnections[0].address}</span>)` : 'Offline';

                statusHtml = `
                    <div class="flex justify-between"><span>Account Status:</span> <span class="font-semibold ${statusClass}">${statusText}</span></div>
                    <div class="flex justify-between"><span>Network Status:</span> <span class="font-semibold">${onlineText}</span></div>
                    <div class="flex justify-between"><span>PPPoE User:</span> <span class="font-mono">${secret.name}</span></div>
                    <div class="flex justify-between"><span>Router:</span> <span class="font-mono">${routerHost}</span></div>
                    <div class="flex justify-between"><span>Uptime:</span> <span>${isOnline ? activeConnections[0].uptime : 'N/A'}</span></div>
                    <div class="flex justify-between"><span>Plan:</span> <span>${secret.profile || 'N/A'}</span></div>
                    <div class="flex justify-between"><span>Usage (Up/Down):</span> 
                        <span class="font-semibold">${formatBytes(secret['bytes-out'])} / ${formatBytes(secret['bytes-in'])}</span>
                    </div>
                `;
            }
            container.innerHTML = statusHtml;

        } catch (e) {
            container.innerHTML = `<p class="text-danger text-center">Error loading live status: ${e.message}</p>`;
        }
    }

    async function loadPaymentHistory() {
        const container = document.getElementById('payment-history-list');
        container.innerHTML = '<p class="text-text-secondary">Loading history...</p>';
        try {
            const payments = await fetchJSON(`/api/clients/${clientId}/payments`);
            if (!payments || payments.length === 0) {
                container.innerHTML = '<p class="text-text-secondary">No payments registered for this client.</p>';
                return;
            }
            
            container.innerHTML = '';
            payments.forEach(payment => {
                const paymentEl = document.createElement('div');
                paymentEl.className = 'flex justify-between items-center bg-surface-2 p-3 rounded-md';
                const paymentDate = new Date(payment.fecha_pago).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
                paymentEl.innerHTML = `
                    <div>
                        <p class="font-semibold text-text-primary">$${payment.monto.toFixed(2)} - <span class="font-medium text-text-secondary">For: ${payment.mes_correspondiente}</span></p>
                        <p class="text-xs text-text-secondary">${paymentDate} (${payment.metodo_pago || 'N/A'})</p>
                        ${payment.notas ? `<p class="text-xs text-warning mt-1">${payment.notas}</p>` : ''}
                    </div>
                `;
                container.appendChild(paymentEl);
            });
            
        } catch (e) {
            container.innerHTML = `<p class="text-danger">Error loading history: ${e.message}</p>`;
        }
    }

    async function handleRegisterPayment(e) {
        e.preventDefault();
        const errorEl = document.getElementById('payment-form-error');
        errorEl.classList.add('hidden');
        
        const data = {
            monto: parseFloat(document.getElementById('payment-amount').value),
            mes_correspondiente: document.getElementById('payment-month').value,
            metodo_pago: document.getElementById('payment-method').value,
            notas: document.getElementById('payment-notes').value,
        };
        
        if (!data.monto || data.monto <= 0) {
            errorEl.textContent = 'Amount must be a valid number.';
            errorEl.classList.remove('hidden');
            return;
        }
        if (!validators.isRequired(data.mes_correspondiente) || !/^\d{4}-\d{2}$/.test(data.mes_correspondiente)) {
            errorEl.textContent = 'Month is required (Format YYYY-MM).';
            errorEl.classList.remove('hidden');
            return;
        }

        try {
            await fetchJSON(`/api/clients/${clientId}/payments`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            alert('Payment registered and service reactivated successfully!');
            document.getElementById('register-payment-form').reset();
            document.getElementById('payment-month').value = new Date().toISOString().slice(0, 7);
            
            // Reload both dynamic parts of the page
            loadServiceStatus();
            loadPaymentHistory();
            
        } catch (error) {
            errorEl.textContent = `Error: ${error.message}`;
            errorEl.classList.remove('hidden');
        }
    }

    // --- Carga Inicial de la Página ---
    async function initializePage() {
        try {
            // No podemos obtener los detalles del cliente desde la API de /clients,
            // así que necesitamos un endpoint que no existe o construirlo.
            // Por ahora, cargaremos la lista y filtraremos.
            const allClients = await fetchJSON(`/api/clients`);
            clientData = allClients.find(c => c.id == clientId);

            if (!clientData) throw new Error("Client not found in the list.");

            document.title = `${clientData.name} - Client Details`;
            document.getElementById('breadcrumb-clientname').textContent = clientData.name;
            document.getElementById('main-clientname').textContent = clientData.name;
            document.getElementById('payment-month').value = new Date().toISOString().slice(0, 7);

            renderClientInfo(clientData);
            loadServiceStatus();
            loadPaymentHistory();
            
            document.getElementById('register-payment-form').addEventListener('submit', handleRegisterPayment);

        } catch (error) {
            document.getElementById('main-clientname').textContent = 'Error Loading Client';
            alert(`Failed to initialize page: ${error.message}`);
        }
    }

    initializePage();
});