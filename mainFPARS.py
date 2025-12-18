import argparse
import tkinter as tk
from truther.FPARSTruth import FPARSTruthClass
import os
from pathlib import Path

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-s", "--sqlite", help="Sqlite database")
    ap.add_argument('-r', '--reviewer', action='store_true')
    args = vars(ap.parse_args())
    if args["sqlite"]:
        sqliteDB = args["sqlite"]
    else:
        sqliteDB = input("Enter path and name OF the sqlite file: ")
    if not Path(sqliteDB).is_file():
        print("ERROR: valid sqlite db required...",sqliteDB)
        ap.print_help()
        quit()
    if args ["reviewer"]:
        is_reviewer= True
    else:
        is_reviewer = False
    root = tk.Tk()
    my_gui = FPARSTruthClass(root, sqliteDB, is_reviewer)

    root.mainloop()
