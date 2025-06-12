from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from flask_mail import Mail, Message

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# --- Mail Configuration ---
# Configure Flask-Mail with credentials from your .env file
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() in ['true', '1', 't']
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'false').lower() in ['true', '1', 't']
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
        {
            "id": 1,
            "question": "What does the Law of Demand state, ceteris paribus?",
            "options": [
                "As price increases, quantity demanded increases",
                "As price increases, quantity demanded decreases",
                "As supply increases, demand increases",
                "As income increases, demand always increases"
            ],
            "correct_answer": 1
        },
        {
            "id": 2,
            "question": "Which of the following can shift the demand curve to the right?",
            "options": [
                "A decrease in consumer income (for normal goods)",
                "A fall in the price of a complement",
                "A fall in the price of the good itself",
                "An increase in input prices"
            ],
            "correct_answer": 1
        },
        {
            "id": 3,
            "question": "The substitution effect means that:",
            "options": [
                "Consumers substitute inferior goods with luxury goods",
                "A good becomes more desirable as it becomes more expensive",
                "Consumers switch to a good when its price falls relative to substitutes",
                "Consumers always prefer imported goods"
            ],
            "correct_answer": 2
        },
        {
            "id": 4,
            "question": "Which of the following is not a determinant of supply?",
            "options": [
                "Input prices",
                "Technology",
                "Consumer tastes",
                "Government subsidies"
            ],
            "correct_answer": 2
        },
        {
            "id": 5,
            "question": "A rightward shift in the supply curve results in:",
            "options": [
                "Higher prices and lower quantity",
                "Lower prices and higher quantity",
                "No change in equilibrium",
                "Lower prices and lower quantity"
            ],
            "correct_answer": 1
        },
        {
            "id": 6,
            "question": "What causes movement along the demand curve?",
            "options": [
                "Change in price of substitute goods",
                "Change in consumer income",
                "Change in the price of the good itself",
                "Change in consumer expectations"
            ],
            "correct_answer": 2
        },
        {
            "id": 7,
            "question": "Market equilibrium occurs when:",
            "options": [
                "Quantity supplied is greater than quantity demanded",
                "Demand equals supply",
                "Supply increases rapidly",
                "Demand is falling while price is rising"
            ],
            "correct_answer": 1
        },
        {
            "id": 8,
            "question": "A shortage occurs when:",
            "options": [
                "Quantity supplied exceeds quantity demanded",
                "Price is above equilibrium",
                "Price is below equilibrium",
                "Demand curve shifts left"
            ],
            "correct_answer": 2
        },
        {
            "id": 9,
            "question": "The Law of Supply states that:",
            "options": [
                "As price rises, supply decreases",
                "As price rises, supply increases",
                "Supply is not affected by price",
                "Supply only increases when demand increases"
            ],
            "correct_answer": 1
        },
        {
            "id": 10,
            "question": "Which factor will most likely cause a leftward shift in the supply curve?",
            "options": [
                "Technological advancement",
                "Fall in input costs",
                "Increase in taxes",
                "Increase in number of sellers"
            ],
            "correct_answer": 2
        },
        # True/False Questions
        {
            "id": 11,
            "question": "The demand curve typically slopes downward because of the substitution and income effects.",
            "options": ["True", "False"],
            "correct_answer": 0
        },
        {
            "id": 12,
            "question": "An increase in consumer income will always increase the demand for every type of good.",
            "options": ["True", "False"],
            "correct_answer": 1
        },
        {
            "id": 13,
            "question": "A surplus occurs when the quantity supplied is less than the quantity demanded.",
            "options": ["True", "False"],
            "correct_answer": 1
        },
        {
            "id": 14,
            "question": "Expectations about future price increases can cause current supply to decrease.",
            "options": ["True", "False"],
            "correct_answer": 0
        },
        {
            "id": 15,
            "question": "The supply curve usually slopes downward because producers are willing to supply more at lower prices.",
            "options": ["True", "False"],
            "correct_answer": 1
        },
        {
            "id": 16,
            "question": "Equilibrium price is also known as the market-clearing price.",
            "options": ["True", "False"],
            "correct_answer": 0
        },
        {
            "id": 17,
            "question": "Changes in the price of a good shift the demand curve.",
            "options": ["True", "False"],
            "correct_answer": 1
        },
        {
            "id": 18,
            "question": "More sellers in a market typically increase the overall market supply.",
            "options": ["True", "False"],
            "correct_answer": 0
        },
        {
            "id": 19,
            "question": "A decrease in the price of a substitute good will increase the demand for the original good.",
            "options": ["True", "False"],
            "correct_answer": 1
        },
        {
            "id": 20,
            "question": "If both demand and supply increase, the equilibrium quantity will definitely rise.",
            "options": ["True", "False"],
            "correct_answer": 0
        }
    ]
}

# In-memory storage for submissions (replaces database)
user_submissions = {}
user_accounts = {}

# --- Routes ---
@app.route('/')
def index_page():
    return send_from_directory('.', 'index.html')

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    data = request.get_json()
    print(f"DEBUG: Received registration data: {data}")

    name = data.get('name') if data else None
    email = data.get('email') if data else None
    password = data.get('password') if data else None

    if not data or not name or not email or not password:
        return jsonify({"success": False, "message": "All fields (name, email, password) are required"}), 400
    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify({"success": False, "message": "Invalid email format"}), 400
    if len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters long"}), 400

    if email in user_accounts:
        return jsonify({"success": False, "message": "Email already registered"}), 409

    user_accounts[email] = {
        "name": name,
        "email": email,
        "password": password,  # In production, this should be hashed
        "created_at": datetime.now(timezone.utc)
    }

    return jsonify({
        "success": True,
        "message": "User registered successfully",
        "user_id": email
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login_user():
    data = request.get_json()
    print(f"DEBUG: Received login data: {data}")
    email = data.get('email') if data else None
    password = data.get('password') if data else None

    if not data or not email or not password:
        return jsonify({"success": False, "message": "Email and password are required"}), 400

    if email not in user_accounts:
        return jsonify({"success": False, "message": "Invalid email or password"}), 401

    if user_accounts[email]["password"] != password:
        return jsonify({"success": False, "message": "Invalid email or password"}), 401

    if email in user_submissions:
        submission = user_submissions[email]
        return jsonify({
            "success": True,
            "quiz_already_taken": True,
            "message": f"You have already completed '{QUIZ_DATA['title']}'. Here are your previous results.",
            "email": email,
            "user_id": email,
            "past_results": {
                "submission_id": submission["submission_id"],
                "quizTitle": QUIZ_DATA["title"],
                "score": submission["score"],
                "totalQuestions": submission["total_questions"],
                "percentage": submission["percentage"],
                "feedback": submission["feedback"],
                "detailed_results": submission["detailed_results"] # Pass detailed results for past quizzes too
            }
        }), 200
    else:
        return jsonify({"success": True, "message": "Login successful. You can start the quiz.", "email": email, "user_id": email}), 200

@app.route('/api/quiz', methods=['GET'])
def get_quiz():
    try:
        return jsonify({
            "success": True,
            "title": QUIZ_DATA["title"],
            "timeLimit": QUIZ_DATA["timeLimit"],
            "timePerQuestion": QUIZ_DATA["timePerQuestion"], # Pass time per question
            "questions": [
                {
                    "id": q["id"],
                    "question": q["question"],
                    "options": q["options"]
                } for q in QUIZ_DATA["questions"]
            ]
        })
    except Exception as e:
        print(f"Error fetching quiz data: {e}")
        return jsonify({"success": False, "message": "An error occurred while fetching the quiz."}), 500

@app.route('/api/submit', methods=['POST'])
def submit_quiz():
    data = request.get_json()
    user_email = data.get('email') if data else None
    user_answers_indices = data.get('answers', []) if data else []

    if not data or not user_email or not isinstance(user_answers_indices, list):
        return jsonify({"success": False, "message": "User email and answers list are required."}), 400

    try:
        if user_email not in user_accounts:
            return jsonify({"success": False, "message": "User not found."}), 401

        if user_email in user_submissions:
            return jsonify({"success": False, "message": "This quiz has already been submitted by you."}), 403

        score = 0
        total_questions = len(QUIZ_DATA["questions"])
        detailed_results_for_frontend = []

        for i, question in enumerate(QUIZ_DATA["questions"]):
            correct_answer_index = question["correct_answer"]
            user_selected_index = None
            user_selected_text = "Not Answered"
            is_correct_flag = False

            if i < len(user_answers_indices) and user_answers_indices[i] is not None:
                try:
                    user_selected_index = int(user_answers_indices[i])
                    if 0 <= user_selected_index < len(question["options"]):
                        user_selected_text = question["options"][user_selected_index]
                    else:
                        user_selected_index = None
                        user_selected_text = "Invalid Option Selected"
                except (ValueError, TypeError):
                    user_selected_index = None
                    user_selected_text = "Invalid Answer Format"

            if user_selected_index == correct_answer_index:
                score += 1
                is_correct_flag = True

            detailed_results_for_frontend.append({
                "id": question["id"],
                "question": question["question"],
                "your_answer": user_selected_text,
                "correct_answer": question["options"][correct_answer_index],
                "is_correct": is_correct_flag
            })

        percentage = (score / total_questions) * 100 if total_questions > 0 else 0
        feedback_name = user_email.split('@')[0]
        feedback_text = ""
        if percentage == 100: feedback_text = f"Perfect score, {feedback_name}! You're a whiz!"
        elif percentage >= 80: feedback_text = f"Excellent work, {feedback_name}!"
        elif percentage >= 60: feedback_text = f"Good job, {feedback_name}!"
        elif percentage >= 40: feedback_text = f"Not bad, {feedback_name}. Keep practicing!"
        else: feedback_text = f"Keep learning, {feedback_name}!"

        submission_id = f"sub_{user_email}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        user_submissions[user_email] = {
            "submission_id": submission_id,
            "score": score,
            "total_questions": total_questions,
            "percentage": percentage,
            "feedback": feedback_text,
            "submitted_at": datetime.now(timezone.utc),
            "detailed_results": detailed_results_for_frontend # Store detailed results
        }

        print(f"Quiz submitted by: {user_email}, Score: {score}/{total_questions}, Submission ID: {submission_id}")

        # --- Send Email Notification to Admin ---
        admin_email = os.getenv('ADMIN_EMAIL_RECIPIENT')
        if admin_email:
            try:
                quiz_title = QUIZ_DATA.get("title", "Quiz")
                subject = f"Quiz Submission: {user_email} on '{quiz_title}'"
                body = f"""
                A user has just completed a quiz.

                User Email: {user_email}
                Quiz Title: {quiz_title}
                Score: {score} out of {total_questions}
                Percentage: {percentage:.2f}%
                Feedback: {feedback_text}

                Submitted at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
                """
                msg = Message(
                    subject,
                    sender=app.config['MAIL_DEFAULT_SENDER'],
                    recipients=[admin_email],
                    body=body,
                    reply_to=user_email
                )
                mail.send(msg)
                print(f"Successfully sent submission email to admin from {user_email}: {admin_email}")
            except Exception as e:
                print(f"!!! FAILED to send submission email from {user_email} to admin: {e}")
        else:
            print("!!! ADMIN_EMAIL_RECIPIENT not set in .env. Skipping email notification.")

        return jsonify({
            "success": True, "email": user_email, "submission_id": submission_id,
            "score": score, "totalQuestions": total_questions, "percentage": percentage,
            "feedback": feedback_text, "detailed_results": detailed_results_for_frontend
        }), 200

    except Exception as e:
        print(f"Error during quiz submission: {e}")
        return jsonify({"success": False, "message": "An unexpected error occurred during submission."}), 500

@app.route('/api/user/submissions', methods=['GET'])
def get_user_submissions():
    user_email = request.args.get('email')
    if not user_email:
        return jsonify({"success": False, "message": "User email parameter is required."}), 400

    try:
        if user_email not in user_accounts:
            return jsonify({"success": False, "message": "User not found."}), 404

        submissions_list = []
        if user_email in user_submissions:
            submission = user_submissions[user_email]
            submissions_list.append({
                "submission_id": submission["submission_id"],
                "quiz_id": "default_quiz",
                "quiz_title": QUIZ_DATA["title"],
                "score": submission["score"],
                "total_questions_in_quiz": submission["total_questions"],
                "percentage": submission["percentage"],
                "submitted_at": submission["submitted_at"].isoformat()
            })

        return jsonify({"success": True, "submissions": submissions_list})
    except Exception as e:
        print(f"Error fetching user submissions: {e}")
        return jsonify({"success": False, "message": "An error occurred while fetching submissions."}), 500

@app.route('/api/submission/<submission_id_str>/details', methods=['GET'])
def get_submission_details(submission_id_str):
    try:
        user_email = None
        submission = None

        for email, sub in user_submissions.items():
            if sub["submission_id"] == submission_id_str:
                user_email = email
                submission = sub
                break

        if not submission:
            return jsonify({"success": False, "message": "Submission not found."}), 404

        summary_response = {
            "submission_id": submission["submission_id"],
            "quiz_id": "default_quiz",
            "quiz_title": QUIZ_DATA["title"],
            "score": submission["score"],
            "total_questions_in_quiz": submission["total_questions"],
            "percentage": submission["percentage"],
            "feedback_text": submission["feedback"],
            "submitted_at": submission["submitted_at"].isoformat(),
            "user_email": user_email
        }

        detailed_questions_list = []
        for result in submission["detailed_results"]:
            detailed_questions_list.append({
                "question_id": str(result["id"]),
                "question_text": result["question"],
                "user_selected_answer_text": result["your_answer"],
                "correct_answer_text": result["correct_answer"],
                "is_correct": result["is_correct"]
            })

        return jsonify({"success": True, "summary": summary_response, "details": detailed_questions_list})

    except Exception as e:
        print(f"Error fetching submission details for {submission_id_str}: {e}")
        return jsonify({"success": False, "message": "An error occurred while fetching submission details."}), 500

# --- End of Routes ---

if __name__ == '__main__':
    print("Starting Quizflow application with embedded data...")
    print(f"Quiz: {QUIZ_DATA['title']} ({len(QUIZ_DATA['questions'])} questions)")
    app.run(debug=True, port=5001)