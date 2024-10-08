import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

API_BASE_URL = "http://127.0.0.1:5000/api"

async def start(update: Update, context):
    telegram_id = str(update.message.from_user.id)
    response = requests.get(f"{API_BASE_URL}/user/{telegram_id}/progress")
    
    if response.status_code == 404:
        if context.args:
            referer_id = context.args[0]
            requests.post(f"{API_BASE_URL}/user/{telegram_id}/referral", json={"referred_id": referer_id})
        
        contact_button = KeyboardButton("📱 Share Contact", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True)
        await update.message.reply_text("👋 Welcome! Please share your contact to register 📱", reply_markup=reply_markup)
    else:
        keyboard = [
            [KeyboardButton("📝 Start Quiz"), KeyboardButton("🏆 Leaderboard")],
            [KeyboardButton("ℹ️ Help"), KeyboardButton("👤 Account Info")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("👋 Welcome back! Choose an option:", reply_markup=reply_markup)

async def handle_contact(update: Update, context):
    contact = update.message.contact
    telegram_id = str(update.message.from_user.id)
    phone_number = contact.phone_number
    response = requests.post(f"{API_BASE_URL}/register", json={
        "telegram_id": telegram_id,
        "phone_number": phone_number
    })
    if response.status_code in [200, 201]:
        await update.message.reply_text(f"✅ {response.json().get('message')}")
        keyboard = [
            [KeyboardButton("📝 Start Quiz"), KeyboardButton("🏆 Leaderboard")],
            [KeyboardButton("ℹ️ Help"), KeyboardButton("👤 Account Info")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Please choose an option:", reply_markup=reply_markup)
    else:
        await update.message.reply_text(f"❌ Server error: {response.status_code} 😢")

async def help_command(update: Update, context):
    help_text = (
        "ℹ️ *Help Menu* ℹ️\n"
        "Here are some commands you can use:\n\n"
        "✅ Start Quiz by clicking on 📝 Start Quiz\n"
        "🏆 View the leaderboard by clicking on 🏆 Leaderboard\n"
        "📊 Check your account details with 👤 Account Info\n"
        "ℹ️ Get help with ℹ️ Help\n"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def quiz(update: Update, context):
    telegram_id = str(update.message.from_user.id)
    response = requests.get(f"{API_BASE_URL}/quizzes", params={"telegram_id": telegram_id})
    if response.status_code == 403:
        await update.message.reply_text("🚫 You have reached the daily quiz limit 🕒.")
        return
    quizzes = response.json()
    if "error" in quizzes:
        await update.message.reply_text("❌ Please register first by sharing your contact 📱.")
        return
    if not quizzes:
        await update.message.reply_text("🎉 You have answered all available quizzes! 🏆")
        return
    buttons = [[InlineKeyboardButton(quiz['title'], callback_data=f"select_quiz_{quiz['_id']}")] for quiz in quizzes]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("📚 Please select a quiz 🧠:", reply_markup=reply_markup)

async def select_quiz(update: Update, context):
    query = update.callback_query
    quiz_id = query.data.split("_")[-1]
    telegram_id = str(query.from_user.id)
    start_response = requests.post(f"{API_BASE_URL}/user/{telegram_id}/start_quiz", json={"quiz_id": quiz_id})
    if start_response.status_code == 200:
        await query.message.reply_text("⏳ Your quiz has started! You have 5 minutes to complete it 🕒.")
    else:
        await query.message.reply_text("❌ Error starting quiz. Please try again 😔.")
        return
    response = requests.get(f"{API_BASE_URL}/quiz/{quiz_id}")
    if response.status_code != 200:
        await query.message.reply_text(f"❌ Error fetching quiz data (status code {response.status_code}) 😢.")
        return
    try:
        quiz = response.json()
    except requests.exceptions.JSONDecodeError:
        await query.message.reply_text("❌ Error: Invalid response format (expected JSON) ⚠️.")
        return
    quiz_questions = quiz['questions']['questions']
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
    if not quiz_questions:
        await query.message.reply_text("❌ No questions available in this quiz 📋.")
        return
    if current_question >= len(quiz_questions):
        await query.edit_message_text("🎉 You have finished this quiz! 🏅")
        return
    question = quiz_questions[current_question]
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
    try:
        quiz = quiz_response.json()
    except requests.exceptions.JSONDecodeError:
        await query.message.reply_text("❌ Error: Invalid response format ⚠️.")
        return
    quiz_questions = quiz['questions']['questions']
    current_question = user_data['current_question']
    if current_question >= len(quiz_questions):
        await query.edit_message_text("🎉 You have finished the quiz! 🏅")
        return
    question = quiz_questions[current_question]
    correct_option = question['correct_option']
    user_answer = query.data
    if user_answer == correct_option:
        await query.edit_message_text(f"🎉 Correct! 🏆")
        requests.put(f"{API_BASE_URL}/user/{telegram_id}/coins", json={"coins": question['reward']})
    else:
        await query.edit_message_text(f"❌ Wrong! The correct answer was: {correct_option} ❓")
    new_question_number = current_question + 1
    if new_question_number < len(quiz_questions):
        requests.put(f"{API_BASE_URL}/user/{telegram_id}/progress", json={
            "current_quiz": quiz_id,
            "current_question": new_question_number
        })
        next_question = quiz_questions[new_question_number]
        options = next_question['options']
        buttons = [[InlineKeyboardButton(option, callback_data=option) for option in options]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.reply_text(f"📝 Next Question: {next_question['question']} 🤔", reply_markup=reply_markup)
    else:
        requests.put(f"{API_BASE_URL}/user/{telegram_id}/finish_quiz", json={"quiz_id": quiz_id})
        await query.message.reply_text("🎉 You have finished the quiz! 🏆")

async def leaderboard(update: Update, context):
    response = requests.get(f"{API_BASE_URL}/leaderboard")
    leaderboard = response.json()
    leaderboard_text = "🏆 Top 10 Users:\n\n"
    for rank, user in enumerate(leaderboard, 1):
        leaderboard_text += f"{rank}. {user['telegram_id']} - {user['coins']} coins 🪙\n"
    await update.message.reply_text(leaderboard_text)

async def account(update: Update, context):
    telegram_id = str(update.message.from_user.id)
    response = requests.get(f"{API_BASE_URL}/user/{telegram_id}/progress")
    if response.status_code == 404:
        await update.message.reply_text("❌ You're not registered yet! Please /start to register 📱.")
    else:
        user_data = response.json()
        current_quiz_id = user_data['current_quiz']
        if current_quiz_id:
            quiz_response = requests.get(f"{API_BASE_URL}/quiz/{current_quiz_id}")
            quiz_title = quiz_response.json().get('title', 'Unknown Quiz')
        else:
            quiz_title = "None"
        
        account_info = (
            f"👤 *Your Account Information* 👤\n\n"
            f"🆔 Telegram ID: {user_data['telegram_id']}\n"
            f"🧠 Current Quiz: {quiz_title}\n"
            f"📊 Current Question: {user_data['current_question']}\n"
            f"🪙 Coins: {user_data['coins']}\n"
            f"🎯 Answered Quizzes: {len(user_data['answered_quizzes'])}\n"
        )
        await update.message.reply_text(account_info, parse_mode='Markdown')

if __name__ == '__main__':
    app = ApplicationBuilder().token('7476580536:AAFhZS6bM63fWJcSyPn0KfFNpWT5Jh5t4vE').build()
    app.add_handler(CommandHandler('start',start))
    app.add_handler(MessageHandler(filters.Regex("📝 Start Quiz"), quiz))
    app.add_handler(MessageHandler(filters.Regex("🏆 Leaderboard"), leaderboard))
    app.add_handler(MessageHandler(filters.Regex("ℹ️ Help"), help_command))
    app.add_handler(MessageHandler(filters.Regex("👤 Account Info"), account))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(CallbackQueryHandler(select_quiz, pattern="^select_quiz_"))
    app.add_handler(CallbackQueryHandler(handle_answer, pattern="^[^select_quiz_]"))
    app.run_polling()
