import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Sadece sahibi /ogret komutunu kullanabilsin
OWNER_ID = 123456789  # BURAYA KENDİ USER ID'ni koyacaksın

DATA_FILE = "qa_database.json"
qa_database = {}
pending_questions = {}

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Merhaba. Lütfen bir soru sorabilirsiniz.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text.lower()
    user_id = update.message.from_user.id

    if user_id in pending_questions:
        question = pending_questions.pop(user_id)
        qa_database[question] = user_message
        save_database()
        await update.message.reply_text(f"'{question}' sorusu için cevabınız kaydedildi.")
    else:
        response = qa_database.get(user_message)
        if response:
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("Bu sorunun cevabını bilmiyorum. Eğer yetkiliyseniz /ogret komutunu kullanarak öğretebilirsiniz.")

async def ogret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != OWNER_ID:
        await update.message.reply_text("Üzgünüm, sadece yetkili kişi yeni bilgi ekleyebilir.")
        return

    text = update.message.text[len("/ogret "):].strip()
    if '|' in text:
        question, answer = map(str.strip, text.split('|', 1))
        qa_database[question.lower()] = answer
        save_database()
        await update.message.reply_text(f"'{question}' sorusuna artık '{answer}' diyeceğim.")
    else:
        user_id = update.message.from_user.id
        pending_questions[user_id] = update.message.text.strip().lower()
        await update.message.reply_text("Sadece soruyu yazdınız. Şimdi cevabını yazınız.")

app = ApplicationBuilder().token("BOT_TOKEN").build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ogret", ogret))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot başlıyor...")
load_database()
app.run_polling()
