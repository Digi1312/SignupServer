from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import bcrypt
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Get MongoDB connection string from environment variable
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not set!")

client = MongoClient(MONGO_URI)
db = client["User_Data"]
users_collection = db["Users"]
images_collection = db["Images"]  # New collection for storing images

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    fullname = data.get("fullname")
    username = data.get("username")
    password = data.get("password")
    roll_number = data.get("rollNumber")  # New field
    section = data.get("section")  # New field
    year = data.get("year")  # New field

    if not username or not password or not roll_number or not section or not year:
        return jsonify({"error": "All fields are required"}), 400

    if users_collection.find_one({"username": username}):
        return jsonify({"error": "User already exists"}), 409

    if users_collection.find_one({"roll_number": roll_number}):  # Ensure unique roll number
        return jsonify({"error": "Roll number already in use"}), 409

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    user_data = {
        "fullname": fullname,
        "username": username,
        "password": hashed_password.decode('utf-8'),
        "roll_number": roll_number,
        "section": section,
        "year": year
    }
    
    users_collection.insert_one(user_data)

    return jsonify({"message": "User registered successfully!"}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    user = users_collection.find_one({"username": username})

    if user and bcrypt.checkpw(password.encode('utf-8'), user["password"].encode('utf-8')):
    return jsonify({
        "message": "Login successful!",
        "fullname": user["fullname"],
        "rollNumber": user["roll_number"],
        "section": user["section"],
        "year": user["year"]
    }), 200

    else:
        return jsonify({"error": "Invalid credentials"}), 401

# New route to store image URLs in MongoDB
@app.route('/saveImage', methods=['POST'])
def save_image():
    data = request.json
    image_url = data.get("imageUrl")
    username = data.get("username")  # Optional: Store user association

    if not image_url:
        return jsonify({"error": "Image URL is required"}), 400

    image_data = {"imageUrl": image_url}
    if username:
        image_data["username"] = username

    images_collection.insert_one(image_data)

    return jsonify({"message": "Image URL saved successfully!"}), 201

@app.route('/getImages', methods=['GET'])
def get_images():
    images = list(images_collection.find({}, {"_id": 0, "imageUrl": 1}))  # Return only image URLs
    return jsonify(images), 200

@app.route('/test', methods=['GET'])
def test():
    return "Test route works!", 200

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
