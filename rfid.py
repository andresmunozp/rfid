from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2 import sql
from datetime import datetime
from flask_socketio import SocketIO  # Correctly import SocketIO

# Configuración de conexión (usa las credenciales de Neon)
DB_HOST = "ep-falling-night-a4zni5ez.us-east-1.aws.neon.tech"       # Ejemplo: "your-project-name.neon.tech"
DB_PORT = "5432"          # Puerto estándar de PostgreSQL
DB_NAME = "apiIa"
DB_USER = "neondb_owner"
DB_PASSWORD = "p4B0cSwgKqae"

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Database connection function remains the same
def connect_to_db():
    try:
        conn = psycopg2.connect(
            host="ep-falling-night-a4zni5ez.us-east-1.aws.neon.tech",
            port="5432",
            database="apiIa",
            user="neondb_owner",
            password="p4B0cSwgKqae"
        )
        print("Conexión exitosa a la base de datos")
        return conn
    except Exception as e:
        print("Error al conectar a la base de datos:", e)
        return None

# Leer todos los datos del inventario
def fetch_inventory():
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inventory")
            rows = cursor.fetchall()
            for row in rows:
                print(row)
            cursor.close()
        except Exception as e:
            print("Error al consultar los datos:", e)
        finally:
            conn.close()

# Insertar un nuevo registro
def insert_rfid(rfid_tag, product_name, count, last_seen):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO inventory (rfid_tag, product_name, count, last_seen)
                VALUES (%s, %s, %s, %s)
                """,
                (rfid_tag, product_name, count, last_seen)
            )
            conn.commit()
            print(f"RFID {rfid_tag} insertado correctamente")
            cursor.close()
        except Exception as e:
            print("Error al insertar datos:", e)
        finally:
            conn.close()

# WebSocket notification function
def notify_frontend(event, data):
    socketio.emit(event, data)

def notify_inventory_update():
    socketio.emit("inventory_update")

@app.route('/api/rfid', methods=['POST'])
def handle_rfid_scan():
    data = request.json
    rfid = data.get("rfid")
    
    if not rfid:
        return jsonify({"error": "RFID no puede estar vacío."}), 400

    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            entry_rfid = "2a99c85"
            exit_rfid = "701ca630"

            if rfid == entry_rfid:
                notify_inventory_update()
                cursor.execute("SELECT available_spaces FROM parking_status WHERE id = 1")
                available_spaces = cursor.fetchone()[0]

                if available_spaces > 0:
                    available_spaces -= 1
                    cursor.execute(
                        "UPDATE parking_status SET available_spaces = %s WHERE id = 1",
                        (available_spaces,)
                    )

                    cursor.execute("SELECT count FROM inventory WHERE rfid_tag = %s", (rfid,))
                    existing_record = cursor.fetchone()

                    if existing_record:
                        new_count = existing_record[0] + 1
                        cursor.execute(
                            """
                            UPDATE inventory
                            SET count = %s, last_seen = %s
                            WHERE rfid_tag = %s
                            """,
                            (new_count, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), rfid)
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO inventory (rfid_tag, product_name, count, last_seen)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (rfid, "Carros de Entrada", 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        )

                    conn.commit()

                    # Notify frontend about the updated parking status
                    notify_frontend("parking_update", {"available_spaces": available_spaces})
                    notify_frontend("inventory_update", {"rfid": rfid, "action": "entry"})

                    return jsonify({"message": "Entrada registrada.", "available_spaces": available_spaces}), 200
                else:
                    return jsonify({"error": "No hay espacios disponibles."}), 400

            elif rfid == exit_rfid:
                notify_inventory_update()
                cursor.execute("SELECT available_spaces FROM parking_status WHERE id = 1")
                available_spaces = cursor.fetchone()[0]

                if available_spaces < 150:
                    available_spaces += 1
                    cursor.execute(
                        "UPDATE parking_status SET available_spaces = %s WHERE id = 1",
                        (available_spaces,)
                    )

                    cursor.execute("SELECT count FROM inventory WHERE rfid_tag = %s", (rfid,))
                    existing_record = cursor.fetchone()

                    if existing_record:
                        new_count = existing_record[0] + 1
                        cursor.execute(
                            """
                            UPDATE inventory
                            SET count = %s, last_seen = %s
                            WHERE rfid_tag = %s
                            """,
                            (new_count, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), rfid)
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO inventory (rfid_tag, product_name, count, last_seen)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (rfid, "Carros de Salida", 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        )

                    conn.commit()

                    # Notify frontend about the updated parking status
                    notify_frontend("parking_update", {"available_spaces": available_spaces})
                    notify_frontend("inventory_update", {"rfid": rfid, "action": "exit"})

                    return jsonify({"message": "Salida registrada.", "available_spaces": available_spaces}), 200
                else:
                    return jsonify({"error": "No hay vehículos para salir."}), 400

            else:
                return jsonify({"error": "RFID desconocido."}), 400

        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()

    return jsonify({"error": "Error al conectar con la base de datos"}), 500


@app.route('/api/parking_status', methods=['GET'])
def get_parking_status():
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT total_spaces, available_spaces FROM parking_status WHERE id = 1")
            parking_status = cursor.fetchone()
            if parking_status:
                total_spaces, available_spaces = parking_status
                return jsonify({
                    "total_spaces": total_spaces,
                    "available_spaces": available_spaces
                }), 200
            else:
                return jsonify({"error": "Estado del parqueadero no encontrado."}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
    return jsonify({"error": "Error al conectar con la base de datos"}), 500

@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inventory")
            rows = cursor.fetchall()
            inventory = [
                {
                    "rfid_tag": row[0],
                    "product_name": row[1],
                    "count": row[2],
                    "last_seen": row[3]
                }
                for row in rows
            ]
            cursor.close()
            return jsonify(inventory)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
    return jsonify({"error": "No se pudo conectar a la base de datos"}), 500


# READ: Obtener un registro específico
@app.route('/api/rfid/<rfid>', methods=['GET'])
def get_rfid_entry(rfid):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inventory WHERE rfid_tag = %s", (rfid,))
            row = cursor.fetchone()
            if row:
                result = {"rfid": row[0], "product_name": row[1], "count": row[2], "last_seen": row[3]}
                cursor.close()
                return jsonify(result), 200
            else:
                return jsonify({"error": "Registro no encontrado"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
    return jsonify({"error": "Error al conectar con la base de datos"}), 500

# UPDATE: Actualizar un registro
@app.route('/api/rfid/<rfid>', methods=['PUT'])
def update_rfid_entry(rfid):
    data = request.json
    product_name = data.get("product_name")
    count = data.get("count")

    if not product_name or not count:
        return jsonify({"error": "Datos incompletos"}), 400

    last_seen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE inventory
                SET product_name = %s, count = %s, last_seen = %s
                WHERE rfid_tag = %s
                """,
                (product_name, count, last_seen, rfid)
            )
            conn.commit()
            cursor.close()
            return jsonify({"message": "Registro actualizado correctamente"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
    return jsonify({"error": "Error al conectar con la base de datos"}), 500

# DELETE: Eliminar un registro
@app.route('/api/rfid/<rfid>', methods=['DELETE'])
def delete_rfid_entry(rfid):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM inventory WHERE rfid_tag = %s", (rfid,))
            conn.commit()
            cursor.close()
            return jsonify({"message": "Registro eliminado correctamente"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
    return jsonify({"error": "Error al conectar con la base de datos"}), 500

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)