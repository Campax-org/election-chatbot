from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Connect to our data (TODO: use an API-module)
import read_csv from pandas
Party = pd.read_csv('../data/Party.csv')

# Quick test routine
async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')

# Return a random party from our data
async def party(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    txt = Party.sample(n=1).get('PartyName').values[0]
    await update.message.reply_text(txt)

# This is a private token for our bot (TODO: store in environment!)
app = ApplicationBuilder().token("6146055236:AAG87qRlGXkXLJkVeDagYJcvlg9CyPZSqDE").build()

# Add the comamnds
app.add_handler(CommandHandler("hello", hello))
app.add_handler(CommandHandler("party", party))

# Start the loop
app.run_polling()
print("Bot operational. Press Ctrl-C to exit ..")
