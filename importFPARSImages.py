import csv
import sys
import argparse
import glob
import os
from database.createFPARSTable import createTruthsTable, createFieldsTable,createPathTable, createIndexes
from database.sqlite3db import DB
import traceback
import time
from pathlib import Path

TRUTH_DB = "FPARS.sqlite3",
EXTENSIONS = [".tif",".tiff",".png",".jpg",".TIF",".TIFF"]
###############
def import_images(db,image_dir):
    image_dir_path = Path(image_dir)
    if image_dir_path.is_dir():
        try:
            db.execute("INSERT INTO PATH(image_dir,time) VALUES (?,?)", (image_dir,time.time()))
        except Exception:
            print("INSERT PATH NOT EXECUTED: " + image_dir)
    else:
        print("INSERT PATH IS NOT a VALID DIRECTORY (ABORT): " + image_dir)
        sys.exit(0)
    image_files = get_all_image_ids(image_dir)
    for image_file in image_files:
        if Path(image_file).suffix in EXTENSIONS:
            base_name = image_file.stem
            try:
                db.execute("INSERT INTO TRUTHS(image_name,flag,comment,istruthed,inuse,time) VALUES (?,?,?,?,?,?)", (base_name,'','','0','0',time.time()))
                print("INSERT EXECUTED "+ str(image_file))
            except Exception:
                print("INSERT NOT EXECUTED: " + str(image_file))
                traceback.print_exc()

###############

def get_all_image_ids(path):
    return [Path(f) for f in Path(path).iterdir() if f.is_file()]
###############

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-d", "--directory", help="Path to a Directory of images")
    ap.add_argument("-s", "--sqlite", help="Path to sqlite3 file")
    args = vars(ap.parse_args())
    image_dir_path = None
    if args["directory"]:
        image_dir_path = args["directory"]
    else:
         print("ERROR: need a directory of images")
         quit()
    if args["sqlite"]:
        dbFile = args["sqlite"]
    else:
        dbFile = TRUTH_DB

    db = DB(dbFile,create=True)
    if not createTruthsTable(db):
        sys.exit("ERROR Importing Data")
    print("createTruthTable")
    createFieldsTable(db)
    print("createFieldsTable")
    createPathTable(db)
    print("createPathTable")
    createIndexes(db)
    import_images(db,image_dir_path)
###############
if __name__ == "__main__":
      main()
