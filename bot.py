from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import requests

BACKEND_URL = 'http://127.0.0.1:5000'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    referral_id = context.args[0] if context.args else None
    data = {'user_id': user_id, 'referral_id': referral_id}
    response = requests.post(f'{BACKEND_URL}/start', json=data)
    message = f"🎉 Welcome to the Quiz Bot, {update.effective_user.first_name}! 🧠 You need to verify your phone number before you can take a quiz."
    await update.message.reply_text(message)

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact_button = KeyboardButton(text="📱 Share your contact", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True)
    await update.message.reply_text("Please verify your mobile number. ☎️✅", reply_markup=reply_markup)

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    phone = contact.phone_number
    user_id = update.effective_user.id
    data = {'user_id': user_id, 'phone': phone}
    response = requests.post(f'{BACKEND_URL}/register', json=data)
    if response.status_code == 200:
        await update.message.reply_text("Your phone number has been verified! 🎉 You can now participate in quizzes 🧠.")
    else:
        await update.message.reply_text("Invalid phone number 🚫. Only numbers from Iran 🇮🇷 and Türkiye 🇹🇷 are allowed.")

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    response = requests.get(f'{BACKEND_URL}/get_quiz/{user_id}')
    
    if response.status_code == 200:
        quiz_data = response.json()

        # Check if the user has completed all quizzes
        if 'message' in quiz_data and quiz_data['message'] == 'You have completed all available quizzes!':
            await update.message.reply_text("🎉 You have completed all available quizzes! 🏆")
            return

        # Check if the current quiz is completed
        if quiz_data.get('quiz_completed', False):
            if update.message:
                await update.message.reply_text("You've already completed this quiz 📝. Stay tuned for new quizzes 🎯!")
            elif update.callback_query:
                await update.callback_query.message.reply_text("You've already completed this quiz 📝. Stay tuned for new quizzes 🎯!")
            return

        # Display the quiz question and options
        current_question = quiz_data['current_question']
        options = quiz_data['options']
        quiz_id = quiz_data['quiz_id']
        keyboard = [
            [InlineKeyboardButton(option, callback_data=f"{quiz_id}:{current_question}:{i}") for i, option in enumerate(options)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(f"🧠 {quiz_data['question']} 🤔", reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.message.reply_text(f"🧠 {quiz_data['question']} 🤔", reply_markup=reply_markup)
    else:
        if update.message:
            await update.message.reply_text("No quiz available right now 🙁. Please try again later 🔄.")
        elif update.callback_query:
            await update.callback_query.message.reply_text("No quiz available right now 🙁. Please try again later 🔄.")


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    quiz_id, question_number, answer = query.data.split(":")
    response = requests.post(f'{BACKEND_URL}/submit_answer', json={'user_id': user_id, 'quiz_id': quiz_id, 'question_number': question_number, 'answer': answer})
    
    if response.status_code == 200:
        result = response.json()
        if result['correct']:
            message = f"🎉 Correct answer! Great job! 🏆 You earned {result['reward_coins']} coins! 🪙"
        else:
            message = "❌ Incorrect answer! Better luck next time 🤔."

        await query.edit_message_text(text=message)

        if result['quiz_completed']:
            await query.message.reply_text("🎉 You've completed the quiz! Stay tuned for more quizzes!")
        else:
            await quiz(update, context)
    else:
        await query.edit_message_text(text="Error submitting answer 😔. Please try again 🔄.")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = requests.get(f'{BACKEND_URL}/leaderboard')
    if response.status_code == 200:
        leaderboard_data = response.json()
        leaderboard_text = "🏆 Leaderboard 🏆:\n"
        for entry in leaderboard_data:
            leaderboard_text += f"🔹 User {entry['user_id']} ({entry['phone']}): {entry['correct_answers']} correct answers ✅, {entry['coins']} coins 🪙\n"
        await update.message.reply_text(leaderboard_text)
    else:
        await update.message.reply_text("Failed to retrieve the leaderboard 🚫. Please try again later 🔄.")

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    referral_message = f"🎉 Invite your friends and earn coins! 🪙 Share this link: https://t.me/GlassButtonCanBot?start={user_id} 📲"
    await update.message.reply_text(referral_message)

if __name__ == '__main__':
    app = ApplicationBuilder().token('7476580536:AAFhZS6bM63fWJcSyPn0KfFNpWT5Jh5t4vE').build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('verify', verify))
    app.add_handler(CommandHandler('quiz', quiz))
    app.add_handler(CommandHandler('leaderboard', leaderboard))
    app.add_handler(CommandHandler('invite', invite))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.run_polling()
