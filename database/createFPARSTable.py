from database.sqlite3db import DB
import traceback

def createTruthsTable(db: DB):
    try:
        db.execute('''
        CREATE TABLE TRUTHS(
        id            INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        image_name    TEXT UNIQUE,
        flag          TEXT,
        comment       TEXT,
        istruthed     BOOLEAN NOT NULL,
        inUse         BOOLEAN NOT NULL,
        time          REAL
        );
        ''')
    except Exception:
        traceback.print_exc()
        return False
    return True
def createFieldsTable(db: DB):
    try:
        db.execute('''
        CREATE TABLE FIELDS(
        id            INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        truth_id      INTEGER,
        field_type    TEXT,
        txt           TEXT,
        add_block_roi   TEXT,
        add_line_roi    TEXT,
        angle         REAL,
        time          TEXT
        );
        ''')
    except Exception:
        traceback.print_exc()

def createPathTable(db: DB):
    try:
        db.execute('''
        CREATE TABLE PATH(
        id            INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        image_dir     TEXT UNIQUE,
        time          REAL
        );
        ''')
    except Exception:
        traceback.print_exc()

def createIndexes(db: DB):
    db.execute("CREATE UNIQUE INDEX idx_imagenames on TRUTHS(image_name)")