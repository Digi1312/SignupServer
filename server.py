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
results_db=client["Results"]
extracted_db = client["extracted"]
user_data_db = client["User_Data"]

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

# ----------- GET ALL PAPER IDS FROM ALL SUBJECT COLLECTIONS ------------
@app.route('/get_all_paper_ids', methods=['GET'])
def get_all_paper_ids():
    all_paper_ids = set()  # To keep only unique paper_ids

    for collection_name in results_db.list_collection_names():
        collection = results_db[collection_name]
        paper_ids = collection.distinct("paper_id")
        all_paper_ids.update(paper_ids)

    return jsonify(sorted(list(all_paper_ids))), 200
# ----------- View result ------------
@app.route('/get_result', methods=['GET'])
def get_result():
    paper_id = request.args.get("paper_id")
    roll_no = request.args.get("roll_no")

    if not all([paper_id, roll_no]):
        return jsonify({"error": "Missing required parameters: paper_id and roll_no"}), 400

    comprehensive_results = []

    try:
        subject_names = results_db.list_collection_names()

        for subject in subject_names:
            result_collection = results_db[subject]
            result_docs = result_collection.find({
                "paper_id": paper_id,
                "roll_no": roll_no
            })

            extracted_collection = client["Extracted"][subject]
            ideal_collection = db[subject.lower()]

            for doc in result_docs:
                try:
                    question_no = doc.get("question_no")
                    similarity_score = doc.get("similarity_score", 0)

                    extracted_doc = extracted_collection.find_one({
                        "paper_id": paper_id,
                        "roll_no": roll_no,
                        "question_no": question_no
                    })
                    student_text = extracted_doc.get("extracted_text", "No extracted text found") if extracted_doc else "No extracted text found"

                    ideal_doc = ideal_collection.find_one({
                        "paper_id": paper_id,
                        "question_no": question_no
                    })
                    teacher_text = ideal_doc.get("answer_text", "No ideal answer found") if ideal_doc else "No ideal answer found"

                    comprehensive_results.append({
                        "subject": subject,
                        "question_no": question_no,
                        "similarity_score": similarity_score,
                        "teacher_text": teacher_text,
                        "student_text": student_text
                    })
                except Exception as e:
                    print(f"Error processing document in subject {subject}: {e}")
                    continue

        if not comprehensive_results:
            return jsonify({"message": "No results found for the given paper_id and roll_no"}), 404

        return jsonify(comprehensive_results), 200

    except Exception as e:
        print(f"Server Error in /get_result: {e}")
        return jsonify({"error": "Server error occurred", "details": str(e)}), 500

# ----------- TEST ROUTE ------------
@app.route('/test', methods=['GET'])
def test():
    return "Test route works!", 200

# ----------- START SERVER ------------
if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))  # Use PORT from environment or default to 5000
    app.run(host="0.0.0.0", port=port, debug=True)
