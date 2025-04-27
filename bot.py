import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Veritabanını oku
qa_database = {}
if os.path.exists("qa_database.json"):
    with open("qa_database.json", "r", encoding="utf-8") as f:
        qa_database = json.load(f)

# /start komutu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Merhaba. Lütfen bir soru sorabilirsiniz.")

# Gelen mesajı işle
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    response = qa_database.get(user_message, None)

    if response:
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("Bilmiyorum.")
        save_new_question(user_message)

# Yeni soruları kaydet
def save_new_question(question):
    filename = "new_questions.json"
    try:
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []

        if question not in data:
            data.append(question)
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Yeni soru kaydederken hata oluştu: {e}")

# Botu başlat
app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.run_polling()
