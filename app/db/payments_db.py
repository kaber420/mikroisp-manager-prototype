# app/db/payments_db.py
import sqlite3
from typing import List, Dict, Any, Optional
from .base import get_db_connection

def get_payment_by_id(payment_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene un pago específico por su ID."""
    conn = get_db_connection()
    cursor = conn.execute("SELECT * FROM pagos WHERE id = ?", (payment_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_payments_for_client(client_id: int) -> List[Dict[str, Any]]:
    """Obtiene todo el historial de pagos de un cliente, del más reciente al más antiguo."""
    conn = get_db_connection()
    cursor = conn.execute(
        "SELECT * FROM pagos WHERE client_id = ? ORDER BY fecha_pago DESC", 
        (client_id,)
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def create_payment(client_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Inserta un nuevo registro de pago en la base de datos.
    Devuelve el registro del pago creado.
    """
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO pagos (client_id, monto, mes_correspondiente, metodo_pago, notas, fecha_pago)
               VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))""",
            (
                client_id,
                data['monto'],
                data['mes_correspondiente'],
                data.get('metodo_pago'),
                data.get('notas')
            )
        )
        new_payment_id = cursor.lastrowid
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise ValueError(str(e))
    finally:
        conn.close()

    new_payment = get_payment_by_id(new_payment_id)
    if not new_payment:
        raise ValueError("No se pudo recuperar el pago después de la creación.")
    return new_payment

def update_payment_notes(payment_id: int, notas: str) -> int:
    """Actualiza las notas de un pago existente (para añadir advertencias de error)."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "UPDATE pagos SET notas = ? WHERE id = ?", (notas, payment_id)
        )
        conn.commit()
        return cursor.rowcount
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error actualizando notas de pago: {e}")
        return 0
    finally:
        conn.close()

# --- ¡NUEVA FUNCIÓN AÑADIDA PARA EL MOTOR DE FACTURACIÓN! ---
def check_payment_exists(client_id: int, billing_cycle: str) -> bool:
    """
    Verifica si un cliente ya tiene un pago registrado para un ciclo (ej. "2025-11").
    """
    conn = get_db_connection()
    cursor = conn.execute(
        "SELECT 1 FROM pagos WHERE client_id = ? AND mes_correspondiente = ? LIMIT 1",
        (client_id, billing_cycle)
    )
    payment_exists = cursor.fetchone() is not None
    conn.close()
    return payment_exists