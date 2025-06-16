from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from flask_mail import Mail, Message
import uuid # Using uuid for more robust submission IDs

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# --- Mail Configuration ---
# Configure Flask-Mail with credentials from your .env file
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() in ['true', '1', 'yes']
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'false').lower() in ['true', '1', 'yes']
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
mail = Mail(app)

# Embedded quiz data
QUIZ_DATA = {
    "title": "Demand and Supply Quiz",
    "timeLimit": 1200,  # Global limit (can be ignored if using per-question)
    "timePerQuestion": 30, # Time allowed per question in seconds
    "questions": [
        { "id": 1, "question": "What does the Law of Demand state, ceteris paribus?", "options": ["As price increases, quantity demanded increases", "As price increases, quantity demanded decreases", "As supply increases, demand increases", "As income increases, demand always increases"], "correct_answer": 1 },
        { "id": 2, "question": "Which of the following can shift the demand curve to the right?", "options": ["A decrease in consumer income (for normal goods)", "A fall in the price of a complement", "A fall in the price of the good itself", "An increase in input prices"], "correct_answer": 1 },
        { "id": 3, "question": "The substitution effect means that:", "options": ["Consumers substitute inferior goods with luxury goods", "A good becomes more desirable as it becomes more expensive", "Consumers switch to a good when its price falls relative to substitutes", "Consumers always prefer imported goods"], "correct_answer": 2 },
        { "id": 4, "question": "Which of the following is not a determinant of supply?", "options": ["Input prices", "Technology", "Consumer tastes", "Government subsidies"], "correct_answer": 2 },
        { "id": 5, "question": "A rightward shift in the supply curve results in:", "options": ["Higher prices and lower quantity", "Lower prices and higher quantity", "No change in equilibrium", "Lower prices and lower quantity"], "correct_answer": 1 },
        { "id": 6, "question": "What causes movement along the demand curve?", "options": ["Change in price of substitute goods", "Change in consumer income", "Change in the price of the good itself", "Change in consumer expectations"], "correct_answer": 2 },
        { "id": 7, "question": "Market equilibrium occurs when:", "options": ["Quantity supplied is greater than quantity demanded", "Demand equals supply", "Supply increases rapidly", "Demand is falling while price is rising"], "correct_answer": 1 },
        { "id": 8, "question": "A shortage occurs when:", "options": ["Quantity supplied exceeds quantity demanded", "Price is above equilibrium", "Price is below equilibrium", "Demand curve shifts left"], "correct_answer": 2 },
        { "id": 9, "question": "The Law of Supply states that:", "options": ["As price rises, supply decreases", "As price rises, supply increases", "Supply is not affected by price", "Supply only increases when demand increases"], "correct_answer": 1 },
        { "id": 10, "question": "Which factor will most likely cause a leftward shift in the supply curve?", "options": ["Technological advancement", "Fall in input costs", "Increase in taxes", "Increase in number of sellers"], "correct_answer": 2 },
        { "id": 11, "question": "The demand curve typically slopes downward because of the substitution and income effects.", "options": ["True", "False"], "correct_answer": 0 },
        { "id": 12, "question": "An increase in consumer income will always increase the demand for every type of good.", "options": ["True", "False"], "correct_answer": 1 },
        { "id": 13, "question": "A surplus occurs when the quantity supplied is less than the quantity demanded.", "options": ["True", "False"], "correct_answer": 1 },
        { "id": 14, "question": "Expectations about future price increases can cause current supply to decrease.", "options": ["True", "False"], "correct_answer": 0 },
        { "id": 15, "question": "The supply curve usually slopes downward because producers are willing to supply more at lower prices.", "options": ["True", "False"], "correct_answer": 1 },
        { "id": 16, "question": "Equilibrium price is also known as the market-clearing price.", "options": ["True", "False"], "correct_answer": 0 },
        { "id": 17, "question": "Changes in the price of a good shift the demand curve.", "options": ["True", "False"], "correct_answer": 1 },
        { "id": 18, "question": "More sellers in a market typically increase the overall market supply.", "options": ["True", "False"], "correct_answer": 0 },
        { "id": 19, "question": "A decrease in the price of a substitute good will increase the demand for the original good.", "options": ["True", "False"], "correct_answer": 1 },
        { "id": 20, "question": "If both demand and supply increase, the equilibrium quantity will definitely rise.", "options": ["True", "False"], "correct_answer": 0 }
    ]
}

# In-memory storage (for demonstration purposes)
user_submissions = {}
user_accounts = {}

# --- Helper function to find submission by ID ---
def find_submission_by_id(submission_id):
    for email, submission in user_submissions.items():
        if submission.get("submission_id") == submission_id:
            return email, submission
    return None, None

# --- Routes ---
@app.route('/')
def index_page():
    return send_from_directory('.', 'index.html')

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Request body must be JSON."}), 400

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not all([name, email, password]):
        return jsonify({"success": False, "message": "All fields (name, email, password) are required"}), 400
    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify({"success": False, "message": "Invalid email format"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters long"}), 400
    if email in user_accounts:
        return jsonify({"success": False, "message": "Email already registered"}), 409

    user_accounts[email] = {
        "name": name,
        "password": password,  # In production, this should always be hashed
        "created_at": datetime.now(timezone.utc)
    }

    return jsonify({"success": True, "message": "User registered successfully", "userId": email}), 201

@app.route('/api/auth/login', methods=['POST'])
def login_user():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Request body must be JSON."}), 400
    
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required"}), 400

    user = user_accounts.get(email)
    if not user or user["password"] != password:
        return jsonify({"success": False, "message": "Invalid email or password"}), 401

    submission = user_submissions.get(email)
    if submission:
        return jsonify({
            "success": True,
            "quizAlreadyTaken": True,
            "message": f"You have already completed '{QUIZ_DATA['title']}'.",
            "email": email,
            "userId": email,
            "pastResults": {
                "submissionId": submission["submission_id"],
                "score": submission["score"],
                "totalQuestions": submission["total_questions"],
                "percentage": submission["percentage"],
                "feedback": submission["feedback"],
                "detailedResults": submission["detailed_results"]
            }
        }), 200
    else:
        return jsonify({"success": True, "message": "Login successful. You can start the quiz.", "email": email, "userId": email}), 200

@app.route('/api/quiz', methods=['GET'])
def get_quiz():
    return jsonify({
        "success": True,
        "title": QUIZ_DATA["title"],
        "timePerQuestion": QUIZ_DATA["timePerQuestion"],
        "questions": [{"id": q["id"], "question": q["question"], "options": q["options"]} for q in QUIZ_DATA["questions"]]
    })

@app.route('/api/submit', methods=['POST'])
def submit_quiz():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Request body must be JSON."}), 400

    user_email = data.get('email')
    user_answers_indices = data.get('answers', [])

    if not user_email or not isinstance(user_answers_indices, list):
        return jsonify({"success": False, "message": "User email and a valid answers list are required."}), 400

    if user_email not in user_accounts:
        return jsonify({"success": False, "message": "User not found."}), 401
    if user_email in user_submissions:
        return jsonify({"success": False, "message": "This quiz has already been submitted by you."}), 403

    score = 0
    total_questions = len(QUIZ_DATA["questions"])
    detailed_results = []

    for i, question in enumerate(QUIZ_DATA["questions"]):
        correct_answer_index = question["correct_answer"]
        user_selected_index = user_answers_indices[i] if i < len(user_answers_indices) else None
        
        is_correct = (user_selected_index is not None and int(user_selected_index) == correct_answer_index)
        if is_correct:
            score += 1

        detailed_results.append({
            "id": question["id"],
            "question_text": question["question"],
            "user_selected_answer_text": question["options"][user_selected_index] if user_selected_index is not None else "Not Answered",
            "correct_answer_text": question["options"][correct_answer_index],
            "is_correct": is_correct
        })

    percentage = (score / total_questions) * 100 if total_questions > 0 else 0
    name = user_accounts.get(user_email, {}).get('name', 'Quiz Taker').split(' ')[0]

    if percentage == 100: feedback_text = f"Perfect score, {name}! You're a demand and supply expert!"
    elif percentage >= 80: feedback_text = f"Excellent work, {name}!"
    elif percentage >= 60: feedback_text = f"Good job, {name}! Solid understanding."
    else: feedback_text = f"Keep practicing, {name}. You'll get there!"

    submission_id = str(uuid.uuid4())
    user_submissions[user_email] = {
        "submission_id": submission_id,
        "score": score,
        "total_questions": total_questions,
        "percentage": round(percentage, 2),
        "feedback": feedback_text,
        "submitted_at": datetime.now(timezone.utc),
        "detailed_results": detailed_results
    }
    
    print(f"Quiz submitted by: {user_email}, Score: {score}/{total_questions}")

    # --- Send Email Notification to Admin (cleaned up) ---
    admin_email = os.getenv('ADMIN_EMAIL_RECIPIENT')
    if admin_email:
        try:
            subject = f"Quiz Submission: {user_email} on '{QUIZ_DATA['title']}'"
            body = f"User {user_email} completed the quiz with a score of {score}/{total_questions} ({percentage:.2f}%)."
            msg = Message(subject, recipients=[admin_email], body=body, reply_to=user_email)
            mail.send(msg)
            print(f"Successfully sent submission email to admin: {admin_email}")
        except Exception as e:
            print(f"!!! FAILED to send submission email to admin: {e}")

    return jsonify({
        "success": True,
        "submissionId": submission_id,
        "score": score,
        "totalQuestions": total_questions,
        "percentage": round(percentage, 2),
        "feedback": feedback_text,
        "detailedResults": detailed_results
    }), 200

@app.route('/api/user/submissions', methods=['GET'])
def get_user_submissions():
    user_email = request.args.get('email')
    if not user_email:
        return jsonify({"success": False, "message": "User email parameter is required."}), 400

    if user_email not in user_accounts:
        return jsonify({"success": False, "message": "User account not found."}), 404

    submissions_list = []
    if user_email in user_submissions:
        sub = user_submissions[user_email]
        submissions_list.append({
            "submissionId": sub["submission_id"],
            "quizTitle": QUIZ_DATA["title"],
            "score": sub["score"],
            "totalQuestionsInQuiz": sub["total_questions"],
            "percentage": sub["percentage"],
            "submittedAt": sub["submitted_at"].isoformat()
        })
    
    return jsonify({"success": True, "submissions": submissions_list})

@app.route('/api/submission/<submission_id_str>/details', methods=['GET'])
def get_submission_details(submission_id_str):
    user_email, submission = find_submission_by_id(submission_id_str)

    if not submission:
        return jsonify({"success": False, "message": "Submission not found."}), 404

    summary_response = {
        "submissionId": submission["submission_id"],
        "quizTitle": QUIZ_DATA["title"],
        "score": submission["score"],
        "totalQuestionsInQuiz": submission["total_questions"],
        "percentage": submission["percentage"],
        "feedback": submission["feedback"],
        "submittedAt": submission["submitted_at"].isoformat(),
        "userEmail": user_email
    }
    
    return jsonify({
        "success": True, 
        "summary": summary_response, 
        "details": submission["detailed_results"]
    })

# --- Main Execution ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"Starting Quizflow application on port {port}...")
    app.run(debug=True, port=port)
