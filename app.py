from flask import Flask, jsonify, request
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, timezone

app = Flask(__name__)

client = MongoClient('mongodb://localhost:27017/')
db = client.quizdb
users_collection = db.users
quizzes_collection = db.quizzes

def is_valid_objectid(id):
    return ObjectId.is_valid(id)

def quiz_serializer(quiz):
    quiz['_id'] = str(quiz['_id'])
    return quiz

@app.route('/api/quiz', methods=['POST'])
def create_quiz():
    data = request.json
    if not data.get('title') or not data.get('questions'):
        return jsonify({"error": "Title and questions are required"}), 400
    quiz = {
        "title": data['title'],
        "questions": data['questions'],
        "created_at": datetime.now(timezone.utc)
    }
    quizzes_collection.insert_one(quiz)
    return jsonify({"message": "Quiz created successfully"}), 201

@app.route('/api/quizzes', methods=['GET'])
def get_quizzes():
    telegram_id = request.args.get('telegram_id')
    user = users_collection.find_one({"telegram_id": telegram_id})
    
    if not user:
        return jsonify({"error": "User not found"}), 404

    answered_quizzes = user.get('answered_quizzes', [])
    available_quizzes = list(quizzes_collection.find({"_id": {"$nin": [ObjectId(qid) for qid in answered_quizzes]}}))
    available_quizzes = [quiz_serializer(quiz) for quiz in available_quizzes]
    
    return jsonify(available_quizzes), 200

@app.route('/api/quiz/<quiz_id>', methods=['GET'])
def get_quiz(quiz_id):
    if not is_valid_objectid(quiz_id):
        return jsonify({"error": "Invalid Quiz ID"}), 400
    quiz = quizzes_collection.find_one({"_id": ObjectId(quiz_id)})
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404
    quiz = quiz_serializer(quiz)
    return jsonify(quiz), 200

@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.json
    if not data.get('telegram_id') or not data.get('phone_number'):
        return jsonify({"error": "Telegram ID and Phone number are required"}), 400
    user = users_collection.find_one({"telegram_id": data['telegram_id']})
    if user:
        return jsonify({"message": "User already registered"}), 200
    country = 'Iran' if data['phone_number'].startswith('98') else 'Türkiye' if data['phone_number'].startswith('90') else 'Other'
    new_user = {
        "telegram_id": data['telegram_id'],
        "phone_number": data['phone_number'],
        "country": country,
        "coins": 0,
        "score": 0,
        "current_question": 0,
        "current_quiz": None,
        "answered_quizzes": [],
        "registered_at": datetime.now(timezone.utc)
    }
    users_collection.insert_one(new_user)
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/api/user/<telegram_id>/progress', methods=['GET'])
def get_user_progress(telegram_id):
    user = users_collection.find_one({"telegram_id": telegram_id})
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({
        "telegram_id": user['telegram_id'],
        "current_quiz": user['current_quiz'],
        "current_question": user['current_question'],
        "coins": user['coins'],
        "answered_quizzes": user['answered_quizzes']
    }), 200

@app.route('/api/user/<telegram_id>/progress', methods=['PUT'])
def update_user_progress(telegram_id):
    data = request.json
    if not data.get('current_quiz') or data.get('current_question') is None:
        return jsonify({"error": "Current quiz and question are required"}), 400
    user = users_collection.find_one({"telegram_id": telegram_id})
    if not user:
        return jsonify({"error": "User not found"}), 404
    users_collection.update_one({"telegram_id": telegram_id}, {
        "$set": {
            "current_quiz": data['current_quiz'],
            "current_question": data['current_question']
        }
    })
    return jsonify({"message": "User progress updated"}), 200

@app.route('/api/user/<telegram_id>/finish_quiz', methods=['PUT'])
def finish_quiz(telegram_id):
    data = request.json
    if not data.get('quiz_id'):
        return jsonify({"error": "Quiz ID is required"}), 400
    user = users_collection.find_one({"telegram_id": telegram_id})
    if not user:
        return jsonify({"error": "User not found"}), 404
    quiz_id = data['quiz_id']
    if quiz_id in user['answered_quizzes']:
        return jsonify({"message": "Quiz already completed"}), 200
    users_collection.update_one({"telegram_id": telegram_id}, {
        "$addToSet": {"answered_quizzes": quiz_id},
        "$set": {"current_quiz": None, "current_question": 0}
    })
    return jsonify({"message": "Quiz marked as completed"}), 200

@app.route('/api/user/<telegram_id>/coins', methods=['PUT'])
def add_coins(telegram_id):
    data = request.json
    if 'coins' not in data:
        return jsonify({"error": "Coins are required"}), 400
    user = users_collection.find_one({"telegram_id": telegram_id})
    if not user:
        return jsonify({"error": "User not found"}), 404
    new_coins = user['coins'] + data['coins']
    users_collection.update_one({"telegram_id": telegram_id}, {"$set": {"coins": new_coins}})
    return jsonify({"message": "Coins updated", "new_coins": new_coins}), 200

if __name__ == '__main__':
    app.run(debug=True)
