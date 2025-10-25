document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;
    let allClients = [];
    let currentFilters = { searchTerm: '', serviceStatus: 'all' };
    let refreshIntervalId = null;

    // --- REFERENCIAS AL DOM ---
    const searchInput = document.getElementById('search-input');
    const tableBody = document.getElementById('client-table-body');
    const addClientButton = document.getElementById('add-client-button');
    const clientModal = document.getElementById('client-modal');
    const clientForm = document.getElementById('client-form');
    const cancelClientButton = document.getElementById('cancel-client-button');
    const cancelClientButtonX = document.getElementById('cancel-client-button-x');
    const clientFormError = document.getElementById('client-form-error');
    const modalTitle = document.getElementById('modal-title');
    const clientIdInput = document.getElementById('client-id');
    const assignedCPEsSection = document.getElementById('assigned-cpes-section');

    /**
     * Devuelve la clase para un badge de estado de servicio.
     * @param {string} status - 'active', 'suspended', o 'cancelled'.
     * @returns {string}
     */
    function getStatusBadgeClass(status) {
        switch (status) {
            case 'active': return 'bg-success/20 text-success';
            case 'suspended': return 'bg-warning/20 text-warning';
            case 'cancelled': return 'bg-danger/20 text-danger';
            default: return 'bg-text-secondary/20 text-text-secondary';
        }
    }

    /**
     * Renderiza la tabla de clientes basada en los filtros actuales.
     */
    function renderClients() {
        if (!tableBody) return;

        let filteredClients = allClients;

        // Filtrar por estado de servicio
        if (currentFilters.serviceStatus !== 'all') {
            filteredClients = filteredClients.filter(client => client.service_status === currentFilters.serviceStatus);
        }

        // Filtrar por término de búsqueda
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

    /**
     * Carga todos los clientes desde la API.
     */
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
     * @param {object|null} client - El objeto del cliente para editar, o null para crear.
     */
    async function openClientModal(client = null) {
        clientForm.reset();
        clientFormError.classList.add('hidden');
        assignedCPEsSection.classList.add('hidden');

        if (client) { // Modo Edición
            modalTitle.textContent = 'Edit Client';
            clientIdInput.value = client.id;
            
            // Poblar formulario
            document.getElementById('client-name').value = client.name;
            document.getElementById('client-email').value = client.email || '';
            document.getElementById('client-phone_number').value = client.phone_number || '';
            document.getElementById('client-whatsapp_number').value = client.whatsapp_number || '';
            document.getElementById('client-address').value = client.address || '';
            document.getElementById('client-service_status').value = client.service_status;
            document.getElementById('client-suspension_method').value = client.suspension_method || '';
            document.getElementById('client-billing_day').value = client.billing_day || '';
            document.getElementById('client-notes').value = client.notes || '';
            
            // Cargar y mostrar CPEs
            assignedCPEsSection.classList.remove('hidden');
            await loadAndRenderAssignedCPEs(client.id);
            await populateUnassignedCPEs();
        } else { // Modo Creación
            modalTitle.textContent = 'Add New Client';
            clientIdInput.value = '';
        }
        clientModal.classList.add('is-open');
    }

    function closeClientModal() {
        if (clientModal) clientModal.classList.remove('is-open');
    }

    /**
     * Maneja el envío del formulario de cliente.
     */
    async function handleClientFormSubmit(event) {
        event.preventDefault();
        const clientId = clientIdInput.value;
        const isEditing = !!clientId;
        
        const url = isEditing ? `${API_BASE_URL}/api/clients/${clientId}` : `${API_BASE_URL}/api/clients`;
        const method = isEditing ? 'PUT' : 'POST';
        
        const formData = new FormData(clientForm);
        const data = Object.fromEntries(formData.entries());

        // Limpiar campos opcionales vacíos para que no se envíen como ""
        for (const key in data) {
            if (data[key] === '') {
                data[key] = null;
            }
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
            closeClientModal();
            loadAllClients(); // Recargar la lista
        } catch (error) {
            clientFormError.textContent = `Error: ${error.message}`;
            clientFormError.classList.remove('hidden');
        }
    }

    /**
     * Maneja la eliminación de un cliente.
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

    /**
     * Carga y muestra los CPEs asignados a un cliente en el modal.
     */
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

    /**
     * Puebla el <select> con los CPEs que no tienen dueño.
     */
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

    /**
     * Maneja el clic en el botón "Assign CPE".
     */
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
            // Recargar ambas listas para reflejar el cambio
            await loadAndRenderAssignedCPEs(clientId);
            await populateUnassignedCPEs();
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    }

    /**
     * Maneja el clic en el botón "Unassign".
     */
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


    /**
     * Configura y arranca el refresco automático de la página.
     */
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
    if (clientModal) clientModal.addEventListener('click', (e) => { if (e.target === clientModal) closeClientModal(); });
    if (clientForm) clientForm.addEventListener('submit', handleClientFormSubmit);

    // Botón de Asignar CPE
    const assignCpeButton = document.getElementById('assign-cpe-button');
    if (assignCpeButton) {
        assignCpeButton.addEventListener('click', handleAssignCPE);
    }

    // Carga inicial
    loadAllClients();
    initializeAutoRefresh();
});