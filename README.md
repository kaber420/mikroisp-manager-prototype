# µMonitor Pro (MikroISP Manager)

##  Características Principales

Este proyecto está evolucionando de un simple monitor a un panel de gestión ligero, incluyendo:

* **Gestión Multi-Fabricante:**
    * **MikroTik (RouterOS):** Monitoreo de recursos, aprovisionamiento de usuario API con SSL, gestión de PPPoE (Planes, Perfiles, Secrets), gestión de Red (IPs, NAT), gestión de Sistema (Usuarios del Router, Backups/Exports).
    * **Ubiquiti (AirOS):** Monitoreo en tiempo real de APs (estado, clientes conectados, airtime, throughput).

* **Gestión de Red y Clientes:**
    * **Gestión de Zonas:** El pilar central. Agrupa tus dispositivos de red (APs y Routers) por ubicación física o lógica.
    * **Gestión de Clientes:** Base de datos de clientes con su información de contacto y estado de servicio.
    * **Gestión de CPEs:** Inventario global de todos los CPEs (clientes Ubiquiti) detectados, con capacidad de asignarlos a un cliente.

* **Sistema y Monitoreo:**
    * **Dashboard:** Vista global del estado de la red, incluyendo APs con mayor airtime y CPEs con peor señal.
    * **Sistema de Usuarios:** Múltiples usuarios administradores para la plataforma.
    * **Alertas:** Notificaciones de estado (ej. AP caído, Router caído) a través de Telegram.
    * **Cifrado:** Las contraseñas de los dispositivos se almacenan cifradas en la base de datos.

## 🛠 Stack Tecnológico

* **Backend:** [FastAPI](https://fastapi.tiangolo.com/) y Uvicorn.
* **Frontend:** [Jinja2](https://jinja.palletsprojects.com/) (para el renderizado de plantillas HTML) y [Tailwind CSS](https://tailwindcss.com/) (para el diseño de la UI).
* **Base de Datos:** SQLite (para el inventario y las estadísticas).
* **Conectividad:**
    * 
outeros-api: Para la comunicación con dispositivos MikroTik.
    * 
equests (Cliente HTTP): Para la comunicación con dispositivos Ubiquiti (vía status.cgi).
* **Autenticación:** passlib[bcrypt] y python-jose[cryptography] para hashing de contraseñas y tokens JWT.

##  Cómo Empezar

### Prerrequisitos

* Python 3.10 o superior.
* pip (Python package installer).

### 1. Instalación

Clona este repositorio y muévete a la carpeta principal:
```bash
git clone <URL-DE-TU-REPOSITORIO>
cd mikroisp-manager-main
```

Instala las dependencias:
```bash
pip install -r requirements.txt
```

### 2. Ejecutar la Aplicación

El script launcher.py se encarga de todo: inicia la base de datos, el monitor en segundo plano y el servidor web.

```bash
python launcher.py
```

---

## ⚙ Configuración Inicial

Si es la primera vez que ejecutas la aplicación, el launcher te guiará a través de dos asistentes en la terminal.

### Asistente de Configuración (.env)

La primera vez que ejecutes launcher.py, o si lo ejecutas con python launcher.py --config, aparecerá un asistente para configurar tu archivo .env. Este archivo guarda las configuraciones básicas del servidor.

El asistente te preguntará por el puerto y el nombre de la base de datos:

1.  **Puerto de la App Web:**
    ```bash
    ¿En qué puerto debe correr la App Web? (Actual: 8000): 
    ```
    * Puedes escribir un nuevo número (ej. 8080) y presionar Enter.
    * O simplemente **presiona Enter** para usar el valor (Actual: 8000).

2.  **Nombre de la Base de Datos:**
    ```bash
    ¿Nombre del archivo de la base de datos? (Actual: inventory.sqlite): 
    ```
    * Puedes escribir un nuevo nombre (ej. mi_red.db) y presionar Enter.
    * O simplemente **presiona Enter** para usar el valor (Actual: inventory.sqlite).

El asistente también generará claves de seguridad (SECRET_KEY y ENCRYPTION_KEY) automáticamente.

### Creación del Primer Administrador

Inmediatamente después del asistente de .env (solo la primera vez), la aplicación detectará que la base de datos está vacía e iniciará un segundo asistente para crear tu cuenta de administrador:

```bash
--- Asistente de Configuración Inicial: Creación del Primer Administrador ---
Introduce el nombre de usuario para el administrador: admin
Introduce la contraseña: 
Confirma la contraseña: 

¡Usuario 'admin' creado! La aplicación ahora se iniciará.
```

### 3. Acceder a la Aplicación

Una vez que la aplicación esté corriendo, abre tu navegador y ve a:

**[http://localhost:8000](http://localhost:8000)** (o el puerto que hayas configurado).

Inicia sesión con el usuario y contraseña que acabas de crear.

---

## 🧭 Flujo de Trabajo Básico (Guía Rápida)

Para que la aplicación funcione correctamente, sigue este orden:

1.  **Crear una Zona:**
    * Ve a **Manage Zones** en el menú lateral.
    * Crea al menos una zona (ej. "Torre Principal", "Zona Centro").
    * **Este paso es un requisito previo** para añadir cualquier dispositivo.

2.  **Añadir Dispositivos (Asignar a Zona):**
    * **Para Routers MikroTik:**
        1.  Ve a **Manage Routers**.
        2.  Añade el router con su IP, usuario dmin y contraseña (del router). Asigna la Zona creada.
        3.  Haz clic en el botón **Provision** en la lista.
        4.  Completa el formulario para crear un usuario API (ej. pi-user). Esto configurará SSL y creará un usuario de solo API con los permisos correctos.
    * **Para APs Ubiquiti:**
        1.  Ve a **Manage APs**.
        2.  Añade el AP con su IP, usuario (ubnt) y contraseña. Asigna la Zona creada.

3.  **Monitorear y Gestionar:**
    * El monitor en segundo plano (monitor.py) comenzará a escanear tus dispositivos.
    * En el **Dashboard**, empezarás a ver el estado de tus APs y CPEs.
    * En **Manage CPEs**, verás una lista global de todos los clientes inalámbricos detectados.
    * En **Manage Routers** > (Selecciona un router), podrás usar las pestañas para **Configurar Red** (IPs, NAT, PPPoE) o **Sistema** (Backups, Usuarios).

4.  **Crear y Asignar Clientes:**
    * Ve a **Manage Clients** y crea un nuevo cliente (persona o empresa).
    * Edita el cliente, ve a la pestaña "Client Information" y podrás asignar los CPEs que se han detectado automáticamente.

## ⚖ Licencia

Este proyecto está licenciado bajo la Licencia Pública General de Affero GNU v3.0 (AGPL-3.0).
