# ap_client.py

import requests
import urllib3

# Desactivar los warnings de SSL ya que los dispositivos de red a menudo
# usan certificados autofirmados, lo cual es normal en una red interna.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class UbiquitiClient:
    """
    Un cliente para interactuar con la API de dispositivos Ubiquiti AirOS.
    Encapsula la lógica de autenticación y obtención de datos.
    """
    def __init__(self, host, username, password, verify_ssl=False):
        """
        Inicializa el cliente.

        Args:
            host (str): La dirección IP del dispositivo.
            username (str): El nombre de usuario para el login.
            password (str): La contraseña para el login.
            verify_ssl (bool): Si se debe verificar el certificado SSL. Por defecto es False.
        """
        self.base_url = f"https://{host}"
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = verify_ssl
        # Añadimos un User-Agent estándar para simular un navegador
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })


    def _authenticate(self) -> bool:
        """
        Método privado para realizar la autenticación.
        Guarda el token CSRF en la sesión si tiene éxito.

        Returns:
            bool: True si la autenticación fue exitosa, False en caso contrario.
        """
        auth_url = self.base_url + "/api/auth"
        payload = {"username": self.username, "password": self.password}
        
        try:
            response = self.session.post(auth_url, data=payload, timeout=15)
            # Lanza una excepción si el código de estado es un error (4xx o 5xx)
            response.raise_for_status() 

            csrf_token = response.headers.get('X-CSRF-ID')
            if csrf_token:
                self.session.headers.update({'X-CSRF-ID': csrf_token})
                return True
            
            print(f"Error de autenticación en {self.base_url}: No se recibió el token CSRF.")
            return False

        except requests.exceptions.RequestException as e:
            # Captura errores de red, timeouts, errores HTTP, etc.
            print(f"Error de red durante la autenticación en {self.base_url}: {e}")
            return False

    def get_status_data(self) -> dict | None:
        """
        Obtiene los datos completos de 'status.cgi' como un diccionario.

        Primero intenta autenticarse. Si tiene éxito, solicita los datos de estado.

        Returns:
            dict | None: Un diccionario con los datos del AP si todo fue exitoso,
                         o None si hubo algún error.
        """
        if not self._authenticate():
            print(f"Fallo en la autenticación para {self.base_url}, no se pueden obtener datos.")
            return None
        
        status_url = self.base_url + "/status.cgi"
        try:
            response = self.session.get(status_url, timeout=15)
            response.raise_for_status()
            
            # Intenta decodificar la respuesta como JSON
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Error de red al obtener datos de estado de {self.base_url}: {e}")
            return None
        except requests.exceptions.JSONDecodeError:
            print(f"Error: La respuesta de {self.base_url} no es un JSON válido.")
            # Esto puede pasar si el login falló silenciosamente y devolvió una página HTML de login
            return None