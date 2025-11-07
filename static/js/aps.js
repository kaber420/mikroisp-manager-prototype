// static/js/aps.js

document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;
    let allAps = [];
    let allZones = [];
    let currentFilter = { zoneId: null, searchTerm: '' };
    let refreshIntervalId = null;

    // --- REFERENCIAS A ELEMENTOS DEL DOM ---
    const addApButton = document.getElementById('add-ap-button');
    const addApModal = document.getElementById('add-ap-modal');
    const addApForm = document.getElementById('add-ap-form');
    const cancelApButton = document.getElementById('cancel-button');
    const zoneSelect = document.getElementById('zona_id'); // Para el modal
    const apFormError = document.getElementById('form-error-main'); 
    const searchInput = document.getElementById('search-input');
    const zoneFilterSelect = document.getElementById('zone-filter-select'); 

    // --- LÓGICA DE FILTRADO Y RENDERIZADO (Sin cambios) ---
    function renderAps() {
        // ... (esta función no cambia)
        const tableBody = document.getElementById('ap-table-body');
        if (!tableBody) return;

        const filteredAps = allAps.filter(ap => {
            const searchTerm = currentFilter.searchTerm.toLowerCase();
            const searchMatch = !searchTerm || 
                (ap.hostname && ap.hostname.toLowerCase().includes(searchTerm)) || 
                ap.host.toLowerCase().includes(searchTerm) || 
                (ap.mac && ap.mac.toLowerCase().includes(searchTerm));
    
            const zoneMatch = currentFilter.zoneId == null || ap.zona_id === currentFilter.zoneId;
            return searchMatch && zoneMatch;
        });

        tableBody.style.filter = 'blur(4px)';
        tableBody.style.opacity = '0.6';
        tableBody.style.transition = 'filter 0.3s ease, opacity 0.3s ease';

        setTimeout(() => {
            tableBody.innerHTML = '';
            if (filteredAps.length === 0) {
                const emptyRow = document.createElement('tr');
                emptyRow.innerHTML = '<td colspan="6" class="text-center p-8 text-text-secondary">No Access Points match the current filter.</td>';
                tableBody.appendChild(emptyRow);
            } else {
                filteredAps.forEach(ap => {
                    const row = document.createElement('tr');
                    row.className = "hover:bg-surface-2 cursor-pointer transition-colors duration-200";
                    row.onclick = () => { window.location.href = `/ap/${encodeURIComponent(ap.host)}`; };

                    const clientCount = ap.client_count != null ? ap.client_count : 'N/A';
                    const airtime = ap.airtime_total_usage != null ? `${(ap.airtime_total_usage / 10.0).toFixed(1)}%` : 'N/A';

                    row.innerHTML = `
                        <td class="px-6 py-4 whitespace-nowrap">${renderStatusBadge(ap.last_status)}</td>
                        <td class="px-6 py-4 whitespace-nowrap font-semibold text-text-primary">${ap.hostname || "N/A"}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-text-secondary">${ap.zona_nombre || "Unassigned"}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-text-secondary font-mono">${ap.host}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-text-primary font-semibold">${clientCount}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-text-primary font-semibold">${airtime}</td>
                    `;
                    tableBody.appendChild(row);
                });
            }

            setTimeout(() => {
                tableBody.style.filter = 'blur(0px)';
                tableBody.style.opacity = '1';
            }, 50);
        }, 300);
    }

    // --- MANEJO DEL MODAL DE AP (Sin cambios) ---
    function openApModal() { 
        formUtils.resetModalForm('add-ap-modal');
        populateZoneSelect(); 
        if (addApModal) addApModal.classList.add('is-open'); 
    }
    
    function closeApModal() { 
        if (addApModal) addApModal.classList.remove('is-open'); 
    }

    async function handleApFormSubmit(event) {
        event.preventDefault();
        
        formUtils.clearFormErrors(addApForm);
        let isValid = true;
        
        const formData = new FormData(addApForm);
        const data = Object.fromEntries(formData.entries());

        // --- INICIO DE CAMBIO: Lógica de validación actualizada ---
        // 1. Validar Host (con la nueva regla inteligente)
        if (!validators.isValidIpOrHostname(data.host)) {
            formUtils.showFieldError('host', 'Debe ser una IP (ej. 1.2.3.4) o un hostname (ej. ap-1.local) válido.');
            isValid = false;
        }
        // --- FIN DE CAMBIO ---

        // 2. Validar Zona
        if (!validators.isRequired(data.zona_id)) {
            formUtils.showFieldError('zona_id', 'Debe seleccionar una zona.');
            isValid = false;
        }
        // 3. Validar Username
        if (!validators.isRequired(data.username)) {
            formUtils.showFieldError('username', 'El usuario es requerido.');
            isValid = false;
        }
        // 4. Validar Password
        if (!validators.isRequired(data.password)) {
            formUtils.showFieldError('password', 'La contraseña es requerida.');
            isValid = false;
        }

        if (!isValid) return; // Detener si hay errores
        
        // Convertir a tipos correctos
        data.zona_id = parseInt(data.zona_id, 10);

        try {
            const response = await fetch(`${API_BASE_URL}/api/aps`, { 
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify(data) 
            });
            if (!response.ok) { 
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to create AP'); 
            }
            closeApModal();
            loadInitialData(); 
        } catch (error) { 
            if (apFormError) {
                apFormError.textContent = `Error: ${error.message}`;
                apFormError.classList.remove('hidden');
            }
        }
    }

    // --- FUNCIONES DE CARGA DE DATOS (Sin cambios) ---
    
    async function populateZoneSelect() {
        // ... (esta función no cambia)
        if (!zoneSelect) return;
        try {
            if (allZones.length === 0) {
                 const response = await fetch(`${API_BASE_URL}/api/zonas`);
                 if (!response.ok) throw new Error('Failed to load zones');
                 allZones = await response.json();
            }
            
            zoneSelect.innerHTML = '<option value="">Select a zone...</option>';
            allZones.forEach(zone => { 
                const option = document.createElement('option'); 
                option.value = zone.id; 
                option.textContent = zone.nombre; 
                zoneSelect.appendChild(option); 
            });
        } catch (error) { 
            console.error('Failed to load zones for modal:', error);
            zoneSelect.innerHTML = '<option value="">Could not load zones</option>'; 
        }
    }

    function populateZoneFilterSelect() {
        // ... (esta función no cambia)
        if (!zoneFilterSelect) return;
        
        const currentValue = zoneFilterSelect.value;
        
        zoneFilterSelect.innerHTML = '<option value="">All Zones</option>';
        allZones.forEach(zone => {
            const option = document.createElement('option');
            option.value = zone.id;
            option.textContent = zone.nombre;
            zoneFilterSelect.appendChild(option);
        });
        
        zoneFilterSelect.value = currentValue;
    }


    function renderStatusBadge(status) {
        // ... (esta función no cambia)
        if (status === 'online') return `<div class="flex items-center gap-2"><div class="size-2 rounded-full bg-success"></div><span>Online</span></div>`;
        if (status === 'offline') return `<div class="flex items-center gap-2 text-danger"><div class="size-2 rounded-full bg-danger"></div><span>Offline</span></div>`;
        return `<div class="flex items-center gap-2 text-text-secondary"><div class="size-2 rounded-full bg-text-secondary"></div><span>Unknown</span></div>`;
    }

    async function loadInitialData() {
        // ... (esta función no cambia)
        const tableBody = document.getElementById('ap-table-body');
        if (!tableBody) {
            console.error("AP table body not found, cannot load data.");
            return;
        }
        
        try {
            const zonesRes = await fetch(`${API_BASE_URL}/api/zonas`);
            if (!zonesRes.ok) throw new Error('Failed to load zones');
            allZones = await zonesRes.json();
            populateZoneFilterSelect(); 
        } catch (error) {
            console.error("Error loading zones:", error);
            if(zoneFilterSelect) {
                 zoneFilterSelect.innerHTML = '<option value="">Error loading zones</option>';
            }
        }

        if (tableBody.children.length === 0 || !tableBody.querySelector('tr')) { 
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center p-8 text-text-secondary">Loading network data...</td></tr>';
        }

        try {
            const apsRes = await fetch(`${API_BASE_URL}/api/aps`);
            if (!apsRes.ok) throw new Error('Failed to load APs');
            allAps = await apsRes.json();
            renderAps(); 
        } catch (error) {
            console.error("Error loading initial data (APs):", error);
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center p-8 text-danger">Failed to load network data.</td></tr>`;
        }
    }
    
    async function initializeAppLogic() {
        // ... (esta función no cambia)
        // Listeners del Modal
        if (addApButton) addApButton.addEventListener('click', openApModal);
        if (cancelApButton) cancelApButton.addEventListener('click', closeApModal);
        if (addApForm) addApForm.addEventListener('submit', handleApFormSubmit);
        if (addApModal) addApModal.addEventListener('click', (e) => { if (e.target === addApModal) closeApModal(); });
        
        // Listeners de Filtros
        if (searchInput) {
            searchInput.addEventListener('input', (e) => { 
                currentFilter.searchTerm = e.target.value.toLowerCase(); 
                renderAps(); 
            });
        }
        
        if (zoneFilterSelect) {
            zoneFilterSelect.addEventListener('change', (e) => {
                const zoneId = e.target.value;
                currentFilter.zoneId = zoneId ? parseInt(zoneId, 10) : null;
                renderAps();
            });
        }

        await loadInitialData();
        
        try {
            const settingsResponse = await fetch(`${API_BASE_URL}/api/settings`);
            const settings = await settingsResponse.json();
            const refreshIntervalSeconds = parseInt(settings.dashboard_refresh_interval, 10);
            if (refreshIntervalSeconds && refreshIntervalSeconds > 0) {
                if (refreshIntervalId) clearInterval(refreshIntervalId);
                refreshIntervalId = setInterval(loadInitialData, refreshIntervalSeconds * 1000);
                console.log(`APs page auto-refresh configured for every ${refreshIntervalSeconds} seconds.`);
            } else {
                console.log('APs page auto-refresh is disabled.');
            }
        } catch (error) {
            console.error("Could not load settings for auto-refresh, using default.", error);
            if (refreshIntervalId) clearInterval(refreshIntervalId);
            refreshIntervalId = setInterval(loadInitialData, 60000);
        }
    }
    
    initializeAppLogic();
});