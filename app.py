from flask import Flask, jsonify, request
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, timezone
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



client = MongoClient('mongodb://localhost:27017/')
db = client.quiz_db
users_collection = db.users
quizzes_collection = db.quizzes

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def is_valid_objectid(id):
    return ObjectId.is_valid(id)

def quiz_serializer(quiz):
    quiz['_id'] = str(quiz['_id'])
    return quiz

@app.route('/api/user/<telegram_id>/details', methods=['GET'])
def get_user_details(telegram_id):
    user = users_collection.find_one({"telegram_id": telegram_id})
    if not user:
        return jsonify({"error": "User not found"}), 404

    referral_count = users_collection.count_documents({"referred_by": telegram_id})  # Count of referred users
    
    return jsonify({
        "telegram_id": user['telegram_id'],
        "phone_number": user['phone_number'],
        "country": user['country'],
        "coins": user['coins'],
        "referral_count": referral_count,  # Add referral count to the response
        "referred_users": list(users_collection.find({"referred_by": telegram_id}, {"telegram_id": 1, "coins": 1}))  # List of referred users and their coins
    }), 200


@app.route('/api/all_quizzes', methods=['GET'])
def get_all_quizzes():
    quizzes = list(quizzes_collection.find())
    quizzes_with_stats = []
    
    for quiz in quizzes:
        quiz_id = str(quiz['_id'])
        
        registered_users = users_collection.count_documents({"answered_quizzes": quiz_id})
        
        winners = users_collection.count_documents({"answered_quizzes": quiz_id})
        
        total_coins_paid = users_collection.aggregate([
            {"$match": {"answered_quizzes": quiz_id}},
            {"$group": {"_id": None, "total_coins": {"$sum": "$coins"}}}
        ])
        
        total_coins = next(total_coins_paid, {}).get("total_coins", 0)
        
        quiz_stats = {
            "title": quiz.get("title"),
            "questions": quiz.get("questions"),
            "registered_users": registered_users,
            "winners": winners,
            "total_coins_paid": total_coins,
            "id" : quiz_id
        }
        
        quizzes_with_stats.append(quiz_stats)

    return jsonify(quizzes_with_stats), 200

def user_serializer(user):
    user['_id'] = str(user['_id'])  
    return user

@app.route('/api/all_users', methods=['GET'])
def get_all_users():
    users = list(users_collection.find())
    
    for user in users:
        user['_id'] = str(user['_id'])  # Convert ObjectId to string
        user['id'] = user['_id']
        user['referral_count'] = users_collection.count_documents({"referred_by": user['telegram_id']})  # Add referral count
    
    return jsonify(users), 200

@app.route('/api/statistics/overall', methods=['GET'])
def get_overall_statistics():
    # 1. Total Coins Paid: Sum of coins paid to users in all completed quizzes
    total_coins_paid = users_collection.aggregate([
        {"$group": {"_id": None, "total_paid": {"$sum": "$coins"}}}
    ])
    total_coins_paid = next(total_coins_paid, {}).get("total_paid", 0)
    
    # 2. Total Coins Held by Users: Sum of all users' coins
    total_coins_held = users_collection.aggregate([
        {"$group": {"_id": None, "total_held": {"$sum": "$coins"}}}
    ])
    total_coins_held = next(total_coins_held, {}).get("total_held", 0)
    
    # 3. Total Winners: Count of users with completed quizzes (users who completed at least one quiz)
    total_winners = users_collection.count_documents({"answered_quizzes": {"$exists": True, "$not": {"$size": 0}}})
    
    # 4. Total Participants: Count of users who have participated in any quiz
    total_participants = users_collection.count_documents({"answered_quizzes": {"$exists": True, "$not": {"$size": 0}}})

    response = {
        "total_coins_paid": total_coins_paid,  # Total coins paid
        "total_coins_held": total_coins_held,  # Total coins held by users
        "total_winners": total_winners,  # Total winners (who completed at least one quiz)
        "total_participants": total_participants  # Total number of participants
    }
    
    return jsonify(response), 200

@app.route('/api/user/<user_id>', methods=['GET'])
def get_user_by_id(user_id):
    # Validate the user_id (check if it's a valid ObjectId)
    if not ObjectId.is_valid(user_id):
        return jsonify({"error": "Invalid user ID"}), 400
    
    # Find the user by user_id in the MongoDB collection
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Serialize user data for JSON response
    user_data = {
        "_id": str(user["_id"]),
        "telegram_id": user.get("telegram_id"),
        "phone_number": user.get("phone_number"),
        "country": user.get("country"),
        "coins": user.get("coins"),
        "referral_count": users_collection.count_documents({"referred_by": user.get("telegram_id")}),
        "referred_users": list(users_collection.find({"referred_by": user.get("telegram_id")}, {"telegram_id": 1, "coins": 1}))
    }
    
    return jsonify(user_data), 200


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
    
    if not ('98' in phone_number or '90' in phone_number):
        return jsonify({"error": "Only phone numbers from Iran and Turkey are allowed"}), 403
    
    user = users_collection.find_one({"telegram_id": data['telegram_id']})
    if user:
        return jsonify({"message": "User already registered"}), 200

    country = 'Iran' if '98' in phone_number else 'Türkiye'
    
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
        "quizzes_today": {},
        "referred_by": data.get('referred_by')
    }
    
    users_collection.insert_one(new_user)

    if data.get('referred_by'):
        referrer = users_collection.find_one({"telegram_id": data['referred_by']})
        
        if referrer:
            users_collection.update_one({"telegram_id": data['referred_by']}, {"$inc": {"coins": 100}})
            users_collection.update_one({"telegram_id": data['telegram_id']}, {"$inc": {"coins": 100}})

    return jsonify({"message": "User registered successfully"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # Example authentication (you would use your database to validate users)
    user = users_collection.find_one({"username": username})
    print(username)
    if username == "admin" and password == "admin":  # You should hash and securely check the password
        return jsonify({"success": True, "user": {"username": "admin", "role": "admin"}}), 200
    else:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401


@app.route('/api/upload_image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"success": False, "message": "No image file provided."}), 400
    
    image = request.files['image']
    
    if image.filename == '':
        return jsonify({"success": False, "message": "No image selected."}), 400
    
    filename = secure_filename(image.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    try:
        image.save(file_path)
        
        img = Image.open(file_path)
        img = img.resize((300, 300)) 
        img.save(file_path)

        image_url = f"static/uploads/{filename}"
        return jsonify({"success": True, "image_url": image_url}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/quiz', methods=['POST'])
def create_quiz():
    data = request.json
    title = data.get('title')
    questions = data.get('questions')
    image = data.get('image')  
    

    if not title or not questions:
        return jsonify({"error": "Title and questions are required"}), 400

    quiz = {
        "title": title,
        "questions": questions,
        "image": image, 
        "created_at": datetime.now(timezone.utc)
    }
    print(quiz)
    quizzes_collection.insert_one(quiz)
    return jsonify({"message": "Quiz created successfully", "quiz": quiz_serializer(quiz)}), 201



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
        "answered_quizzes": user['answered_quizzes'],
        "language" : user['language'],
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

@app.route('/api/user/<telegram_id>/language', methods=['POST'])
def update_user_language(telegram_id):
    data = request.json
    if 'language' not in data:
        return jsonify({"error": "Language is required"}), 400

    language = data['language']

    user = users_collection.find_one({"telegram_id": telegram_id})
    if not user:
        return jsonify({"error": "User not found"}), 404

    users_collection.update_one({"telegram_id": telegram_id}, {"$set": {"language": language}})
    return jsonify({"message": "Language updated successfully"}), 200


if __name__ == '__main__':
    app.run(debug=True,port=8080,host="0.0.0.0")
