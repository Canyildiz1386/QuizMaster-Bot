from flask import Flask, jsonify, request
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, timezone
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


client = MongoClient('mongodb://localhost:27017/')
db = client.quizdb
users_collection = db.users
quizzes_collection = db.quizzes

def is_valid_objectid(id):
    return ObjectId.is_valid(id)

def quiz_serializer(quiz):
    quiz['_id'] = str(quiz['_id'])
    return quiz


@app.route('/api/all_quizzes', methods=['GET'])
def get_all_quizzes():
    quizzes = list(quizzes_collection.find())
    quizzes = [quiz_serializer(quiz) for quiz in quizzes]
    return jsonify(quizzes), 200

def user_serializer(user):
    user['_id'] = str(user['_id'])  
    return user

@app.route('/api/all_users', methods=['GET'])
def get_all_users():
    users = list(users_collection.find())  
    serialized_users = [user_serializer(user) for user in users]  
    return jsonify(serialized_users), 200 


@app.route('/api/user/<user_id>', methods=['PUT'])
def update_user(user_id):
    if not is_valid_objectid(user_id):
        return jsonify({"error": "Invalid user ID"}), 400
    data = request.json
    users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": {
        "telegram_id": data['telegram_id'],
        "phone_number": data['phone_number']
    }})
    return jsonify({"message": "User updated successfully"}), 200


@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.json
    if not data.get('telegram_id') or not data.get('phone_number'):
        return jsonify({"error": "Telegram ID and Phone number are required"}), 400
    
    phone_number = data['phone_number']
    
    if not (phone_number.startswith('98') or phone_number.startswith('90')):
        return jsonify({"error": "Only phone numbers from Iran and Turkey are allowed"}), 403
    
    user = users_collection.find_one({"telegram_id": data['telegram_id']})
    if user:
        return jsonify({"message": "User already registered"}), 200

    country = 'Iran' if phone_number.startswith('98') else 'Türkiye'
    
    new_user = {
        "telegram_id": data['telegram_id'],
        "phone_number": phone_number,
        "country": country,
        "coins": 0,
        "score": 0,
        "current_question": 0,
        "current_quiz": None,
        "answered_quizzes": [],
        "registered_at": datetime.now(timezone.utc),
        "quizzes_today": {}
    }
    users_collection.insert_one(new_user)
    return jsonify({"message": "User registered successfully"}), 201

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

@app.route('/api/quiz/<quiz_id>', methods=['DELETE'])
def delete_quiz(quiz_id):
    if not is_valid_objectid(quiz_id):
        return jsonify({"error": "Invalid Quiz ID"}), 400
    quizzes_collection.delete_one({"_id": ObjectId(quiz_id)})
    return jsonify({"message": "Quiz deleted successfully"}), 200


@app.route('/api/user/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    if not ObjectId.is_valid(user_id):
        return jsonify({"error": "Invalid user ID"}), 400
    result = users_collection.delete_one({"_id": ObjectId(user_id)})
    
    if result.deleted_count == 0:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"message": "User deleted successfully"}), 200


@app.route('/api/quiz/<quiz_id>', methods=['PUT'])
def update_quiz(quiz_id):
    if not is_valid_objectid(quiz_id):
        return jsonify({"error": "Invalid quiz ID"}), 400
    data = request.json
    quizzes_collection.update_one({"_id": ObjectId(quiz_id)}, {"$set": {
        "title": data['title'],
        "questions": data['questions']
    }})
    return jsonify({"message": "Quiz updated successfully"}), 200


@app.route('/api/statistics/quizzes', methods=['GET'])
def get_quiz_statistics():
    total_quizzes = quizzes_collection.count_documents({})
    avg_questions_per_quiz = quizzes_collection.aggregate([
        {"$project": {"num_questions": {"$size": "$questions"}}},
        {"$group": {"_id": None, "avg_questions": {"$avg": "$num_questions"}}}
    ])
    popular_quiz = users_collection.aggregate([
        {"$unwind": "$answered_quizzes"},
        {"$group": {"_id": "$answered_quizzes", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 1}
    ])
    popular_quiz_info = next(popular_quiz, None)

    response = {
        "total_quizzes": total_quizzes,
        "avg_questions_per_quiz": list(avg_questions_per_quiz)[0]["avg_questions"] if avg_questions_per_quiz else 0,
        "most_popular_quiz_id": popular_quiz_info['_id'] if popular_quiz_info else None,
        "times_taken": popular_quiz_info['count'] if popular_quiz_info else 0
    }

    return jsonify(response), 200

@app.route('/api/statistics/users', methods=['GET'])
def get_user_statistics():
    total_users = users_collection.count_documents({})
    users_by_country = users_collection.aggregate([
        {"$group": {"_id": "$country", "count": {"$sum": 1}}}
    ])
    total_coins = users_collection.aggregate([{"$group": {"_id": None, "total_coins": {"$sum": "$coins"}}}])

    response = {
        "total_users": total_users,
        "users_by_country": list(users_by_country),
        "total_coins": list(total_coins)[0]["total_coins"] if total_coins else 0
    }

    return jsonify(response), 200


@app.route('/api/user/<telegram_id>/progress', methods=['PUT'])
def update_user_progress(telegram_id):
    data = request.json
    if not data.get('current_quiz') or data.get('current_question') is None:
        return jsonify({"error": "Current quiz and question are required"}), 400
    user = users_collection.find_one({"telegram_id": telegram_id})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    quizzes_today = user.get('quizzes_today', {}).get(today, 0)
    if quizzes_today >= 3:
        return jsonify({"error": "Daily quiz limit reached"}), 403
    users_collection.update_one({"telegram_id": telegram_id}, {
        "$set": {
            "current_quiz": data['current_quiz'],
            "current_question": data['current_question']
        },
        "$inc": {
            f"quizzes_today.{today}": 1
        }
    })
    return jsonify({"message": "User progress updated"}), 200

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
    new_coins = user['coins'] + data['coins']
    users_collection.update_one({"telegram_id": telegram_id}, {"$set": {"coins": new_coins}})
    return jsonify({"message": "Coins updated", "new_coins": new_coins}), 200

@app.route('/api/user/<telegram_id>/referral', methods=['POST'])
def referral(telegram_id):
    referred_id = request.json.get('referred_id')
    referred_user = users_collection.find_one({"telegram_id": referred_id})
    if referred_user and "referred_by" not in referred_user:
        users_collection.update_one({"telegram_id": referred_id}, {
            "$set": {"referred_by": telegram_id}
        })
        users_collection.update_one({"telegram_id": telegram_id}, {
            "$inc": {"coins": 10}
        })
        return jsonify({"message": "Referral successful"}), 200
    return jsonify({"error": "User already referred or does not exist"}), 400

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    users = list(users_collection.find().sort("coins", -1).limit(10))
    leaderboard = [{"telegram_id": user['telegram_id'], "coins": user['coins']} for user in users]
    return jsonify(leaderboard), 200

@app.route('/api/user/<telegram_id>/start_quiz', methods=['POST'])
def start_quiz(telegram_id):
    quiz_id = request.json.get('quiz_id')
    start_time = datetime.now(timezone.utc)
    users_collection.update_one({"telegram_id": telegram_id}, {
        "$set": {"quiz_start_time": start_time, "current_quiz": quiz_id}
    })
    return jsonify({"message": "Quiz started"}), 200

@app.route('/api/user/<telegram_id>/finish_quiz', methods=['POST'])
def finish_quiz_with_time(telegram_id):
    quiz_id = request.json.get('quiz_id')
    user = users_collection.find_one({"telegram_id": telegram_id})
    start_time = user.get("quiz_start_time")
    if not start_time:
        return jsonify({"error": "Quiz was not started"}), 400
    end_time = datetime.now(timezone.utc)
    time_taken = (end_time - start_time).total_seconds()
    if time_taken > 300:
        return jsonify({"message": "Time limit exceeded"}), 400
    users_collection.update_one({"telegram_id": telegram_id}, {
        "$set": {"quiz_start_time": None, "current_quiz": None}
    })
    return jsonify({"message": "Quiz finished successfully", "time_taken": time_taken}), 200

@app.route('/api/quiz/<quiz_id>', methods=['GET', 'PUT', 'DELETE'])
def get_quiz(quiz_id):
    if not is_valid_objectid(quiz_id):
        return jsonify({"error": "Invalid Quiz ID"}), 400
    quiz = quizzes_collection.find_one({"_id": ObjectId(quiz_id)})
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404
    quiz = quiz_serializer(quiz)
    return jsonify(quiz), 200

if __name__ == '__main__':
    app.run(debug=True)
