import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from deep_translator import GoogleTranslator

API_BASE_URL = "http://127.0.0.1:8080/api"

MAIN_MENU_OPTIONS = {
    "en": {
        "start_quiz": "📝 Start Quiz",
        "leaderboard": "🏆 Leaderboard",
        "help": "ℹ️ Help",
        "account_info": "👤 Account Info"
    },
    "fa": {
        "start_quiz": "📝 شروع آزمون",
        "leaderboard": "🏆 جدول امتیازات",
        "help": "ℹ️ راهنما",
        "account_info": "👤 اطلاعات حساب"
    }
}

def translate_text(text, target_lang):
    translator = GoogleTranslator(source='auto', target=target_lang)
    return translator.translate(text)

async def start(update: Update, context):
    telegram_id = str(update.message.from_user.id)
    response = requests.get(f"{API_BASE_URL}/user/{telegram_id}/progress")
    
    if response.status_code == 404:
        contact_button = KeyboardButton("📱 Share Contact", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True)
        await update.message.reply_text("👋 Welcome! Please share your contact to register 📱", reply_markup=reply_markup)
    else:
        keyboard = [
            [InlineKeyboardButton("🌍 English", callback_data="lang_en")],
            [InlineKeyboardButton("🌍 Farsi", callback_data="lang_fa")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🌐 Please select your language:", reply_markup=reply_markup)

async def handle_contact(update: Update, context):
    contact = update.message.contact
    telegram_id = str(update.message.from_user.id)
    phone_number = contact.phone_number
    
    response = requests.post(f"{API_BASE_URL}/register", json={"telegram_id": telegram_id, "phone_number": phone_number})
    if response.status_code in [200, 201]:
        await update.message.reply_text("✅ You are registered successfully! 🎉")
        
        keyboard = [
            [InlineKeyboardButton("🌍 English", callback_data="lang_en")],
            [InlineKeyboardButton("🌍 Farsi", callback_data="lang_fa")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🌐 Please select your language:", reply_markup=reply_markup)
    else:
        await update.message.reply_text(f"❌ Server error: {response.status_code} 😢")

async def handle_language_selection(update: Update, context):
    query = update.callback_query
    telegram_id = str(query.from_user.id)
    selected_language = query.data.split("_")[1]
    
    response = requests.post(f"{API_BASE_URL}/user/{telegram_id}/language", json={"language": selected_language})
    
    if response.status_code == 200:
        message = translate_text("✅ Language updated successfully! 🎉", selected_language)
        await query.message.reply_text(message)
        
        main_menu_text = translate_text("Please choose an option from the menu below:", selected_language)
        
        options = MAIN_MENU_OPTIONS[selected_language]
        keyboard = [
            [KeyboardButton(options["start_quiz"]), KeyboardButton(options["leaderboard"])],
            [KeyboardButton(options["help"]), KeyboardButton(options["account_info"])]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await query.message.reply_text(main_menu_text, reply_markup=reply_markup)
    else:
        await query.message.reply_text("❌ Error updating language.")



async def help_command(update: Update, context):
    telegram_id = str(update.message.from_user.id)
    user_data = requests.get(f"{API_BASE_URL}/user/{telegram_id}/progress").json()
    user_lang = user_data.get('language', 'en')
    
    help_text = translate_text(
        "ℹ️ *Help Menu* ℹ️\n"
        "Here are some commands you can use:\n\n"
        "✅ Start Quiz by clicking on 📝 Start Quiz\n"
        "🏆 View the leaderboard by clicking on 🏆 Leaderboard\n"
        "📊 Check your account details with 👤 Account Info\n"
        "ℹ️ Get help with ℹ️ Help\n", user_lang
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def quiz(update: Update, context):
    telegram_id = str(update.message.from_user.id)
    user_data = requests.get(f"{API_BASE_URL}/user/{telegram_id}/progress").json()
    user_lang = user_data.get('language', 'en')
    
    response = requests.get(f"{API_BASE_URL}/quizzes", params={"telegram_id": telegram_id})
    if response.status_code == 403:
        await update.message.reply_text(translate_text("🚫 You have reached the daily quiz limit 🕒.", user_lang))
        return
    
    quizzes = response.json()
    if "error" in quizzes:
        await update.message.reply_text(translate_text("❌ Please register first by starting the bot 📱.", user_lang))
        return
    
    if not quizzes:
        await update.message.reply_text(translate_text("🎉 You have answered all available quizzes! 🏆", user_lang))
        return
    
    buttons = [[InlineKeyboardButton(translate_text(quiz['title'], user_lang), callback_data=f"select_quiz_{quiz['_id']}")] for quiz in quizzes]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(translate_text("📚 Please select a quiz 🧠:", user_lang), reply_markup=reply_markup)

async def select_quiz(update: Update, context):
    query = update.callback_query
    quiz_id = query.data.split("_")[-1]
    telegram_id = str(query.from_user.id)
    
    start_response = requests.post(f"{API_BASE_URL}/user/{telegram_id}/start_quiz", json={"quiz_id": quiz_id})
    user_data = requests.get(f"{API_BASE_URL}/user/{telegram_id}/progress").json()
    user_lang = user_data.get('language', 'en')
    
    if start_response.status_code == 200:
        await query.message.reply_text(translate_text("⏳ Your quiz has started! You have 5 minutes to complete it 🕒.", user_lang))
    else:
        await query.message.reply_text(translate_text("❌ Error starting quiz. Please try again 😔.", user_lang))
        return
    
    response = requests.get(f"{API_BASE_URL}/quiz/{quiz_id}")
    if response.status_code != 200:
        await query.message.reply_text(translate_text(f"❌ Error fetching quiz data (status code {response.status_code}) 😢.", user_lang))
        return
    
    quiz = response.json()
    quiz_questions = quiz['questions']
    if user_data['current_quiz'] != quiz_id:
        requests.put(f"{API_BASE_URL}/user/{telegram_id}/progress", json={"current_quiz": quiz_id, "current_question": 0})
        current_question = 0
    else:
        current_question = user_data.get('current_question', 0)
    
    if not quiz_questions:
        await query.message.reply_text(translate_text("❌ No questions available in this quiz 📋.", user_lang))
        return
    
    if current_question >= len(quiz_questions):
        await query.edit_message_text(translate_text("🎉 You have finished this quiz! 🏅", user_lang))
        return
    
    question = quiz_questions[current_question]
    options = question['options']
    buttons = [[InlineKeyboardButton(translate_text(option, user_lang), callback_data=option) for option in options]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.message.reply_text(translate_text(f"📝 Question: {question['question']} 🤔", user_lang), reply_markup=reply_markup)

async def handle_answer(update: Update, context):
    query = update.callback_query
    await query.answer()
    telegram_id = str(query.from_user.id)
    user_data = requests.get(f"{API_BASE_URL}/user/{telegram_id}/progress").json()
    user_lang = user_data.get('language', 'en')
    quiz_id = user_data['current_quiz']
    
    quiz_response = requests.get(f"{API_BASE_URL}/quiz/{quiz_id}")
    quiz = quiz_response.json()
    quiz_questions = quiz['questions']
    current_question = user_data['current_question']
    
    if current_question >= len(quiz_questions):
        await query.edit_message_text(translate_text("🎉 You have finished the quiz! 🏅", user_lang))
        return
    
    question = quiz_questions[current_question]
    correct_option = question['correct_option']
    user_answer = query.data
    
    correct_option_int = str(correct_option).split('_')[1]
    correct_option_int = int(correct_option_int) - 1
    options_list = question['options']
    
    if user_answer == options_list[correct_option_int]:
        await query.edit_message_text(translate_text("🎉 Correct! 🏆", user_lang))
        requests.put(f"{API_BASE_URL}/user/{telegram_id}/coins", json={"coins": question['reward']})
    else:
        await query.edit_message_text(translate_text(f"❌ Wrong! The correct answer was: {options_list[correct_option_int]} ❓", user_lang))
    
    new_question_number = current_question + 1
    if new_question_number < len(quiz_questions):
        requests.put(f"{API_BASE_URL}/user/{telegram_id}/progress", json={"current_quiz": quiz_id, "current_question": new_question_number})
        next_question = quiz_questions[new_question_number]
        options = next_question['options']
        buttons = [[InlineKeyboardButton(translate_text(option, user_lang), callback_data=option) for option in options]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.reply_text(translate_text(f"📝 Next Question: {next_question['question']} 🤔", user_lang), reply_markup=reply_markup)
    else:
        requests.put(f"{API_BASE_URL}/user/{telegram_id}/finish_quiz", json={"quiz_id": quiz_id})
        await query.message.reply_text(translate_text("🎉 You have finished the quiz! 🏆", user_lang))

async def leaderboard(update: Update, context):
    response = requests.get(f"{API_BASE_URL}/leaderboard")
    leaderboard = response.json()
    telegram_id = str(update.message.from_user.id)
    user_data = requests.get(f"{API_BASE_URL}/user/{telegram_id}/progress").json()
    user_lang = user_data.get('language', 'en')
    
    leaderboard_text = translate_text("🏆 Top 10 Users:\n\n", user_lang)
    for rank, user in enumerate(leaderboard, 1):
        leaderboard_text += f"{rank}. {user['telegram_id']} - {user['coins']} {translate_text('coins 🪙', user_lang)}\n"
    
    await update.message.reply_text(leaderboard_text)

async def account(update: Update, context):
    telegram_id = str(update.message.from_user.id)
    response = requests.get(f"{API_BASE_URL}/user/{telegram_id}/progress")
    
    if response.status_code == 404:
        await update.message.reply_text("❌ You're not registered yet! Please /start to register 📱.")
    else:
        user_data = response.json()
        user_lang = user_data.get('language', 'en')
        current_quiz_id = user_data['current_quiz']
        if current_quiz_id:
            quiz_response = requests.get(f"{API_BASE_URL}/quiz/{current_quiz_id}")
            quiz_title = quiz_response.json().get('title', 'Unknown Quiz')
        else:
            quiz_title = "Nothing"
        
        account_info = (
            translate_text("👤 *Your Account Information* 👤\n\n", user_lang)
            + translate_text("\n\n 🆔 Telegram ID: ", user_lang) + user_data['telegram_id'] + "\n"
            + translate_text("🧠 Current Quiz: ", user_lang) + quiz_title + "\n"
            + translate_text("📊 Current Question: ", user_lang) + str(user_data['current_question']) + "\n"
            + translate_text("🪙 Coins: ", user_lang) + str(user_data['coins']) + "\n"
            + translate_text("🎯 Answered Quizzes: ", user_lang) + str(len(user_data['answered_quizzes'])) + "\n"
        )
        await update.message.reply_text(account_info, parse_mode='Markdown')

if __name__ == '__main__':
    app = ApplicationBuilder().token('7476580536:AAFhZS6bM63fWJcSyPn0KfFNpWT5Jh5t4vE').build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(handle_language_selection, pattern="^lang_"))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.Regex("📝 (Start Quiz|شروع آزمون)"), quiz))
    app.add_handler(MessageHandler(filters.Regex("🏆 (Leaderboard|جدول امتیازات)"), leaderboard))
    app.add_handler(MessageHandler(filters.Regex("ℹ️ (Help|راهنما)"), help_command))
    app.add_handler(MessageHandler(filters.Regex("👤 (Account Info|اطلاعات حساب)"), account))
    
    app.add_handler(CallbackQueryHandler(select_quiz, pattern="^select_quiz_"))
    app.add_handler(CallbackQueryHandler(handle_answer, pattern="^[^select_quiz_]"))
    
    app.run_polling()