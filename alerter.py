# alerter.py

import requests
# Importamos la nueva función 'get_setting' de nuestro módulo de base de datos
from database import get_setting

def send_telegram_alert(message: str):
    """
    Envía un mensaje de texto a un chat específico de Telegram a través de un bot.
    Ahora lee la configuración (token y chat_id) directamente desde la base de datos.

    Args:
        message (str): El texto del mensaje que se va a enviar. Soporta formato Markdown.
    """
    # 1. Leer la configuración desde la base de datos en cada llamada.
    #    Esto asegura que si se cambian en la web, la alerta los usará inmediatamente.
    bot_token = get_setting('telegram_bot_token')
    chat_id = get_setting('telegram_chat_id')

    # 2. Verificar si las credenciales están configuradas en la base de datos.
    #    Si no lo están, imprime la alerta en la consola en lugar de fallar.
    if not bot_token or not chat_id:
        print("\n--- ALERTA (Simulada) ---")
        print("ADVERTENCIA: Token o Chat ID de Telegram no configurados en la base de datos.")
        print("La siguiente alerta solo se mostrará en la consola.")
        print(message)
        print("--------------------------\n")
        return

    # 3. Construir la URL de la API de Telegram
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    # 4. Preparar el payload del mensaje
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    # 5. Enviar la petición con manejo de errores
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        # Lanza una excepción si la API de Telegram devuelve un error (ej. token inválido)
        response.raise_for_status()
        print(f"Alerta enviada exitosamente a Telegram.")
        
    except requests.exceptions.RequestException as e:
        print(f"Error crítico: No se pudo enviar la alerta de Telegram. Causa: {e}")