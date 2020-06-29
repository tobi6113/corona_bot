import csv
import sqlite3

from keyboards import DATABASE

con = sqlite3.connect(DATABASE)
cur = con.cursor()
cur.execute("CREATE TABLE plz_kv (plz text, ort text, kreis text, land text);") # use your column names here

with open('zuordnung_plz_ort_landkreis.csv', 'rt', encoding="utf8") as fin: # `with` statement available in 2.5+
    # csv.DictReader uses first line in file for column headings by default
    dr = csv.DictReader(fin) # comma is default delimiter
    to_db = [(i['plz'], i["ort"], i['landkreis'], i["bundesland"]) for i in dr]

cur.executemany("INSERT INTO plz_kv (plz, ort, kreis, land) VALUES (?, ?, ?, ?);", to_db)
con.commit()
con.close()
