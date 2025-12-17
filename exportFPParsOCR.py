import argparse
import re
import sys
from collections import defaultdict
from typing import List, DefaultDict

from database.sqlite3db import DB

def export(sqliteDB: DB, out_file: str = None) -> DefaultDict:
    addresses = defaultdict()
    truth_rs = sqliteDB.select("SELECT id,image_name,istruthed,flag FROM TRUTHS WHERE istruthed <> 0 ")
    if out_file is None:
        f = sys.stdout
    else:
        f = open(out_file, "w")
    for truth in truth_rs:
        truth_id, image_name, istruthed, flag = truth
        addresses[image_name] = []
        address = print_address(f, sqliteDB, truth)
        addresses[image_name] = []
        if flag == "U":
            address.append("UNRESOLVABLE")
        if not re.search('CURRENT|RESIDENT', ''.join(address)) is None:
            address.append("CURRENT")
        addresses[image_name] = address[1:]
    return addresses


def print_address(f: str, sqliteDB: DB, truth: List[str]) -> List[str]:
    address = []
    truth_id, image_name, istruthed, flag = truth
    field_rs = sqliteDB.select(
        "SELECT id, txt FROM FIELDS WHERE truth_id = ?",
        (truth_id,))
    field_rs.reverse()
    print(image_name, file=f)
    address.append(image_name)

    for field in field_rs:
        id, txt = field
        txt = clean_txt(txt)
        if not txt == "":
            address.append(txt)

        print(txt.encode('ascii', 'ignore').decode('ascii'), file=f)
    print("", file=f)

    return address


def clean_txt(txt: str) -> str:
    txt = re.sub(r"\.'", '', txt)
    txt = re.sub(r'[^0-9]-', '', txt)
    txt = re.sub(r'-[^0-9]', '', txt)
    txt = re.sub(r'-\b', '', txt)
    txt = re.sub(r'\b-', '', txt)
    txt = re.sub(r'([^0-9])/([^0-9])', r"\1 \2", txt)
    txt = re.sub(r'[^ A-Z0-9#/&-]', ' ', txt, flags=re.I)
    txt = re.sub(r"^\s+$", '', txt)
    txt = re.sub(r'\bBLYD\b', ' BLVD ', txt, flags=re.I)
    txt = re.sub(r'\bR[O0]\b', ' RD ', txt, flags=re.I)
    txt = re.sub(r'\bP0\b', ' PO ', txt, flags=re.I)
    txt = re.sub(r'\b[O0]D\b', ' RD ', txt, flags=re.I)
    txt = re.sub(r'\bVLY\b', ' VALLEY ', txt, flags=re.I)
    txt = re.sub(r'AVENUE\s*DE', '', txt, flags=re.I)
    txt = re.sub(r'^\s*ONE\b', ' 1 ', txt, flags=re.I)
    txt = re.sub(r'^\s*TWO\b', ' 2 ', txt, flags=re.I)
    txt = re.sub(r'^\s*THREE\b', ' 3 ', txt, flags=re.I)
    return txt.upper()


######################################################

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-s", "--sqlite", help="Sqlite database")
    ap.add_argument("-o", "--outfile", help="Output file")

    outfile = None

    args = vars(ap.parse_args())
    if args["sqlite"]:
        sqliteDB = args["sqlite"]
    else:
        print("ERROR: sqlite db required...")
        ap.print_help()
        quit()
    if args["outfile"]:
        outfile = args["outfile"]
    db = DB(sqliteDB)

    export(db, outfile)
