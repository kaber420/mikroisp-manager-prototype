// static/js/router_details.js

document.addEventListener('DOMContentLoaded', () => {
    // --- 1. CONFIGURACIÓN INICIAL ---
    const API_BASE_URL = window.location.origin;
    const currentHost = window.location.pathname.split('/')[2]; 
    
    let allInterfaces = []; 
    let currentRouterName = 'router'; // Valor por defecto

    // --- Lógica de Pestañas ---
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabPanels = document.querySelectorAll('.tab-panel');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            const tabName = button.getAttribute('data-tab');
            
            tabPanels.forEach(panel => {
                if (panel.id === `tab-${tabName}`) {
                    panel.classList.add('active');
                } else {
                    panel.classList.remove('active');
                }
            });
        });
    });

    // --- 2. REFERENCIAS AL DOM (Listas y Contenedores) ---
    const breadcrumbHostname = document.getElementById('breadcrumb-hostname');
    const mainHostname = document.getElementById('main-hostname');
    
    const ipAddressList = document.getElementById('ip-address-list');
    const natRulesList = document.getElementById('nat-rules-list');
    const pppoeServerList = document.getElementById('pppoe-server-list');
    const pppProfileList = document.getElementById('ppp-profile-list');
    const parentQueueListDisplay = document.getElementById('parent-queue-list-display');
    const ipPoolList = document.getElementById('ip-pool-list');
    
    const pppoeSecretsList = document.getElementById('pppoe-secrets-list');
    const pppoeActiveList = document.getElementById('pppoe-active-list');
    
    const resModel = document.getElementById('res-model');
    const resFirmware = document.getElementById('res-firmware');
    const resCpu = document.getElementById('res-cpu');

    // Formularios
    const addIpForm = document.getElementById('add-ip-form');
    const addNatForm = document.getElementById('add-nat-form');
    const addPppoeForm = document.getElementById('add-pppoe-form');
    const addPlanForm = document.getElementById('add-plan-form');
    const addParentQueueForm = document.getElementById('add-parent-queue-form');
    
    // Selects
    const parentQueueSelect = document.getElementById('add-plan-parent_queue');
    
    const createBackupForm = document.getElementById('create-backup-form');
    const backupNameInput = document.getElementById('backup-name');
    const backupFilesList = document.getElementById('backup-files-list');

    const routerUsersList = document.getElementById('router-users-list');
    const addRouterUserForm = document.getElementById('add-router-user-form');
    const appUserSelect = document.getElementById('app-user-select');
    const routerUserNameInput = document.getElementById('router-user-name');
    const routerUserPasswordInput = document.getElementById('router-user-password');
    const routerUserGroupSelect = document.getElementById('router-user-group');
    const routerUserFormError = document.getElementById('router-user-form-error');

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
        if (profiles.length === 0) {
            pppProfileList.innerHTML = '<p class="text-text-secondary">No hay planes (perfiles) creados.</p>';
            return;
        }
        profiles.forEach(profile => {
            const planName = profile.name.replace('profile-', '');
            const isManaged = profile.comment && profile.comment.includes('µMonitor');
            const rateLimit = profile['rate-limit'] ? `Limit: <span class="text-warning">${profile['rate-limit']}</span>` : 'Limit: N/A';
            const parentQ = profile['parent-queue'] ? `Parent: ${profile['parent-queue']}` : 'Parent: none';
            
            pppProfileList.innerHTML += `
                <div class="p-2 bg-surface-2 rounded-md relative group">
                    <div class="flex justify-between items-center">
                        <p class="font-bold text-sm">${profile.name}</p>
                        ${isManaged ? 
                        `<button class="delete-plan-btn invisible group-hover:visible text-danger hover:text-red-400 absolute top-1 right-1" 
                                data-plan-name="${planName}" title="Eliminar Plan (Perfil y Pool)">
                            ${deleteIcon}
                        </button>` : ''}
                    </div>
                    <p class="text-xs">${rateLimit} | Pool: ${profile['remote-address'] || 'N/A'}</p>
                    <p class="text-xs">${parentQ}</p>
                </div>
            `;
        });
        document.querySelectorAll('.delete-plan-btn').forEach(btn => {
            btn.addEventListener('click', handleDeletePlan);
        });
    }
    
    function renderParentQueues(queues) {
        // Responsabilidad 1: Poblar la lista de display
        if(parentQueueListDisplay) parentQueueListDisplay.innerHTML = '';
        
        // Responsabilidad 2: Poblar el select del formulario de planes
        if (parentQueueSelect) {
            parentQueueSelect.innerHTML = '<option value="none">-- Sin Cola Padre --</option>';
        }

        if (queues.length === 0) {
            if(parentQueueListDisplay) parentQueueListDisplay.innerHTML = '<p class="text-text-secondary">No hay colas padre creadas.</p>';
            return;
        }
        
        queues.forEach(queue => {
            const bandwidth = queue['max-limit'] || '0/0';
            const queueId = queue['.id'] || queue['id'];

            // 1. Poblar la lista de display
            if(parentQueueListDisplay) {
                parentQueueListDisplay.innerHTML += `
                    <div class="flex justify-between items-center group hover:bg-surface-2 -mx-2 px-2 rounded-md">
                        <span class="text-sm">${queue.name}</span>
                        <div class="flex items-center gap-2">
                            <span class="text-warning font-mono text-xs">${bandwidth}</span>
                            <button class="delete-parent-queue-btn invisible group-hover:visible text-danger hover:text-red-400" 
                                    data-queue-id="${queueId}" data-queue-name="${queue.name}" title="Eliminar Cola Padre">
                                ${deleteIcon}
                            </button>
                        </div>
                    </div>
                `;
            }
            
            // 2. Poblar el select
            if (parentQueueSelect) {
                const option = document.createElement('option');
                option.value = queue.name;
                option.textContent = `${queue.name} (${bandwidth})`;
                parentQueueSelect.appendChild(option);
            }
        });

        // Añadir el event listener para los nuevos botones de borrado
        document.querySelectorAll('.delete-parent-queue-btn').forEach(btn => {
            btn.addEventListener('click', handleDeleteParentQueue);
        });
    }
    
    function renderIpPools(pools) {
        ipPoolList.innerHTML = '';
        if (pools.length === 0) {
            ipPoolList.innerHTML = '<p class="text-text-secondary">No hay pools creados.</p>';
            return;
        }
        pools.forEach(pool => {
            ipPoolList.innerHTML += `
                <div class="flex justify-between items-center text-sm">
                    <span>${pool.name}</span>
                    <span class="text-text-secondary font-mono">${pool.ranges}</span>
                </div>
            `;
        });
    }
    
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

    function renderBackupFiles(files) {
        backupFilesList.innerHTML = '';
        if (!files || files.length === 0) {
            backupFilesList.innerHTML = '<p class="text-text-secondary">No hay archivos .backup o .rsc en el router.</p>';
            return;
        }

        files.forEach(file => {
            const fileTypeClass = file.type === 'backup' ? 'text-primary' : 'text-orange';
            const icon = file.type === 'backup' ? 'archive' : 'description';
            
            const fSize = parseInt(file.size, 10);
            const fileSize = fSize ? `${(fSize / 1024).toFixed(1)} KB` : '';
            
            const fileId = file['.id'] || file['id']; 

            backupFilesList.innerHTML += `
                <div class="flex justify-between items-center group hover:bg-surface-2 -mx-2 px-2 rounded-md">
                    <div class="flex items-center gap-2 overflow-hidden">
                        <span class="material-symbols-outlined text-base ${fileTypeClass}">${icon}</span>
                        <span class="font-semibold text-sm truncate" title="${file.name}">${file.name}</span>
                    </div>
                    <div class="flex items-center gap-2 flex-shrink-0">
                        <span class="text-text-secondary text-xs">${fileSize}</span>
                        <button class="delete-backup-btn invisible group-hover:visible text-danger hover:text-red-400" 
                                data-file-id="${fileId}" data-file-name="${file.name}" title="Eliminar Archivo">
                            ${deleteIcon}
                        </button>
                    </div>
                </div>
            `;
        });

        document.querySelectorAll('.delete-backup-btn').forEach(btn => {
            btn.addEventListener('click', handleDeleteBackupFile);
        });
    }

    function renderRouterUsers(users) {
        routerUsersList.innerHTML = '';
        if (!users || users.length === 0) {
            routerUsersList.innerHTML = '<p class="text-text-secondary">No se encontraron usuarios.</p>';
            return;
        }
        
        users.forEach(user => {
            const isProtected = user.name === 'admin' || user.name === 'api-user'; 
            const isDisabled = user.disabled === 'true';
            
            const userId = user['.id'] || user['id']; 

            routerUsersList.innerHTML += `
                <div class="flex justify-between items-center group hover:bg-surface-2 -mx-2 px-2 rounded-md">
                    <div class="${isDisabled ? 'text-text-secondary' : 'text-text-primary'}">
                        <span class="font-semibold text-sm">${user.name}</span>
                        <span class="text-xs text-text-secondary ml-2">(${user.group})</span>
                    </div>
                    <div class="flex items-center gap-2">
                        ${isDisabled ? '<span class="text-xs text-danger">Disabled</span>' : ''}
                        ${isProtected ? '' : 
                        `<button class="delete-user-btn invisible group-hover:visible text-danger hover:text-red-400" 
                                data-user-id="${userId}" data-user-name="${user.name}" title="Eliminar Usuario">
                            ${deleteIcon}
                        </button>`}
                    </div>
                </div>
            `;
        });

        document.querySelectorAll('.delete-user-btn').forEach(btn => {
            btn.addEventListener('click', handleDeleteRouterUser);
        });
    }


    // --- 4. FUNCIONES DE CARGA ---
    async function loadAllRouterData() {
        const lists = [ipAddressList, natRulesList, pppoeServerList, pppProfileList, parentQueueListDisplay, ipPoolList];
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

    async function loadSystemResources() {
        try {
            const resources = await fetchJSON(`/api/routers/${currentHost}/resources`);
            
            if(resModel) resModel.textContent = resources['board-name'] || 'N/A';
            if(resFirmware) resFirmware.textContent = resources.version || 'N/A';
            if(resCpu) resCpu.textContent = resources.cpu || 'N/A';

            if (resources.name) {
                 mainHostname.textContent = resources.name;
                 breadcrumbHostname.textContent = resources.name;
                 currentRouterName = resources.name.split(' ')[0].replace(/[^a-zA-Z0-9_-]/g, '');
            } else {
                 currentRouterName = currentHost;
            }
            
            updateBackupNameInput();

        } catch (error) {
            if(resModel) resModel.textContent = 'Error';
            if(resFirmware) resFirmware.textContent = 'Error';
            if(resCpu) resCpu.textContent = 'Error';
        }
    }

    async function loadBackupFiles() {
        if (backupFilesList) backupFilesList.innerHTML = '<p class="text-text-secondary">Cargando archivos...</p>';
        try {
            const files = await fetchJSON(`/api/routers/${currentHost}/system/files`);
            renderBackupFiles(files);
        } catch (error) {
            if (backupFilesList) backupFilesList.innerHTML = `<p class="text-danger text-sm">Error al cargar archivos: ${error.message}</p>`;
        }
    }

    async function loadRouterUsers() {
        if (routerUsersList) routerUsersList.innerHTML = '<p class="text-text-secondary">Cargando usuarios...</p>';
        try {
            const users = await fetchJSON(`/api/routers/${currentHost}/system/users`);
            renderRouterUsers(users);
        } catch (error) {
            if (routerUsersList) routerUsersList.innerHTML = `<p class="text-danger text-sm">Error al cargar usuarios: ${error.message}</p>`;
        }
    }

    async function loadAppUsersForSync() {
        if (!appUserSelect) return;
        appUserSelect.innerHTML = '<option value="">Cargando usuarios de la App...</option>';
        try {
            const appUsers = await fetchJSON(`/api/users`); 
            appUserSelect.innerHTML = '<option value="">Selecciona un usuario de la App...</option>';
            appUsers.forEach(user => {
                const option = document.createElement('option');
                option.value = user.username;
                option.textContent = user.username;
                appUserSelect.appendChild(option);
            });
        } catch (error) {
            appUserSelect.innerHTML = '<option value="">Error al cargar usuarios</option>';
        }
    }


    // --- 5. FUNCIONES DE AYUDA (Fetch, Feedback, etc.) ---
    const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));

    function getFormattedDate() {
        const now = new Date();
        const year = now.getFullYear();
        const month = (now.getMonth() + 1).toString().padStart(2, '0');
        const day = now.getDate().toString().padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function updateBackupNameInput() {
        if (backupNameInput) {
            backupNameInput.value = `${currentRouterName}-${getFormattedDate()}`;
        }
    }

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

    // --- 6. MANEJADORES DE EVENTOS (Formularios ADD) ---
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

    if (addParentQueueForm) {
        addParentQueueForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            formUtils.clearFormErrors(addParentQueueForm);
            let isValid = true;
            const formData = new FormData(addParentQueueForm);
            const data = {
                name: formData.get('name'),
                max_limit: formData.get('max_limit'),
                comment: "Managed by µMonitor (Parent Queue)"
            };

            if (!validators.isValidZoneName(data.name)) {
                formUtils.showFieldError('add-queue-name', 'Nombre inválido (letras, números, guiones).');
                isValid = false;
            }
            if (!/^[0-9]+[Mk]?(\/[0-9]+[Mk]?)?$/.test(data.max_limit) && data.max_limit !== '0') {
                    formUtils.showFieldError('add-queue-max_limit', 'Formato inválido. Usar "UL/DL" (ej. 100M/500M) o 0.');
                    isValid = false;
            }
            if (!isValid) return;

            try {
                await fetchJSON(`/api/routers/${currentHost}/write/add-simple-queue`, {
                    method: 'POST',
                    body: JSON.stringify(data)
                });
                showFeedback('Cola Padre creada.', true);
                addParentQueueForm.reset();
                loadAllRouterData(); // Recargará la lista y el select
            } catch (error) {
                showFeedback(error.message, false);
            }
        });
    }

    addPlanForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        formUtils.clearFormErrors(addPlanForm);
        let isValid = true;
        const formData = new FormData(addPlanForm);
        const data = {
            plan_name: formData.get('plan_name'),
            rate_limit: formData.get('rate_limit'),
            local_address: formData.get('local_address'),
            pool_range: formData.get('pool_range'),
            parent_queue: formData.get('parent_queue'),
            comment: "Managed by µMonitor"
        };
        
        if (!validators.isValidZoneName(data.plan_name)) { 
            formUtils.showFieldError('add-plan-plan_name', 'Nombre de plan inválido (solo letras, números, guiones).');
            isValid = false;
        }
        
        if (!validators.isRequired(data.rate_limit)) { 
             formUtils.showFieldError('add-plan-rate_limit', 'Límite de Tasa es requerido.');
             isValid = false;
        } else if (!/^[0-9]+[Mk]?(\/[0-9]+[Mk]?)?$/.test(data.rate_limit) && data.rate_limit !== '0') {
             formUtils.showFieldError('add-plan-rate_limit', 'Formato inválido. Usar "UL/DL" (ej. 2M/8M) o 0.');
             isValid = false;
        }

        if (!validators.isValidIPv4(data.local_address)) {
            formUtils.showFieldError('add-plan-local_address', 'Debe ser una IP de Gateway válida (ej. 10.10.0.1).');
            isValid = false;
        }
        
        if (!validators.isValidIPv4WithCIDR(data.pool_range)) {
            formUtils.showFieldError('add-plan-pool_range', 'Red inválida. Debe estar en formato CIDR (ej. 10.10.0.0/24).');
            isValid = false;
        }
        
        if (!isValid) return;
        
        try {
            await fetchJSON(`/api/routers/${currentHost}/write/create-plan`, {
                method: 'POST',
                body: JSON.stringify(data)
            });
            showFeedback(`Plan (Perfil) '${data.plan_name}' creado.`, true);
            addPlanForm.reset();
            loadAllRouterData();
        } catch (error) {
            showFeedback(error.message, false);
        }
    });

    if (createBackupForm) {
        createBackupForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const backupType = e.submitter ? e.submitter.dataset.type : null;
            if (!backupType) return;
            handleCreateBackup(backupType);
        });
    }

    async function handleCreateBackup(backupType) {
        const backupName = backupNameInput.value;
        if (!backupName) {
            showFeedback('Por favor, introduce un nombre para el backup.', false);
            return;
        }

        const button = document.querySelector(`#create-backup-form button[data-type="${backupType}"]`);
        const originalText = button.innerHTML;
        button.innerHTML = '<span class="material-symbols-outlined text-base animate-spin">sync</span> Creando...';
        button.disabled = true;

        try {
            const data = {
                backup_name: backupName,
                backup_type: backupType
            };
            const result = await fetchJSON(`/api/routers/${currentHost}/system/create-backup`, {
                method: 'POST',
                body: JSON.stringify(data)
            });

            showFeedback(result.message + " Refrescando en 3s...", true);
            await wait(3000); 

            showFeedback(result.message, true);
            updateBackupNameInput(); 
            loadBackupFiles(); 

        } catch (error) {
            showFeedback(error.message, false);
        } finally {
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }

    if (appUserSelect) {
        appUserSelect.addEventListener('change', () => {
            if (appUserSelect.value && routerUserNameInput) {
                routerUserNameInput.value = appUserSelect.value;
            }
        });
    }

    if (addRouterUserForm) {
        addRouterUserForm.addEventListener('submit', (e) => {
            e.preventDefault();
            handleAddRouterUser();
        });
    }

    async function handleAddRouterUser() {
        if (routerUserFormError) routerUserFormError.classList.add('hidden');
        
        const username = routerUserNameInput.value;
        const password = routerUserPasswordInput.value;
        const group = routerUserGroupSelect.value;

        if (!username || !password || !group) {
            if (routerUserFormError) {
                routerUserFormError.textContent = 'Todos los campos son requeridos.';
                routerUserFormError.classList.remove('hidden');
            }
            return;
        }

        const button = addRouterUserForm.querySelector('button[type="submit"]');
        const originalText = button.innerHTML;
        button.innerHTML = '<span class="material-symbols-outlined text-base animate-spin">sync</span> Añadiendo...';
        button.disabled = true;

        try {
            const data = { username, password, group };
            await fetchJSON(`/api/routers/${currentHost}/system/users`, {
                method: 'POST',
                body: JSON.stringify(data)
            });
            showFeedback(`Usuario '${username}' añadido al router.`, true);
            addRouterUserForm.reset(); 
            appUserSelect.value = ""; 
            loadRouterUsers(); 
        } catch (error) {
            if (routerUserFormError) {
                routerUserFormError.textContent = `Error: ${error.message}`;
                routerUserFormError.classList.remove('hidden');
            } else {
                showFeedback(error.message, false);
            }
        } finally {
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }


    // --- 7. MANEJADORES DE EVENTOS (DELETE) ---
    
    async function handleDeleteRouterUser(event) {
        const userId = event.currentTarget.dataset.userId;
        const userName = event.currentTarget.dataset.userName;
        
        if (!confirm(`¿Estás seguro de que quieres eliminar al usuario "${userName}" (${userId}) del router?`)) return;

        try {
            await fetchJSON(`/api/routers/${currentHost}/system/users/${encodeURIComponent(userId)}`, {
                method: 'DELETE'
            });
            showFeedback(`Usuario '${userName}' eliminado del router.`, true);
            loadRouterUsers(); 
        } catch (error) {
            showFeedback(error.message, false);
        }
    }
    
    async function handleDeleteBackupFile(event) {
        const fileId = event.currentTarget.dataset.fileId;
        const fileName = event.currentTarget.dataset.fileName;
        
        if (!confirm(`¿Estás seguro de que quieres eliminar el archivo "${fileName}" (${fileId}) del router?\n¡Esta acción no se puede deshacer!`)) return;

        try {
            await fetchJSON(`/api/routers/${currentHost}/system/files/${encodeURIComponent(fileId)}`, {
                method: 'DELETE'
            });

            showFeedback(`Archivo '${fileName}' eliminado del router.`, true);
            loadBackupFiles(); 
        } catch (error) {
            showFeedback(error.message, false);
        }
    }

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
        if (!confirm(`¿Estás seguro de que quieres eliminar el plan "${planName}"?\nEsto eliminará el perfil PPPoE y el Pool de IPs asociado (la cola padre NO se tocará).`)) return;
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

    async function handleDeleteParentQueue(event) {
        const queueId = event.currentTarget.dataset.queueId;
        const queueName = event.currentTarget.dataset.queueName;
        
        if (!confirm(`¿Estás seguro de que quieres eliminar la Cola Padre "${queueName}"?\n\nADVERTENCIA: Los perfiles PPPoE que apunten a esta cola fallarán.`)) return;

        try {
            await fetchJSON(`/api/routers/${currentHost}/write/delete-simple-queue/${encodeURIComponent(queueId)}`, {
                method: 'DELETE'
            });
            showFeedback(`Cola Padre '${queueName}' eliminada.`, true);
            loadAllRouterData();
        } catch (error) {
            showFeedback(error.message, false);
        }
    }
    
    // --- 8. INICIALIZACIÓN ---
    function init() {
        breadcrumbHostname.textContent = currentHost;
        mainHostname.textContent = `Router: ${currentHost}`;
        
        loadAllRouterData();
        loadPppoeSecrets();
        loadActiveConnections();
        loadSystemResources();
        loadBackupFiles();
        loadRouterUsers();
        loadAppUsersForSync();
    }
    
    init();
});