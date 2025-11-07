/**
 * Objeto global de Validadores.
 * Contiene funciones de lógica pura para validar formatos de datos.
 * No manipula el DOM, solo devuelve true o false.
 */
(function(window) {
    "use strict";

    // --- NUEVA FUNCIÓN DE AYUDA ---
    /**
     * Verifica si un string contiene SÓLO números y puntos.
     * @param {string} str - El string a verificar.
     * @returns {boolean}
     */
    function _isNumbersAndDotsOnly(str) {
        if (typeof str !== 'string' || str === null) return false;
        const regex = /^[0-9.]+$/;
        return regex.test(str);
    }

    // --- Validadores de Red ---

    /**
     * Valida una dirección IPv4 estándar.
     * @param {string} ip - La IP a validar (ej. "192.168.1.1").
     * @returns {boolean} - true si es válida, false si no.
     */
    function isValidIPv4(ip) {
        if (typeof ip !== 'string' || ip === null) return false;
        const ipv4Regex = /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
        return ipv4Regex.test(ip);
    }

    /**
     * Valida una dirección IPv4 con notación CIDR.
     * @param {string} ipCidr - La IP con CIDR (ej. "192.168.1.0/24").
     * @returns {boolean} - true si es válida, false si no.
     */
    function isValidIPv4WithCIDR(ipCidr) {
        if (typeof ipCidr !== 'string' || ipCidr === null) return false;
        const cidrRegex = /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(3[0-2]|[12]?[0-9])$/;
        return cidrRegex.test(ipCidr);
    }

    /**
     * Valida un hostname (DNS-like).
     * Permite letras, números, guiones y puntos. No puede empezar ni terminar con guion.
     * @param {string} hostname - El hostname a validar (ej. "router-1.local").
     * @returns {boolean} - true si es válido, false si no.
     */
    function isValidHostname(hostname) {
        if (typeof hostname !== 'string' || hostname === null || hostname.length > 253) return false;
        // Regex para validar un hostname
        const hostnameRegex = /^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*$/;
        return hostnameRegex.test(hostname);
    }

    // --- NUEVA FUNCIÓN DE LÓGICA COMBINADA ---
    /**
     * Valida si un input es una IP válida O un Hostname válido.
     * Si el input SÓLO contiene números y puntos, FUERZA que sea una IP válida.
     * @param {string} input - El texto a validar.
     * @returns {boolean} - true si es válido, false si no.
     */
    function isValidIpOrHostname(input) {
        if (typeof input !== 'string' || input === null) return false;

        if (_isNumbersAndDotsOnly(input)) {
            // Si solo tiene números y puntos, DEBE ser una IP válida.
            return isValidIPv4(input);
        } else {
            // Si tiene letras o guiones, DEBE ser un hostname válido.
            return isValidHostname(input);
        }
    }


    /**
     * Valida un puerto de red (1-65535).
     * @param {string|number} port - El puerto a validar.
     * @returns {boolean} - true si es válido, false si no.
     */
    function isValidPort(port) {
        const portNum = parseInt(port, 10);
        return !isNaN(portNum) && portNum >= 1 && portNum <= 65535;
    }

    /**
     * Valida un rango de IPs (para pools de DHCP).
     * @param {string} ipRange - El rango (ej. "10.0.0.100-10.0.0.200").
     * @returns {boolean} - true si es válido, false si no.
     */
    function isValidIPRange(ipRange) {
        if (typeof ipRange !== 'string' || ipRange === null) return false;
        const parts = ipRange.split('-');
        if (parts.length !== 2) return false;
        // Valida que ambas partes sean IPs válidas
        return isValidIPv4(parts[0].trim()) && isValidIPv4(parts[1].trim());
    }

    // --- Validadores de Formularios Generales ---

    /**
     * Valida un formato de email básico.
     * @param {string} email - El email a validar.
     * @returns {boolean} - true si es válido, false si no.
     */
    function isValidEmail(email) {
        if (typeof email !== 'string' || email === null || email.trim() === '') return true; // Permitir campo vacío (opcional)
        // Regex simple para emails
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    /**
     * Valida un número de teléfono (formato muy flexible).
     * @param {string} phone - El teléfono a validar.
     * @returns {boolean} - true si es válido, false si no.
     */
    function isValidPhone(phone) {
        if (typeof phone !== 'string' || phone === null || phone.trim() === '') return true; // Permitir campo vacío (opcional)
        // Permite números, espacios, guiones, +, ()
        const phoneRegex = /^[0-9\s\-()+]{7,20}$/; 
        return phoneRegex.test(phone);
    }

    /**
     * Verifica que un valor no esté vacío.
     * @param {string} value - El valor del campo.
     * @returns {boolean} - true si *no* está vacío, false si está vacío.
     */
    function isRequired(value) {
        return value !== null && value.trim() !== '';
    }

    /**
     * Verifica que un número esté dentro de un rango.
     * @param {string|number} number - El número a validar.
     * @param {number} min - El valor mínimo (inclusivo).
     * @param {number} max - El valor máximo (inclusivo).
     * @returns {boolean} - true si está en rango, false si no.
     */
    function isInRange(number, min, max) {
        const num = parseInt(number, 10);
        return !isNaN(num) && num >= min && num <= max;
    }

    // --- Validadores de Reglas de Negocio ---

    /**
     * Valida un nombre de zona o plan (alfanumérico, guiones).
     * @param {string} name - El nombre a validar.
     * @returns {boolean} - true si es válido, false si no.
     */
    function isValidZoneName(name) {
        if (typeof name !== 'string' || name === null) return false;
        // Permite letras, números, espacios y guiones.
        const zoneRegex = /^[A-Za-z0-9\s-]{1,50}$/;
        return zoneRegex.test(name.trim());
    }

    // Exponer las funciones en un objeto global 'validators'
    window.validators = {
        isValidIPv4,
        isValidIPv4WithCIDR,
        isValidHostname,
        isValidIpOrHostname, // <-- NUEVA FUNCIÓN AÑADIDA
        isValidPort,
        isValidIPRange,
        isValidEmail,
        isValidPhone,
        isRequired,
        isInRange,
        isValidZoneName
    };

})(window);