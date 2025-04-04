from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import bcrypt
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# 🔹 Get MongoDB connection string from environment variable
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not set!")

client = MongoClient(MONGO_URI)
db = client["User_Data"]
users_collection = db["Users"]
submissions_db = client["SUBMISSIONS"]  # Database for storing submissions

# ----------- SIGNUP ------------
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    fullname = data.get("fullname")
    username = data.get("username")
    password = data.get("password")
    roll_number = data.get("rollNumber")  # Ensure roll number is unique
    section = data.get("section")
    year = data.get("year")

    if not all([fullname, username, password, roll_number, section, year]):
        return jsonify({"error": "All fields are required"}), 400

    # Check if username or roll number already exists
    if users_collection.find_one({"username": username}):
        return jsonify({"error": "Username already exists"}), 409
    if users_collection.find_one({"roll_number": roll_number}):
        return jsonify({"error": "Roll number already in use"}), 409

    # Hash the password before storing
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

# ----------- LOGIN ------------
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
    
    return jsonify({"error": "Invalid credentials"}), 401

# ----------- SAVE IMAGE URL ------------
@app.route('/save_submission', methods=['POST'])
def save_submission():
    data = request.json
    subject = request.args.get("subject")  # Subject passed as query parameter
    year = data.get("year")
    section = data.get("section")
    roll_number = data.get("roll_number")
    paper_id = data.get("paper_id")
    question_number = str(data.get("question_number"))
    image_url = data.get("image_url")

    if not all([subject, year, section, roll_number, paper_id, question_number, image_url]):
        return jsonify({"error": "All fields are required"}), 400

    subject_collection = submissions_db[subject]  # Select the collection for the subject

    # Find if submission exists
    submission = subject_collection.find_one({
        "year": year, "section": section, "roll_number": roll_number, "paper_id": paper_id
    })

    if submission:
        # Update existing submission and replace image URL at correct index
        subject_collection.update_one(
            {"_id": submission["_id"]},
            {"$set": {f"image_urls.{question_number}": image_url}}
        )
    else:
        # Create new submission document
        submission_data = {
            "year": year,
            "section": section,
            "roll_number": roll_number,
            "paper_id": paper_id,
            "image_urls": {question_number: image_url}  # Initialize array-like dictionary
        }
        subject_collection.insert_one(submission_data)

    return jsonify({"message": "Image URL saved successfully!"}), 201

# ----------- GET PAPER IDS FOR SUBJECT ------------
@app.route('/get_paper_ids', methods=['GET'])
def get_paper_ids():
    subject = request.args.get("subject")
    if not subject:
        return jsonify({"error": "Subject is required"}), 400

    print(f"Querying collection: {subject}")
    print(f"Available collections: {submissions_db.list_collection_names()}")

    subject_collection = submissions_db[subject]
    paper_ids = db[subject].distinct("paper_id")

    print(f"Found paper IDs: {paper_ids}")  # Debugging
    return jsonify({"paper_ids": paper_ids}), 200


# ----------- TEST ROUTE ------------
@app.route('/test', methods=['GET'])
def test():
    return "Test route works!", 200

# ----------- START SERVER ------------
if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))  # Use PORT from environment or default to 5000
    app.run(host="0.0.0.0", port=port, debug=True)
