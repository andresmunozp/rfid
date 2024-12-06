from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2 import sql
from datetime import datetime

# Configuración de conexión (usa las credenciales de Neon)
DB_HOST = "ep-falling-night-a4zni5ez.us-east-1.aws.neon.tech"       # Ejemplo: "your-project-name.neon.tech"
DB_PORT = "5432"          # Puerto estándar de PostgreSQL
DB_NAME = "apiIa"
DB_USER = "neondb_owner"
DB_PASSWORD = "p4B0cSwgKqae"

# Conectar a la base de datos
def connect_to_db():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
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

app = Flask(__name__)
CORS(app)

@app.route('/api/rfid', methods=['POST'])
def add_rfid_entry():
    data = request.json  # Recibe el JSON enviado desde Arduino

    # Extrae los datos del JSON
    rfid = data.get("rfid")
    product_name = data.get("product_name")
    count = data.get("count")

    # Verifica que todos los datos estén presentes
    if not rfid or not product_name or not count:
        return jsonify({"error": "Datos incompletos"}), 400

    # Conexión a la base de datos
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()

            # Verifica si el RFID ya existe
            cursor.execute("SELECT count FROM inventory WHERE rfid_tag = %s", (rfid,))
            existing_record = cursor.fetchone()

            if existing_record:
                # Si el RFID ya existe, incrementa la cantidad
                new_count = existing_record[0] + count
                cursor.execute(
                    """
                    UPDATE inventory
                    SET count = %s, last_seen = %s
                    WHERE rfid_tag = %s
                    """,
                    (new_count, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), rfid)
                )
                conn.commit()
                cursor.close()
                return jsonify({"message": "Cantidad actualizada correctamente", "rfid": rfid, "new_count": new_count}), 200
            else:
                # Si el RFID no existe, inserta un nuevo registro
                cursor.execute(
                    """
                    INSERT INTO inventory (rfid_tag, product_name, count, last_seen)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (rfid, product_name, count, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                conn.commit()
                cursor.close()
                return jsonify({"message": "Datos insertados correctamente", "rfid": rfid}), 201
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
    app.run(host='0.0.0.0', port=5000)