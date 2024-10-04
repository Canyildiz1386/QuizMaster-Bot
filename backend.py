from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
client = MongoClient('mongodb://localhost:27017/')
db = client['quiz_db']

# Collections
users = db['users']
quizzes = db['quizzes']
user_attempts = db['user_attempts']

# Admin API: Manage Quizzes (Create, Edit, Delete, Get All Quizzes)
@app.route('/admin/quizzes', methods=['GET', 'POST', 'PUT', 'DELETE'])
def manage_quizzes():
    if request.method == 'GET':
        quizzes_list = list(quizzes.find({}, {'_id': 0}))
        return jsonify(quizzes_list), 200

    data = request.json
    quiz_id = data.get('quiz_id')

    if request.method == 'POST':
        quiz = {
            'quiz_id': quiz_id,
            'name': data['name'],
            'description': data['description'],
            'questions': data['questions'],  
            'reward_coins': data['reward_coins'],  
        }
        quizzes.insert_one(quiz)
        return jsonify({'status': 'success', 'message': 'Quiz created successfully'}), 201

    elif request.method == 'PUT':
        quizzes.update_one({'quiz_id': quiz_id}, {'$set': data})
        return jsonify({'status': 'success', 'message': 'Quiz updated successfully'}), 200

    elif request.method == 'DELETE':
        quizzes.delete_one({'quiz_id': quiz_id})
        return jsonify({'status': 'success', 'message': 'Quiz deleted successfully'}), 200

# Admin API: View Contest Statistics
@app.route('/admin/statistics', methods=['GET'])
def view_statistics():
    total_users = users.count_documents({})
    total_participation = user_attempts.count_documents({})
    total_correct_answers = sum([attempt['correct_answers'] for attempt in user_attempts.find()])
    winners = user_attempts.count_documents({'completed': True, 'correct_answers': {'$gte': 1}})

    return jsonify({
        'total_users': total_users,
        'total_participation': total_participation,
        'total_correct_answers': total_correct_answers,
        'winners': winners
    }), 200

# Admin API: Manage User Info
@app.route('/admin/users', methods=['GET'])
def view_users():
    country_filter = request.args.get('country')
    query = {}

    if country_filter == 'Iran':
        query['phone'] = {'$regex': '^98'}
    elif country_filter == 'Türkiye':
        query['phone'] = {'$regex': '^90'}

    users_list = list(users.find(query, {'_id': 0, 'user_id': 1, 'phone': 1, 'coins': 1}))
    return jsonify(users_list), 200

# User Registration and Referral System
@app.route('/start', methods=['POST'])
def start():
    data = request.json
    user_id = data['user_id']
    referral_id = data['referral_id']

    if not users.find_one({'user_id': user_id}):
        new_user = {
            'user_id': user_id,
            'coins': 0,
            'referral_id': referral_id,
            'registered_on': datetime.now(),
            'verified': False
        }
        users.insert_one(new_user)

        if referral_id:
            referrer = users.find_one({'user_id': referral_id})
            if referrer:
                users.update_one({'user_id': referral_id}, {'$inc': {'coins': 5}})
                users.update_one({'user_id': user_id}, {'$inc': {'coins': 5}})

    return jsonify({'status': 'success'}), 200

# Mobile Verification
@app.route('/register', methods=['POST'])
def register_user():
    data = request.json
    user_id = data['user_id']
    phone = data['phone']

    if phone.startswith('98') or phone.startswith('90'):
        users.update_one({'user_id': user_id}, {'$set': {'phone': phone, 'verified': True}}, upsert=True)
        return jsonify({'status': 'success', 'message': 'Phone number verified!'}), 200
    else:
        return jsonify({'status': 'fail', 'message': 'Invalid phone number'}), 400

# Get Quiz Questions
@app.route('/get_quiz/<int:user_id>', methods=['GET'])
def get_quiz(user_id):
    user = users.find_one({'user_id': user_id})
    
    if not user or not user.get('verified', False):
        return jsonify({'error': 'User not verified'}), 400

    available_quiz = None
    for quiz in quizzes.find():
        quiz_id = quiz['quiz_id']
        attempt = user_attempts.find_one({'user_id': user_id, 'quiz_id': quiz_id})

        if not attempt or not attempt.get('completed', False):
            available_quiz = quiz
            break

    if not available_quiz:
        return jsonify({'message': 'You have completed all available quizzes!'}), 200

    current_question_index = 0
    if attempt:
        current_question_index = attempt.get('current_question', 0)
    else:
        user_attempts.insert_one({
            'user_id': user_id,
            'quiz_id': available_quiz['quiz_id'],
            'current_question': 0,
            'correct_answers': 0,
            'completed': False
        })

    question_data = available_quiz['questions'][current_question_index]

    return jsonify({
        'quiz_id': available_quiz['quiz_id'],
        'name': available_quiz['name'],
        'description': available_quiz['description'],
        'question': question_data['question'],
        'options': question_data['options'],
        'current_question': current_question_index,
        'quiz_completed': False
    }), 200

# Submit Quiz Answer
@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    data = request.json
    user_id = data['user_id']
    quiz_id = int(data['quiz_id'])
    question_number = int(data['question_number'])
    answer = int(data['answer'])
    quiz = quizzes.find_one({'quiz_id': quiz_id})

    if not quiz:
        return jsonify({'status': 'fail', 'message': 'Quiz not found'}), 404

    correct = quiz['questions'][question_number]['correct_option'] == answer
    reward_coins = quiz['questions'][question_number]['reward'] if correct else 0

    attempt = user_attempts.find_one({'user_id': user_id, 'quiz_id': quiz_id})

    if not attempt:
        attempt = {'user_id': user_id, 'quiz_id': quiz_id, 'current_question': 0, 'correct_answers': 0, 'completed': False}

    attempt['current_question'] += 1
    if correct:
        attempt['correct_answers'] += 1

    if attempt['current_question'] >= len(quiz['questions']):
        attempt['completed'] = True

    user_attempts.update_one({'user_id': user_id, 'quiz_id': quiz_id}, {'$set': attempt}, upsert=True)

    if correct:
        users.update_one({'user_id': user_id}, {'$inc': {'coins': reward_coins}})

    return jsonify({'status': 'success', 'correct': correct, 'reward_coins': reward_coins, 'quiz_completed': attempt['completed']}), 200

# View Leaderboard
@app.route('/leaderboard', methods=['GET'])
def leaderboard():
    leaderboard_data = []
    for user in users.find():
        correct_answers = user_attempts.count_documents({'user_id': user['user_id'], 'correct': True})
        leaderboard_data.append({
            'user_id': user['user_id'],
            'phone': user.get('phone', ''),
            'correct_answers': correct_answers,
            'coins': user['coins']
        })
    leaderboard_data.sort(key=lambda x: x['correct_answers'], reverse=True)
    return jsonify(leaderboard_data), 200

if __name__ == '__main__':
    app.run(debug=True)
