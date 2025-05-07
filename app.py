from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from db import get_db_connection
import os
import uuid
import mimetypes
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
# Extended allowed extensions to include various file types
ALLOWED_EXTENSIONS = {
    # Images
    'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp',
    # Documents
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf',
    # Archives
    'zip', 'rar', '7z',
    # Audio
    'mp3', 'wav', 'ogg',
    # Video
    'mp4', 'avi', 'mov', 'wmv'
}

# File size limit (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024  

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    # Group extensions into categories
    if extension in ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp']:
        return 'image'
    elif extension in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf']:
        return 'document'
    elif extension in ['zip', 'rar', '7z']:
        return 'archive'
    elif extension in ['mp3', 'wav', 'ogg']:
        return 'audio'
    elif extension in ['mp4', 'avi', 'mov', 'wmv']:
        return 'video'
    else:
        return 'other'

# Serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Signup endpoint
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    name = data.get("name")
    company = data.get("company")
    email = data.get("email")
    password = data.get("password")  # Plain text for now, hash later

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if user already exists
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        return jsonify({"message": "Email already registered"}), 409

    cursor.execute(
        "INSERT INTO users (name, company, email, password) VALUES (%s, %s, %s, %s)",
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
    
    # Transform the file_url to include the full server path
    for todo in todos:
        if todo.get('file_url'):
            todo['file_url'] = request.host_url + todo['file_url']
    
    return jsonify(todos)

# Add todo with optional file
@app.route("/todos", methods=["POST"])
def add_todo():
    if request.content_type and 'multipart/form-data' in request.content_type:
        user_id = request.form.get("user_id")
        text = request.form.get("text")
        uploaded_file = request.files.get('file')
        
        file_url = None
        file_type = None
        file_name = None
        
        # Save file if it exists and is valid
        if uploaded_file and uploaded_file.filename:
            if allowed_file(uploaded_file.filename):
                original_filename = secure_filename(uploaded_file.filename)
                filename = secure_filename(f"{uuid.uuid4()}_{original_filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                uploaded_file.save(filepath)
                file_url = f"{UPLOAD_FOLDER}/{filename}"
                file_type = get_file_type(original_filename)
                file_name = original_filename
            else:
                return jsonify({"message": "File type not allowed"}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO todos (user_id, text, file_url, file_type, file_name) VALUES (%s, %s, %s, %s, %s)", 
            (user_id, text, file_url, file_type, file_name)
        )
        todo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "Todo added", 
            "id": todo_id, 
            "file_url": request.host_url + file_url if file_url else None,
            "file_type": file_type,
            "file_name": file_name
        }), 201
    
    else:
        data = request.get_json()
        user_id = data.get("user_id")
        text = data.get("text")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO todos (user_id, text) VALUES (%s, %s)", (user_id, text))
        todo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Todo added", "id": todo_id}), 201

# Update todo with optional file
@app.route("/todos/<int:todo_id>", methods=["PUT"])
def update_todo(todo_id):
    if request.content_type and 'multipart/form-data' in request.content_type:
        text = request.form.get("text")
        uploaded_file = request.files.get('file')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT file_url FROM todos WHERE id = %s", (todo_id,))
        current_todo = cursor.fetchone()
        old_file_url = current_todo.get('file_url') if current_todo else None
        
        update_query = "UPDATE todos SET text = %s"
        params = [text]
        
        if uploaded_file and uploaded_file.filename:
            if allowed_file(uploaded_file.filename):
                original_filename = secure_filename(uploaded_file.filename)
                filename = secure_filename(f"{uuid.uuid4()}_{original_filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                uploaded_file.save(filepath)
                file_url = f"{UPLOAD_FOLDER}/{filename}"
                file_type = get_file_type(original_filename)
                file_name = original_filename
                
                if old_file_url and os.path.exists(old_file_url):
                    try:
                        os.remove(old_file_url)
                    except:
                        pass
                
                update_query += ", file_url = %s, file_type = %s, file_name = %s"
                params.extend([file_url, file_type, file_name])
            else:
                return jsonify({"message": "File type not allowed"}), 400
        
        update_query += " WHERE id = %s"
        params.append(todo_id)
        
        cursor.execute(update_query, tuple(params))
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Todo updated"})
    
    else:
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
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT file_url FROM todos WHERE id = %s", (todo_id,))
    todo = cursor.fetchone()
    
    cursor.execute("DELETE FROM todos WHERE id = %s", (todo_id,))
    conn.commit()
    conn.close()
    
    if todo and todo.get('file_url'):
        file_path = todo['file_url']
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
    
    return jsonify({"message": "Todo deleted"})

if __name__ == "__main__":
    app.run(debug=True)
