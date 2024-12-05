from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2 import sql

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
def add_rfid():
    data = request.json
    rfid_tag = data.get("rfid_tag")
    product_name = data.get("product_name")
    count = data.get("count", 1)  # Por defecto, la cantidad será 1
    last_seen = data.get("last_seen")

    if not (rfid_tag and product_name and last_seen):
        return jsonify({"error": "Todos los campos son obligatorios"}), 400

    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO inventory (rfid_tag, product_name, count, last_seen)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (rfid_tag) DO UPDATE
                SET count = inventory.count + EXCLUDED.count,
                    last_seen = EXCLUDED.last_seen
                """,
                (rfid_tag, product_name, count, last_seen)
            )
            conn.commit()
            cursor.close()
            return jsonify({"message": "RFID agregado/actualizado correctamente"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
    return jsonify({"error": "No se pudo conectar a la base de datos"}), 500


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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)