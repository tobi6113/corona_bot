from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

START_KB = ReplyKeyboardMarkup([["Anmelden"], ["Einkaufshilfe"], ["Hilfe"]])

ADM_KB = ReplyKeyboardMarkup([["Neuer Auftrag"], ["Status"], ["Hauptmenü"]])

EKH_KB = InlineKeyboardMarkup([[InlineKeyboardButton("Für mich", callback_data='1'),
                                InlineKeyboardButton("Für andere", callback_data='2')]])

ANM_KB = InlineKeyboardMarkup([[InlineKeyboardButton("Weiter ✅", callback_data='1'),
                                InlineKeyboardButton("Abbrechen ❌", callback_data='2')]])

CHK_KB = InlineKeyboardMarkup([[InlineKeyboardButton("Veröffentlichen ✅", callback_data='1'),
                                InlineKeyboardButton("Abbrechen ❌", callback_data='2')]])
DATABASE = './datenbanken/gulasch2.db'

CHANNEL_ID = 12

PBL_KB = InlineKeyboardMarkup([[InlineKeyboardButton("Übernehmen ✅", callback_data='1'),
                                InlineKeyboardButton("Absagen", callback_data='2')]])

PRV_KB_S = InlineKeyboardMarkup([[InlineKeyboardButton("Storno ❌", callback_data="3")]])

PRV_KB_S_0 = InlineKeyboardMarkup([[InlineKeyboardButton("Abbrechen", callback_data="4")],
                                   [InlineKeyboardButton("Wirklich entfernen ❌", callback_data="5")]])

PRV_KB_H = InlineKeyboardMarkup([[InlineKeyboardButton("Erledigt ✅", callback_data='9')],
                                 [InlineKeyboardButton("Absagen ❌", callback_data="6")]])

PRV_KB_H_0 = InlineKeyboardMarkup([[InlineKeyboardButton("Abbrechen ", callback_data="7")],
                                   [InlineKeyboardButton("Wirklich absagen", callback_data="8")]])

PRV_KB_H_1 = InlineKeyboardMarkup([[InlineKeyboardButton("Erledigt ✅", callback_data='10')],
                                   [InlineKeyboardButton("Abbrechen", callback_data="7")]])
