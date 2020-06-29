"""
Old module current version uses Postgres
"""

import sqlite3
from logger import logger

USER_ROWS = ["user_id", "username", "vorname", "nachname", "strasse", "nummer", "plz", "chat_id", "active",
             "admin", "tel"]


def init_database():
    with sqlite3.connect('./datenbanken/gulasch2.db') as con:
        c = con.cursor()
        c.execute("""create table if not exists benutzer (user_id integer primary key,
                          username text, 
                          vorname text, 
                          nachname text, 
                          strasse text,
                          nummer text, 
                          plz text, 
                          chat_id integer, 
                          active integer, 
                          admin integer,
                          tel text)""")

        c.execute(""" create table if not exists fahrten (id integer primary key autoincrement , 
                          datetime text, 
                          einheiten integer, 
                          fahrer_id integer, 
                          msg_id integer, 
                          pbl_id integer)""")
        c.execute("create table einkauf_details"
                  "(id integer primary key, name text, strasse text,"
                  " hausnummer text, plz text, tel text )")

        c.execute("create table if not exists einkauf"
                  "        (id integer primary key autoincrement,"
                  "helfer_id integer,"
                  "details_id integer,"
                  "pbl_id integer,"
                  "constraint fk_user foreign key (helfer_id) references benutzer(user_id),"
                  "constraint fk_details foreign key (details_id) references  einkauf_details(id))")

        con.commit()
        logger.info("Database ready ")


def db_get_user_data(user_id):
    try:
        with sqlite3.connect("./datenbanken/gulasch2.db") as con:
            c = con.cursor()
            sql_str = """Select * FROM benutzer where user_id=?"""
            c.execute(sql_str, (user_id,))
            ls = c.fetchone()
            usr = dict(zip(USER_ROWS, ls))
            logger.info("User-data of user-id %s fetched from database", user_id)
            return usr
    except Exception as e:
        print(e)
        logger.warning("unregistered user-id %s tried to get data", user_id)
        return -1


def db_update_adr(user_id, strasse, nummer, plz):
    try:
        with sqlite3.connect("./datenbanken/gulasch2.db") as con:
            c = con.cursor()
            sql_str = """   UPDATE benutzer set     plz = ?,
                                                        strasse = ?,
                                                        nummer = ?
                                                where   user_id = ?"""
            c.execute(sql_str, (plz, strasse, nummer, user_id))
            logger.info("Data send to Database")
            con.commit()
    except Exception as e:
        print(e)
        logger.warning("Cant write on database")
        con.close()


def db_update_name(user_id, vorname, nachname):
    try:
        with sqlite3.connect("./datenbanken/gulasch2.db") as con:
            c = con.cursor()
            sql_str = """   UPDATE benutzer set     vorname = ?,
                                                    nachname = ?
                                            where   user_id = ?"""
            c.execute(sql_str, (vorname, nachname, user_id))
            logger.info("Data send to Database")
            con.commit()
    except Exception as e:
        print(e)
        logger.warning("Cant write on database")
        con.close()


def db_update_tel(user_id, tel):
    try:
        with sqlite3.connect("./datenbanken/gulasch2.db") as con:
            c = con.cursor()
            sql_str = """   UPDATE benutzer set     tel = ?
                                            where   user_id = ?"""
            c.execute(sql_str, (tel, user_id))
            logger.info("Data send to Database")
            con.commit()
    except Exception as e:
        print(e)
        logger.warning("Cant write on database")
        con.close()


def db_create_new_user(user_id, chat_id, vorname, nachname, username):
    curr_usr = [chat_id, vorname, nachname, user_id, username]
    logger.info("User %s tries to register", curr_usr)
    try:
        with sqlite3.connect("./datenbanken/gulasch2.db") as con:
            c = con.cursor()
            sql_str = """   insert into benutzer(user_id, chat_id, vorname, nachname, username) 
                            values(?,?,?,?,?) """
            c.execute(sql_str, (user_id, chat_id, vorname, nachname, username))
            con.commit()
            logger.info("User %s add to database", curr_usr)

            ret = 1
    except Exception as e:
        logger.debug("%s", e)
        logger.info("User %s already exists", curr_usr)
        ret = -1
    finally:
        con.close()
    return ret


def db_set_active(user_id, status):
    try:
        with sqlite3.connect("./datenbanken/gulasch2.db") as con:
            c = con.cursor()
            sql_str = """ UPDATE benutzer set    active = ?
                                        where user_id = ?"""
            c.execute(sql_str, (status, user_id))
            logger.info("%s marked as active, registration complet", user_id)
    except Exception as e:
        print(e)
        logger.warning("Cant write on database")
        con.close()


def db_new_job(job_details):
    logger.info("Try to register new job %s", job_details)
    try:
        with sqlite3.connect("./datenbanken/gulasch2.db") as con:
            c = con.cursor()
            sql_str = """   insert into fahrten(datetime, einheiten) 
                            values(?,?) """
            c.execute(sql_str, job_details)
            ret = c.lastrowid
            con.commit()
            logger.info("Job %s add to database", job_details)
    except Exception as e:
        logger.warning("%s", e)
        logger.info("Failure at add job %s", job_details)
        ret = -1
    finally:
        con.close()
    return ret


def db_update_pbl_id(pbl_id, job_id):
    try:
        with sqlite3.connect("./datenbanken/gulasch2.db") as con:
            c = con.cursor()
            sql_str = """ UPDATE fahrten set    pbl_id = ?
                                        where id = ?"""
            c.execute(sql_str, (pbl_id, job_id))
            logger.info("%s pbl_id set to %s", job_id, pbl_id)
    except Exception as e:
        print(e)
        logger.warning("Cant write on database")
        con.close()
    return


def db_update_fahrer(fahrer_id, job_id):
    try:
        with sqlite3.connect("./datenbanken/gulasch2.db") as con:
            c = con.cursor()
            sql_str = """ UPDATE fahrten set   fahrer_id = ?
                                        where id = ?"""
            c.execute(sql_str, (fahrer_id, job_id))
            logger.info("%s fahrer_id set to %s", job_id, fahrer_id)
    except Exception as e:
        print(e)
        logger.warning("Cant write on database")
        con.close()
    return


def db_query_exist(user_id):
    try:
        with sqlite3.connect("./datenbanken/gulasch2.db") as con:
            c = con.cursor()
            sql_str = "Select EXISTS(SELECT 1 FROM benutzer where user_id=?)"
            c.execute(sql_str, (user_id,))
            ret = c.fetchone()[0]
            logger.info("user %s known", user_id)
            return ret
    except Exception as e:
        print(e)
        logger.warning("Cant read on database")
        con.close()
    return


def db_new_ekh_detail(name, strasse, hausnummer, plz, tel):
    try:
        with sqlite3.connect("./datenbanken/gulasch2.db") as con:
            c = con.cursor()
            sql_str = "Insert into einkauf_details(name, strasse, hausnummer, plz, tel)" \
                      "values(?,?,?,?,?)"
            c.execute(sql_str, (name, strasse, hausnummer, plz, tel))
            logger.info("New ekh_detail")
            return c.lastrowid
    except Exception as e:
        print(e)
        logger.warning("Can't write on database")
        con.close()
        return


def db_delete_ekh_detail_row(row_id):
    try:
        with sqlite3.connect("./datenbanken/gulasch2.db") as con:
            c = con.cursor()
            sql_str = "DELETE from einkauf_details where id =?"
            c.execute(sql_str, (row_id))
            logger.info("ekh_detail deleted")
    except Exception as e:
        print(e)
        logger.warning("Can't write on database")
        con.close()
        return

def db_new_ekh_job(detail_id):
    try:
        with sqlite3.connect("./datenbanken/gulasch2.db") as con:
            c = con.cursor()
            sql_str = "Insert into einkauf(details_id) values(?)"
            c.execute(sql_str, (detail_id,))
            logger.info("New ekh_job")
            return c.lastrowid
    except Exception as e:
        print(e)
        logger.warning("Can't write on database")
        con.close()
        return
