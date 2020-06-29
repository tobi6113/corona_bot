import os
import time
from functools import wraps
from telegram import Update, Message
from telegram.error import BadRequest
from telegram.ext import ConversationHandler, MessageHandler, Filters, CallbackQueryHandler, CommandHandler, \
    Dispatcher, CallbackContext, run_async

from Modules.sign_up import db_get_user_data, PSCON
from Modules.channel_callbackqueryhandler import ChannelCallbackQueryHandler
from geocoder import get_adr, get_full_adr
from keyboards import EKH_KB, START_KB, ANM_KB, CHK_KB, CHANNEL_ID, PBL_KB, PRV_KB_S
from keyboards import PRV_KB_H, PRV_KB_S_0, PRV_KB_H_0, PRV_KB_H_1
from logger import logger

EKH_ROWS = ["id", "h_id", "h_msg_id", "s_id", "s_msg_id", "s_name", "s_strasse", "s_nummer", "s_plz", "s_ort", "s_tel",
            "ch_id", "ch_msg_id", "file_id", "time"]

JOB_ARCH_ROW = ["id", "h_id", "h_msg_id", "s_id", "s_msg_id", "s_name", "s_strasse", "s_nummer", "s_plz", "s_ort",
                "s_tel", "ch_id", "ch_msg_id", "file_id", "posted", "done"]

PLZ_KV_ROWS = ["plz", "ort", "kreis", "land"]

KV_CH_ID_ROWS = ["kv, ch_id"]

PLZ_CH_ID_DICT = {}

try:
    PRIVACY = int(os.environ["PRIVACY"])
except Exception as e:
    PRIVACY = 2
    logger.exception(e)
    logger.warning("Use PRIVACY = 2 (maximal protection) by default")


def restricted_to_reg(func):
    """
    Wrapper, which checks if a user is registered, if yes the wrapped function func will be called, 
    if not the user will receive a warning.
    :param func: callable
    :return: Return value of the wrapped function
    """
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        res = db_query_exist(user_id)
        if res:
            return func(update, context, *args, **kwargs)
        else:
            logger.warning("Unauthorized access denied for {}.".format(user_id))
            if update.callback_query:
                update.callback_query.answer("Bitte zu erst anmelden!")
            else:
                update.effective_message.delete()
                update.message.reply_text("Bitte zuerst anmelden!")
            return

    return wrapped


def only_one(func):
    """
        Wrapper, which checks if a job is open, if yes the wrapped function func will be called, 
        if not the user will receive a warning.
        :param func: callable
        :return: Return value of the wrapped function
        """
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        ch_id = update.effective_chat.id
        ch_msg_id = update.effective_message.message_id
        res = db_get_job_data(ch_id, ch_msg_id)
        if res["h_id"]:
            update.callback_query.answer("Es kann nur ein Einkäufer eingetragen sein!")
            return
        else:
            return func(update, context, *args, **kwargs)

    return wrapped


def pbl_only(func):
    """
    Wrapper, which checks if a update comes from a channel, if yes the wrapped function func will be called, 
    if not nothing happens.
    :param func: callable
    :return: Return value of the wrapped function
    """
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        if update.effective_chat.type == "channel":
            return func(update, context, *args, **kwargs)
        else:
            return

    return wrapped


def init_db():
    """
    Initializes the database tabel, needed in this module.
    """
    with PSCON as con:
        with con.cursor() as c:
            # Create table entry_point
            c.execute(("create table if not exists entry_point ({} serial primary key,"  # id
                       "                                  {} bigint,"  # h_id
                       "                                  {} bigint,"  # h_msg_id
                       "                                  {} bigint,"  # s_id
                       "                                  {} bigint,"  # s_msg_id
                       "                                  {} text,"  # s_name
                       "                                  {} text,"  # s_strasse
                       "                                  {} text,"  # s_nummer
                       "{} text,"  # s_plz
                       "{} text,"  # s_ort
                       "{} text,"  # s_tel
                       "{} bigint,"  # ch_id
                       "{} bigint,"  # ch_msg_id
                       "{} text,"  # file_id
                       "{} real"  # time
                       ")").format(*EKH_ROWS))
            # Create table job_archive
            c.execute(("create table if not exists job_archive ({} serial primary key,"  # id
                       "                                  {} bigint,"  # h_id
                       "                                  {} bigint,"  # h_msg_id
                       "                                  {} bigint,"  # s_id
                       "                                  {} bigint,"  # s_msg_id
                       "                                  {} text,"  # s_name
                       "                                  {} text,"  # s_strasse
                       "                                  {} text,"  # s_nummer
                       "{} text,"  # s_plz
                       "{} text,"  # s_ort
                       "{} text,"  # s_tel
                       "{} bigint,"  # ch_id
                       "{} bigint,"  # ch_msg_id
                       "{} text,"  # file_id
                       "{} real,"  # posted
                       "{} real"  # done 
                       ")").format(*JOB_ARCH_ROW))
            c.execute(("create table if not exists plz_kv ("
                       "plz text, "
                       "ort text,"
                       "kreis text,"
                       "land text)"))
            c.execute(("create table if not exists kv_ch_id_hessen ("
                       "kv text,"
                       "ch_id bigint)"))
            c.execute("create unique index if not exists kv_ch_id_ch_id_uindex on kv_ch_id_hessen(ch_id)")
            logger.info("Database for Module %s ready", __name__)


def db_get_job_data(ch_id, ch_msg_id):
    """
    Reads the job details by its channel id and message id from entry_point table.
    :rtype: dict
    :param int ch_id: Channel ID of the channel the job was posted in
    :param int ch_msg_id: ID of the message the job was posted in
    :return: Database row as a dictionary, if no row matches query all values are None 
    """
    try:
        with PSCON as con:
            with con.cursor() as c:
                sql_str = """Select * FROM entry_point where ch_id=%s and ch_msg_id=%s"""
                c.execute(sql_str, (ch_id, ch_msg_id))
                ls = c.fetchone()
                usr = dict(zip(EKH_ROWS, ls))
                logger.info("Jpb-data of job-id %s fetched from database", usr["id"])
                return usr
    except Exception as e:
        print(e)
        logger.warning("unregistered user-id %s tried to get data", ch_id)
        return dict.fromkeys(EKH_ROWS)


def db_query_exist(user_id: int) -> bool:
    """
    Checks if a user is in the database by its id
    :param user_id: User ID
    :return: True if exists 
    """
    try:
        with PSCON as con:
            with con.cursor() as c:
                sql_str = "Select EXISTS(SELECT 1 FROM benutzer where user_id=%s)"
                c.execute(sql_str, (user_id,))
                ret = c.fetchone()[0]
                logger.info("user %s known", user_id)
                return ret
    except Exception as e:
        print(e)
        logger.warning("Cant read on database")
        con.close()
    return False


def db_get_job_data_from_h(h_id: int, h_msg_id: int) -> dict:
    """
    Reads the job details by its helper id (user id of helper) and message id in the helpers chat from entry_point table.
    :param h_id: user id of the helper
    :param h_msg_id: message id in the helpers chat
    :return: Database row as a dictionary, if no row matches query all values are None 
    """
    try:
        with PSCON as con:
            with con.cursor() as c:
                sql_str = """Select * FROM entry_point where h_id=%s and h_msg_id=%s"""
                c.execute(sql_str, (h_id, h_msg_id))
                ls = c.fetchone()
                usr = dict(zip(EKH_ROWS, ls))
                logger.info("Jpb-data of job-id %s fetched from database", usr["h_id"])
                return usr
    except Exception as e:
        print(e)
        logger.warning("unregistered user-id %s tried to get data", h_id)
        return dict.fromkeys(EKH_ROWS)


def db_get_job_data_from_s(s_id: int, s_msg_id: int) -> dict:
    """
    Reads the job details by its requester id (user id of requester) and
    message id in the requesters chat from entry_point table.
    :param s_id: user id of the requester
    :param s_msg_id: message id in the requester chat
    :return: Database row as a dictionary, if no row matches query all values are None 
    """
    try:
        with PSCON as con:
            with con.cursor() as c:
                sql_str = """Select * FROM entry_point where s_id=%s and s_msg_id=%s"""
                c.execute(sql_str, (s_id, s_msg_id))
                ls = c.fetchone()
                usr = dict(zip(EKH_ROWS, ls))
                logger.info("Jpb-data of job-id %s fetched from database", usr["h_id"])
                return usr
    except Exception as e:
        print(e)
        logger.warning("unregistered user-id %s tried to get data", s_id)
        return dict.fromkeys(EKH_ROWS)


@run_async
def db_update_h_infos(ch_id: int, ch_msg_id: int, h_id: [int, None], h_msg_id: [int, None]) -> None:
    """
    Updates the helpers id and message id into database after taking the job
    :param ch_id: Channel id of the public channel the job is posted in
    :param ch_msg_id: Message id of the job in the public channel
    :param h_id: user id of the helper, who took the job if None the helper gave the job back
    :param h_msg_id: message id of the jobs copy in the helpers chat if None the helper gave the job back
    """
    try:
        with PSCON as con:
            with con.cursor() as c:
                sql_str = "Update entry_point set h_id = %s, h_msg_id = %s where ch_id = %s and ch_msg_id = %s"
                c.execute(sql_str, (h_id, h_msg_id, ch_id, ch_msg_id))
                logger.info("Job-data of ch_msg_id %s updated", ch_msg_id)
    except Exception as e:
        print(e)
        logger.warning("unregistered user-id %s tried to get data", ch_id)


@restricted_to_reg
def entry_point(update: Update, context: CallbackContext) -> [int, None]:
    """
    Entry point of the entry_point conversation, accessible for registered users only
    :param update: Incoming telegram update
    :param context: Context data of the incoming telegram update
    :return: key of the next conversation step
    """
    update.message.delete()
    ud: dict = context.user_data
    ud.update(dict.fromkeys(EKH_ROWS))
    ud["s_id"] = update.effective_user.id
    ud["last_question"]: Message = update.message.reply_text("Benötigst du einen Einkaufsheld für dich "
                                                             "oder jemand anderen?",
                                                             reply_markup=EKH_KB)
    return 1


@run_async
def help_router(update: Update, context: CallbackContext) -> [int]:
    """
    First step of the conversation, routes the conversation depending who needs help
    :param update: Incoming telegram update
    :param context: Context data of the incoming telegram update
    :return: 5 if the user who started the conversation needs help, 2 if others
    """
    ud: dict = context.user_data
    query = update.callback_query
    query.answer()
    data = query.data
    if data == "1":  # Sender braucht Hilfe
        qr = db_get_user_data(update.effective_user.id)
        ud["s_name"] = qr["name"]
        ud["s_strasse"] = qr["strasse"]
        ud["s_nummer"] = qr["nummer"]
        ud["s_plz"] = qr["plz"]
        ud["s_tel"] = qr["tel"]
        ud["s_ort"] = qr["ort"]
        lq: Message = ud["last_question"]
        ud["last_question"] = lq.edit_text(text="Falls du willst, kannst du eine Einkaufsliste hinzufügen,"
                                                " indem du ein Bild von ihr sendest.", reply_markup=ANM_KB)
        return 5
    else:  # Jemand anderes braucht Hilfe
        ud["last_question"].edit_text("Bitte sende den Namen, der Person, die Hilfe benötigt und drücke danach auf"
                                      " weiter.\nFalls du dich vertippt hast, sende den Namen einfach erneut.")
        return 2


@run_async
def get_name(update: Update, context: CallbackContext) -> None:
    """
    Reads the requester name from incoming message text.
    Stores the name in context.user_data["s_name"]
    :param update: Incoming Telegram Update
    :param context: Context data of the incoming telegram update
    :return: None to stay in the same conversation state
    """
    update.message.delete()
    ud: dict = context.user_data
    name = ud["s_name"] = update.effective_message.text
    ud["last_question"].delete()
    ud["last_question"]: Message = update.message.reply_text("Der Name laute:\n{}\nZum Aktualisieren"
                                                             " bitte erneut senden".format(name),
                                                             reply_markup=ANM_KB)
    return


def clean_up(update: Update, context: CallbackContext) -> int:
    """
    Cleans up the chat with the user and frees RAM by popping the context.user_data dict.
    Send the user back to main menu.
    :param update: Incoming telegram update
    :param context: Context data of the incoming telegram update
    :return: -1 (End of conversation)
    """
    ud: dict = context.user_data
    ud["last_question"].delete()
    [ud.pop(i) for i in EKH_ROWS]
    ud.pop("last_question")
    update.message.reply_text("Willkommen im Hauptmenü", reply_markup=START_KB)
    return -1


def to_step_3(update: Update, context: CallbackContext) -> int:
    """
    Asks the address of the requester and starts next conversation step.
    callback for CallbackQueryHandler
    :param update: Incoming telegram update
    :param context: Context data of the incoming telegram update
    :return: 3 Next conversation step or -1 cancel
    """
    query = update.callback_query
    query.answer()
    data = query.data
    if data == "1":
        ud: dict = context.user_data
        lq: Message = ud["last_question"]
        ud["last_question"] = lq.edit_text(text="Bitte gib die Adresse des Hilfsbedürfitgen ein\n"
                                                "Format(Strasse, Nummer, PLZ)\n"
                                                "oder wähle die Adresse über 📎 ➡ Standort aus ")
        return 3
    else:
        return clean_up(query, context)


def adr_text(update: Update, context: CallbackContext) -> None:
    """
    Stores the address of the person who needs help in user_data dictionary.
    :param update: Incoming telegram Update
    :param context:  Context data of the incoming telegram update
    :return: None
    """
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
def adr_loc(update: Update, context: CallbackContext) -> None:
    """
    Gets the current address by the GPS coordinates send to the bot by calling googles reverse geocoder
    :param update: Incoming telegram update
    :param context:  Context data of the incoming telegram update
    :return: None
    """
    update.message.delete()
    ud: dict = context.user_data
    loc = update.message.location
    strasse, nummer, ort, plz = get_adr(loc["latitude"], loc["longitude"])
    ud["plz"] = plz
    ud["strasse"] = strasse
    ud["nummer"] = nummer
    ud["ort"] = ort
    adresse = strasse + " " + nummer + ", " + plz + " " + ort
    ud["last_question"].delete()
    ud["last_question"]: Message = update.message.reply_text("Deine Adresse lautet:\n{}\nZum Aktualiseren schreibe "
                                                             "deine Adresse (Strasse, Nummer, PLZ)\n"
                                                             "oder wähle deine Adresse "
                                                             "über 📎 ➡ Standort aus ".format(adresse),
                                                             reply_markup=ANM_KB)
    return


def to_step_4(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    if data == "1":
        ud: dict = context.user_data
        lq: Message = ud["last_question"]
        ud["last_question"] = lq.edit_text(text="Bitte gib die Telefonnummer des Hilfsbedürfitgen ein\n")
        return 4
    else:
        return clean_up(query, context)


def get_tel(update, context):
    update.message.delete()
    ud: dict = context.user_data
    ud["s_tel"] = tel = update.effective_message.text
    ud["last_question"].delete()
    ud["last_question"]: Message = update.message.reply_text(
        "Die Telefonnummer lautet:\n{}\nZum Aktualiseren sende "
        "die Telefonnummer erneut.".format(tel),
        reply_markup=ANM_KB)
    return


def to_step_5(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    if data == "1":
        ud: dict = context.user_data
        lq: Message = ud["last_question"]
        ud["last_question"] = lq.edit_text(text="Falls du willst, kannst du eine Einkaufsliste hinzufügen,"
                                                " indem du ein Bild von ihr sendest.", reply_markup=ANM_KB)
        return 5
    else:
        return clean_up(query, context)


def get_einkaufslist(update, context):
    update.message.delete()
    ud: dict = context.user_data
    photo = update.message.photo[0]
    file_id = photo.file_id
    ud["file_id"] = file_id
    ud["last_question"].delete()
    ud["last_question"]: Message = update.message.reply_photo(photo, caption="Ist diese Einkaufsliste korrekt%s\n"
                                                                             "Falls nein sende einfach das "
                                                                             "richtige Photo.",
                                                              reply_markup=ANM_KB)
    return


def to_step_6(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    if data == "1":
        ud: dict = context.user_data
        lq: Message = ud["last_question"]
        lq.delete()
        ud["auftrag"] = auftrag = gen_auftrag(ud)
        ud["last_question"] = update.effective_message.reply_text(text="Dein Auftrag lautet:\n{}\nWillst "
                                                                       "du ihn veröffentlichen?".format(auftrag),
                                                                  reply_markup=CHK_KB)
        return 6
    else:
        return clean_up(query, context)


@run_async
def db_create_new_job(ud):
    try:
        with PSCON as con:
            with con.cursor() as c:
                sql_str = "insert into entry_point(s_id, s_msg_id, s_name, s_strasse, s_nummer, s_plz, s_ort, s_tel," \
                          " ch_id, ch_msg_id, file_id, time) " \
                          "values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                c.execute(sql_str, (ud["s_id"], ud["s_msg_id"], ud["s_name"], ud["s_strasse"], ud["s_nummer"],
                                    ud["s_plz"], ud["s_ort"], ud["s_tel"], ud["ch_id"], ud["ch_msg_id"],
                                    ud["file_id"], time.time()))
                logger.info("Job add to database")
    except Exception as e:
        logger.warning("%s", e)


def db_get_channel_route(s_plz, try_cache=True):
    if try_cache:
        try:
            ch_id = PLZ_CH_ID_DICT[s_plz]
            logger.info("Channel-ID %s for PLZ %s loaded get cache", ch_id, s_plz)
            return ch_id
        except KeyError:
            logger.warning("Couldn't find PLZ %s in cache, try to fetch from DB", s_plz)
            pass
    sql_str = "SELECT plz_kv.plz, kv_ch_id_hessen.ch_id from plz_kv " \
              "inner join kv_ch_id_hessen on plz_kv.kreis = kv_ch_id_hessen.kv " \
              "where plz = %s"
    try:
        with PSCON as con:
            with con.cursor() as c:
                c.execute(sql_str, (s_plz,))
                res = c.fetchone()
                logger.info("Get %s from DB", res)
    except Exception as e:
        logger.critical("DB-Error %s", e)
        res = None
        return res
    if res is None:
        print("here")
        return
    else:
        PLZ_CH_ID_DICT[res[0]] = res[1]  # Update Cache
        logger.info("Updated cached channel-id of plz %s to %s", res[0], res[1])
        return res[1]


def route_to_channel(s_plz):
    ch_id = db_get_channel_route(s_plz)
    if ch_id:
        return ch_id
    else:
        return CHANNEL_ID


@run_async
def release(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    if data == "1":
        ud: dict = context.user_data
        ch_id = route_to_channel(ud["s_plz"])
        try:
            pbl_auftrag = gen_auftrag_channel(ud)
            pbl_msg = context.bot.send_message(chat_id=ch_id, text=pbl_auftrag, reply_markup=PBL_KB)
            ud["ch_id"] = pbl_msg.chat.id
            ud["ch_msg_id"] = pbl_msg.message_id
            prv_msg = query.message.reply_text(ud["auftrag"], reply_markup=PRV_KB_S)
            ud["s_msg_id"] = prv_msg.message_id
            db_create_new_job(ud)
        except BadRequest as e:
            logger.warning("Invalid cached data of channel for PLZ or ch_id %s", ch_id)
            logger.warning(e)
            update.effective_message.reply_text("Zu der von dir eingebenen PLZ exisitert kein Kanal!\n"
                                                "Versuche es bitte nochmal sollte der Fehler erneut auftreten, wende"
                                                " dich an das Admin-Team")
            db_get_channel_route(ud["s_plz"], try_cache=False)  # Update cache
        return clean_up(query, context)
    else:
        return clean_up(query, context)


def gen_auftrag(ud, done=False):
    name = ud["s_name"]
    adresse = ud["s_strasse"] + " " + ud["s_nummer"] + ", " + ud["s_plz"] + " " + ud["s_ort"]
    tel = ud["s_tel"]
    if ud["file_id"] is None:
        zettel = "Keiner"
    else:
        zettel = "Vorhanden"
    if ud["h_id"] is None:
        helfer = ""
        status = "🔴 unbesetzt"
    else:
        helfer = db_get_user_data(ud["h_id"])["name"]
        status = "✅ Aktiv"
        if done:
            status = "Erledigt ✅"
    res = "Name : {}\n" \
          "Adresse : {}\n" \
          "Tel. : {}\n" \
          "Zettel : {}\n" \
          "Helfer : {}\n" \
          "Status : {}".format(name, adresse, tel, zettel, helfer, status)
    return res


def gen_auftrag_channel(ud, done=False):
    if PRIVACY:
        ort = ud["s_plz"] + " " + ud["s_ort"]
        if ud["h_id"] is None:
            helfer = ""
            status = "🔴 unbesetzt"
        else:
            helfer = db_get_user_data(ud["h_id"])["name"]
            status = "✅ Aktiv"
            if done:
                status = "Erledigt ✅"
        if ud["file_id"] is None:
            zettel = "Keiner"
        else:
            zettel = "Vorhanden"
        if PRIVACY-1:
            res = "Ort : {}\n" \
                  "Zettel : {}\n" \
                  "Status : {}".format(ort, zettel, status)
        else:
            res = "Ort : {}\n" \
                  "Zettel : {}\n" \
                  "Helfer : {}\n" \
                  "Status : {}".format(ort, zettel, helfer, status)
        return res
    else:
        return gen_auftrag(ud, done)


new_job = ConversationHandler(entry_points=[MessageHandler(Filters.regex("Einkaufshelden"), entry_point)],
                              states={
                                  1: [CallbackQueryHandler(help_router)],
                                  2: [CallbackQueryHandler(to_step_3), MessageHandler(Filters.text, get_name)],
                                  3: [CallbackQueryHandler(to_step_4), MessageHandler(Filters.text, adr_text),
                                      MessageHandler(Filters.location, adr_loc)],
                                  4: [CallbackQueryHandler(to_step_5), MessageHandler(Filters.text, get_tel)],
                                  5: [CallbackQueryHandler(to_step_6), MessageHandler(Filters.photo, get_einkaufslist)],
                                  6: [CallbackQueryHandler(release)]
                              },
                              fallbacks=[CommandHandler("cancel", clean_up)]
                              )


@run_async
@only_one
@restricted_to_reg
def take_job(update, context):
    ch_id = update.callback_query.message.chat.id
    ch_msg_id = update.callback_query.message.message_id
    ud = db_get_job_data(ch_id, ch_msg_id)
    h_id = ud["h_id"] = update.callback_query.from_user.id
    auftrag = gen_auftrag(ud)
    pbl_auftrag = gen_auftrag_channel(ud)
    if ud["file_id"] is None:
        h_msg_id = ud["h_msg_id"] = context.bot.send_message(chat_id=h_id,
                                                             text=auftrag, reply_markup=PRV_KB_H).message_id
    else:
        h_msg_id = ud["h_msg_id"] = context.bot.send_photo(chat_id=h_id, photo=ud["file_id"],
                                                           caption=auftrag, reply_markup=PRV_KB_H).message_id
    update.callback_query.message.edit_text(pbl_auftrag, reply_markup=PBL_KB)
    context.bot.edit_message_text(chat_id=ud["s_id"], message_id=ud["s_msg_id"], text=auftrag, reply_markup=PRV_KB_S)
    db_update_h_infos(ch_id, ch_msg_id, h_id, h_msg_id)
    update.callback_query.answer("Einkauf übernommen")
    pass


@run_async
def give_up_job(update, context):
    h_id = update.effective_user.id
    ch_id = update.callback_query.message.chat.id
    ch_msg_id = update.callback_query.message.message_id
    jd = db_get_job_data(ch_id, ch_msg_id)
    h_msg_id = jd["h_msg_id"]
    if h_msg_id:
        context.bot.deleteMessage(h_id, h_msg_id)
        jd["h_id"] = jd["h_msg_id"] = None
        db_update_h_infos(ch_id, ch_msg_id, None, None)
        auftrag = gen_auftrag(jd)
        pbl_auftrag = gen_auftrag_channel(jd)
        update.callback_query.message.edit_text(pbl_auftrag, reply_markup=PBL_KB)
        print(jd)
        context.bot.edit_message_text(chat_id=jd["s_id"], message_id=jd["s_msg_id"], text=auftrag,
                                      reply_markup=PRV_KB_S)
        update.callback_query.answer("Einkauf abgesagt")
    else:
        update.callback_query.answer()


def pbl_cb(update, context):
    data = update.callback_query.data
    if data == "1":  # Job übernehmen
        take_job(update, context)
    else:
        give_up_job(update, context)


@run_async
def db_delete_job(j_id):
    try:
        with PSCON as con:
            with con.cursor() as c:
                sql_str = """Delete FROM entry_point where id=%s"""
                c.execute(sql_str, (j_id,))
                logger.info("Delete Job with ID %s from database", j_id)
    except Exception as e:
        print(e)
        logger.warning("unregistered user-id %s tried to get data", j_id)


@run_async
def revoke_job(update, context):
    s_id = update.effective_user.id
    s_msg_id = update.callback_query.message.message_id
    jd = db_get_job_data_from_s(s_id, s_msg_id)
    if jd["h_id"] is None:
        db_delete_job(jd["id"])
        update.effective_message.delete()
        context.bot.deleteMessage(chat_id=jd["ch_id"], message_id=jd["ch_msg_id"])
        update.callback_query.answer("Auftrag gelöscht")
    else:
        update.callback_query.answer("Nur inaktive Aufträge können gelöscht werden!\n"
                                     "Bitte setze dich mit deinem Einkaufshelden in Verbindung, damit er den Auftrag"
                                     "zuerst absagt.")
    pass


@run_async
def give_up_job_from_prv(update, context):
    h_id = update.effective_user.id
    h_msg_id = update.callback_query.message.message_id
    jd = db_get_job_data_from_h(h_id, h_msg_id)
    update.effective_message.delete()
    jd["h_id"] = jd["h_msg_id"] = None
    db_update_h_infos(jd["ch_id"], jd["ch_msg_id"], None, None)
    auftrag = gen_auftrag(jd)
    pbl_auftrag = gen_auftrag_channel(jd)
    context.bot.edit_message_text(chat_id=jd["ch_id"], message_id=jd["ch_msg_id"], text=pbl_auftrag, reply_markup=PBL_KB)
    context.bot.edit_message_text(chat_id=jd["s_id"], message_id=jd["s_msg_id"], text=auftrag,
                                  reply_markup=PRV_KB_S)
    update.callback_query.answer("Einkauf abgesagt")


@run_async
def db_insert_into_archive(ud):
    try:
        with PSCON as con:
            with con.cursor() as c:
                sql_str = "insert into job_archive(h_id, h_msg_id, s_id, s_msg_id, s_name, s_strasse, s_nummer," \
                          " s_plz, s_ort, s_tel, ch_id, ch_msg_id, file_id, posted, done) " \
                          "values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                c.execute(sql_str, (ud["h_id"], ud["h_msg_id"], ud["s_id"], ud["s_msg_id"], ud["s_name"],
                                    ud["s_strasse"], ud["s_nummer"], ud["s_plz"], ud["s_ort"], ud["s_tel"], ud["ch_id"],
                                    ud["ch_msg_id"], ud["file_id"], ud["time"], time.time()))
                logger.info("Job archived")
    except Exception as e:
        logger.warning("%s", e)


def db_archive_job(h_id, h_msg_id):
    jd = db_get_job_data_from_h(h_id, h_msg_id)
    db_insert_into_archive(jd)
    return jd


@run_async
def job_done(update, context):
    h_id = update.effective_user.id
    h_msg_id = update.effective_message.message_id
    jd = db_archive_job(h_id, h_msg_id)
    auftrag = gen_auftrag(jd, done=True)
    if jd["file_id"] is None:
        update.effective_message.edit_text(text=auftrag)
    else:
        update.effective_message.edit_caption(caption=auftrag)
    context.bot.edit_message_text(chat_id=jd["s_id"], message_id=jd["s_msg_id"], text=auftrag)
    context.bot.deleteMessage(chat_id=jd["ch_id"], message_id=jd["ch_msg_id"])
    update.callback_query.answer("Vielen Dank!\nDer Empfänger wurde über dein baliges Erscheinen informiert.\nBitte "
                                 "rufe ihn zur Sicherheit dennoch an.")
    pass


def prv_cb(update, context):
    query = update.callback_query
    data = query.data
    if data == "3":
        query.answer("Bitte bestätige, dass der Auftrag endgültig gelöscht werden soll.")
        query.message.edit_reply_markup(reply_markup=PRV_KB_S_0)
    elif data == "4":
        query.answer()
        query.message.edit_reply_markup(reply_markup=PRV_KB_S)
    elif data == "5":
        revoke_job(update, context)
    elif data == "6":
        query.answer("Bitte bestätige, dass du den Auftrag absagen willst.")
        query.message.edit_reply_markup(reply_markup=PRV_KB_H_0)
    elif data == "7":
        query.answer()
        query.message.edit_reply_markup(reply_markup=PRV_KB_H)
    elif data == "8":
        give_up_job_from_prv(update, context)
    elif data == "9":
        query.answer("Bitte bestätige, dass der Auftrag ferig ist.")
        query.message.edit_reply_markup(reply_markup=PRV_KB_H_1)
    elif data == "10":
        job_done(update, context)
    pass


def db_get_all_channel_id():
    sql_str = "Select ch_id from kv_ch_id_hessen"
    try:
        with PSCON as con:
            with con.cursor() as c:
                c.execute(sql_str)
                res = c.fetchall()
    except Exception as e:
        logger.critical("DB-Error: %s", e)
    return res


def gen_invite_links(bot):
    ch_id_ls = db_get_all_channel_id()
    for i in ch_id_ls:
        bot.export_chat_invite_link(i[0])


class CHR:  # CHR = Corona Help Router
    def __init__(self):
        init_db()
        self.handlers = [new_job, ChannelCallbackQueryHandler(pbl_cb),
                         CallbackQueryHandler(prv_cb)]

    def add_to_dispatcher(self, dispatcher: Dispatcher):
        for handler in self.handlers:
            dispatcher.add_handler(handler)


if __name__ == "__main__":
    init_db()
