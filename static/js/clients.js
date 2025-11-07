document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;
    let allClients = [];
    let currentFilters = { searchTerm: '', serviceStatus: 'all' };
    let refreshIntervalId = null;
    
    // --- NUEVA VARIABLE ---
    // Guarda el cliente que estamos editando para que el formulario PPPoE pueda verlo
    let currentEditingClient = null; 

    // --- REFERENCIAS AL DOM (Generales) ---
    const searchInput = document.getElementById('search-input');
    const tableBody = document.getElementById('client-table-body');
    const addClientButton = document.getElementById('add-client-button');
    const clientModal = document.getElementById('client-modal');
    
    // --- Pestañas del Modal ---
    const tabBtnInfo = document.getElementById('tab-btn-info');
    const tabBtnService = document.getElementById('tab-btn-service');
    const tabPanelInfo = document.getElementById('tab-panel-info');
    const tabPanelService = document.getElementById('tab-panel-service');
    const cancelClientButtonTab2 = document.getElementById('cancel-client-button-tab2');

    // --- Pestaña 1: Formulario de Cliente ---
    const clientForm = document.getElementById('client-form');
    const cancelClientButton = document.getElementById('cancel-client-button');
    const cancelClientButtonX = document.getElementById('cancel-client-button-x');
    const clientFormError = document.getElementById('client-form-error-main'); 
    const modalTitle = document.getElementById('modal-title');
    const clientIdInput = document.getElementById('client-id');
    const assignedCPEsSection = document.getElementById('assigned-cpes-section');
    
    // --- Pestaña 2: Formulario de Servicio PPPoE ---
    const pppoeServiceForm = document.getElementById('pppoe-service-form');
    const pppoeRouterSelect = document.getElementById('pppoe-router-select');
    const pppoeProfileSelect = document.getElementById('pppoe-profile-select');
    const pppoeUsername = document.getElementById('pppoe-username');
    const pppoePassword = document.getElementById('pppoe-password');
    const pppoeFormErrorMain = document.getElementById('pppoe-form-error-main');
    const savePppoeFormBtn = document.getElementById('save-pppoe-form-btn');
    const cancelPppoeFormBtn = document.getElementById('cancel-pppoe-form-btn');
    const pppoeServiceStatus = document.getElementById('pppoe-service-status');


    // --- Lógica de Pestañas ---
    function switchTab(tabName) {
        if (tabName === 'info') {
            tabBtnInfo.classList.add('active');
            tabPanelInfo.classList.add('active');
            tabBtnService.classList.remove('active');
            tabPanelService.classList.remove('active');
        } else if (tabName === 'service') {
            tabBtnInfo.classList.remove('active');
            tabPanelInfo.classList.remove('active');
            tabBtnService.classList.add('active');
            tabPanelService.classList.add('active');
        }
    }

    // --- Lógica de Renderizado (Sin cambios) ---
    function getStatusBadgeClass(status) {
        switch (status) {
            case 'active': return 'bg-success/20 text-success';
            case 'suspended': return 'bg-warning/20 text-warning';
            case 'cancelled': return 'bg-danger/20 text-danger';
            default: return 'bg-text-secondary/20 text-text-secondary';
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
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center p-8 text-text-secondary">No clients match the current filters.</td></tr>`;
        } else {
            filteredClients.forEach(client => {
                const row = document.createElement('tr');
                row.className = "hover:bg-surface-2 transition-colors duration-200";
                const statusClass = getStatusBadgeClass(client.service_status);
                row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="text-xs font-semibold px-2 py-1 rounded-full ${statusClass}">${client.service_status}</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap font-semibold text-text-primary">${client.name}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-text-secondary">${client.address || 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-text-secondary font-mono">${client.phone_number || 'N/A'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-center text-text-primary font-semibold">${client.cpe_count}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-right">
                        <button class="edit-btn text-text-secondary hover:text-primary" title="Edit Client">
                            <span class="material-symbols-outlined">edit</span>
                        </button>
                         <button class="delete-btn text-text-secondary hover:text-danger" title="Delete Client">
                            <span class="material-symbols-outlined">delete</span>
                        </button>
                    </td>
                `;
                row.querySelector('.edit-btn').onclick = () => openClientModal(client);
                row.querySelector('.delete-btn').onclick = () => handleDeleteClient(client.id, client.name);
                tableBody.appendChild(row);
            });
        }
    }

    function loadAllClients() {
        if (!tableBody) return;
        tableBody.style.filter = 'blur(4px)';
        tableBody.style.opacity = '0.6';
        if (allClients.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center p-8 text-text-secondary">Loading clients...</td></tr>';
        }
        setTimeout(async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/api/clients`);
                if (!response.ok) throw new Error('Failed to load clients');
                allClients = await response.json();
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
        }, 300);
    }
    
    /**
     * Abre el modal para crear o editar un cliente.
     * (ACTUALIZADO para manejar pestañas y cargar servicios)
     */
    async function openClientModal(client = null) {
        formUtils.resetModalForm('client-modal');
        formUtils.clearFormErrors(pppoeServiceForm); // Limpiar también el 2do formulario
        pppoeServiceForm.classList.add('hidden');
        pppoeServiceStatus.innerHTML = '<p class="text-text-secondary text-center">Loading network service details...</p>';
        switchTab('info'); // Volver siempre a la pestaña de info
        currentEditingClient = null; // Limpiar cliente anterior
        
        if (client) { // Modo Edición
            modalTitle.textContent = 'Edit Client';
            clientIdInput.value = client.id;
            currentEditingClient = client; // Guardar cliente actual
            
            // Poblar Pestaña 1
            document.getElementById('client-name').value = client.name;
            document.getElementById('client-email').value = client.email || '';
            document.getElementById('client-phone_number').value = client.phone_number || '';
            document.getElementById('client-whatsapp_number').value = client.whatsapp_number || '';
            document.getElementById('client-address').value = client.address || '';
            document.getElementById('client-service_status').value = client.service_status;
            document.getElementById('client-suspension_method').value = client.suspension_method || '';
            document.getElementById('client-billing_day').value = client.billing_day || '';
            document.getElementById('client-notes').value = client.notes || '';
            
            // Activar CPEs y Pestaña de Servicio
            assignedCPEsSection.classList.remove('hidden');
            tabBtnService.disabled = false;
            await loadAndRenderAssignedCPEs(client.id);
            await populateUnassignedCPEs();
            
            // Cargar datos de la Pestaña 2
            await loadNetworkServiceDetails(client);

        } else { // Modo Creación
            modalTitle.textContent = 'Add New Client';
            clientIdInput.value = '';
            assignedCPEsSection.classList.add('hidden');
            tabBtnService.disabled = true; // No se puede añadir servicio a un cliente que no existe
        }
        clientModal.classList.add('is-open');
    }

    function closeClientModal() {
        if (clientModal) clientModal.classList.remove('is-open');
        currentEditingClient = null; // Limpiar al cerrar
    }

    /**
     * Maneja el envío del formulario de cliente (Pestaña 1).
     * (Sin cambios, ya estaba validado)
     */
    async function handleClientFormSubmit(event) {
        event.preventDefault();
        
        formUtils.clearFormErrors(clientForm);
        let isValid = true;
        
        const name = document.getElementById('client-name').value;
        const email = document.getElementById('client-email').value;
        const phone = document.getElementById('client-phone_number').value;

        if (!validators.isRequired(name)) {
            formUtils.showFieldError('client-name', 'El nombre es requerido.');
            isValid = false;
        }
        if (validators.isRequired(email) && !validators.isValidEmail(email)) {
            formUtils.showFieldError('client-email', 'Debe ser un email válido.');
            isValid = false;
        }
        if (validators.isRequired(phone) && !validators.isValidPhone(phone)) {
            formUtils.showFieldError('client-phone_number', 'Debe ser un teléfono válido.');
            isValid = false;
        }

        if (!isValid) return;
        
        const clientId = clientIdInput.value;
        const isEditing = !!clientId;
        
        const url = isEditing ? `${API_BASE_URL}/api/clients/${clientId}` : `${API_BASE_URL}/api/clients`;
        const method = isEditing ? 'PUT' : 'POST';
        
        const formData = new FormData(clientForm);
        const data = Object.fromEntries(formData.entries());

        for (const key in data) {
            if (data[key] === '') data[key] = null;
        }
        
        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Failed to ${isEditing ? 'update' : 'create'} client`);
            }
            
            const savedClient = await response.json();
            
            // Si estábamos creando, ahora podemos activar la pestaña de servicio
            if (!isEditing) {
                modalTitle.textContent = 'Edit Client';
                clientIdInput.value = savedClient.id;
                currentEditingClient = savedClient;
                tabBtnService.disabled = false;
                // Mostrar un feedback de éxito y cambiar a la pestaña de servicio
                alert('Cliente creado. Ahora puede añadir el servicio de red.');
                switchTab('service');
                await loadNetworkServiceDetails(savedClient);
            } else {
                closeClientModal();
            }
            
            loadAllClients(); // Recargar la lista de la tabla principal
        } catch (error) {
            clientFormError.textContent = `Error: ${error.message}`;
            clientFormError.classList.remove('hidden');
        }
    }

    /**
     * Maneja la eliminación de un cliente.
     * (Sin cambios)
     */
    async function handleDeleteClient(clientId, clientName) {
        if (confirm(`Are you sure you want to delete client "${clientName}"?\nThis will also unassign all their CPEs.`)) {
            try {
                const response = await fetch(`${API_BASE_URL}/api/clients/${clientId}`, { method: 'DELETE' });
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to delete client');
                }
                loadAllClients();
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }
    }

    // --- Lógica de CPE (Sin cambios) ---
    async function loadAndRenderAssignedCPEs(clientId) {
        const listDiv = document.getElementById('assigned-cpes-list');
        listDiv.innerHTML = '<p class="text-sm text-text-secondary">Loading assigned CPEs...</p>';
        try {
            const response = await fetch(`${API_BASE_URL}/api/clients/${clientId}/cpes`);
            const cpes = await response.json();
            listDiv.innerHTML = '';
            if (cpes.length === 0) {
                listDiv.innerHTML = '<p class="text-sm text-text-secondary">No CPEs assigned to this client.</p>';
            } else {
                cpes.forEach(cpe => {
                    const cpeDiv = document.createElement('div');
                    cpeDiv.className = 'flex items-center justify-between bg-surface-2 p-2 rounded-md';
                    cpeDiv.innerHTML = `
                        <p class="text-sm font-mono">${cpe.hostname || cpe.mac}</p>
                        <button type="button" class="unassign-cpe-btn text-danger text-xs font-semibold">UNASSIGN</button>
                    `;
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
        select.innerHTML = '<option value="">Loading available CPEs...</option>';
        try {
            const response = await fetch(`${API_BASE_URL}/api/cpes/unassigned`);
            const cpes = await response.json();
            select.innerHTML = '<option value="">Select a CPE to assign...</option>';
            if (cpes.length === 0) {
                select.innerHTML = '<option value="" disabled>No unassigned CPEs available</option>';
            } else {
                cpes.forEach(cpe => {
                    const option = document.createElement('option');
                    option.value = cpe.mac;
                    option.textContent = `${cpe.hostname || 'Unnamed'} (${cpe.mac})`;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            select.innerHTML = '<option value="">Error loading CPEs</option>';
        }
    }
    async function handleAssignCPE() {
        const select = document.getElementById('unassigned-cpe-select');
        const cpeMac = select.value;
        const clientId = clientIdInput.value;
        if (!cpeMac || !clientId) {
            alert('Please select a CPE to assign.');
            return;
        }
        try {
            const response = await fetch(`${API_BASE_URL}/api/cpes/${cpeMac}/assign/${clientId}`, { method: 'POST' });
            if (!response.ok) throw new Error('Failed to assign CPE');
            await loadAndRenderAssignedCPEs(clientId);
            await populateUnassignedCPEs();
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    }
    async function handleUnassignCPE(cpeMac, clientId) {
        if (!confirm(`Are you sure you want to unassign CPE ${cpeMac}?`)) return;
        try {
            const response = await fetch(`${API_BASE_URL}/api/cpes/${cpeMac}/unassign`, { method: 'POST' });
            if (!response.ok) throw new Error('Failed to unassign CPE');
            await loadAndRenderAssignedCPEs(clientId);
            await populateUnassignedCPEs();
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    }
    
    // --- Lógica de Auto-refresco (Sin cambios) ---
    async function initializeAutoRefresh() {
        try {
            const settingsResponse = await fetch(`${API_BASE_URL}/api/settings`);
            const settings = await settingsResponse.json();
            const refreshIntervalSeconds = parseInt(settings.dashboard_refresh_interval, 10);
            if (refreshIntervalSeconds && refreshIntervalSeconds > 0) {
                if (refreshIntervalId) clearInterval(refreshIntervalId);
                refreshIntervalId = setInterval(loadAllClients, refreshIntervalSeconds * 1000);
            }
        } catch (error) {
            console.error("Could not load settings for auto-refresh.", error);
        }
    }
    
    // ---
    // --- NUEVAS FUNCIONES (Pestaña de Servicio PPPoE) ---
    // ---
    
    /**
     * Carga los detalles del servicio de red para un cliente.
     * Por ahora, solo muestra el formulario de creación.
     */
    async function loadNetworkServiceDetails(client) {
        pppoeServiceForm.classList.remove('hidden');
        pppoeServiceStatus.innerHTML = ''; // Limpiar 'Loading...'
        
        // Poner un nombre de usuario PPPoE sugerido
        pppoeUsername.value = client.name.trim().replace(/\s+/g, '.').toLowerCase();
        
        try {
            // 1. Cargar Routers
            const response = await fetch(`${API_BASE_URL}/api/routers`);
            if (!response.ok) throw new Error('Failed to load routers');
            const routers = await response.json();
            
            pppoeRouterSelect.innerHTML = '<option value="">Select a router...</option>';
            routers.forEach(router => {
                // Solo mostrar routers que estén aprovisionados
                if(router.api_port === router.api_ssl_port) {
                    const option = document.createElement('option');
                    option.value = router.host;
                    option.textContent = router.hostname || router.host;
                    pppoeRouterSelect.appendChild(option);
                }
            });

            // 2. Resetear perfiles
            pppoeProfileSelect.innerHTML = '<option value="">Select a router first</option>';
            pppoeProfileSelect.disabled = true;

        } catch (error) {
            pppoeServiceStatus.innerHTML = `<p class="text-danger">Error loading routers: ${error.message}</p>`;
        }
    }
    
    /**
     * Se activa cuando el usuario selecciona un router en el formulario PPPoE.
     * Carga los perfiles (planes) de ese router.
     */
    async function handleRouterSelectChange(event) {
        const host = event.target.value;
        pppoeProfileSelect.innerHTML = '<option value="">Loading profiles...</option>';
        pppoeProfileSelect.disabled = true;

        if (!host) {
            pppoeProfileSelect.innerHTML = '<option value="">Select a router first</option>';
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/routers/${host}/read/ppp-profiles`);
            if (!response.ok) throw new Error('Failed to load profiles');
            const profiles = await response.json();
            
            // Filtrar para mostrar solo los perfiles que creamos (planes)
            const managedProfiles = profiles.filter(p => p.comment && p.comment.includes('Managed by µMonitor'));

            pppoeProfileSelect.innerHTML = '<option value="">Select a plan...</option>';
            if (managedProfiles.length === 0) {
                 pppoeProfileSelect.innerHTML = '<option value="" disabled>No plans found on this router</option>';
                 return;
            }

            managedProfiles.forEach(profile => {
                const option = document.createElement('option');
                option.value = profile.name;
                option.textContent = `${profile.name} (${profile.parent_queue || 'No queue'})`;
                pppoeProfileSelect.appendChild(option);
            });
            pppoeProfileSelect.disabled = false;

        } catch (error) {
            pppoeProfileSelect.innerHTML = '<option value="">Error loading profiles</option>';
            console.error(error);
        }
    }
    
    /**
     * Maneja el envío del formulario de creación de servicio PPPoE.
     */
    async function handlePppoeFormSubmit(event) {
        event.preventDefault();
        formUtils.clearFormErrors(pppoeServiceForm);
        let isValid = true;
        
        const host = pppoeRouterSelect.value;
        const profile = pppoeProfileSelect.value;
        const username = pppoeUsername.value;
        const password = pppoePassword.value;
        const clientName = currentEditingClient ? currentEditingClient.name : 'Unknown Client';
        
        // Validación
        if (!validators.isRequired(host)) {
            formUtils.showFieldError('pppoe-router-select', 'Debe seleccionar un router.');
            isValid = false;
        }
        if (!validators.isRequired(profile)) {
            formUtils.showFieldError('pppoe-profile-select', 'Debe seleccionar un plan.');
            isValid = false;
        }
        if (!validators.isRequired(username)) {
            formUtils.showFieldError('pppoe-username', 'El nombre de usuario es requerido.');
            isValid = false;
        }
        if (!validators.isRequired(password)) {
            formUtils.showFieldError('pppoe-password', 'La contraseña es requerida.');
            isValid = false;
        }
        
        if (!isValid) return;

        try {
            const data = {
                username: username,
                password: password,
                profile: profile,
                comment: `client_id:${currentEditingClient.id}:${clientName}`, // Comentario para enlazar
                service: 'pppoe'
            };

            const response = await fetch(`${API_BASE_URL}/api/routers/${host}/pppoe/secrets`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to create service');
            }

            alert('¡Servicio PPPoE creado exitosamente!');
            closeClientModal();
            
        } catch (error) {
            pppoeFormErrorMain.textContent = `Error: ${error.message}`;
            pppoeFormErrorMain.classList.remove('hidden');
        }
    }


    // --- INICIALIZACIÓN Y EVENT LISTENERS ---
    
    // Filtros de estado
    document.querySelectorAll('.filter-button').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.filter-button').forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            currentFilters.serviceStatus = button.dataset.status;
            renderClients();
        });
    });

    // Búsqueda
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            currentFilters.searchTerm = e.target.value;
            renderClients();
        });
    }

    // Modal
    if (addClientButton) addClientButton.addEventListener('click', () => openClientModal());
    if (cancelClientButton) cancelClientButton.addEventListener('click', closeClientModal);
    if (cancelClientButtonX) cancelClientButtonX.addEventListener('click', closeClientModal);
    if (cancelClientButtonTab2) cancelClientButtonTab2.addEventListener('click', closeClientModal);
    if (clientModal) clientModal.addEventListener('click', (e) => { if (e.target === clientModal) closeClientModal(); });
    
    // Pestañas
    if (tabBtnInfo) tabBtnInfo.addEventListener('click', () => switchTab('info'));
    if (tabBtnService) tabBtnService.addEventListener('click', () => switchTab('service'));

    // Formularios
    if (clientForm) clientForm.addEventListener('submit', handleClientFormSubmit);
    if (pppoeServiceForm) pppoeServiceForm.addEventListener('submit', handlePppoeFormSubmit);
    
    // Botón de Asignar CPE
    const assignCpeButton = document.getElementById('assign-cpe-button');
    if (assignCpeButton) {
        assignCpeButton.addEventListener('click', handleAssignCPE);
    }
    
    // Select de Router (Pestaña 2)
    if (pppoeRouterSelect) pppoeRouterSelect.addEventListener('change', handleRouterSelectChange);
    if (cancelPppoeFormBtn) cancelPppoeFormBtn.addEventListener('click', () => {
         pppoeServiceForm.classList.add('hidden');
         // (Aquí podríamos mostrar un botón de "Crear servicio" de nuevo)
    });

    // Carga inicial
    loadAllClients();
    initializeAutoRefresh();
});