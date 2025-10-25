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
    const zoneSelect = document.getElementById('zona_id');
    const apFormError = document.getElementById('form-error');
    const searchInput = document.getElementById('search-input');

    // --- LÓGICA DE FILTRADO Y RENDERIZADO CON BLUR SUAVE ---
    function renderAps() {
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

        // Aplicar blur suave a la tabla
        tableBody.style.filter = 'blur(4px)';
        tableBody.style.opacity = '0.6';
        tableBody.style.transition = 'filter 0.3s ease, opacity 0.3s ease';

        // Esperar un momento para que se vea el blur
        setTimeout(() => {
            // Actualizar contenido
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

            // Remover blur suavemente
            setTimeout(() => {
                tableBody.style.filter = 'blur(0px)';
                tableBody.style.opacity = '1';
            }, 50);
        }, 300);
    }

    function applyFilter(zoneId = null) {
        currentFilter.zoneId = zoneId;
        const zone = allZones.find(z => z.id === zoneId);
        document.getElementById('dashboard-title').textContent = zone ? `Zone: ${zone.nombre}` : 'Dashboard';
        document.querySelectorAll('.nav-link-zone').forEach(link => {
            link.classList.remove('active');
            if ((zoneId === null && link.id === 'all-zones-link') || (zoneId !== null && link.dataset.zoneId == zoneId)) {
                link.classList.add('active');
            }
        });
        renderAps();
    }

    // --- MANEJO DEL MODAL DE AP ---
    function openApModal() { 
        populateZoneSelect(); 
        if (addApModal) addApModal.classList.add('is-open'); 
    }
    function closeApModal() { 
        if (addApForm) addApForm.reset(); 
        if (apFormError) apFormError.classList.add('hidden'); 
        if (addApModal) addApModal.classList.remove('is-open'); 
    }
    async function handleApFormSubmit(event) {
        event.preventDefault();
        const formData = new FormData(addApForm);
        const data = { 
            host: formData.get('host'), 
            username: formData.get('username'), 
            password: formData.get('password'), 
            zona_id: parseInt(formData.get('zona_id'), 10) 
        };
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
            initializeDashboard();
        } catch (error) { 
            if (apFormError) {
                apFormError.textContent = `Error: ${error.message}`; 
                apFormError.classList.remove('hidden');
            }
        }
    }

    // --- FUNCIONES DE CARGA DE DATOS ---
    async function populateZoneSelect() {
        if (!zoneSelect) return;
        try {
            const response = await fetch(`${API_BASE_URL}/api/zonas`);
            const zones = await response.json();
            zoneSelect.innerHTML = '<option value="">Select a zone...</option>';
            zones.forEach(zone => { 
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

    function renderStatusBadge(status) {
        if (status === 'online') return `<div class="flex items-center gap-2"><div class="size-2 rounded-full bg-success"></div><span>Online</span></div>`;
        if (status === 'offline') return `<div class="flex items-center gap-2 text-danger"><div class="size-2 rounded-full bg-danger"></div><span>Offline</span></div>`;
        return `<div class="flex items-center gap-2 text-text-secondary"><div class="size-2 rounded-full bg-text-secondary"></div><span>Unknown</span></div>`;
    }

    async function loadTopStats() {
        const topAirtimeList = document.getElementById('top-airtime-list');
        const topSignalList = document.getElementById('top-signal-list');
        if (!topAirtimeList || !topSignalList) return;

        topAirtimeList.style.filter = 'blur(4px)';
        topAirtimeList.style.opacity = '0.6';
        topSignalList.style.filter = 'blur(4px)';
        topSignalList.style.opacity = '0.6';
        topAirtimeList.style.transition = 'filter 0.3s ease, opacity 0.3s ease';
        topSignalList.style.transition = 'filter 0.3s ease, opacity 0.3s ease';

        try {
            // --- CAMBIO: Actualizado el endpoint para CPEs ---
            const [airtimeRes, signalRes] = await Promise.all([
                fetch(`${API_BASE_URL}/api/stats/top-aps-by-airtime`),
                fetch(`${API_BASE_URL}/api/stats/top-cpes-by-signal`)
            ]);
            
            if (!airtimeRes.ok || !signalRes.ok) {
                 throw new Error('Failed to fetch top stats');
            }

            const topAirtime = await airtimeRes.json();
            const topSignal = await signalRes.json();
            
            setTimeout(() => {
                topAirtimeList.innerHTML = '';
                if(topAirtime.length > 0) {
                    topAirtime.forEach(ap => { 
                        topAirtimeList.innerHTML += `<div class="flex items-center justify-between"><p class="text-sm font-medium truncate">${ap.hostname || ap.host}</p><span class="text-sm font-bold text-warning">${(ap.airtime_total_usage / 10.0).toFixed(1)}%</span></div>`; 
                    });
                } else { 
                    topAirtimeList.innerHTML = `<div class="text-text-secondary text-sm">No airtime data available.</div>`; 
                }
                
                topSignalList.innerHTML = '';
                if(topSignal.length > 0) {
                    // --- CAMBIO: Actualizados los nombres de campo ---
                    topSignal.forEach(cpe => { 
                        topSignalList.innerHTML += `<div class="flex items-center justify-between"><p class="text-sm font-medium truncate">${cpe.cpe_hostname || cpe.cpe_mac}</p><span class="text-sm font-bold text-danger">${cpe.signal} dBm</span></div>`; 
                    });
                } else { 
                    topSignalList.innerHTML = `<div class="text-text-secondary text-sm">No CPE signal data available.</div>`; 
                }

                setTimeout(() => {
                    topAirtimeList.style.filter = 'blur(0px)';
                    topAirtimeList.style.opacity = '1';
                    topSignalList.style.filter = 'blur(0px)';
                    topSignalList.style.opacity = '1';
                }, 50);
            }, 300);
        } catch (error) {
            console.error("Error loading top stats:", error);
            topAirtimeList.innerHTML = `<div class="text-danger text-sm">Error loading data.</div>`;
            topSignalList.innerHTML = `<div class="text-danger text-sm">Error loading data.</div>`;
            topAirtimeList.style.filter = 'blur(0px)';
            topAirtimeList.style.opacity = '1';
            topSignalList.style.filter = 'blur(0px)';
            topSignalList.style.opacity = '1';
        }
    }

    async function loadInitialData() {
        const tableBody = document.getElementById('ap-table-body');
        if (!tableBody) {
            console.error("AP table body not found, cannot load data.");
            return;
        }
        
        if (tableBody.children.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center p-8 text-text-secondary">Loading network data...</td></tr>';
        }

        try {
            const [zonesRes, apsRes] = await Promise.all([ 
                fetch(`${API_BASE_URL}/api/zonas`), 
                fetch(`${API_BASE_URL}/api/aps`) 
            ]);
            if (!zonesRes.ok) throw new Error('Failed to load zones');
            if (!apsRes.ok) throw new Error('Failed to load APs');
            allZones = await zonesRes.json();
            allAps = await apsRes.json();
            
            const nav = document.getElementById('zones-nav');
            if (nav && nav.children.length === 0) {
                nav.innerHTML = `<a href="#" id="all-zones-link" class="nav-link-zone nav-link flex items-center gap-3 px-3 py-2 rounded-lg"><span class="material-symbols-outlined">grid_view</span><span class="text-sm">All Zones</span></a>`;
                allZones.forEach(zone => {
                    const link = document.createElement('a');
                    link.href = `#`;
                    link.dataset.zoneId = zone.id;
                    link.className = 'nav-link-zone nav-link flex items-center gap-3 px-3 py-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-surface-2';
                    link.innerHTML = `<span class="material-symbols-outlined">router</span><span class="text-sm">${zone.nombre}</span>`;
                    nav.appendChild(link);
                });
                nav.querySelectorAll('.nav-link-zone').forEach(link => {
                    link.addEventListener('click', (e) => { 
                        e.preventDefault(); 
                        const zoneId = link.dataset.zoneId ? parseInt(link.dataset.zoneId, 10) : null; 
                        applyFilter(zoneId); 
                    });
                });
            }

            let totalClients = 0;
            allAps.forEach(ap => { 
                if (ap.last_status === 'online' && ap.client_count != null) { 
                    totalClients += ap.client_count; 
                } 
            });
            
            updateStatWithTransition('total-aps', allAps.length);
            updateStatWithTransition('aps-online', allAps.filter(ap => ap.last_status === 'online').length);
            updateStatWithTransition('aps-offline', allAps.filter(ap => ap.last_status === 'offline').length);
            updateStatWithTransition('total-clients', totalClients);
            
            applyFilter(currentFilter.zoneId);
            loadTopStats();
        } catch (error) {
            console.error("Error loading initial data:", error);
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center p-8 text-danger">Failed to load network data.</td></tr>`;
        }
    }

    function updateStatWithTransition(elementId, newValue) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        const currentValue = element.textContent;
        if (currentValue === newValue.toString()) return;
        
        element.style.transition = 'opacity 0.2s ease';
        element.style.opacity = '0.5';
        
        setTimeout(() => {
            element.textContent = newValue;
            element.style.opacity = '1';
        }, 200);
    }
    
    async function initializeDashboard() {
        if (addApButton) addApButton.addEventListener('click', openApModal);
        if (cancelApButton) cancelApButton.addEventListener('click', closeApModal);
        if (addApForm) addApForm.addEventListener('submit', handleApFormSubmit);
        if (addApModal) addApModal.addEventListener('click', (e) => { if (e.target === addApModal) closeApModal(); });
        if (searchInput) searchInput.addEventListener('input', (e) => { currentFilter.searchTerm = e.target.value.toLowerCase(); renderAps(); });

        await loadInitialData();

        try {
            const settingsResponse = await fetch(`${API_BASE_URL}/api/settings`);
            const settings = await settingsResponse.json();
            const refreshIntervalSeconds = parseInt(settings.dashboard_refresh_interval, 10);

            if (refreshIntervalSeconds && refreshIntervalSeconds > 0) {
                if (refreshIntervalId) clearInterval(refreshIntervalId);
                refreshIntervalId = setInterval(loadInitialData, refreshIntervalSeconds * 1000);
                console.log(`Dashboard auto-refresh configured for every ${refreshIntervalSeconds} seconds.`);
            } else {
                console.log('Dashboard auto-refresh is disabled.');
            }
        } catch (error) {
            console.error("Could not load settings for auto-refresh, using default.", error);
            if (refreshIntervalId) clearInterval(refreshIntervalId);
            refreshIntervalId = setInterval(loadInitialData, 60000);
        }
    }
    
    initializeDashboard();
});