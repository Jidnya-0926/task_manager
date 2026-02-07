from flask import Flask, render_template, request, jsonify
import mysql.connector
import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Initialize the Flask application
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_default_key")

# --- DATABASE CONFIGURATION ---
def get_db_connection():
    """
    Establishes a connection to the MySQL database.
    """
    try:
        db_port = int(os.environ.get("DB_PORT", 3306))

        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASS", ""),
            database=os.getenv("DB_NAME", "task_manager"),
            port=db_port,
            charset='utf8',
            connect_timeout=5
        )
        return connection
    except mysql.connector.Error as err:
        print(f"CRITICAL: Database Connection Error: {err}")
        return None

@app.route('/')
def index():
    """
    Renders the main page and performs a diagnostic DB check by fetching user count.
    """
    db_status = "Connected"
    error_msg = ""
    user_count = 0

    conn = get_db_connection()
    if conn is None:
        db_status = "Disconnected"
        error_msg = "Could not connect to MySQL. Check XAMPP and .env settings."
    else:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            cursor.close()
        except mysql.connector.Error as err:
            db_status = "Table Error"
            error_msg = f"Connected to DB, but failed to fetch users: {err}"
            print(f"DB Query Error: {err}")
        finally:
            conn.close()

    print(f"--- Diagnostic: DB Status: {db_status} | Registered Users: {user_count} ---")
    return render_template('index.html', db_status=db_status, error_msg=error_msg, user_count=user_count)

# --- AUTH ROUTES ---

@app.route('/register', methods=['POST'])
def register():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed."}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        conn.commit()
        return jsonify({"message": "User registered successfully"}), 201
    except mysql.connector.Error:
        return jsonify({"error": "Username already exists"}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    print(f"--- Login Attempt: Username='{username}' ---")

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        # Using a parameterized query to securely check credentials
        cursor.execute("SELECT id, username FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()

        if user:
            print(f"--- Login Success for ID: {user['id']} ---")
            return jsonify(user), 200
        else:
            print("--- Login Failed: Invalid Credentials ---")
            return jsonify({"error": "Invalid username or password"}), 401
    except mysql.connector.Error as err:
        print(f"--- Login DB Error: {err} ---")
        return jsonify({"error": "Database query failed"}), 500
    finally:
        cursor.close()
        conn.close()

# --- TASK ROUTES ---

@app.route('/tasks/<int:user_id>', methods=['GET'])
def get_tasks(user_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tasks WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
    tasks = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(tasks)

@app.route('/tasks', methods=['POST'])
def add_task():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json()
    title = data.get('title')
    user_id = data.get('user_id')

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title, user_id) VALUES (%s, %s)", (title, user_id))
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()

    return jsonify({"id": new_id, "title": title, "status": "pending"}), 201

@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json()
    new_status = data.get('status')

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status = %s WHERE id = %s", (new_status, task_id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Updated"})

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Deleted"})

if __name__ == '__main__':
    # Running on Port 5000
    print("\n" + "="*50)
    print("  STUDENT TASK MANAGER SERVER")
    print("  Local URL: http://127.0.0.1:5000")
    print("="*50 + "\n")
    # app.run(debug=True, port=5000)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)