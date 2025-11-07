// static/js/router_details.js

document.addEventListener('DOMContentLoaded', () => {
    // --- 1. CONFIGURACIÓN INICIAL ---
    const API_BASE_URL = window.location.origin;
    const currentHost = window.location.pathname.split('/')[2]; 
    
    let allInterfaces = []; 

    // --- 2. REFERENCIAS AL DOM (Listas y Contenedores) ---
    const breadcrumbHostname = document.getElementById('breadcrumb-hostname');
    const mainHostname = document.getElementById('main-hostname');
    
    const ipAddressList = document.getElementById('ip-address-list');
    const natRulesList = document.getElementById('nat-rules-list');
    const pppoeServerList = document.getElementById('pppoe-server-list');
    const pppProfileList = document.getElementById('ppp-profile-list');
    const parentQueueList = document.getElementById('parent-queue-list');
    const ipPoolList = document.getElementById('ip-pool-list');
    
    // --- ¡NUEVAS REFERENCIAS! ---
    const pppoeSecretsList = document.getElementById('pppoe-secrets-list');
    const pppoeActiveList = document.getElementById('pppoe-active-list');
    
    // Formularios
    const addIpForm = document.getElementById('add-ip-form');
    const addNatForm = document.getElementById('add-nat-form');
    const addPppoeForm = document.getElementById('add-pppoe-form');
    const addPlanForm = document.getElementById('add-plan-form');
    
    // Feedback
    const formFeedback = document.getElementById('form-feedback');

    // --- 3. FUNCIONES DE RENDERIZADO (Mostrar datos) ---
    
    const deleteIcon = `<span class="material-symbols-outlined text-base">delete</span>`;

    function renderIpAddresses(ips) {
        ipAddressList.innerHTML = '';
        if (!ips || ips.length === 0) {
            ipAddressList.innerHTML = '<p class="text-text-secondary">No hay IPs configuradas.</p>';
            return;
        }
        ips.forEach(ip => {
            ipAddressList.innerHTML += `
                <div class="flex justify-between items-center group hover:bg-surface-2 -mx-2 px-2 rounded-md">
                    <span class="font-mono text-sm">${ip.address} @ ${ip.interface}</span>
                    <div class="flex items-center gap-2">
                        <span class="text-text-secondary text-xs">${ip.comment || ''}</span>
                        <button class="delete-ip-btn invisible group-hover:visible text-danger hover:text-red-400" 
                                data-address="${ip.address}" title="Eliminar IP">
                            ${deleteIcon}
                        </button>
                    </div>
                </div>
            `;
        });
        document.querySelectorAll('.delete-ip-btn').forEach(btn => {
            btn.addEventListener('click', handleDeleteIp);
        });
    }

    function renderNatRules(rules) {
        natRulesList.innerHTML = '';
        const wanRules = rules.filter(rule => rule.comment && rule.comment.includes('µMonitor'));
        if (wanRules.length === 0) {
            natRulesList.innerHTML = '<p class="text-text-secondary">No hay reglas NAT activas.</p>';
            return;
        }
        wanRules.forEach(rule => {
            natRulesList.innerHTML += `
                <div class="flex justify-between items-center group hover:bg-surface-2 -mx-2 px-2 rounded-md">
                    <span class="text-sm">${rule.action} -> ${rule['out-interface-list'] || rule['out-interface']}</span>
                    <div class="flex items-center gap-2">
                        <span class="text-success text-xs">Activa</span>
                        <button class="delete-nat-btn invisible group-hover:visible text-danger hover:text-red-400" 
                                data-comment="${rule.comment}" title="Eliminar NAT">
                            ${deleteIcon}
                        </button>
                    </div>
                </div>
            `;
        });
        document.querySelectorAll('.delete-nat-btn').forEach(btn => {
            btn.addEventListener('click', handleDeleteNat);
        });
    }

    function renderPppoeServers(servers) {
        pppoeServerList.innerHTML = '';
        if (!servers || servers.length === 0) {
            pppoeServerList.innerHTML = '<p class="text-text-secondary">No hay servidores PPPoE.</p>';
            return;
        }
        servers.forEach(server => {
            pppoeServerList.innerHTML += `
                <div class="flex justify-between items-center group hover:bg-surface-2 -mx-2 px-2 rounded-md">
                    <span class="text-sm">${server['service-name']} @ ${server.interface}</span>
                    <div class="flex items-center gap-2">
                        <span class="text-text-secondary text-xs">Perfil: ${server['default-profile']}</span>
                         <button class="delete-pppoe-btn invisible group-hover:visible text-danger hover:text-red-400" 
                                data-service="${server['service-name']}" title="Eliminar Servidor PPPoE">
                            ${deleteIcon}
                        </button>
                    </div>
                </div>
            `;
        });
        document.querySelectorAll('.delete-pppoe-btn').forEach(btn => {
            btn.addEventListener('click', handleDeletePppoe);
        });
    }

    function renderPppProfiles(profiles) {
        pppProfileList.innerHTML = '';
        // --- CORRECCIÓN DE FILTRO: Mostramos todos ---
        const managedProfiles = profiles;
        if (managedProfiles.length === 0) {
            pppProfileList.innerHTML = '<p class="text-text-secondary">No hay planes (perfiles) creados.</p>';
            return;
        }
        managedProfiles.forEach(profile => {
            const planName = profile.name.replace('profile-', '');
            const isManaged = profile.comment && profile.comment.includes('µMonitor');
            
            pppProfileList.innerHTML += `
                <div class="p-2 bg-surface-2 rounded-md relative group">
                    <div class="flex justify-between items-center">
                        <p class="font-bold text-sm">${profile.name}</p>
                        ${isManaged ? 
                        `<button class="delete-plan-btn invisible group-hover:visible text-danger hover:text-red-400 absolute top-1 right-1" 
                                data-plan-name="${planName}" title="Eliminar Plan Completo">
                            ${deleteIcon}
                        </button>` : ''}
                    </div>
                    <p class="text-xs">Parent: ${profile['parent-queue'] || 'N/A'} | Pool: ${profile['remote-address'] || 'N/A'}</p>
                    <p class="text-xs">Queue: ${profile['queue-type'] || 'N/A'}</p>
                </div>
            `;
        });
        document.querySelectorAll('.delete-plan-btn').forEach(btn => {
            btn.addEventListener('click', handleDeletePlan);
        });
    }
    
    function renderParentQueues(queues) {
        parentQueueList.innerHTML = '';
        const managedQueues = queues.filter(q => q.comment && q.comment.includes('µMonitor'));
        if (managedQueues.length === 0) {
            parentQueueList.innerHTML = '<p class="text-text-secondary">No hay colas padre creadas.</p>';
            return;
        }
        managedQueues.forEach(queue => {
            parentQueueList.innerHTML += `
                <div class="flex justify-between items-center text-sm">
                    <span>${queue.name}</span>
                    <span class="text-warning font-mono">${queue['max-limit']}</span>
                </div>
            `;
        });
    }
    
    function renderIpPools(pools) {
        ipPoolList.innerHTML = '';
        const managedPools = pools.filter(p => p.name.startsWith('pool-')); 
        if (managedPools.length === 0) {
            ipPoolList.innerHTML = '<p class="text-text-secondary">No hay pools creados.</p>';
            return;
        }
        managedPools.forEach(pool => {
            ipPoolList.innerHTML += `
                <div class="flex justify-between items-center text-sm">
                    <span>${pool.name}</span>
                    <span class="text-text-secondary font-mono">${pool.ranges}</span>
                </div>
            `;
        });
    }
    
    // --- ¡NUEVAS FUNCIONES DE RENDERIZADO! ---
    function renderPppoeSecrets(secrets) {
        pppoeSecretsList.innerHTML = '';
        if (!secrets || secrets.length === 0) {
            pppoeSecretsList.innerHTML = '<p class="text-text-secondary">No hay secretos PPPoE configurados.</p>';
            return;
        }
        secrets.forEach(secret => {
            const isDisabled = secret.disabled === 'true';
            const statusClass = isDisabled ? 'text-danger' : 'text-success';
            const statusText = isDisabled ? 'Disabled' : 'Active';
            
            pppoeSecretsList.innerHTML += `
                <div class="flex justify-between items-center group hover:bg-surface-2 -mx-2 px-2 rounded-md">
                    <div>
                        <span class="font-semibold text-sm">${secret.name}</span>
                        <span class="text-xs text-text-secondary ml-2">(${secret.profile || 'default'})</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="text-xs font-semibold ${statusClass}">${statusText}</span>
                        </div>
                </div>
            `;
        });
    }
    
    function renderActiveConnections(connections) {
        pppoeActiveList.innerHTML = '';
        if (!connections || connections.length === 0) {
            pppoeActiveList.innerHTML = '<p class="text-text-secondary">No hay clientes conectados por PPPoE.</p>';
            return;
        }
        connections.forEach(conn => {
            pppoeActiveList.innerHTML += `
                <div class="flex justify-between items-center group hover:bg-surface-2 -mx-2 px-2 rounded-md">
                    <div>
                        <span class="font-semibold text-sm">${conn.name}</span>
                        <span class="text-xs text-text-secondary ml-2 font-mono">(${conn.address || 'N/A'})</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="text-xs text-text-primary">${conn.uptime || 'N/A'}</span>
                    </div>
                </div>
            `;
        });
    }

    // --- 4. FUNCIÓN DE CARGA PRINCIPAL (Sin cambios) ---
    async function loadAllRouterData() {
        // ... (cargando configuración)
        const lists = [ipAddressList, natRulesList, pppoeServerList, pppProfileList, parentQueueList, ipPoolList];
        lists.forEach(list => {
            if (list) list.innerHTML = '<p class="text-text-secondary text-sm">Cargando...</p>';
        });
        try {
            const data = await fetchJSON(`/api/routers/${currentHost}/full-details`);
            allInterfaces = data.interfaces || [];
            populateInterfaceSelects();
            renderIpAddresses(data.ip_addresses);
            renderNatRules(data.nat_rules);
            renderPppoeServers(data.pppoe_servers);
            renderPppProfiles(data.ppp_profiles);
            renderParentQueues(data.simple_queues);
            renderIpPools(data.ip_pools);
        } catch (error) {
            showFeedback(`Error al cargar datos de config: ${error.message}`, false);
            lists.forEach(list => {
                if (list) list.innerHTML = '<p class="text-danger text-sm">Error al cargar.</p>';
            });
        }
    }
    
    // --- ¡NUEVAS FUNCIONES DE CARGA! ---
    async function loadPppoeSecrets() {
        pppoeSecretsList.innerHTML = '<p class="text-text-secondary text-sm">Cargando secretos...</p>';
        try {
            const secrets = await fetchJSON(`/api/routers/${currentHost}/pppoe/secrets`);
            renderPppoeSecrets(secrets);
        } catch (error) {
            pppoeSecretsList.innerHTML = `<p class="text-danger text-sm">Error al cargar secretos: ${error.message}</p>`;
        }
    }
    
    async function loadActiveConnections() {
        pppoeActiveList.innerHTML = '<p class="text-text-secondary text-sm">Cargando conexiones...</p>';
        try {
            const connections = await fetchJSON(`/api/routers/${currentHost}/pppoe/active`);
            renderActiveConnections(connections);
        } catch (error) {
            pppoeActiveList.innerHTML = `<p class="text-danger text-sm">Error al cargar conexiones: ${error.message}</p>`;
        }
    }


    // --- 5. FUNCIONES DE AYUDA (Fetch, Feedback, etc.) ---
    // (Sin cambios)
    async function fetchJSON(url, options = {}) {
        const fetchOptions = {
            ...options,
            headers: { 'Content-Type': 'application/json', ...options.headers, },
        };
        if (options.method === 'GET' || options.method === 'DELETE' || !options.method) {
           delete fetchOptions.headers['Content-Type'];
        }
        const response = await fetch(API_BASE_URL + url, fetchOptions);
        if (!response.ok) {
            if (response.status === 204) return null; 
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || 'Error en la petición');
        }
        return response.status === 204 ? null : response.json();
    }
    function showFeedback(message, isSuccess) {
        formFeedback.textContent = message;
        formFeedback.className = isSuccess ? 'text-success text-center text-sm font-medium' : 'text-danger text-center text-sm font-medium';
        setTimeout(() => { 
            if (formFeedback.textContent === message) {
                formFeedback.textContent = ''; 
            }
        }, 4000);
    }
    function populateInterfaceSelects() {
        const selects = document.querySelectorAll('.interface-select');
        if (allInterfaces.length === 0) {
            selects.forEach(select => {
                select.innerHTML = '<option value="">Error al cargar</option>';
            });
            return;
        }
        selects.forEach(select => {
            select.innerHTML = '<option value="">Selecciona interfaz...</option>';
            allInterfaces.forEach(iface => {
                select.innerHTML += `<option value="${iface.name}">${iface.name}</option>`;
            });
        });
    }

    // --- 6. MANEJADORES DE EVENTOS (Formularios ADD - ACTUALIZADOS) ---
    // (Sin cambios)
    addIpForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        formUtils.clearFormErrors(addIpForm);
        let isValid = true;
        const formData = new FormData(addIpForm);
        const data = {
            interface: formData.get('interface'),
            address: formData.get('address'),
            comment: "Managed by µMonitor (LAN)"
        };
        if (!validators.isRequired(data.interface)) {
            formUtils.showFieldError('add-ip-interface', 'Debes seleccionar una interfaz.');
            isValid = false;
        }
        if (!validators.isValidIPv4WithCIDR(data.address)) {
            formUtils.showFieldError('add-ip-address', 'Debe ser una IP con CIDR válido (ej. 192.168.1.1/24).');
            isValid = false;
        }
        if (!isValid) return;
        try {
            await fetchJSON(`/api/routers/${currentHost}/write/add-ip`, {
                method: 'POST',
                body: JSON.stringify(data)
            });
            showFeedback('IP añadida correctamente.', true);
            addIpForm.reset();
            loadAllRouterData(); 
        } catch (error) {
            showFeedback(error.message, false);
        }
    });

    addNatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        formUtils.clearFormErrors(addNatForm);
        let isValid = true;
        const formData = new FormData(addNatForm);
        const data = {
            out_interface: formData.get('out-interface'),
            comment: formData.get('comment')
        };
        if (!validators.isRequired(data.out_interface)) {
            formUtils.showFieldError('add-nat-out-interface', 'Debes seleccionar una interfaz.');
            isValid = false;
        }
        if (!isValid) return;
        try {
            await fetchJSON(`/api/routers/${currentHost}/write/add-nat`, {
                method: 'POST',
                body: JSON.stringify(data)
            });
            showFeedback('Regla NAT añadida.', true);
            loadAllRouterData();
        } catch (error) {
            showFeedback(error.message, false);
        }
    });

    addPppoeForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        formUtils.clearFormErrors(addPppoeForm);
        let isValid = true;
        const formData = new FormData(addPppoeForm);
        const data = {
            service_name: formData.get('service_name'),
            interface: formData.get('interface'),
            default_profile: "default"
        };
        if (!validators.isRequired(data.service_name)) {
            formUtils.showFieldError('add-pppoe-service_name', 'El nombre es requerido.');
            isValid = false;
        }
         if (!validators.isRequired(data.interface)) {
            formUtils.showFieldError('add-pppoe-interface', 'Debes seleccionar una interfaz.');
            isValid = false;
        }
        if (!isValid) return;
        try {
            await fetchJSON(`/api/routers/${currentHost}/write/add-pppoe-server`, {
                method: 'POST',
                body: JSON.stringify(data)
            });
            showFeedback('Servidor PPPoE añadido.', true);
            addPppoeForm.reset();
            loadAllRouterData();
        } catch (error) {
            showFeedback(error.message, false);
        }
    });

    addPlanForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        formUtils.clearFormErrors(addPlanForm);
        let isValid = true;
        const formData = new FormData(addPlanForm);
        const data = {
            plan_name: formData.get('plan_name'),
            bandwidth: formData.get('bandwidth'),
            local_address: formData.get('local_address'),
            pool_range: formData.get('pool_range'),
            comment: "Managed by µMonitor"
        };
        if (!validators.isValidZoneName(data.plan_name)) { 
            formUtils.showFieldError('add-plan-plan_name', 'Nombre de plan inválido (solo letras, números, guiones).');
            isValid = false;
        }
        if (!validators.isRequired(data.bandwidth)) { 
             formUtils.showFieldError('add-plan-bandwidth', 'Ancho de banda requerido.');
            isValid = false;
        }
        if (!validators.isValidIPv4(data.local_address)) {
            formUtils.showFieldError('add-plan-local_address', 'Debe ser una IP de Gateway válida (ej. 10.10.0.1).');
            isValid = false;
        }
        if (!validators.isValidIPRange(data.pool_range)) {
            formUtils.showFieldError('add-plan-pool_range', 'Rango de IP inválido (ej. 10.10.0.2-10.10.0.254).');
            isValid = false;
        }
        if (!isValid) return;
        try {
            await fetchJSON(`/api/routers/${currentHost}/write/create-plan`, {
                method: 'POST',
                body: JSON.stringify(data)
            });
            showFeedback(`Plan '${data.plan_name}' creado.`, true);
            addPlanForm.reset();
            loadAllRouterData();
        } catch (error) {
            showFeedback(error.message, false);
        }
    });

    // --- 7. MANEJADORES DE EVENTOS (DELETE) (Sin cambios) ---
    async function handleDeleteIp(event) {
        const address = event.currentTarget.dataset.address;
        if (!confirm(`¿Estás seguro de que quieres eliminar la IP "${address}"?`)) return;
        try {
            const url = new URL(`${API_BASE_URL}/api/routers/${currentHost}/write/delete-ip`);
            url.searchParams.append('address', address);
            await fetchJSON(url.pathname + url.search, { method: 'DELETE' });
            showFeedback('IP eliminada.', true);
            loadAllRouterData(); 
        } catch (error) {
            showFeedback(error.message, false);
        }
    }
    async function handleDeleteNat(event) {
        const comment = event.currentTarget.dataset.comment;
        if (!confirm(`¿Estás seguro de que quieres eliminar la regla NAT "${comment}"?`)) return;
        try {
            const url = new URL(`${API_BASE_URL}/api/routers/${currentHost}/write/delete-nat`);
            url.searchParams.append('comment', comment);
            await fetchJSON(url.pathname + url.search, { method: 'DELETE' });
            showFeedback('Regla NAT eliminada.', true);
            loadAllRouterData(); 
        } catch (error) {
            showFeedback(error.message, false);
        }
    }
    async function handleDeletePppoe(event) {
        const serviceName = event.currentTarget.dataset.service;
        if (!confirm(`¿Estás seguro de que quieres eliminar el servidor PPPoE "${serviceName}"?`)) return;
        try {
            const url = new URL(`${API_BASE_URL}/api/routers/${currentHost}/write/delete-pppoe-server`);
            url.searchParams.append('service_name', serviceName);
            await fetchJSON(url.pathname + url.search, { method: 'DELETE' });
            showFeedback('Servidor PPPoE eliminado.', true);
            loadAllRouterData();
        } catch (error) {
            showFeedback(error.message, false);
        }
    }
    async function handleDeletePlan(event) {
        const planName = event.currentTarget.dataset.planName;
        if (!confirm(`¿Estás seguro de que quieres eliminar el plan "${planName}"?\nEsto eliminará el perfil, el pool y la cola padre.`)) return;
        try {
            const url = new URL(`${API_BASE_URL}/api/routers/${currentHost}/write/delete-plan`);
            url.searchParams.append('plan_name', planName);
            await fetchJSON(url.pathname + url.search, { method: 'DELETE' });
            showFeedback(`Plan "${planName}" eliminado.`, true);
            loadAllRouterData();
        } catch (error) {
            showFeedback(error.message, false);
        }
    }

    // --- 8. INICIALIZACIÓN (ACTUALIZADA) ---
    function init() {
        breadcrumbHostname.textContent = currentHost;
        mainHostname.textContent = `Router: ${currentHost}`;
        
        // Cargar todos los datos de configuración
        loadAllRouterData();
        
        // --- ¡NUEVAS LLAMADAS! ---
        // Cargar los datos en vivo de PPPoE
        loadPppoeSecrets();
        loadActiveConnections();
        
        // (Opcional) Recargar los datos en vivo cada 30 segundos
        // setInterval(loadPppoeSecrets, 30000);
        // setInterval(loadActiveConnections, 30000);
    }
    
    init();
});