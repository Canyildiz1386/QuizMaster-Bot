import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

API_BASE_URL = "http://127.0.0.1:5000/api"

async def start(update: Update, context):
    contact_button = InlineKeyboardButton(text="📱 Share Contact", callback_data="share_contact")
    await update.message.reply_text("👋 Welcome! Please share your contact to register.")

async def handle_contact(update: Update, context):
    contact = update.message.contact
    telegram_id = str(update.message.from_user.id)
    phone_number = contact.phone_number
    response = requests.post(f"{API_BASE_URL}/register", json={
        "telegram_id": telegram_id,
        "phone_number": phone_number
    })
    await update.message.reply_text(response.json().get("message"))

async def quiz(update: Update, context):
    telegram_id = str(update.message.from_user.id)
    response = requests.get(f"{API_BASE_URL}/quizzes", params={"telegram_id": telegram_id})
    quizzes = response.json()
    
    if "error" in quizzes:
        await update.message.reply_text("❌ Please register first by sharing your contact.")
        return

    if not quizzes:
        await update.message.reply_text("🎉 You have answered all available quizzes!")
        return

    buttons = [[InlineKeyboardButton(quiz['title'], callback_data=f"select_quiz_{quiz['_id']}")] for quiz in quizzes]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("📚 Please select a quiz:", reply_markup=reply_markup)

async def select_quiz(update: Update, context):
    query = update.callback_query
    quiz_id = query.data.split("_")[-1]
    telegram_id = str(query.from_user.id)

    response = requests.get(f"{API_BASE_URL}/quiz/{quiz_id}")
    quiz = response.json()

    user_response = requests.get(f"{API_BASE_URL}/user/{telegram_id}/progress")
    user_data = user_response.json()

    if user_data['current_quiz'] != quiz_id:
        requests.put(f"{API_BASE_URL}/user/{telegram_id}/progress", json={
            "current_quiz": quiz_id,
            "current_question": 0
        })
        current_question = 0
    else:
        current_question = user_data.get('current_question', 0)

    if current_question >= len(quiz['questions']):
        await query.edit_message_text("🎉 You have finished this quiz!")
        return

    question = quiz['questions'][current_question]
    options = question['options']
    buttons = [[InlineKeyboardButton(option, callback_data=option) for option in options]]
    reply_markup = InlineKeyboardMarkup(buttons)

    await query.message.reply_text(f"📝 Question: {question['question']} 🤔", reply_markup=reply_markup)

async def handle_answer(update: Update, context):
    query = update.callback_query
    await query.answer()

    telegram_id = str(query.from_user.id)
    user_response = requests.get(f"{API_BASE_URL}/user/{telegram_id}/progress")
    user_data = user_response.json()
    quiz_id = user_data['current_quiz']

    quiz_response = requests.get(f"{API_BASE_URL}/quiz/{quiz_id}")
    quiz = quiz_response.json()

    current_question = user_data['current_question']

    if current_question >= len(quiz['questions']):
        await query.edit_message_text("🎉 You have finished the quiz!")
        return

    question = quiz['questions'][current_question]
    correct_option = question['correct_option']
    user_answer = query.data

    if user_answer == correct_option:
        await query.edit_message_text(f"🎉 Correct!")
        requests.put(f"{API_BASE_URL}/user/{telegram_id}/coins", json={"coins": question['reward']})
    else:
        await query.edit_message_text(f"❌ Wrong! The correct answer was: {correct_option}")

    new_question_number = current_question + 1

    if new_question_number < len(quiz['questions']):
        requests.put(f"{API_BASE_URL}/user/{telegram_id}/progress", json={
            "current_quiz": quiz_id,
            "current_question": new_question_number
        })

        next_question = quiz['questions'][new_question_number]
        options = next_question['options']
        buttons = [[InlineKeyboardButton(option, callback_data=option) for option in options]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.reply_text(f"📝 Next Question: {next_question['question']} 🤔", reply_markup=reply_markup)

    else:
        requests.put(f"{API_BASE_URL}/user/{telegram_id}/finish_quiz", json={
            "quiz_id": quiz_id
        })
        await query.message.reply_text("🎉 You have finished the quiz!")

if __name__ == '__main__':
    app = ApplicationBuilder().token('7476580536:AAFhZS6bM63fWJcSyPn0KfFNpWT5Jh5t4vE').build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(select_quiz, pattern="^select_quiz_"))
    app.add_handler(CallbackQueryHandler(handle_answer, pattern="^[^select_quiz_]"))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(CommandHandler("quiz", quiz))

    app.run_polling()
