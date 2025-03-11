from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import bcrypt
import ssl

app = Flask(__name__)
CORS(app)

# Connect to MongoDB Atlas
client = MongoClient(
    "mongodb+srv://digvijaysonawane007:ABCDE@cluster0.rpjgb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
    ssl_cert_reqs=ssl.CERT_NONE
)
db = client["User_Data"]
users_collection = db["Users"]

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    # Hash the password before storing
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Check if user exists
    if users_collection.find_one({"username": username}):
        return jsonify({"error": "User already exists"}), 409

    # Store in database
    users_collection.insert_one({"username": username, "password": hashed_password})

    return jsonify({"message": "User registered successfully!"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    user = users_collection.find_one({"username": username})

    if user and bcrypt.checkpw(password.encode('utf-8'), user["password"]):
        return jsonify({"message": "Login successful!"}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.route('/test', methods=['GET'])
def test():
    return "Test route works!", 200


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
