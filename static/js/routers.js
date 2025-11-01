document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;
    let allRouters = [];
    let allZones = [];

    // --- REFERENCIAS AL DOM (Página Principal) ---
    const addRouterButton = document.getElementById('add-router-button');
    const tableBody = document.getElementById('router-table-body');

    // --- REFERENCIAS AL DOM (Modal de Añadir/Editar Router) ---
    const routerModal = document.getElementById('router-modal');
    const routerForm = document.getElementById('router-form');
    const cancelRouterButton = document.getElementById('cancel-router-button');
    const cancelRouterButtonX = document.getElementById('cancel-router-button-x');
    const routerFormError = document.getElementById('router-form-error');
    const modalTitle = document.getElementById('modal-title');
    const routerHostInput = document.getElementById('router-host');
    const routerHostEditInput = document.getElementById('router-host-edit');
    const routerZoneSelect = document.getElementById('router-zona_id');

    // --- REFERENCIAS AL DOM (Modal de Aprovisionamiento) ---
    const provisionModal = document.getElementById('provision-modal');
    const provisionForm = document.getElementById('provision-form');
    const provisionModalTitle = document.getElementById('provision-modal-title');
    const provisionHostInput = document.getElementById('provision-host');
    const cancelProvisionButton = document.getElementById('cancel-provision-button');
    const startProvisionButton = document.getElementById('start-provision-button');
    const provisionFeedback = document.getElementById('provision-feedback');
    const provisionSpinner = document.getElementById('provision-spinner');
    const provisionStatusText = document.getElementById('provision-status-text');
    const provisionErrorDetails = document.getElementById('provision-error-details');


    /**
     * Carga y renderiza la lista de routers.
     */
    async function loadRouters() {
        if (!tableBody) return;
        tableBody.innerHTML = '<tr><td colspan="6" class="p-8 text-center text-text-secondary">Loading routers...</td></tr>';
        
        try {
            const [routersRes, zonesRes] = await Promise.all([
                fetch(`${API_BASE_URL}/api/routers`),
                fetch(`${API_BASE_URL}/api/zonas`)
            ]);

            if (!routersRes.ok) throw new Error('Failed to load routers');
            if (!zonesRes.ok) throw new Error('Failed to load zones');
            
            allRouters = await routersRes.json();
            allZones = await zonesRes.json();
            
            renderRouters();
            populateZoneSelect(routerZoneSelect);

        } catch (error) {
            console.error("Error loading routers:", error);
            tableBody.innerHTML = `<tr><td colspan="6" class="p-8 text-center text-danger">Failed to load routers.</td></tr>`;
        }
    }

    /**
     * Renderiza la tabla de routers basada en los datos cargados.
     */
    function renderRouters() {
        if (!tableBody) return;
        tableBody.innerHTML = '';

        if (allRouters.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="6" class="p-8 text-center text-text-secondary">No routers found. Click "Add New Router" to get started.</td></tr>`;
            return;
        }

        allRouters.forEach(router => {
            const row = document.createElement('tr');
            row.className = "hover:bg-surface-2 transition-colors duration-200";
            
            const zone = allZones.find(z => z.id === router.zona_id);
            const status = getStatusBadge(router.last_status, router.api_port);
            
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap">${status.html}</td>
                <td class="px-6 py-4 whitespace-nowrap font-semibold text-text-primary">${router.hostname || 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-text-secondary font-mono">${router.host}</td>
                <td class="px-6 py-4 whitespace-nowrap text-text-secondary">${zone ? zone.nombre : 'Unassigned'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-text-secondary">${router.model || 'N/A'} / ${router.firmware || 'N/A'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-center space-x-2">
                    ${status.provisionButton}
                    <button class="edit-btn text-text-secondary hover:text-primary" title="Edit Router">
                        <span class="material-symbols-outlined">edit</span>
                    </button>
                    <button class="delete-btn text-text-secondary hover:text-danger" title="Delete Router">
                        <span class="material-symbols-outlined">delete</span>
                    </button>
                </td>
            `;

            // Añadir event listeners a los botones
            const provisionBtn = row.querySelector('.provision-btn');
            if (provisionBtn) {
                provisionBtn.onclick = () => openProvisionModal(router);
            }
            row.querySelector('.edit-btn').onclick = () => openRouterModal(router);
            row.querySelector('.delete-btn').onclick = () => handleDeleteRouter(router.host, router.hostname);
            
            tableBody.appendChild(row);
        });
    }

    /**
     * Genera el badge de estado y el botón de aprovisionamiento.
     */
    function getStatusBadge(status, apiPort) {
        // Si el puerto es 8728, significa que no está aprovisionado.
        if (apiPort === 8728) {
            return {
                html: `<div class="flex items-center gap-2 text-warning"><div class="size-2 rounded-full bg-warning"></div><span>Needs Provisioning</span></div>`,
                provisionButton: `<button class="provision-btn px-2 py-1 text-xs font-semibold rounded-md bg-orange/20 text-orange hover:bg-orange/30" title="Provision Router">Provision</button>`
            };
        }

        let html = '';
        switch (status) {
            case 'online':
                html = `<div class="flex items-center gap-2 text-success"><div class="size-2 rounded-full bg-success"></div><span>Online</span></div>`;
                break;
            case 'offline':
                html = `<div class="flex items-center gap-2 text-danger"><div class="size-2 rounded-full bg-danger"></div><span>Offline</span></div>`;
                break;
            default:
                html = `<div class="flex items-center gap-2 text-text-secondary"><div class="size-2 rounded-full bg-text-secondary"></div><span>Unknown</span></div>`;
        }

        return { html, provisionButton: '' };
    }

    /**
     * Rellena el <select> de zonas en los modales.
     */
    function populateZoneSelect(selectElement) {
        if (!selectElement) return;
        const currentVal = selectElement.value;
        selectElement.innerHTML = '<option value="">Select a zone...</option>';
        allZones.forEach(zone => {
            const option = document.createElement('option');
            option.value = zone.id;
            option.textContent = zone.nombre;
            if (zone.id.toString() === currentVal) {
                option.selected = true;
            }
            selectElement.appendChild(option);
        });
    }

    /**
     * Abre el modal para añadir o editar un router.
     * @param {object|null} router - El objeto router para editar, o null para crear.
     */
    function openRouterModal(router = null) {
        routerForm.reset();
        routerFormError.classList.add('hidden');
        populateZoneSelect(routerZoneSelect);

        if (router) { // Modo Edición
            modalTitle.textContent = 'Edit Router';
            routerHostEditInput.value = router.host; // Guarda el host original para el PUT
            routerHostInput.value = router.host;
            routerHostInput.readOnly = true;
            routerHostInput.classList.add('bg-surface-2', 'cursor-not-allowed');

            // Poblar el formulario
            document.getElementById('router-zona_id').value = router.zona_id || '';
            document.getElementById('router-api_port').value = router.api_port || 8728;
            document.getElementById('router-username').value = router.username;
            document.getElementById('router-password').placeholder = "Leave blank to keep current password";
            document.getElementById('router-password').required = false;

        } else { // Modo Creación
            modalTitle.textContent = 'Add New Router';
            routerHostEditInput.value = '';
            routerHostInput.readOnly = false;
            routerHostInput.classList.remove('bg-surface-2', 'cursor-not-allowed');
            document.getElementById('router-api_port').value = 8728;
            document.getElementById('router-username').value = 'admin';
            document.getElementById('router-password').placeholder = "Admin password";
            document.getElementById('router-password').required = true;
        }
        routerModal.classList.add('is-open');
    }

    function closeRouterModal() {
        routerModal.classList.remove('is-open');
        routerForm.reset();
    }

    /**
     * Maneja el guardado (POST o PUT) de un router.
     */
    async function handleRouterFormSubmit(event) {
        event.preventDefault();
        const formData = new FormData(routerForm);
        const data = Object.fromEntries(formData.entries());
        
        // Convertir a tipos correctos
        data.zona_id = parseInt(data.zona_id, 10) || null;
        data.api_port = parseInt(data.api_port, 10) || 8728;
        
        const isEditing = !!data.host_edit;
        const host = isEditing ? data.host_edit : data.host;
        const url = isEditing ? `${API_BASE_URL}/api/routers/${encodeURIComponent(host)}` : `${API_BASE_URL}/api/routers`;
        const method = isEditing ? 'PUT' : 'POST';

        // En modo edición, no enviar la contraseña si está vacía
        if (isEditing && !data.password) {
            delete data.password;
        }
        // No enviar el campo auxiliar
        delete data.host_edit;

        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Failed to ${isEditing ? 'update' : 'create'} router`);
            }
            closeRouterModal();
            loadRouters(); // Recargar la lista
        } catch (error) {
            routerFormError.textContent = `Error: ${error.message}`;
            routerFormError.classList.remove('hidden');
        }
    }

    /**
     * Maneja la eliminación de un router.
     */
    async function handleDeleteRouter(host, hostname) {
        const displayName = hostname || host;
        if (confirm(`Are you sure you want to delete router "${displayName}" (${host})?\nThis action cannot be undone.`)) {
            try {
                const response = await fetch(`${API_BASE_URL}/api/routers/${encodeURIComponent(host)}`, { method: 'DELETE' });
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Failed to delete router');
                }
                loadRouters();
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }
    }

    /**
     * Abre el modal de aprovisionamiento.
     */
    function openProvisionModal(router) {
        provisionForm.reset();
        provisionHostInput.value = router.host;
        provisionModalTitle.textContent = `Provision Router: ${router.hostname || router.host}`;
        
        // Resetear UI de feedback
        provisionFeedback.classList.add('hidden');
        provisionErrorDetails.classList.add('hidden');
        provisionErrorDetails.textContent = '';
        provisionStatusText.textContent = 'Aprovisionando, por favor espera...';
        startProvisionButton.disabled = false;
        provisionSpinner.classList.add('animate-spin');
        provisionStatusText.classList.remove('text-success', 'text-danger');
        
        document.getElementById('provision-new-user').value = 'api-user'; // Default
        
        provisionModal.classList.add('is-open');
    }

    function closeProvisionModal() {
        provisionModal.classList.remove('is-open');
    }

    /**
     * Maneja el envío del formulario de aprovisionamiento.
     */
    async function handleProvisionFormSubmit(event) {
        event.preventDefault();
        startProvisionButton.disabled = true;
        provisionFeedback.classList.remove('hidden');
        provisionErrorDetails.classList.add('hidden');
        provisionErrorDetails.textContent = '';
        provisionSpinner.style.display = 'inline-block';
        provisionStatusText.textContent = 'Contactando al router...';

        const host = provisionHostInput.value;
        const newUser = document.getElementById('provision-new-user').value;
        const newPass = document.getElementById('provision-new-pass').value;

        if (!host || !newUser || !newPass) {
            provisionStatusText.textContent = 'Todos los campos son requeridos.';
            provisionStatusText.classList.add('text-danger');
            startProvisionButton.disabled = false;
            return;
        }
        
        const data = {
            new_api_user: newUser,
            new_api_password: newPass
        };

        try {
            provisionStatusText.textContent = 'Aprovisionando, esto puede tardar un minuto...';
            const response = await fetch(`${API_BASE_URL}/api/routers/${encodeURIComponent(host)}/provision`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Error desconocido durante el aprovisionamiento');
            }

            const result = await response.json();
            
            // Éxito
            provisionStatusText.textContent = '¡Aprovisionado con éxito!';
            provisionStatusText.classList.add('text-success');
            provisionSpinner.style.display = 'none';
            
            // Cerrar modal y recargar lista después de 2 segundos
            setTimeout(() => {
                closeProvisionModal();
                loadRouters();
            }, 2000);

        } catch (error) {
            provisionStatusText.textContent = 'Error de aprovisionamiento:';
            provisionStatusText.classList.add('text-danger');
            provisionErrorDetails.textContent = error.message;
            provisionErrorDetails.classList.remove('hidden');
            provisionSpinner.style.display = 'none';
            startProvisionButton.disabled = false;
        }
    }


    // --- INICIALIZACIÓN Y EVENT LISTENERS ---
    
    // Botones de la página principal
    if (addRouterButton) addRouterButton.addEventListener('click', () => openRouterModal());

    // Botones del modal de Router
    if (cancelRouterButton) cancelRouterButton.addEventListener('click', closeRouterModal);
    if (cancelRouterButtonX) cancelRouterButtonX.addEventListener('click', closeRouterModal);
    if (routerModal) routerModal.addEventListener('click', (e) => { if (e.target === routerModal) closeRouterModal(); });
    if (routerForm) routerForm.addEventListener('submit', handleRouterFormSubmit);

    // Botones del modal de Aprovisionamiento
    if (cancelProvisionButton) cancelProvisionButton.addEventListener('click', closeProvisionModal);
    if (provisionModal) provisionModal.addEventListener('click', (e) => { if (e.target === provisionModal) closeProvisionModal(); });
    if (provisionForm) provisionForm.addEventListener('submit', handleProvisionFormSubmit);

    // Carga inicial
    loadRouters();
});