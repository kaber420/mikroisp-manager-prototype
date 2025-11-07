µMonitor Pro (Prototipo de MikroISP Manager)

Un sistema de monitoreo y gestión para Proveedores de Servicios de Internet Inalámbrico (WISP). Este prototipo está diseñado para gestionar tanto puntos de acceso (APs) Ubiquiti AirOS como routers MikroTik desde una única interfaz web unificada.

🚀 Características Principales

Este proyecto, aunque es un prototipo, incluye una base sólida de características de gestión:

    Gestión de Red Multi-Fabricante:

        MikroTik: Gestión completa de routers, incluyendo el aprovisionamiento inicial (creación de usuario API y certificado SSL) e instalación de configuraciones base (PPPoE, Queues).

        Ubiquiti: Monitoreo de APs AirOS (estado, clientes, airtime) a través de la API status.cgi.

    Gestión de Clientes y Dispositivos:

        Gestión de Clientes (Personas) con su información de contacto y estado de servicio.

        Gestión de CPEs (Dispositivos) con capacidad de asignarlos a un cliente.

    Organización y Sistema:

        Gestión de Zonas: Agrupa tus dispositivos de red (APs y Routers) por ubicación física o lógica.

        Sistema de Usuarios: Múltiples usuarios administradores con autenticación segura (JWT).

        Alertas: Notificaciones de estado (ej. AP caído) a través de Telegram.

🛠️ Stack Tecnológico

Este proyecto está construido con un stack de Python moderno y ligero:

    Backend: FastAPI (para la API REST) y Uvicorn (como servidor web).

    Frontend: Jinja2 (para el renderizado de plantillas HTML) y Tailwind CSS (para el diseño de la UI).

    Base de Datos: SQLite (para el inventario y las estadísticas).

    Conectividad:

        routeros-api: Para la comunicación con dispositivos MikroTik.

        ap_client.py: Para la comunicación con dispositivos Ubiquiti.

    Autenticación: passlib[bcrypt] y python-jose[cryptography] para hashing de contraseñas y tokens JWT.

🏁 Cómo Empezar

Prerrequisitos

    Python 3.x

    pip (Python package installer)

1. Clonar el repositorio

Bash

git clone <URL-DE-TU-REPOSITORIO>
cd mikroisp-manager-prototype-router-mod

2. Instalar dependencias

Este proyecto usa un archivo requirements.txt para gestionar sus dependencias.
Bash

pip install -r requirements.txt

3. Ejecutar la aplicación

El script main.py se encarga de iniciar la base de datos, el monitor en segundo plano y el servidor web.
Bash

python launcher.py

4. Configuración Inicial (Primer Usuario)

La primera vez que ejecutes launcher.py, la aplicación detectará que no hay usuarios en la base de datos e iniciará un asistente interactivo en tu terminal para crear la primera cuenta de administrador.
Bash

--- Asistente de Configuración Inicial: Creación del Primer Administrador ---
Introduce el nombre de usuario para el administrador: admin
Introduce la contraseña: 
Confirma la contraseña: 

5. Acceder a la Aplicación

Una vez que la aplicación esté corriendo, abre tu navegador y ve a:

http://localhost:8000 o el purto elegido en el asistnt

Inicia sesión con el usuario y contraseña que acabas de crear.

⚖️ Licencia

Este proyecto está licenciado bajo la GNU Affero General Public License v3.0 (AGPL-3.0).
