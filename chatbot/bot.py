from telegram import (
    Update,
    InlineQueryResultArticle, InputTextMessageContent,
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    InlineQueryHandler, MessageHandler, filters,
)

# Connect to our data (TODO: use an API-module)
import nlpcloud
from pandas import read_csv

Party = read_csv('../data/Party.csv')

Vote = read_csv('../data/Vote.csv')
Vote.dropna(subset=['BusinessAuthor'], inplace=True)

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

# Get votes by a politician
async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    qry = ' '.join(context.args).lower()
    if not qry:
        print("No query")
        return
    print('Vote', qry)
    votes = Vote[Vote['BusinessAuthor'].str.lower().str.contains(qry)]
    if votes.count()[0] > 0:
        t = '3 / ' + str(votes.count()[0])
        for index, row in votes.sample(n=3).iterrows():
            t = t + '\n'
            t = t + '- ' + row['BusinessTitle']
            if row['SessionName']:
                t = t + ' (' + row['SessionName'] + ')'
    else:
        t = 'No results'
    await update.message.reply_text(t)


# Say something smart
async def parl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    qry = ' '.join(context.args)
    if not qry:
        print("No query")
        return
    print(qry)
    txt = nlpcli.chatbot(qry,
        context="""Dies ist eine Diskussion über Parlamentswahlen basierend auf den Daten von parlament.ch"""
    )['response']
    await update.message.reply_text(txt)

# Say something smarter
async def inline_parl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    qry = update.inline_query.query
    if not qry:
        print("Blank query")
        return
    print(qry)
    txt = nlpcli.chatbot(qry,
        context="""Dies ist eine Diskussion über Parlamentswahlen basierend auf den Daten von parlament.ch"""
    )['response']
    results = [
        InlineQueryResultArticle(
            id='parl',
            title='PARL',
            description=txt,
            input_message_content=InputTextMessageContent(f'/parl {query}')
        )
    ]
    await context.bot.answer_inline_query(update.inline_query.id, results)

# Be confused
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

# Set up the app
app = ApplicationBuilder().token(TELEGRAM_KEY).build()

# Connect to NLP cloud
nlpcli = nlpcloud.Client("finetuned-gpt-neox-20b", API_KEY, gpu=True)

if __name__ == '__main__':

    # Add bot commands
    app.add_handler(CommandHandler("hello", hello))
    app.add_handler(CommandHandler("party", party))
    app.add_handler(CommandHandler("parl",  parl))
    app.add_handler(CommandHandler("vote",  vote))
    
    # Add inline support
    app.add_handler(InlineQueryHandler(inline_parl))
    
    # Finally add 404
    app.add_handler(MessageHandler(filters.COMMAND, unknown))
    
    # Start the loop
    print("Bot operational. Press Ctrl-C to exit ..")
    app.run_polling()

app.run_polling()
