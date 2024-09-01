from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import logging
import random
import re
from datetime import datetime, timedelta
import pytz

# Initialize the scheduler
scheduler = BackgroundScheduler(timezone=pytz.utc)
scheduler.start()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define a dictionary to hold reminders
reminders = {}

# Conversation states
REMINDER_NAME, REMINDER_TIME, REMINDER_REPEAT = range(3)

# Start command handler
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        f"Hey welcome {update.message.from_user.username} to the bot! Type /setrem to set a reminder."
    )

# Set reminder command handler
def setrem(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Please enter the reminder name:')
    return REMINDER_NAME

# Save reminder name and ask for time
def save_reminder_name(update: Update, context: CallbackContext) -> int:
    context.user_data['reminder_name'] = update.message.text
    update.message.reply_text('When should I remind you? (format: YYYY-MM-DD HH:MM)')
    return REMINDER_TIME

# Save reminder time and ask for repeat option
def save_reminder_time(update: Update, context: CallbackContext) -> int:
    try:
        reminder_time = datetime.strptime(update.message.text, "%Y-%m-%d %H:%M")
        context.user_data['reminder_time'] = reminder_time
        update.message.reply_text('How often should I remind you? (daily, weekly, none)')
        return REMINDER_REPEAT
    except ValueError:
        update.message.reply_text('Invalid time format. Please enter the time in the format: YYYY-MM-DD HH:MM')
        return REMINDER_TIME

# Save reminder repeat option and confirm the reminder
def save_reminder(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    reminder_name = context.user_data['reminder_name']
    reminder_time = context.user_data['reminder_time']
    reminder_repeat = update.message.text.lower()
    
    reminder_id = generate_unique_id()

    if user_id not in reminders:
        reminders[user_id] = []

    reminder = {
        'id': reminder_id,
        'name': reminder_name,
        'time': reminder_time,
        'repeat': reminder_repeat
    }

    reminders[user_id].append(reminder)

    # Schedule the reminder
    schedule_reminder(user_id, reminder)

    update.message.reply_text(f"Reminder set! ID: `{reminder_id}`", parse_mode=ParseMode.MARKDOWN_V2)

    return ConversationHandler.END

# Helper function to schedule a reminder
def schedule_reminder(user_id: int, reminder: dict) -> None:
    def job_function():
        context.bot.send_message(chat_id=user_id, text=f"Reminder: {reminder['name']}")
        logger.info(f"Reminder sent to user {user_id}: {reminder['name']}")

        if reminder['repeat'] == 'daily':
            next_run = reminder['time'] + timedelta(days=1)
            reminder['time'] = next_run
            schedule_reminder(user_id, reminder)
        elif reminder['repeat'] == 'weekly':
            next_run = reminder['time'] + timedelta(weeks=1)
            reminder['time'] = next_run
            schedule_reminder(user_id, reminder)

    run_date = reminder['time'].astimezone(pytz.utc)
    scheduler.add_job(job_function, DateTrigger(run_date=run_date))
    logger.info(f"Scheduled reminder for user {user_id}: {reminder['name']} at {run_date}")

# Show all reminders
def allrem(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id in reminders and reminders[user_id]:
        all_reminders = "\n\n".join([
            f"*Name:* {escape_markdown(rem['name'], version=2)}\n"
            f"*Timing:* {rem['time'].strftime('%Y-%m-%d %H:%M')}\n"
            f"*ID:* `{rem['id']}`"
            for rem in reminders[user_id]
        ])
        update.message.reply_text(f"Your reminders:\n{all_reminders}", parse_mode=ParseMode.MARKDOWN_V2)
    else:
        update.message.reply_text("You have no reminders set.")

# Delete reminder command handler
def delrem(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    reminder_id = context.args[0]

    if user_id in reminders:
        reminders[user_id] = [rem for rem in reminders[user_id] if rem['id'] != reminder_id]
        update.message.reply_text(f"Reminder with ID `{reminder_id}` deleted.", parse_mode=ParseMode.MARKDOWN_V2)
    else:
        update.message.reply_text("No reminders found to delete.")

# Generate unique ID for each reminder
def generate_unique_id() -> str:
    return str(random.randint(10000, 99999))

# Helper function to escape special characters for Markdown V2
def escape_markdown(text: str, version: int = 2) -> str:
    """
    Escape Telegram markdown special characters.
    :param text: Text to escape
    :param version: Telegram markdown version (1 or 2)
    :return: Escaped text
    """
    if version == 1:
        escape_chars = r'_*[]()~`>#+-=|{}.!'
    elif version == 2:
        escape_chars = r'_*[]()~`>#+-=|{}.!'
    else:
        raise ValueError('Invalid Markdown version specified. Only version 1 and 2 are supported.')

    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def main() -> None:
    updater = Updater("7374426816:AAHD35aacg_OLd7U9KyNBckoZysG_IFJ4BY")

    dp = updater.dispatcher

    # Add conversation handler with the states REMINDER_NAME, REMINDER_TIME, REMINDER_REPEAT
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('setrem', setrem)],
        states={
            REMINDER_NAME: [MessageHandler(Filters.text & ~Filters.command, save_reminder_name)],
            REMINDER_TIME: [MessageHandler(Filters.text & ~Filters.command, save_reminder_time)],
            REMINDER_REPEAT: [MessageHandler(Filters.text & ~Filters.command, save_reminder)],
        },
        fallbacks=[]
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("allrem", allrem))
    dp.add_handler(CommandHandler("delrem", delrem, pass_args=True))

    # Start the Bot
    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
          
