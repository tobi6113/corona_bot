import os

import psycopg2
from telegram import Message, Update
from telegram.ext import ConversationHandler, MessageHandler, Filters, CommandHandler, Dispatcher, \
    CallbackQueryHandler, run_async

from geocoder import get_adr, get_full_adr
from keyboards import START_KB, ANM_KB, CHANNEL_ID
from logger import logger

try:
    PUBLISH_LINK = int(os.environ["PL"])
except KeyError:
    PUBLISH_LINK = 0
    logger.exception("Environment variable PL not set, using default 0")
except Exception as exp:
    PUBLISH_LINK = 0
    logger.exception(exp)
    logger.critical("Environment variable PL isn t an integer")

USER_ROWS = ["user_id", "name", "strasse", "nummer", "ort", "plz", "chat_id", "active",
             "admin", "tel"]


PSCON = psycopg2.connect(os.environ["DATABASE_URL"])


def init_db():
    with PSCON as con:
        with con.cursor() as c:
            c.execute("""create table if not exists benutzer ({} integer primary key,
                          {} text,  
                          {} text,
                          {} text,
                          {} text, 
                          {} text, 
                          {} bigint, 
                          {} integer, 
                          {} integer,
                          {} text)""".format(*USER_ROWS))
            logger.info("Database for Module %s ready", __name__)


def db_get_user_data(user_id):
    try:
        with PSCON as con:
            with con.cursor() as c:
                sql_str = "Select * FROM benutzer where user_id=%s"
                c.execute(sql_str, (user_id,))
                ls = c.fetchone()
                usr = dict(zip(USER_ROWS, ls))
                logger.info("User-data of user-id %s fetched from database", user_id)
                return usr
    except Exception as e:
        print(e)
        logger.warning("unregistered user-id %s tried to get data", user_id)
        return dict.fromkeys(USER_ROWS, "")


@run_async
def db_update_user_data(user_id, name, strasse, nummer, ort, plz, tel):
    try:
        with PSCON as con:
            with con.cursor() as c:
                sql_str = """   UPDATE benutzer set     name = %s,
                                                        strasse = %s,
                                                        nummer = %s,
                                                        plz = %s,
                                                        tel = %s,
                                                        ort = %s
                                                where   user_id = %s"""
                c.execute(sql_str, (name, strasse, nummer, plz, tel, ort, user_id))
                logger.info("Data send to Database")
    except Exception as e:
        print(e)
        logger.warning("Cant write on database")


@run_async
def db_create_new_user(user_id, name, strasse, nummer, plz, chat_id, tel, ort, active=1):
    curr_usr = [chat_id, name, user_id]
    logger.info("User %s tries to register", curr_usr)
    try:
        with PSCON as con:
            with con.cursor() as c:
                print("here")
                sql_str = """   insert into benutzer(user_id, chat_id, name, strasse, nummer, plz, active, tel, ort) 
                                values(%s,%s,%s,%s,%s,%s,%s,%s,%s) """
                c.execute(sql_str, (user_id, chat_id, name, strasse, nummer, plz, active, tel, ort))
                logger.info("User %s add to database", curr_usr)
    except Exception as e:
        logger.warning("%s", e)
        logger.info("User %s already exists", curr_usr)


@run_async
def anmelden(update, context):
    update.message.delete()
    uid = update.effective_user.id
    ud: dict = context.user_data
    ud.update(db_get_user_data(uid))
    ud["chat_id"] = update.effective_chat.id
    name = ud["name"]
    if name == "":
        name = ud["name"] = update.effective_user.full_name
    ud["user_id"] = uid
    ud["last_question"]: Message = update.message.reply_text("Dein Name laute:\n{}\nZum Aktualisieren"
                                                             " sende bitte deinen Namen".format(name),
                                                             reply_markup=ANM_KB)
    return 1


@run_async
def get_name(update, context):
    update.message.delete()
    ud: dict = context.user_data
    name = ud["name"] = update.effective_message.text
    ud["last_question"].delete()
    ud["last_question"]: Message = update.message.reply_text("Dein Name laute:\n{}\nZum Aktualisieren"
                                                             " sende bitte deinen Namen".format(name),
                                                             reply_markup=ANM_KB)
    return


@run_async
def to_step_2(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    if data == "1":
        ud: dict = context.user_data
        lq: Message = ud["last_question"]

        adresse = str(ud["strasse"] or " ") + " " + ud["nummer"] + ", " + ud["plz"]
        ud["last_question"] = lq.edit_text(text="Deine Adresse lautet:\n{}\nZum Aktualiseren schreibe "
                                                "deine Adresse (Strasse, Nummer, PLZ)\n"
                                                "oder wähle deine Adresse über 📎 ➡ Standort aus ".format(adresse),
                                           reply_markup=ANM_KB)
        return 2
    else:
        return clean_up(query, context)


@run_async
def adr_text(update, context):
    update.message.delete()
    ud: dict = context.user_data
    message = update.effective_message.text
    google_res = get_full_adr(message)
    ud["plz"] = plz = google_res[-1]
    ud["strasse"] = strasse = google_res[0]
    ud["nummer"] = nummer = google_res[1]
    ud["ort"] = ort = google_res[-2]
    logger.info("Get %s, %s, %s, %s as adress from %s", strasse, nummer, ort, plz, ud["user_id"])
    ud["last_question"].delete()
    adresse = strasse + " " + nummer + ", " + plz + " " + ort
    ud["last_question"]: Message = update.message.reply_text("Deine Adresse lautet:\n{}\nZum Aktualiseren schreibe "
                                                             "deine Adresse (Strasse, Nummer, PLZ)\n"
                                                             "oder wähle"
                                                             " deine Adresse über 📎 ➡ Standort aus ".format(adresse),
                                                             reply_markup=ANM_KB)
    return


@run_async
def adr_loc(update: Update, context):
    update.message.delete()
    ud: dict = context.user_data
    loc = update.message.location
    strasse, nummer, ort, plz = get_adr(loc["latitude"], loc["longitude"])
    ud["plz"] = plz
    ud["strasse"] = strasse
    ud["nummer"] = nummer
    ud["ort"] = ort
    adresse = ud["strasse"] + " " + ud["nummer"] + ", " + ud["plz"] + " " + ort
    ud["last_question"].delete()
    ud["last_question"]: Message = update.message.reply_text("Deine Adresse lautet:\n{}\nZum Aktualiseren schreibe "
                                                             "deine Adresse (Strasse, Nummer, PLZ)\n"
                                                             "oder wähle deine Adresse "
                                                             "über 📎 ➡ Standort aus ".format(adresse),
                                                             reply_markup=ANM_KB)
    return


@run_async
def to_step_3(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    if data == "1":
        ud: dict = context.user_data
        lq: Message = ud["last_question"]
        tel = ud["tel"]
        ud["last_question"] = lq.edit_text(text="Deine Telefonnummer lautet:\n{}\nZum Aktualiseren schreibe "
                                                "deine Telefonnummer".format(tel), reply_markup=ANM_KB)
        return 3
    else:
        return clean_up(query, context)


@run_async
def get_tel(update, context):
    update.message.delete()
    ud: dict = context.user_data
    ud["tel"] = tel = update.effective_message.text
    ud["last_question"].delete()
    ud["last_question"]: Message = update.message.reply_text(
        "Deine Telefonnummer lautet:\n{}\nZum Aktualiseren schreibe "
        "deine Telefonnummer".format(tel),
        reply_markup=ANM_KB)
    return


@run_async
def finish(update, context):
    from Modules.bot_core_module import route_to_channel
    ud: dict = context.user_data
    query = update.callback_query
    if ud["active"] == 1:
        db_update_user_data(ud["user_id"], ud["name"], ud["strasse"], ud["nummer"], ud["ort"], ud["plz"], ud["tel"])
    else:
        db_create_new_user(ud["user_id"], ud["name"], ud["strasse"], ud["nummer"], ud["plz"],
                           ud["chat_id"], ud["tel"], ud["ort"])
    query.answer("Daten erfolgreich gespeichert")
    if PUBLISH_LINK:
        ch_id = route_to_channel(ud["plz"])
        invite_link = context.bot.get_chat(ch_id).invite_link
        title = context.bot.get_chat(ch_id).title
        if ch_id != CHANNEL_ID:
            update.effective_message.reply_text("Dein lokaler Kanal (basierend auf deiner Adresse) heißt {}.\n"
                                                "Klicke auf den folgenden Link um ihm beizutreten:\n"
                                                "{}".format(title, invite_link))
    else:
        update.effective_message.reply_text("Deine Anmeldung war erfolgreich, bitte kontaktiere deinen lokalen"
                                            " Ansprechpartner, um in den Kanal hinzugefügt zu werden.")
    clean_up(query, context)
    return -1


def clean_up(update, context):
    ud: dict = context.user_data
    ud["last_question"].delete()
    [ud.pop(i) for i in USER_ROWS]
    ud.pop("last_question")
    update.message.reply_text("Willkommen im Hauptmenü", reply_markup=START_KB)
    return -1


anmeldung = ConversationHandler(entry_points=[MessageHandler(Filters.regex("Anmelden"), anmelden)],
                                states={
                                    1: [CallbackQueryHandler(to_step_2), MessageHandler(Filters.text, get_name)],
                                    2: [CallbackQueryHandler(to_step_3), MessageHandler(Filters.text, adr_text),
                                        MessageHandler(Filters.location, adr_loc)],
                                    3: [CallbackQueryHandler(finish), MessageHandler(Filters.text, get_tel)]
                                },
                                fallbacks=[CommandHandler("cancel", clean_up)]
                                )


class Registration:
    def __init__(self):
        init_db()
        self.handlers = [anmeldung, ]

    def add_to_dispatcher(self, dispatcher: Dispatcher):
        for handler in self.handlers:
            dispatcher.add_handler(handler)
