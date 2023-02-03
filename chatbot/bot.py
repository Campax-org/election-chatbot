from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Connect to our data (TODO: use an API-module)
import nlpcloud
from pandas import read_csv
Party = read_csv('../data/Party.csv')

# Private tokens for our demo (TODO: store in environment!)
API_KEY = "4329be765d81cb0c809270d9911cb3798c541fd5"
TELEGRAM_KEY = "6146055236:AAG87qRlGXkXLJkVeDagYJcvlg9CyPZSqDE"
    
# Quick test routine
async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')

# Return a random party from our data
async def party(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    txt = Party.sample(n=1).get('PartyName').values[0]
    await update.message.reply_text(txt)

# Say something smart
async def parl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    qry = ' '.join(context.args)
    print(qry)
    txt = nlpcli.chatbot(qry,
        context="""Dies ist eine Diskussion über Parlamentswahlen basierend auf den Daten von parlament.ch"""
    )['response']
    await update.message.reply_text(txt)

# Set up the app
app = ApplicationBuilder().token(TELEGRAM_KEY).build()

# Connect to NLP cloud
nlpcli = nlpcloud.Client("finetuned-gpt-neox-20b", API_KEY, gpu=True)

# Add the comamnds
app.add_handler(CommandHandler("hello", hello))
app.add_handler(CommandHandler("party", party))
app.add_handler(CommandHandler("parl", parl))

# Start the loop
print("Bot operational. Press Ctrl-C to exit ..")
app.run_polling()
