import time
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from pymongo import MongoClient

# Bot Token and MongoDB Configuration
BOT_TOKEN = '7707728265:AAGbMuvnLudGHRAn1w_P4jn9pfJkxmV0LDA'
MONGO_URI = 'mongodb+srv://Cenzo:Cenzo123@cenzo.azbk1.mongodb.net/'  # Replace with your MongoDB connection string
DB_NAME = 'telegram_bot'
COLLECTION_NAME = 'channels'

# MongoDB Setup
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
channels_collection = db[COLLECTION_NAME]

# Global state to manage forwarding process
forwarding_status = {'active': False}

# Command to set the source channel
def set_source(update: Update, context: CallbackContext):
    if update.message.forward_from_chat:
        source_id = update.message.forward_from_chat.id
        channels_collection.update_one(
            {'_id': 'settings'},
            {'$set': {'source': source_id}},
            upsert=True
        )
        update.message.reply_text(f"Source channel set successfully: {source_id}")
    else:
        update.message.reply_text("Please forward a message from the source channel to set it.")

# Command to set the target channel
def set_target(update: Update, context: CallbackContext):
    if update.message.forward_from_chat:
        target_id = update.message.forward_from_chat.id
        channels_collection.update_one(
            {'_id': 'settings'},
            {'$set': {'target': target_id}},
            upsert=True
        )
        update.message.reply_text(f"Target channel set successfully: {target_id}")
    else:
        update.message.reply_text("Please forward a message from the target channel to set it.")

# Command to start forwarding
def start_forward(update: Update, context: CallbackContext):
    global forwarding_status
    settings = channels_collection.find_one({'_id': 'settings'})

    if not settings or not settings.get('source') or not settings.get('target'):
        update.message.reply_text("Source or target channel is not set. Use /setsource and /settarget first.")
        return

    if forwarding_status['active']:
        update.message.reply_text("Forwarding is already active.")
        return

    update.message.reply_text(
        "Forwarding started! Please forward the starting message from the source channel."
    )
    forwarding_status['active'] = True
    forwarding_status['start_message'] = None

# Command to stop forwarding
def stop_forward(update: Update, context: CallbackContext):
    global forwarding_status
    if not forwarding_status['active']:
        update.message.reply_text("No forwarding process is active.")
        return

    forwarding_status['active'] = False
    update.message.reply_text("Forwarding process stopped.")

# Forward messages from the source to the target
def forward_message(update: Update, context: CallbackContext):
    global forwarding_status
    if not forwarding_status['active']:
        return

    settings = channels_collection.find_one({'_id': 'settings'})
    source_id = settings.get('source')
    target_id = settings.get('target')

    if not forwarding_status['start_message']:
        # Set the starting message
        if update.message.chat.id == source_id:
            forwarding_status['start_message'] = update.message.message_id
            update.message.reply_text(
                f"Starting message set. Forwarding messages from message ID {forwarding_status['start_message']}."
            )
        return

    if update.message.chat.id == source_id:
        try:
            # Forward the message to the target channel
            context.bot.forward_message(
                chat_id=target_id,
                from_chat_id=source_id,
                message_id=update.message.message_id
            )

            # Display progress
            current_msg_id = update.message.message_id
            total_msgs = current_msg_id - forwarding_status['start_message'] + 1
            progress = int((current_msg_id - forwarding_status['start_message'] + 1) / total_msgs * 100)
            estimated_time = total_msgs * 2  # Assuming 2 seconds per message

            update.message.reply_text(
                f"Forwarding progress: {progress}%\n"
                f"Estimated time remaining: {estimated_time} seconds."
            )

            time.sleep(2)  # Delay to avoid hitting Telegram rate limits
        except Exception as e:
            update.message.reply_text(f"Error forwarding message: {e}")
            forwarding_status['active'] = False

# Start command
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Welcome to the Forwarding Bot!\n"
        "Commands:\n"
        "/setsource - Set the source channel by forwarding a message.\n"
        "/settarget - Set the target channel by forwarding a message.\n"
        "/forward - Start the forwarding process.\n"
        "/stop - Stop the forwarding process."
    )

# Main function
def main():
    updater = Updater(token=BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('setsource', set_source))
    dispatcher.add_handler(CommandHandler('settarget', set_target))
    dispatcher.add_handler(CommandHandler('forward', start_forward))
    dispatcher.add_handler(CommandHandler('stop', stop_forward))

    # Message handler to forward messages
    dispatcher.add_handler(MessageHandler(Filters.all, forward_message))

    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
    
