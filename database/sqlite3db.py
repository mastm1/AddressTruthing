import sqlite3
from typing import List, Tuple
from os.path import isfile, getsize
import sys

class DB(object):
    def __init__(self, datasource,create=False):
        if not create and not isSQLite3(datasource):
            sys.stderr.write("'%s' is not a SQLite3 database file\n" % datasource)
            sys.exit()
        self.conn = sqlite3.connect(datasource, uri=True)

    def __del__(self):
        try:
            self.conn.close()
        except:
            pass

    def execute(self, sql: str, params:Tuple=()):
        self.conn.cursor().execute(sql, params)
        self.conn.commit()

    def select(self, sql: str, params:Tuple=()) -> Tuple:
        cursor = self.conn.execute(sql, params)
        return cursor.fetchall()

    def executemany(self, sql: str, params:Tuple=()):
        self.conn.cursor().executemany(sql, params)
        self.conn.commit()
    def executemultiplecommands(self, sql:list[list[str | tuple[str]] | list[str | tuple[str, int, str, any, any, str, float]] | list[str | tuple[float, str, str]]]):
        for sql_command in sql:
            if not sql_command[0].upper().startswith('SELECT'):
                self.conn.cursor().execute(sql_command[0], sql_command[1])
            else:
                raise Exception("Select statements not supported by the \'executemultiplecommands\' method")
        self.conn.commit()

def isSQLite3(filename):
    if not isfile(filename):
        return False
    if getsize(filename) < 100:  # SQLite database file header is 100 bytes
        return False
    with open(filename, 'rb') as fd:
        header = fd.read(100)
    return header[:16] == b'SQLite format 3\x00'

def getCanBeNull(column: str) -> str:
    return "(" + column + " = ? OR " + column + " IS NULL OR " + column + " = '')"
