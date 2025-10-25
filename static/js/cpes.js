document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = window.location.origin;
    let allCPEs = [];
    let searchTerm = '';
    let refreshIntervalId = null;

    // --- REFERENCIAS A ELEMENTOS DEL DOM ---
    const searchInput = document.getElementById('search-input');
    const tableBody = document.getElementById('cpe-table-body');

    /**
     * Devuelve la clase y el texto para un badge de estado basado en la señal.
     * @param {number|null} signal - El nivel de señal del CPE en dBm.
     * @returns {{badgeClass: string, text: string}}
     */
    function getStatusFromSignal(signal) {
        if (signal == null) {
            return { badgeClass: 'bg-text-secondary/20 text-text-secondary', text: 'Unknown' };
        }
        if (signal > -65) {
            return { badgeClass: 'bg-success/20 text-success', text: 'Excellent' };
        }
        if (signal > -75) {
            return { badgeClass: 'bg-primary/20 text-primary', text: 'Good' };
        }
        if (signal > -85) {
            return { badgeClass: 'bg-warning/20 text-warning', text: 'Weak' };
        }
        return { badgeClass: 'bg-danger/20 text-danger', text: 'Poor' };
    }

    /**
     * Filtra y renderiza la lista de CPEs en la tabla.
     */
    function renderCPEs() {
        if (!tableBody) return;

        const filteredCPEs = allCPEs.filter(cpe => {
            const term = searchTerm.toLowerCase();
            return !term ||
                (cpe.cpe_hostname && cpe.cpe_hostname.toLowerCase().includes(term)) ||
                (cpe.ap_hostname && cpe.ap_hostname.toLowerCase().includes(term)) ||
                cpe.cpe_mac.toLowerCase().includes(term) ||
                (cpe.ip_address && cpe.ip_address.toLowerCase().includes(term));
        });
        
        // Ordenamos los CPEs por señal, de más débil a más fuerte
        filteredCPEs.sort((a, b) => (a.signal || -100) - (b.signal || -100));

        tableBody.innerHTML = '';

        if (filteredCPEs.length === 0) {
            const emptyRow = document.createElement('tr');
            emptyRow.innerHTML = `<td colspan="6" class="text-center p-8 text-text-secondary">No CPEs match the current filter.</td>`;
            tableBody.appendChild(emptyRow);
        } else {
            filteredCPEs.forEach(cpe => {
                const row = document.createElement('tr');
                row.className = "hover:bg-surface-2 transition-colors duration-200";

                const status = getStatusFromSignal(cpe.signal);
                const signalStrength = cpe.signal != null ? `${cpe.signal} dBm` : 'N/A';
                
                const apLink = cpe.ap_host ? `<a href="/ap/${cpe.ap_host}" class="text-primary hover:underline">${cpe.ap_hostname || cpe.ap_host}</a>` : 'N/A';

                row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="text-xs font-semibold px-2 py-1 rounded-full ${status.badgeClass}">${status.text}</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap font-semibold text-text-primary">${cpe.cpe_hostname || "Unnamed Device"}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-text-secondary">${apLink}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-text-primary font-semibold">${signalStrength}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-text-secondary font-mono">${cpe.cpe_mac}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-text-secondary font-mono">${cpe.ip_address || "No IP"}</td>
                `;
                tableBody.appendChild(row);
            });
        }
    }

    /**
     * Carga todos los datos de los CPEs desde la API y los renderiza.
     */
    function loadAllCPEs() {
        if (!tableBody) return;

        tableBody.style.filter = 'blur(4px)';
        tableBody.style.opacity = '0.6';

        if (allCPEs.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center p-8 text-text-secondary">Loading CPE data...</td></tr>';
        }

        setTimeout(async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/api/cpes/all`);
                if (!response.ok) {
                    throw new Error('Failed to load CPEs');
                }
                allCPEs = await response.json();
                renderCPEs();
            } catch (error) {
                console.error("Error loading CPE data:", error);
                tableBody.innerHTML = `<tr><td colspan="6" class="text-center p-8 text-danger">Failed to load network data. Please check the API.</td></tr>`;
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
    
    async function initializeAutoRefresh() {
        try {
            const settingsResponse = await fetch(`${API_BASE_URL}/api/settings`);
            if (!settingsResponse.ok) throw new Error('Could not fetch settings');
            const settings = await settingsResponse.json();
            const refreshIntervalSeconds = parseInt(settings.dashboard_refresh_interval, 10);

            if (refreshIntervalSeconds && refreshIntervalSeconds > 0) {
                if (refreshIntervalId) clearInterval(refreshIntervalId);
                refreshIntervalId = setInterval(loadAllCPEs, refreshIntervalSeconds * 1000);
                console.log(`CPEs page auto-refresh configured for every ${refreshIntervalSeconds} seconds.`);
            } else {
                console.log('CPEs page auto-refresh is disabled.');
            }
        } catch (error) {
            console.error("Could not load settings for auto-refresh. It will be disabled.", error);
        }
    }

    // --- INICIALIZACIÓN ---
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            searchTerm = e.target.value;
            renderCPEs();
        });
    }

    loadAllCPEs();
    initializeAutoRefresh();
});