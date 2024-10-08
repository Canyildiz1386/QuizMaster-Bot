# 🎉 QuizMaster Bot 🧠

Welcome to **QuizMaster Bot** – a comprehensive quiz competition bot built with **Flask**, **MongoDB**, and the **Telegram Bot API**! This project allows you to create and manage quizzes, track user performance, and analyze statistics with ease. 📊

---

## 🚀 Features

- **Quiz Management**: Create, update, and delete quizzes 📚.
- **User Management**: Register users with phone verification (Iran & Turkey only) 📱.
- **Telegram Integration**: Interact with users via a Telegram bot 🤖.
- **Leaderboards**: Keep track of the top users based on quiz performance 🏆.
- **Daily Quiz Limits**: Limit users to a set number of quizzes per day ⏳.
- **Multilingual Support**: Available in both English and Farsi 🌍.
- **Real-time Statistics**: Analyze quiz and user performance with detailed statistics 📊.

---

## 🛠️ Setup

Follow these instructions to get the QuizMaster Bot up and running on your local machine.

### Prerequisites

- Python 3.7+
- MongoDB
- A Telegram bot token (get it from [BotFather](https://t.me/botfather))

### Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/Canyildiz1386/quizmaster-bot.git
    cd quizmaster-bot
    ```

2. Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

3. Update the `API_BASE_URL` and `TELEGRAM_TOKEN` in the `bot.py` file to match your local server and bot token.
   
4. Start MongoDB (if it's not running already):
    ```bash
    mongod
    ```

5. Run the Flask application:
    ```bash
    python app.py
    ```

6. Run the Telegram bot:
    ```bash
    python bot.py
    ```

---

## 📝 API Endpoints

### User-related endpoints:
- **GET** `/api/all_users`: Retrieve all registered users.
- **POST** `/api/register`: Register a new user (requires `telegram_id` and `phone_number`).
- **PUT** `/api/user/<user_id>`: Update user information (telegram ID, phone number).
- **DELETE** `/api/user/<user_id>`: Delete a user.

### Quiz-related endpoints:
- **GET** `/api/all_quizzes`: Retrieve all quizzes.
- **POST** `/api/quiz`: Create a new quiz (requires title and questions).
- **PUT** `/api/quiz/<quiz_id>`: Update an existing quiz.
- **DELETE** `/api/quiz/<quiz_id>`: Delete a quiz.

### Statistics endpoints:
- **GET** `/api/statistics/users`: Get user statistics (total users, users by country, total coins).
- **GET** `/api/statistics/quizzes`: Get quiz statistics (total quizzes, average questions per quiz, most popular quiz).

---

## 📊 Usage (Telegram Commands)

- **/start**: Register or choose your language.
- **📝 Start Quiz**: Begin a new quiz and answer questions.
- **🏆 Leaderboard**: Check the top performers.
- **ℹ️ Help**: Get instructions on how to use the bot.
- **👤 Account Info**: View your account details and current progress.

---

## 🌟 Contributions

Feel free to fork this repository and submit pull requests if you have any improvements or new features to add! 🙌

---

## 🛡️ License

This project is licensed under the MIT License.

---

Enjoy your quiz competition experience with **QuizMaster Bot**! 🎮✨
