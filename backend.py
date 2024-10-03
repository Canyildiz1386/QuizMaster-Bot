from flask import Flask, render_template, request, redirect
import pymongo

app = Flask(__name__)

client = pymongo.MongoClient('mongodb://localhost:27017/')
db = client['quiz_bot']
users_collection = db['users']
quizzes_collection = db['quizzes']

@app.route('/')
def dashboard():
    users = users_collection.count_documents({})
    quizzes = quizzes_collection.count_documents({})
    return render_template('dashboard.html', users=users, quizzes=quizzes)

@app.route('/quizzes', methods=['GET', 'POST'])
def manage_quizzes():
    if request.method == 'POST':
        quiz_name = request.form['name']
        description = request.form['description']
        questions = []
        for i in range(len(request.form.getlist('question'))):
            question_text = request.form.getlist('question')[i]
            options = request.form.getlist(f'options_{i}')
            correct_answer = request.form.getlist(f'correct_answer')[i]
            questions.append({
                'text': question_text,
                'options': options,
                'correct_answer': correct_answer
            })
        quizzes_collection.insert_one({
            'name': quiz_name,
            'description': description,
            'questions': questions
        })
        return redirect('/quizzes')

    quizzes = quizzes_collection.find()
    return render_template('manage_quizzes.html', quizzes=quizzes)

@app.route('/users')
def manage_users():
    users = users_collection.find()
    return render_template('manage_users.html', users=users)

if __name__ == '__main__':
    app.run(debug=True)
