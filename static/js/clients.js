// static/js/clients.js

document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;
    let allClients = [];
    let currentFilters = { searchTerm: '', serviceStatus: 'all' };
    let refreshIntervalId = null;
    let currentEditingClient = null;

    // --- DOM REFERENCES ---
    const searchInput = document.getElementById('search-input');
    const tableBody = document.getElementById('client-table-body');
    const addClientButton = document.getElementById('add-client-button');
    const clientModal = document.getElementById('client-modal');
    
    // Modal Tabs
    const tabBtnInfo = document.getElementById('tab-btn-info');
    const tabBtnService = document.getElementById('tab-btn-service');
    const tabPanelInfo = document.getElementById('tab-panel-info');
    const tabPanelService = document.getElementById('tab-panel-service');
    
    // Client Form (Tab 1)
    const clientForm = document.getElementById('client-form');
    const cancelClientButton = document.getElementById('cancel-client-button');
    const cancelClientButtonX = document.getElementById('cancel-client-button-x');
    const clientFormError = document.getElementById('client-form-error-main');
    const modalTitle = document.getElementById('modal-title');
    const clientIdInput = document.getElementById('client-id');
    const assignedCPEsSection = document.getElementById('assigned-cpes-section');
    
    // Service Form (Tab 2)
    const serviceTypeSelect = document.getElementById('service_type');
    const pppoeServiceForm = document.getElementById('pppoe-service-form');
    const pppoeRouterSelect = document.getElementById('pppoe-router-select');
    const pppoeProfileSelect = document.getElementById('pppoe-profile-select');
    const pppoeUsername = document.getElementById('pppoe-username');
    const pppoePassword = document.getElementById('pppoe-password');
    const pppoeFormErrorMain = document.getElementById('pppoe-form-error-main');
    const suspensionWrapper = document.getElementById('suspension-method-wrapper');
    const suspensionSelect = document.getElementById('suspension_method');
    const saveServiceButton = document.getElementById('save-service-button');
    const cancelClientButtonTab2 = document.getElementById('cancel-client-button-tab2');

    async function fetchJSON(url, options = {}) {
        const fullUrl = new URL(url, API_BASE_URL);
        if (!options.method || options.method.toUpperCase() === 'GET') {
            fullUrl.searchParams.append('_', new Date().getTime());
        }
        const response = await fetch(fullUrl.toString(), options);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || 'API Request Failed');
        }
        return response.status === 204 ? null : response.json();
    }

    // --- Tab Logic ---
    function switchTab(tabName) {
        tabBtnInfo.classList.toggle('active', tabName === 'info');
        tabPanelInfo.classList.toggle('active', tabName === 'info');
        tabBtnService.classList.toggle('active', tabName === 'service');
        tabPanelService.classList.toggle('active', tabName === 'service');
    }

    // --- Render Logic (COLORES ACTUALIZADOS FASE 6) ---
    function getStatusBadgeClass(status) {
        switch (status) {
            case 'active': 
                return 'bg-success/20 text-success'; // Verde
            case 'pendiente': 
                return 'bg-warning/20 text-warning'; // Amarillo
            case 'suspended': 
                return 'bg-danger/20 text-danger';   // Rojo
            case 'cancelled': 
                return 'bg-surface-2 text-text-secondary'; // Gris
            default: 
                return 'bg-surface-2 text-text-secondary';
        }
    }

    function renderClients() {
        if (!tableBody) return;
        let filteredClients = allClients;
        if (currentFilters.serviceStatus !== 'all') {
            filteredClients = filteredClients.filter(client => client.service_status === currentFilters.serviceStatus);
        }
        if (currentFilters.searchTerm) {
            const term = currentFilters.searchTerm.toLowerCase();
            filteredClients = filteredClients.filter(client =>
                client.name.toLowerCase().includes(term) ||
                (client.address && client.address.toLowerCase().includes(term)) ||
                (client.phone_number && client.phone_number.includes(term))
            );
        }
        
        tableBody.innerHTML = '';
        if (filteredClients.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center p-8 text-text-secondary">No clients found.</td></tr>`;
        } else {
            filteredClients.forEach(client => {
                const row = document.createElement('tr');
                row.className = "hover:bg-surface-2 transition-colors duration-200 cursor-pointer";
                row.onclick = () => { window.location.href = `/client/${client.id}`; };
                
                const statusClass = getStatusBadgeClass(client.service_status);
                // Capitalizar primera letra
                const statusText = client.service_status.charAt(0).toUpperCase() + client.service_status.slice(1);

                row.innerHTML = `
                    <td class="px-6 py-4"><span class="text-xs font-semibold px-2 py-1 rounded-full ${statusClass}">${statusText}</span></td>
                    <td class="px-6 py-4 font-semibold text-text-primary">${client.name}</td>
                    <td class="px-6 py-4 text-text-secondary">${client.address || 'N/A'}</td>
                    <td class="px-6 py-4 text-text-secondary font-mono">${client.phone_number || 'N/A'}</td>
                    <td class="px-6 py-4 text-center font-semibold">${client.cpe_count}</td>
                    <td class="px-6 py-4 text-right">
                        <button class="edit-btn text-text-secondary hover:text-primary" title="Edit Client"><span class="material-symbols-outlined">edit</span></button>
                        <button class="delete-btn text-text-secondary hover:text-danger" title="Delete Client"><span class="material-symbols-outlined">delete</span></button>
                    </td>
                `;
                row.querySelector('.edit-btn').onclick = (e) => { e.stopPropagation(); openClientModal(client); };
                row.querySelector('.delete-btn').onclick = (e) => { e.stopPropagation(); handleDeleteClient(client.id, client.name); };
                tableBody.appendChild(row);
            });
        }
    }

    // --- Data Loading Functions ---
    async function loadAllClients() {
        if (!tableBody) return;
        tableBody.style.filter = 'blur(4px)';
        tableBody.style.opacity = '0.6';
        if (allClients.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center p-8 text-text-secondary">Loading clients...</td></tr>';
        }
        try {
            allClients = await fetchJSON('/api/clients');
            renderClients();
        } catch (error) {
            console.error("Error loading clients:", error);
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center p-8 text-danger">Failed to load clients.</td></tr>`;
        } finally {
            setTimeout(() => {
                if (tableBody) {
                    tableBody.style.filter = 'blur(0px)';
                    tableBody.style.opacity = '1';
                }
            }, 50);
        }
    }
    
    // --- Modal Logic & Form Handlers ---
    async function openClientModal(client = null) {
        formUtils.resetModalForm('client-modal');
        switchTab('info');
        currentEditingClient = null;

        // --- AÑADIR ESTO: Resetear visualización de password ---
        const passInput = document.getElementById('pppoe-password');
        const toggleBtn = document.getElementById('toggle-pppoe-password');
        if (passInput) passInput.type = 'password';
        if (toggleBtn) toggleBtn.querySelector('span').textContent = 'visibility_off';
        // -------------------------------------------------------

        // Resetear estado visual de la pestaña de servicio
        pppoeServiceForm.classList.add('hidden');
        suspensionWrapper.classList.add('hidden');

        if (client) {
            modalTitle.textContent = 'Edit Client';
            clientIdInput.value = client.id;
            currentEditingClient = client;
            
            // Rellenar datos básicos del cliente
            document.getElementById('client-name').value = client.name;
            document.getElementById('client-email').value = client.email || '';
            document.getElementById('client-phone_number').value = client.phone_number || '';
            document.getElementById('client-whatsapp_number').value = client.whatsapp_number || '';
            document.getElementById('client-address').value = client.address || '';
            document.getElementById('client-service_status').value = client.service_status;
            document.getElementById('client-billing_day').value = client.billing_day || '';
            document.getElementById('client-notes').value = client.notes || '';
            
            assignedCPEsSection.classList.remove('hidden');
            tabBtnService.disabled = false;
            
            // Cargas iniciales
            await loadAndRenderAssignedCPEs(client.id);
            await populateUnassignedCPEs();
            await loadRoutersForSelect(); // IMPORTANTE: Cargar routers antes de asignar valor

            // --- NUEVA LÓGICA: Cargar y mostrar datos del servicio existente ---
            try {
                const services = await fetchJSON(`/api/clients/${client.id}/services`);
                
                if (services && services.length > 0) {
                    // Tomamos el servicio más reciente
                    const service = services[0]; 
                    
                    if (service.service_type === 'pppoe') {
                        // 1. Activar UI de PPPoE
                        serviceTypeSelect.value = 'pppoe';
                        pppoeServiceForm.classList.remove('hidden');
                        suspensionWrapper.classList.remove('hidden');
                        // Asegurar que el select de suspensión tenga opciones
                        if (suspensionSelect.options.length <= 1) {
                             suspensionSelect.innerHTML = `<option value="pppoe_secret_disable">Disable Secret (Recommended)</option>`;
                        }

                        // 2. Rellenar campos guardados en DB local
                        pppoeRouterSelect.value = service.router_host;
                        pppoeUsername.value = service.pppoe_username;
                        suspensionSelect.value = service.suspension_method;

                        // 3. Cargar planes del router seleccionado y marcar el actual
                        // Llamamos a la función existente que carga los perfiles
                        await handleRouterSelectChange(); 
                        pppoeProfileSelect.value = service.profile_name;

                        // 4. Obtener la CONTRASEÑA real desde el Router (MikroTik)
                        // Consultamos la API usando el username para traer el 'secret'
                        try {
                            const secrets = await fetchJSON(`/api/routers/${service.router_host}/pppoe/secrets?name=${encodeURIComponent(service.pppoe_username)}`);
                            if (secrets && secrets.length > 0) {
                                pppoePassword.value = secrets[0].password; // Rellenar password
                            }
                        } catch (err) {
                            console.error("Error obteniendo password del router:", err);
                            pppoePassword.placeholder = "Error retrieving password";
                        }
                    }
                } else {
                    // Si no tiene servicio, sugerir usuario por defecto como antes
                    pppoeUsername.value = client.name.trim().replace(/\s+/g, '.').toLowerCase();
                }
            } catch (e) {
                console.error("Error cargando servicios del cliente:", e);
            }
            // --- FIN NUEVA LÓGICA ---

        } else {
            // Modo Crear Nuevo
            modalTitle.textContent = 'Add New Client';
            clientIdInput.value = '';
            assignedCPEsSection.classList.add('hidden');
            tabBtnService.disabled = true;
        }
        clientModal.classList.add('is-open');
    }

    function closeClientModal() {
        clientModal.classList.remove('is-open');
        currentEditingClient = null;
    }

    async function handleClientFormSubmit(event) {
        event.preventDefault();
        formUtils.clearFormErrors(clientForm);
        if (!validators.isRequired(document.getElementById('client-name').value)) {
            formUtils.showFieldError('client-name', 'Name is required.');
            return;
        }
        
        const clientId = clientIdInput.value;
        const isEditing = !!clientId;
        const url = isEditing ? `/api/clients/${clientId}` : `/api/clients`;
        const method = isEditing ? 'PUT' : 'POST';
        
        const formData = new FormData(clientForm);
        const data = Object.fromEntries(formData.entries());
        Object.keys(data).forEach(key => { if (data[key] === '') data[key] = null; });
        
        try {
            const savedClient = await fetchJSON(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            if (!isEditing) {
                currentEditingClient = savedClient;
                clientIdInput.value = savedClient.id;
                modalTitle.textContent = 'Edit Client';
                tabBtnService.disabled = false;
                alert('Client created. You can now add a network service.');
                switchTab('service');
                await loadRoutersForSelect();
                pppoeUsername.value = savedClient.name.trim().replace(/\s+/g, '.').toLowerCase();
            } else {
                closeClientModal();
            }
            await loadAllClients();
        } catch (error) {
            clientFormError.textContent = `Error: ${error.message}`;
            clientFormError.classList.remove('hidden');
        }
    }
    
    async function handleSavePppoeService() {
        formUtils.clearFormErrors(pppoeServiceForm);
        let isValid = true;
        
        const host = pppoeRouterSelect.value;
        const profile = pppoeProfileSelect.value;
        const username = pppoeUsername.value;
        const password = pppoePassword.value;
        const suspensionMethod = suspensionSelect.value;

        if (!validators.isRequired(host)) { formUtils.showFieldError('pppoe-router-select', 'Router is required.'); isValid = false; }
        if (!validators.isRequired(profile)) { formUtils.showFieldError('pppoe-profile-select', 'Plan is required.'); isValid = false; }
        if (!validators.isRequired(username)) { formUtils.showFieldError('pppoe-username', 'Username is required.'); isValid = false; }
        if (!validators.isRequired(password)) { formUtils.showFieldError('pppoe-password', 'Password is required.'); isValid = false; }
        if (!isValid) return;

        try {
            const secretData = { username, password, profile, comment: `client_id:${currentEditingClient.id}:${currentEditingClient.name}`, service: 'pppoe' };
            const newSecret = await fetchJSON(`/api/routers/${host}/pppoe/secrets`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(secretData)
            });
            const routerSecretId = newSecret['.id'] || newSecret['id'];
            if (!routerSecretId) throw new Error("Could not get ID of created secret.");

            const serviceData = {
                router_host: host,
                service_type: 'pppoe',
                pppoe_username: username,
                router_secret_id: routerSecretId,
                profile_name: profile,
                suspension_method: suspensionMethod
            };
            await fetchJSON(`/api/clients/${currentEditingClient.id}/services`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(serviceData)
            });

            alert('PPPoE service created successfully!');
            closeClientModal();
        } catch (error) {
            pppoeFormErrorMain.textContent = `Error: ${error.message}`;
            pppoeFormErrorMain.classList.remove('hidden');
        }
    }
    
    async function handleDeleteClient(clientId, clientName) {
        if (confirm(`Are you sure you want to delete client "${clientName}"?`)) {
            try {
                await fetchJSON(`/api/clients/${clientId}`, { method: 'DELETE' });
                await loadAllClients();
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }
    }

    // --- Network Service Helpers (Actualizado Fase 8) ---
    async function loadRoutersForSelect() {
        try {
            const routers = await fetchJSON('/api/routers');
            pppoeRouterSelect.innerHTML = '<option value="">Select a router...</option>';
            routers.filter(r => r.api_port === r.api_ssl_port).forEach(router => {
                pppoeRouterSelect.innerHTML += `<option value="${router.host}">${router.hostname || router.host}</option>`;
            });
        } catch (error) {
            pppoeRouterSelect.innerHTML = '<option value="">Error loading routers</option>';
        }
    }

    async function handleRouterSelectChange() {
        const host = pppoeRouterSelect.value;
        pppoeProfileSelect.innerHTML = '<option value="">Loading...</option>';
        pppoeProfileSelect.disabled = true;
        
        if (!host) {
            pppoeProfileSelect.innerHTML = '<option value="">Select a router first</option>';
            return;
        }
        
        try {
            const profiles = await fetchJSON(`/api/routers/${host}/pppoe/profiles`);
            
            pppoeProfileSelect.innerHTML = '<option value="">Select a plan...</option>';
            
            if (profiles.length === 0) {
                pppoeProfileSelect.innerHTML = '<option value="" disabled>No plans found on router</option>';
                return;
            }
            
            profiles.forEach(p => {
                const label = `${p.name} ${p['rate-limit'] ? '(' + p['rate-limit'] + ')' : ''}`;
                pppoeProfileSelect.innerHTML += `<option value="${p.name}">${label}</option>`;
            });
            
            pppoeProfileSelect.disabled = false;
            
        } catch (error) {
            console.error(error);
            pppoeProfileSelect.innerHTML = '<option value="">Error loading plans</option>';
        }
    }
    
    async function loadAndRenderAssignedCPEs(clientId) {
        const listDiv = document.getElementById('assigned-cpes-list');
        listDiv.innerHTML = '<p class="text-sm text-text-secondary">Loading...</p>';
        try {
            const cpes = await fetchJSON(`/api/clients/${clientId}/cpes`);
            listDiv.innerHTML = '';
            if (cpes.length === 0) {
                listDiv.innerHTML = '<p class="text-sm text-text-secondary">No CPEs assigned.</p>';
            } else {
                cpes.forEach(cpe => {
                    const cpeDiv = document.createElement('div');
                    cpeDiv.className = 'flex items-center justify-between bg-surface-2 p-2 rounded-md';
                    cpeDiv.innerHTML = `<p class="text-sm font-mono">${cpe.hostname || cpe.mac}</p><button type="button" class="unassign-cpe-btn text-danger text-xs font-semibold">UNASSIGN</button>`;
                    cpeDiv.querySelector('.unassign-cpe-btn').onclick = () => handleUnassignCPE(cpe.mac, clientId);
                    listDiv.appendChild(cpeDiv);
                });
            }
        } catch (error) {
            listDiv.innerHTML = '<p class="text-sm text-danger">Could not load CPEs.</p>';
        }
    }

    async function populateUnassignedCPEs() {
        const select = document.getElementById('unassigned-cpe-select');
        select.innerHTML = '<option value="">Loading...</option>';
        try {
            const cpes = await fetchJSON('/api/cpes/unassigned');
            select.innerHTML = '<option value="">Select a CPE to assign...</option>';
            if (cpes.length === 0) {
                select.innerHTML = '<option value="" disabled>No unassigned CPEs available</option>';
            } else {
                cpes.forEach(cpe => {
                    select.innerHTML += `<option value="${cpe.mac}">${cpe.hostname || 'Unnamed'} (${cpe.mac})</option>`;
                });
            }
        } catch (error) {
            select.innerHTML = '<option value="">Error loading CPEs</option>';
        }
    }

    async function handleAssignCPE() {
        const cpeMac = document.getElementById('unassigned-cpe-select').value;
        const clientId = clientIdInput.value;
        if (!cpeMac || !clientId) return;
        try {
            await fetchJSON(`/api/cpes/${cpeMac}/assign/${clientId}`, { method: 'POST' });
            await loadAndRenderAssignedCPEs(clientId);
            await populateUnassignedCPEs();
            await loadAllClients();
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    }

    async function handleUnassignCPE(cpeMac, clientId) {
        if (!confirm('Unassign this CPE?')) return;
        try {
            await fetchJSON(`/api/cpes/${cpeMac}/unassign`, { method: 'POST' });
            await loadAndRenderAssignedCPEs(clientId);
            await populateUnassignedCPEs();
            await loadAllClients();
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    }
    
    // --- Auto-refresh
    async function initializeAutoRefresh() {
        try {
            const settings = await fetchJSON('/api/settings');
            const interval = parseInt(settings.dashboard_refresh_interval, 10);
            if (interval > 0) {
                if (refreshIntervalId) clearInterval(refreshIntervalId);
                refreshIntervalId = setInterval(loadAllClients, interval * 1000);
            }
        } catch (error) {
            console.error("Could not load settings for auto-refresh.", error);
        }
    }

    // --- INITIALIZATION AND EVENT LISTENERS ---
    document.querySelectorAll('.filter-button').forEach(button => button.addEventListener('click', () => {
        document.querySelectorAll('.filter-button').forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        currentFilters.serviceStatus = button.dataset.status;
        renderClients();
    }));
    
    if (searchInput) searchInput.addEventListener('input', (e) => { currentFilters.searchTerm = e.target.value; renderClients(); });
    if (addClientButton) addClientButton.addEventListener('click', () => openClientModal());
    if (cancelClientButton) cancelClientButton.addEventListener('click', closeClientModal);
    if (cancelClientButtonX) cancelClientButtonX.addEventListener('click', closeClientModal);
    if (clientModal) clientModal.addEventListener('click', (e) => { if (e.target === clientModal) closeClientModal(); });
    if (tabBtnInfo) tabBtnInfo.addEventListener('click', () => switchTab('info'));
    if (tabBtnService) tabBtnService.addEventListener('click', () => switchTab('service'));
    if (clientForm) clientForm.addEventListener('submit', handleClientFormSubmit);
    if (saveServiceButton) saveServiceButton.addEventListener('click', handleSavePppoeService);
    if(cancelClientButtonTab2) cancelClientButtonTab2.addEventListener('click', closeClientModal);
    if (pppoeRouterSelect) pppoeRouterSelect.addEventListener('change', handleRouterSelectChange);

    document.getElementById('assign-cpe-button').addEventListener('click', handleAssignCPE);

    serviceTypeSelect.addEventListener('change', () => {
        const isPppoe = serviceTypeSelect.value === 'pppoe';
        pppoeServiceForm.classList.toggle('hidden', !isPppoe);
        suspensionWrapper.classList.toggle('hidden', !isPppoe);
        if (isPppoe) {
            suspensionSelect.innerHTML = `<option value="pppoe_secret_disable">Disable Secret (Recommended)</option>`;
        }
    });

    // Lógica para el botón de Ojo (Show/Hide Password)
    const togglePassBtn = document.getElementById('toggle-pppoe-password');
    const passInput = document.getElementById('pppoe-password');

    if (togglePassBtn && passInput) {
        togglePassBtn.addEventListener('click', () => {
            const isPassword = passInput.getAttribute('type') === 'password';
            
            // Alternar tipo
            passInput.setAttribute('type', isPassword ? 'text' : 'password');
            
            // Alternar icono
            const icon = togglePassBtn.querySelector('span');
            if (icon) {
                icon.textContent = isPassword ? 'visibility' : 'visibility_off'; // visibility = ojo abierto
            }
        });
    }

    loadAllClients();
    initializeAutoRefresh();
});