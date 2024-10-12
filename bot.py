import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters


# API_BASE_URL = "http://127.0.0.1:8080/api"

API_BASE_URL = "http://128.140.49.195:8080/api"

BOT_NAME = "FlopPlay_bot"
ADMIN_TELEGRAM_ID_NUM = "6876153654"
ADMIN_TELEGRAM_ID = "@tina_salimi_pk"


MAIN_MENU_OPTIONS = {
    "fa": {
        "start_quiz": "📝 شروع آزمون",
        "leaderboard": "🏆 جدول امتیازات",
        "help": "ℹ️ راهنما",
        "account_info": "👤 اطلاعات حساب",
        "referral": "🔗 لینک ارجاع",
        "convert_coins": "💰 تبدیل سکه‌ها",
        "support": "💬 پشتیبانی"
    }
}


async def start(update: Update, context):
    telegram_id = str(update.message.from_user.id)

    args = context.args
    referred_by = None
    if args:
        referred_by = args[0]

    response = requests.get(f"{API_BASE_URL}/user/{telegram_id}/progress")
    
    if response.status_code == 404:
        contact_button = KeyboardButton("📱 اشتراک گذاری شماره", request_contact=True)
        reply_markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True)

        await update.message.reply_text("👋 خوش آمدید! لطفاً برای ثبت نام شماره شماره خود را به اشتراک بگذارید 📱", reply_markup=reply_markup)
        context.user_data['referred_by'] = referred_by
    else:
        keyboard = [
            [KeyboardButton(MAIN_MENU_OPTIONS["fa"]["start_quiz"]), KeyboardButton(MAIN_MENU_OPTIONS["fa"]["convert_coins"])],
            [KeyboardButton(MAIN_MENU_OPTIONS["fa"]["help"]), KeyboardButton(MAIN_MENU_OPTIONS["fa"]["account_info"])],
            [KeyboardButton(MAIN_MENU_OPTIONS["fa"]["referral"]), KeyboardButton(MAIN_MENU_OPTIONS["fa"]["support"])]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("لطفاً یک گزینه از منوی زیر انتخاب کنید:", reply_markup=reply_markup)


async def referral(update: Update, context):
    telegram_id = str(update.message.from_user.id)
    user_data = requests.get(f"{API_BASE_URL}/user/{telegram_id}/progress").json()
    
    referral_link = "\n\n" + f"https://t.me/{BOT_NAME}?start={telegram_id}"  
    
    referral_message = "🔗 *این لینک ارجاع شماست:* 🔗\n\n" \
                       "این لینک را با دوستان خود به اشتراک بگذارید. وقتی آنها ثبت نام کنند، شما سکه دریافت می‌کنید! 🪙\n\n" \
                       + referral_link
    await update.message.reply_text(referral_message, parse_mode='Markdown')


async def handle_contact(update: Update, context):
    contact = update.message.contact
    telegram_id = str(update.message.from_user.id)
    phone_number = contact.phone_number
    
    referred_by = context.user_data.get('referred_by')

    payload = {"telegram_id": telegram_id, "phone_number": phone_number}
    
    if referred_by:
        payload["referred_by"] = referred_by
    
    response = requests.post(f"{API_BASE_URL}/register", json=payload)
    if response.status_code in [200, 201]:
        await update.message.reply_text("✅ شما با موفقیت ثبت نام شدید!")
        
        keyboard = [
            [KeyboardButton(MAIN_MENU_OPTIONS["fa"]["start_quiz"]), KeyboardButton(MAIN_MENU_OPTIONS["fa"]["convert_coins"])],
            [KeyboardButton(MAIN_MENU_OPTIONS["fa"]["help"]), KeyboardButton(MAIN_MENU_OPTIONS["fa"]["account_info"])],
            [KeyboardButton(MAIN_MENU_OPTIONS["fa"]["referral"]), KeyboardButton(MAIN_MENU_OPTIONS["fa"]["support"])]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("لطفاً یک گزینه از منوی زیر انتخاب کنید:", reply_markup=reply_markup)
    else:
        await update.message.reply_text(f"❌ خطای سرور: {response.json()['error']} 😢")


async def help_command(update: Update, context):
    help_text = "ℹ️ *منوی راهنما* ℹ️\n\n" \
                "در اینجا تعدادی از دستورات که می‌توانید استفاده کنید آورده شده است:\n\n" \
                "✅ شروع آزمون با کلیک روی 📝 شروع آزمون\n" \
                "🏆 مشاهده جدول امتیازات با کلیک روی 🏆 جدول امتیازات\n" \
                "📊 بررسی اطلاعات حساب با 👤 اطلاعات حساب\n" \
                "ℹ️ دریافت راهنما با ℹ️ راهنما\n"
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def quiz(update: Update, context):
    telegram_id = str(update.message.from_user.id)
    response = requests.get(f"{API_BASE_URL}/quizzes", params={"telegram_id": telegram_id})
    
    if response.status_code == 403:
        await update.message.reply_text("🚫 شما به حد مجاز آزمون‌های روزانه رسیده‌اید 🕒.")
        return
    
    quizzes = response.json()
    if "error" in quizzes:
        await update.message.reply_text("❌ لطفاً ابتدا با شروع ربات ثبت نام کنید 📱.")
        return
    
    if not quizzes:
        await update.message.reply_text("🎉 شما به همه آزمون‌های موجود پاسخ داده‌اید! 🏆")
        return
    
    buttons = [[InlineKeyboardButton(quiz['title'], callback_data=f"select_quiz_{quiz['_id']}")] for quiz in quizzes]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("📚 لطفاً یک آزمون انتخاب کنید 🧠:", reply_markup=reply_markup)




async def select_quiz(update: Update, context):
    query = update.callback_query
    quiz_id = query.data.split("_")[-1]
    telegram_id = str(query.from_user.id)
    
    start_response = requests.post(f"{API_BASE_URL}/user/{telegram_id}/start_quiz", json={"quiz_id": quiz_id})
    
    if start_response.status_code != 200:
        await query.message.reply_text("❌ خطا در شروع آزمون. لطفاً دوباره امتحان کنید 😔.")
        return

    await query.message.delete()

    response = requests.get(f"{API_BASE_URL}/quiz/{quiz_id}")
    if response.status_code != 200:
        await query.message.reply_text(f"❌ خطا در بازیابی داده‌های آزمون (کد وضعیت {response.status_code}) 😢.")
        return
    
    quiz = response.json()
    quiz_questions = quiz['questions']
    
    if not quiz_questions:
        await query.message.reply_text("❌ هیچ سوالی در این آزمون وجود ندارد 📋.")
        return
    
    current_question = 0
    context.user_data['correct_answers'] = 0  
    context.user_data['total_questions'] = len(quiz_questions)

    await send_question(update, context, quiz_questions, current_question, quiz_id)


async def send_question(update, context, quiz_questions, current_question, quiz_id):
    telegram_id = str(update.callback_query.from_user.id)
    question = quiz_questions[current_question]
    question_text = question['question_text']
    question_image = question.get('question_image')
    options = question['options']
    
    buttons = [[InlineKeyboardButton(option, callback_data=option) for option in options]]
    reply_markup = InlineKeyboardMarkup(buttons)

    if question_image:
        with open(question_image, 'rb') as img:
            await update.callback_query.message.reply_photo(photo=img, caption=question_text, reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text(question_text, reply_markup=reply_markup)
    
    context.user_data['current_question'] = current_question
    context.user_data['quiz_id'] = quiz_id


async def handle_answer(update: Update, context):
    query = update.callback_query
    await query.answer()

    telegram_id = str(query.from_user.id)
    user_data = requests.get(f"{API_BASE_URL}/user/{telegram_id}/progress").json()
    quiz_id = context.user_data['quiz_id']

    quiz_response = requests.get(f"{API_BASE_URL}/quiz/{quiz_id}")
    quiz = quiz_response.json()
    quiz_questions = quiz['questions']
    current_question = context.user_data['current_question']

    await query.message.delete()

    question = quiz_questions[current_question]
    correct_option = int(str(question['correct_option']).split('_')[1]) - 1
    user_answer = query.data

    if user_answer == question['options'][correct_option]:
        context.user_data['correct_answers'] += 1  # Increment correct answers
        reward = question['reward']  # Get the reward for the question
        requests.put(f"{API_BASE_URL}/user/{telegram_id}/coins", json={"coins": reward})  # Reward the user


    new_question_number = current_question + 1

    if new_question_number >= len(quiz_questions):
        total_correct = context.user_data['correct_answers']
        total_questions = context.user_data['total_questions']
        percentage = (total_correct / total_questions) * 100
        requests.put(f"{API_BASE_URL}/user/{telegram_id}/finish_quiz", json={"quiz_id": quiz_id})

        await query.message.reply_text(f"🎉 آزمون به پایان رسید! \nدرصد پاسخ صحیح شما: {percentage:.2f}%")
    else:
        requests.put(f"{API_BASE_URL}/user/{telegram_id}/progress", json={"current_quiz": quiz_id, "current_question": new_question_number})
        await send_question(update, context, quiz_questions, new_question_number, quiz_id)


async def leaderboard(update: Update, context):
    response = requests.get(f"{API_BASE_URL}/leaderboard")
    leaderboard = response.json()
    
    leaderboard_text = "🏆 10 کاربر برتر:\n\n"
    for rank, user in enumerate(leaderboard, 1):
        leaderboard_text += f"{rank}. {user['coins']} سکه 🪙\n"
    
    await update.message.reply_text(leaderboard_text)


async def account(update: Update, context):
    telegram_id = str(update.message.from_user.id)
    response = requests.get(f"{API_BASE_URL}/user/{telegram_id}/progress")
    
    if response.status_code == 404:
        await update.message.reply_text("❌ هنوز ثبت نام نکرده‌اید! لطفاً برای ثبت نام /start را بزنید 📱.")
    else:
        user_data = response.json()
        current_quiz_id = user_data['current_quiz']
        if current_quiz_id:
            quiz_response = requests.get(f"{API_BASE_URL}/quiz/{current_quiz_id}")
            quiz_title = quiz_response.json().get('title', 'آزمون نامشخص')
        else:
            quiz_title = "هیچ"
        
        account_info = (
            "👤 *اطلاعات حساب شما* 👤\n\n"
            + f"\n\n 🆔 آیدی تلگرام: {user_data['telegram_id']}\n"
            + f"🧠 آزمون جاری: {quiz_title}\n"
            + f"📊 سوال جاری: {user_data['current_question']}\n"
            + f"🪙 سکه‌ها: {user_data['coins']}\n"
            + f"🎯 آزمون‌های پاسخ داده شده: {len(user_data['answered_quizzes'])}\n"
        )
        await update.message.reply_text(account_info, parse_mode='Markdown')


async def convert_coins(update: Update, context):
    telegram_id = str(update.message.from_user.id)
    
    response = requests.get(f"{API_BASE_URL}/user/{telegram_id}/progress")
    
    if response.status_code != 200:
        await update.message.reply_text("❌ خطا در بازیابی اطلاعات حساب. لطفاً بعداً دوباره امتحان کنید.")
        print(f"Error: {response.status_code}, Response Text: {response.text}")
        return

    try:
        user_data = response.json()
    except requests.exceptions.JSONDecodeError as e:
        await update.message.reply_text("❌ خطای داخلی: نتوانستیم اطلاعات را از سرور پردازش کنیم.")
        print(f"JSON Decode Error: {e}, Response Text: {response.text}")
        return
    
    user_coins = user_data.get('coins', 0)
    
    await update.message.reply_text(
        f"💰 شما {user_coins} سکه دارید. چند سکه می‌خواهید تبدیل کنید؟"
    )
    
    context.user_data['coins_to_convert'] = user_coins

async def handle_conversion_request(update: Update, context):
    telegram_id = str(update.message.from_user.id)
    coins_to_convert = (update.message.text)
    total_coins = context.user_data.get('coins_to_convert')
    print(total_coins , coins_to_convert , telegram_id)
    if int(coins_to_convert) > int(total_coins):
        await update.message.reply_text("❌ شما به اندازه کافی سکه ندارید.")
        return

    admin_message = f"🔔 کاربر {telegram_id} درخواست تبدیل {coins_to_convert} سکه را دارد."
    await context.bot.send_message(chat_id=ADMIN_TELEGRAM_ID_NUM, text=admin_message)

    await update.message.reply_text("✅ درخواست شما برای تأیید به مدیر ارسال شد.")


async def support(update: Update, context):
    support_text = f"💬 در صورتی که به پشتیبانی نیاز دارید، با مدیر به آیدی: {ADMIN_TELEGRAM_ID} تماس بگیرید."
    await update.message.reply_text(support_text)


if __name__ == '__main__':
    # app = ApplicationBuilder().token('7476580536:AAFhZS6bM63fWJcSyPn0KfFNpWT5Jh5t4vE').build()
    app = ApplicationBuilder().token('7693869905:AAE3mOdC_zCmXJVmmF_cAJUbgj-WQI911AE').build()
    # app = ApplicationBuilder().token('7476580536:AAFhZS6bM63fWJcSyPn0KfFNpWT5Jh5t4vE').build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.Regex("📝 شروع آزمون"), quiz))
    app.add_handler(MessageHandler(filters.Regex("🏆 جدول امتیازات"), leaderboard))
    app.add_handler(MessageHandler(filters.Regex("ℹ️ راهنما"), help_command))
    app.add_handler(MessageHandler(filters.Regex("👤 اطلاعات حساب"), account))
    app.add_handler(MessageHandler(filters.Regex("🔗 لینک ارجاع"), referral))
    app.add_handler(MessageHandler(filters.Regex("💰 تبدیل سکه‌ها"), convert_coins))
    app.add_handler(MessageHandler(filters.Regex("💬 پشتیبانی"), support))
    
    app.add_handler(CallbackQueryHandler(select_quiz, pattern="^select_quiz_"))
    app.add_handler(CallbackQueryHandler(handle_answer, pattern="^[^select_quiz_]"))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^\d+$'), handle_conversion_request))

    app.run_polling()
