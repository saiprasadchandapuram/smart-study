from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from pymongo import MongoClient
from dotenv import load_dotenv
from flask_bcrypt import Bcrypt
from datetime import datetime
import os
import certifi
import requests

# Load environment variables
load_dotenv()

# Load Together AI Key
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
print("DEBUG: TOGETHER_API_KEY =", TOGETHER_API_KEY)

if not TOGETHER_API_KEY:
    raise ValueError("TOGETHER_API_KEY environment variable not set. Please check your .env file.")

# Flask app setup
app = Flask(__name__)
app.secret_key = 'your_secret_key_here_change_this_to_something_secure'

# Bcrypt setup for password hashing
bcrypt = Bcrypt(app)

# MongoDB setup with TLS support and certificate verification
client = MongoClient(
    "mongodb+srv://saiprasad:saiprasad0330@cluster0.22gvmip.mongodb.net/?appName=Cluster0",
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=5000
)
db = client.smartstudy
chat_collection = db.chats
user_collection = db.users

# -------------------- ROUTES --------------------
@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    if 'username' not in session:
        return jsonify({"response": "Please log in to use the chat."}), 401

    user_input = request.json.get('message')
    if not user_input:
        return jsonify({"error": "No input message provided."}), 400

    try:
        headers = {
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "messages": [
                {"role": "user", "content": user_input}
            ],
            "temperature": 0.7,
            "max_tokens": 200
        }

        res = requests.post("https://api.together.xyz/v1/chat/completions", headers=headers, json=data)
        response_data = res.json()

        ai_response = response_data['choices'][0]['message']['content']

        chat_data = {
            "username": session['username'],
            "question": user_input,
            "answer": ai_response,
            "timestamp": datetime.utcnow()
        }
        chat_collection.insert_one(chat_data)

        return jsonify({"response": ai_response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/history')
def history():
    if 'username' not in session:
        return redirect(url_for('login'))

    chat_logs = chat_collection.find({"username": session['username']}).sort("timestamp", -1)
    return render_template('history.html', chats=chat_logs)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if user_collection.find_one({'username': username}):
            return "Username already exists."

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        user_collection.insert_one({'username': username, 'password': hashed_pw})
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = user_collection.find_one({'username': username})
        if user and bcrypt.check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('home'))
        return "Invalid credentials."

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# -------------------- RUN --------------------
if __name__ == '__main__':
    app.run(debug=True)