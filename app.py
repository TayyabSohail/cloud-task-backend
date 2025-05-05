from flask import Flask, request, jsonify
from flask_cors import CORS
from db import get_db_connection

app = Flask(__name__)
CORS(app)

# Signup endpoint
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    name = data.get("name")
    company = data.get("company_name")
    email = data.get("email")
    password = data.get("password")  # Plain text for now, hash later

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if user already exists
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        return jsonify({"message": "Email already registered"}), 409

    cursor.execute(
        "INSERT INTO users (name, company_name, email, password) VALUES (%s, %s, %s, %s)",
        (name, company, email, password),
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "User registered successfully"}), 201

# Login endpoint
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({"message": "Invalid email or password"}), 401

    return jsonify({"message": "Login successful", "user": user}), 200

# Get todos
@app.route("/todos/<int:user_id>", methods=["GET"])
def get_todos(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM todos WHERE user_id = %s", (user_id,))
    todos = cursor.fetchall()
    conn.close()
    return jsonify(todos)

# Add todo
@app.route("/todos", methods=["POST"])
def add_todo():
    data = request.get_json()
    user_id = data.get("user_id")
    text = data.get("text")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO todos (user_id, text) VALUES (%s, %s)", (user_id, text))
    conn.commit()
    conn.close()

    return jsonify({"message": "Todo added"}), 201

# Update todo
@app.route("/todos/<int:todo_id>", methods=["PUT"])
def update_todo(todo_id):
    data = request.get_json()
    text = data.get("text")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE todos SET text = %s WHERE id = %s", (text, todo_id))
    conn.commit()
    conn.close()

    return jsonify({"message": "Todo updated"})

# Delete todo
@app.route("/todos/<int:todo_id>", methods=["DELETE"])
def delete_todo(todo_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM todos WHERE id = %s", (todo_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Todo deleted"})

if __name__ == "__main__":
    app.run(debug=True)
