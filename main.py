from telegram.ext import Updater
import os

from Modules.sign_up import Registration
from Modules.bot_core_module import CHR, gen_invite_links
from Modules.start import start_handler
from logger import logger


if __name__ == "__main__":
    NW = int(os.environ["NUMBER_WORKER"])
    TOKEN = os.environ["Bot-Token"]
    WEBHOOK = os.environ["Webhook"]
    updater = Updater(token=TOKEN, use_context=True, workers=NW)
    dispatcher = updater.dispatcher
    logger.info("Bot started")



    #  gen_invite_links(updater.bot)
    dispatcher.add_handler(start_handler)
    Registration().add_to_dispatcher(dispatcher)
    CHR().add_to_dispatcher(dispatcher)
    if os.environ["mode"] == "prod":
        PORT = int(os.environ.get('PORT', '8443'))
        logger.info(PORT)
        updater.start_webhook(listen="0.0.0.0",
                              port=int(PORT),
                              url_path=TOKEN)
        updater.bot.set_webhook(WEBHOOK + TOKEN)
    else:
        updater.start_polling()
    updater.idle()
