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

# Global forwarding status
forwarding_status = {'active': False, 'waiting_for_start_message': False, 'start_message': None, 'source_id': None, 'target_id': None}

# Command to set the source channel
def set_source(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Please forward any message from the source channel to set it as the source."
    )
    context.user_data['waiting_for_source'] = True

def set_target(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Please forward any message from the target channel to set it as the target."
    )
    context.user_data['waiting_for_target'] = True

# Handle forwarded messages for source/target setting
def handle_forwarded_message(update: Update, context: CallbackContext):
    if context.user_data.get('waiting_for_source'):
        if update.message.forward_from_chat:
            source_id = update.message.forward_from_chat.id
            channels_collection.update_one(
                {'_id': 'settings'},
                {'$set': {'source': source_id}},
                upsert=True
            )
            update.message.reply_text(f"Source channel set successfully: {source_id}")
            forwarding_status['source_id'] = source_id
        else:
            update.message.reply_text("This message does not appear to be forwarded from a channel.")
        context.user_data['waiting_for_source'] = False

    elif context.user_data.get('waiting_for_target'):
        if update.message.forward_from_chat:
            target_id = update.message.forward_from_chat.id
            channels_collection.update_one(
                {'_id': 'settings'},
                {'$set': {'target': target_id}},
                upsert=True
            )
            update.message.reply_text(f"Target channel set successfully: {target_id}")
            forwarding_status['target_id'] = target_id
        else:
            update.message.reply_text("This message does not appear to be forwarded from a channel.")
        context.user_data['waiting_for_target'] = False

    elif forwarding_status['waiting_for_start_message']:
        settings = channels_collection.find_one({'_id': 'settings'})
        if update.message.forward_from_chat and update.message.forward_from_chat.id == settings.get('source'):
            forwarding_status['start_message'] = update.message.message_id
            forwarding_status['waiting_for_start_message'] = False
            forwarding_status['active'] = True
            update.message.reply_text(
                f"Starting message set. Forwarding messages from message ID {forwarding_status['start_message']}."
            )
        else:
            update.message.reply_text("Please forward a message from the source channel.")

# Command to display current settings
def show_settings(update: Update, context: CallbackContext):
    settings = channels_collection.find_one({'_id': 'settings'})
    if settings:
        source = settings.get('source', 'Not Set')
        target = settings.get('target', 'Not Set')
        update.message.reply_text(f"Source Channel: {source}\nTarget Channel: {target}")
    else:
        update.message.reply_text("Source and target channels are not set.")

# Command to remove source and target channels
def remove_settings(update: Update, context: CallbackContext):
    channels_collection.delete_one({'_id': 'settings'})
    update.message.reply_text("Source and target channels have been removed.")

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
        "Please forward the starting message from the source channel to begin forwarding."
    )
    forwarding_status['waiting_for_start_message'] = True

# Command to stop forwarding
def stop_forward(update: Update, context: CallbackContext):
    global forwarding_status
    if not forwarding_status['active']:
        update.message.reply_text("No forwarding process is active.")
        return

    forwarding_status['active'] = False
    forwarding_status['start_message'] = None
    update.message.reply_text("Forwarding process stopped.")

# Forward messages from the source to the target
def forward_message(update: Update, context: CallbackContext):
    global forwarding_status
    if not forwarding_status['active']:
        return

    settings = channels_collection.find_one({'_id': 'settings'})
    source_id = settings.get('source')
    target_id = settings.get('target')

    # Ensure that we only forward messages from the source channel after the starting message ID
    if update.message.chat.id == source_id:
        # Check if the message is greater than or equal to the starting message ID
        if update.message.message_id >= forwarding_status['start_message']:
            try:
                # Forward the message to the target channel
                context.bot.forward_message(
                    chat_id=target_id,
                    from_chat_id=source_id,
                    message_id=update.message.message_id
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
        "/setsource - Set the source channel.\n"
        "/settarget - Set the target channel.\n"
        "/settings - View current settings.\n"
        "/remove - Remove source and target channels.\n"
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
    dispatcher.add_handler(CommandHandler('settings', show_settings))
    dispatcher.add_handler(CommandHandler('remove', remove_settings))
    dispatcher.add_handler(CommandHandler('forward', start_forward))
    dispatcher.add_handler(CommandHandler('stop', stop_forward))

    # Message handler for forwarded messages
    dispatcher.add_handler(MessageHandler(Filters.forwarded, handle_forwarded_message))

    # Message handler for forwarding messages
    dispatcher.add_handler(MessageHandler(Filters.all, forward_message))

    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
