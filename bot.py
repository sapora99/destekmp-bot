import os
import json
import asyncio
import random
from datetime import datetime
from rapidfuzz import process
from textblob import TextBlob
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import openai

# OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Sadece sahibi /ogret komutunu kullanabilsin
OWNER_IDS = [1816905363, 7422411288, 2109262579]

DATA_FILE = "qa_database.json"
NEW_QUESTIONS_FILE = "new_questions.json"
BACKUP_FOLDER = "backups"
USERS_FOLDER = "users"
qa_database = {}
pending_questions = {}

# Klasörleri yoksa oluştur
for folder in [BACKUP_FOLDER, USERS_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

def load_database():
    global qa_database
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            qa_database = json.load(f)
        print("Veritabanı yüklendi.")
    except FileNotFoundError:
        print("Veritabanı bulunamadı, sıfırdan başlıyoruz.")
        qa_database = {}

def save_database():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(qa_database, f, ensure_ascii=False, indent=2)

def save_user_profile(user_id, message):
    user_file = os.path.join(USERS_FOLDER, f"{user_id}.json")
    profile = []
    if os.path.exists(user_file):
        with open(user_file, "r", encoding="utf-8") as f:
            profile = json.load(f)
    profile.append({"message": message, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    with open(user_file, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

def analyze_sentiment(message):
    blob = TextBlob(message)
    polarity = blob.sentiment.polarity
    if polarity > 0.3:
        return "Neşeli"
    elif polarity < -0.3:
        return "Üzgün"
    else:
        return "Nötr"

def suggest_related_topics(message):
    keywords = ["hava", "spor", "yemek", "gezi", "teknoloji", "eğitim"]
    suggestions = []
    for word in keywords:
        if word in message:
            suggestions.append(f"{word} hakkında daha fazlasını öğrenmek ister misin?")
    return suggestions

async def generate_chatgpt_response(question):
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=question,
            max_tokens=150
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"ChatGPT hatası: {e}")
        return None

def save_new_question(question):
    try:
        if os.path.exists(NEW_QUESTIONS_FILE):
            with open(NEW_QUESTIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []
        data.append(question)
        with open(NEW_QUESTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Yeni soru kaydederken hata oluştu: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Merhaba. Lütfen bir soru sorabilirsiniz.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.lower()
    user_id = update.message.from_user.id

    save_user_profile(user_id, user_message)

    if user_id in pending_questions:
        question = pending_questions.pop(user_id)
        qa_database[question] = {
            "answer": user_message,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_database()
        await update.message.reply_text(f"'{question}' sorusu için cevabınız kaydedildi.")
    else:
        questions = list(qa_database.keys())
        match, score, _ = process.extractOne(user_message, questions)

        if score and score >= 80:
            response = qa_database[match]["answer"]
            await update.message.reply_text(response)
        elif score and score >= 60:
            await update.message.reply_text(f"Şunu mu demek istediniz: {match}")
        else:
            sentiment = analyze_sentiment(user_message)
            suggestions = suggest_related_topics(user_message)
            suggestion_text = "\n".join(suggestions) if suggestions else ""
            gpt_response = await generate_chatgpt_response(user_message)

            if gpt_response:
                await update.message.reply_text(f"ChatGPT Cevap: {gpt_response}\n(Duygu: {sentiment})\n{suggestion_text}")
                qa_database[user_message] = {
                    "answer": gpt_response,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                save_database()
            else:
                await update.message.reply_text("Bu sorunun cevabını bilmiyorum. Eğer yetkiliyseniz /ogret komutunu kullanarak öğretebilirsiniz.")
            save_new_question(user_message)
            await auto_learn()

async def ogret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in OWNER_IDS:
        await update.message.reply_text("Üzgünüm, sadece yetkili kişiler yeni bilgi ekleyebilir.")
        return

    text = update.message.text[len("/ogret "):].strip()
    if '|' in text:
        question, answer = map(str.strip, text.split('|', 1))
        qa_database[question.lower()] = {
            "answer": answer,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_database()
        await update.message.reply_text(f"'{question}' sorusuna artık '{answer}' diyeceğim.")
    else:
        user_id = update.message.from_user.id
        pending_questions[user_id] = update.message.text.strip().lower()
        await update.message.reply_text("Sadece soruyu yazdınız. Şimdi cevabını yazınız.")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in OWNER_IDS:
        await update.message.reply_text("Bu komutu sadece yetkililer kullanabilir.")
        return

    total_questions = len(qa_database)
    if os.path.exists(NEW_QUESTIONS_FILE):
        with open(NEW_QUESTIONS_FILE, "r", encoding="utf-8") as f:
            new_questions = json.load(f)
        total_new_questions = len(new_questions)
    else:
        total_new_questions = 0

    await update.message.reply_text(
        f"Toplam öğretilmiş soru: {total_questions}\nCevapsız yeni soru: {total_new_questions}"
    )

async def auto_learn():
    if os.path.exists(NEW_QUESTIONS_FILE):
        with open(NEW_QUESTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        question_counts = {}
        for question in data:
            question_counts[question] = question_counts.get(question, 0) + 1

        for question, count in question_counts.items():
            if count >= 3 and question not in qa_database:
                qa_database[question] = {
                    "answer": "Henüz cevaplanmadı.",
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                save_database()
                print(f"Otomatik öğrenildi: {question}")

async def auto_backup():
    while True:
        await asyncio.sleep(6 * 60 * 60)  # 6 saat bekle
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
        backup_file = os.path.join(BACKUP_FOLDER, f"qa_database_backup_{timestamp}.json")
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(qa_database, f, ensure_ascii=False, indent=2)
        print(f"Backup alındı: {backup_file}")

app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ogret", ogret))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot başlıyor...")
load_database()

async def main():
    await asyncio.gather(
        app.run_polling(),
        auto_backup()
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
