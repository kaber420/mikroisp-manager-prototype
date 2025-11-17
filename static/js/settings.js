document.addEventListener('DOMContentLoaded', () => {

    const API_BASE_URL = window.location.origin;
    const settingsForm = document.getElementById('settings-form');
    const saveStatus = document.getElementById('save-status');
    const saveButton = document.getElementById('save-button');
    const saveSpinner = document.getElementById('save-spinner');
    const forceBillingBtn = document.getElementById('force-billing-btn');

    async function loadSettings() {
        if (!settingsForm) return;

        try {
            const response = await fetch(`${API_BASE_URL}/api/settings`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || "Failed to load settings");
            }
            const settings = await response.json();
            
            for (const [key, value] of Object.entries(settings)) {
                const inputElement = document.getElementById(key);
                if (inputElement) {
                    inputElement.value = value;
                }
            }
        } catch (error) {
            console.error("Error loading settings:", error);
            alert("Could not load settings. Please check the API connection.");
        }
    }

    async function handleSettingsSubmit(event) {
        event.preventDefault();
        saveStatus.classList.add('hidden');
        saveButton.disabled = true;
        saveSpinner.classList.remove('hidden');

        const formData = new FormData(settingsForm);
        const settingsData = Object.fromEntries(formData.entries());
        
        try {
            const response = await fetch(`${API_BASE_URL}/api/settings`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settingsData)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || "Failed to save settings");
            }

            saveStatus.textContent = "Settings saved successfully!";
            saveStatus.classList.remove('hidden', 'text-danger');
            saveStatus.classList.add('text-success');
            setTimeout(() => {
                saveStatus.classList.add('hidden');
            }, 3000);
            
        } catch (error) {
            console.error("Error saving settings:", error);
            saveStatus.textContent = `Error: ${error.message}`;
            saveStatus.classList.remove('hidden', 'text-success');
            saveStatus.classList.add('text-danger');
        } finally {
            saveButton.disabled = false;
            saveSpinner.classList.add('hidden');
        }
    }
    
    // --- Manejo del Botón de Fuerza (Fase 6) ---
    if (forceBillingBtn) {
        forceBillingBtn.addEventListener('click', async () => {
            if(!confirm("Are you sure? This will update statuses (Active/Pending/Suspended) for ALL clients based on their payments.")) return;
            
            const originalText = forceBillingBtn.innerHTML;
            forceBillingBtn.innerHTML = '<span class="material-symbols-outlined animate-spin">sync</span> Processing...';
            forceBillingBtn.disabled = true;
            
            try {
                const res = await fetch(`${API_BASE_URL}/api/settings/force-billing`, { method: 'POST' });
                if (!res.ok) throw new Error('Request failed');
                const data = await res.json();
                alert(`Done! \nProcessed: ${data.stats.processed}\nActive: ${data.stats.active || 0}\nPending: ${data.stats.pendiente || 0}\nSuspended: ${data.stats.suspended || 0}`);
            } catch (e) {
                alert("Error updating statuses: " + e.message);
            } finally {
                forceBillingBtn.innerHTML = originalText;
                forceBillingBtn.disabled = false;
            }
        });
    }
    
    if (settingsForm) {
        settingsForm.addEventListener('submit', handleSettingsSubmit);
        loadSettings();
    }
});