from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from keyboards import START_KB


def start(update: Update, context: CallbackContext):
    start_dia = "Hallo {}!\nSuper, dass du mithelfen willst.\nZum Anmelden klicke auf Anmelden"
    name = update.effective_user.full_name
    chat_id = update.effective_chat.id
    context.bot.send_message(chat_id, start_dia.format(name), reply_markup=START_KB)


start_handler = CommandHandler("start", start)
