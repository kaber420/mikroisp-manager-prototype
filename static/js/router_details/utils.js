// static/js/router_details/utils.js
import { CONFIG, DOM_ELEMENTS, state } from './config.js';

/**
 * Clase unificada para todas las peticiones a la API.
 */
export class ApiClient {
    static async request(url, options = {}) {
        const fetchOptions = {
            ...options,
            headers: { 'Content-Type': 'application/json', ...options.headers },
        };
        // No enviar Content-Type en GET o DELETE
        if (!options.method || ['GET', 'DELETE'].includes(options.method?.toUpperCase())) {
            delete fetchOptions.headers['Content-Type'];
        }

        const response = await fetch(CONFIG.API_BASE_URL + url, fetchOptions);

        if (!response.ok) {
            // Manejar 204 (No Content)
            if (response.status === 204) return null;
            
            // Intentar parsear el error de la API
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            let errorMessage = 'Error en la petición';
            
            if (errorData.detail) {
                if (Array.isArray(errorData.detail)) { // Errores de validación Pydantic
                    errorMessage = errorData.detail
                        .map(err => `${err.loc[err.loc.length - 1]}: ${err.msg}`)
                        .join('; ');
                } else { // Errores estándar
                    errorMessage = errorData.detail;
                }
            } else if (response.statusText) {
                errorMessage = response.statusText;
            }
            throw new Error(errorMessage);
        }
        // Manejar 204 (No Content) para DELETE exitoso
        return response.status === 204 ? null : response.json();
    }
}

/**
 * Clase de utilidades para manipular el DOM.
 */
export class DomUtils {
    static formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 Bytes';
        const k = 1024;
        const bytesNum = parseInt(bytes, 10);
        if (isNaN(bytesNum)) return 'N/A';
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytesNum) / Math.log(k));
        return parseFloat((bytesNum / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    static updateFeedback(message, isSuccess = true) {
        const feedbackEl = DOM_ELEMENTS.formFeedback;
        if (!feedbackEl) {
            console.log("Feedback:", message);
            return;
        }
        feedbackEl.textContent = message;
        feedbackEl.className = `text-sm text-center mt-4 text-${isSuccess ? 'success' : 'danger'}`;
        setTimeout(() => {
            if (feedbackEl.textContent === message) feedbackEl.textContent = '';
        }, 4000);
    }

    static updateBackupNameInput() {
        if (DOM_ELEMENTS.backupNameInput) {
            const now = new Date();
            const dateStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
            DOM_ELEMENTS.backupNameInput.value = `${state.currentRouterName}-${dateStr}`;
        }
    }

    static confirmAndExecute(message, callback) {
        if (confirm(message)) {
            callback();
        }
    }
}