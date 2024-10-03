import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import requests
import pymongo

client = pymongo.MongoClient('mongodb://localhost:27017/')
db = client['quiz_bot']
users_collection = db['users']
quizzes_collection = db['quizzes']

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7476580536:AAFhZS6bM63fWJcSyPn0KfFNpWT5Jh5t4vE"
VALID_COUNTRY_CODES = ['98', '90']

async def start(update: Update, context):
    await update.message.reply_text("🎉 Welcome to the Quiz Bot! 📝 Please verify your mobile number by typing /verify <mobile_number>.")

async def verify(update: Update, context):
    try:
        print(context.args[0])
        mobile_number = context.args[0]
        country_code = mobile_number[:2]
        if country_code in VALID_COUNTRY_CODES:
            telegram_id = update.message.from_user.id
            users_collection.update_one(
                {"telegram_id": telegram_id},
                {"$set": {"mobile_number": mobile_number, "country_code": country_code}},
                upsert=True
            )
            await update.message.reply_text(f"✅ Mobile number {mobile_number} verified successfully! 🎊")
        else:
            await update.message.reply_text("⚠️ Sorry, only users from Iran 🇮🇷 or Turkey 🇹🇷 can participate.")
    except (IndexError, ValueError):
        await update.message.reply_text("❗ Please provide a valid mobile number. Usage: /verify <mobile_number> 📱")

async def participate(update: Update, context):
    telegram_id = update.message.from_user.id
    user = users_collection.find_one({"telegram_id": telegram_id})
    
    if user and "mobile_number" in user:
        quiz = quizzes_collection.find_one()
        if quiz:
            await update.message.reply_text(f"🎯 Quiz: {quiz['name']}\n📝 Description: {quiz['description']}")
            question = quiz['questions'][0]
            keyboard = [[InlineKeyboardButton(option, callback_data=option) for option in question['options']]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(f"🧐 {question['text']}", reply_markup=reply_markup)
            context.user_data['current_quiz'] = quiz['_id']
            context.user_data['current_question_index'] = 0
        else:
            await update.message.reply_text("🚫 No quiz available at the moment. Please check back later! ⏳")
    else:
        await update.message.reply_text("📲 You need to verify your mobile number first. Use /verify <mobile_number> 📱")

async def button(update: Update, context):
    query = update.callback_query
    await query.answer()
    selected_option = query.data
    telegram_id = query.from_user.id
    quiz_id = context.user_data.get('current_quiz')
    question_index = context.user_data.get('current_question_index', 0)

    if quiz_id is not None:
        quiz = quizzes_collection.find_one({"_id": quiz_id})
        question = quiz['questions'][question_index]
        correct_answer = question['correct_answer']
        
        if selected_option == correct_answer:
            await query.edit_message_text(f"🎉 Correct! ✅ You selected: {selected_option}")
            users_collection.update_one({"telegram_id": telegram_id}, {"$inc": {"coins": 10}})
        else:
            await query.edit_message_text(f"❌ Wrong! The correct answer was: {correct_answer}")

        next_question_index = question_index + 1
        if next_question_index < len(quiz['questions']):
            next_question = quiz['questions'][next_question_index]
            keyboard = [[InlineKeyboardButton(option, callback_data=option) for option in next_question['options']]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(f"🤔 {next_question['text']}", reply_markup=reply_markup)
            context.user_data['current_question_index'] = next_question_index
        else:
            await query.message.reply_text("🏁 Quiz completed! 🎉 Thanks for participating. 🎊")

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("verify", verify))
    application.add_handler(CommandHandler("participate", participate))
    application.add_handler(CallbackQueryHandler(button))
    application.run_polling()

if __name__ == '__main__':
    main()
