import subprocess
import argparse
import  os
from pathlib import Path
from unittest import case

from database.sqlite3db import DB
from post_process.PCOALookup import process
import exportFPParsOCR as exp
import random
from collections import defaultdict
import sys
import yaml
from util.decorators import timer


YAML_FILE = 'MatchWithPostalDatabase'
with open(f'post_process' + os.sep + f'{YAML_FILE}.yml', 'r') as f:
    yml_data = yaml.safe_load(f)
IS_WINDOWS = bool(yml_data['IS_WINDOWS'])
if sys.platform.startswith("linux"):
    PLATFORM = 'LINUX'
    if IS_WINDOWS:
        PLATFORM += '_WINDOWS'
else:
    PLATFORM = 'WINDOWS'

ADDRESS_MATCHER_EXE = yml_data[PLATFORM]['ADDRESS_MATCHER_EXE']
ADDRESS_MATCHER_CONFIG = yml_data[PLATFORM]['ADDRESS_MATCHER_CONFIG']
PCOA_DB_FILE = yml_data[PLATFORM]['PCOA_DB_FILE']

NICKNAMES_FILE = yml_data['NICKNAMES_FILE']

def print_address_matcher_results(am_list):
    for ln in am_list:
        id = nm = zipcode = primary = pre_directional = streetname = suffix = \
            post_directional = firm = secondary_abbr = secondary_num = ""
        for i,am in enumerate(ln.split(',')):
            am = am.strip()
            match i:
                case 0:
                    id = am
                case 1:
                    nm = am
                case 2:
                    zipcode = am
                case 4:
                    primary = am
                case 5:
                    pre_directional = am
                case 6:
                    streetname = am
                case 7:
                    suffix = am
                case 8:
                    post_directional = am
                case 9:
                    firm = am
                case 10:
                    secondary_abbr = am
                case 11:
                    secondary_num = am
        print(id)
        if firm != "":
            print(firm)
        if nm != "":
            print(nm)
        if streetname != "":
            print(primary,pre_directional,streetname,suffix,post_directional,secondary_abbr,secondary_num,secondary_abbr)
        if zipcode != "":
            print(zipcode)
        print()


@timer
def execute_address_matcher(export_tmp_file):
    command = [ADDRESS_MATCHER_EXE, '-f', ADDRESS_MATCHER_CONFIG, '-i', export_tmp_file, '-verbose']
    proc = subprocess.run(command,capture_output=True)
    address_matcher_lines = proc.stdout.decode('UTF-8').split(os.linesep)
    return address_matcher_lines

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-s", "--sqlite", help="Sqlite database")
    ap.add_argument('-r', '--return address', action='store_true')
    args = vars(ap.parse_args())

    if args["sqlite"]:
        sqliteDB = args["sqlite"]
    else:
        sqliteDB = input("Enter path and name OF the sqlite file: ")
        if not Path(sqliteDB).is_file():
            print("ERROR: valid sqlite db required...")
            ap.print_help()
            quit()
    is_return_address =  args["return address"]

    original = defaultdict()
    random_num = round(random.random() * 1000000)
    export_tmp_file = str(random_num) + "-export.txt"

    db = DB(sqliteDB)
    sys.stderr.write("Exporting Addresses...")
    sys.stderr.flush()
    exp.export(db,out_file=export_tmp_file)
    sys.stderr.write("complete\n")
    sys.stderr.flush()
    try:
        sys.stderr.write("Executing address matcher...")
        sys.stderr.flush()
        address_matcher_lines,address_matcher_time = execute_address_matcher(export_tmp_file)
        sys.stderr.write("complete\n\n\n")
        sys.stderr.flush()
        print_address_matcher_results(address_matcher_lines)

    except Exception as e:
        sys.stderr.write("Error executing the Address Matcher. Address Matcher configuration file might need modification." + os.linesep)
        sys.stderr.flush()
    os.remove(export_tmp_file)

    try:
        sys.stderr.write("Looking up Names...\n")
        sys.stderr.flush()
        pcoa_time = process(PCOA_DB_FILE,address_matcher_lines,NICKNAMES_FILE,original,is_return_address=is_return_address)
        print(pcoa_time[1])
    except Exception as e:
        sys.stderr.write("The PCOA (forwarding address database) is not currently operational." + os.linesep)

    sys.stderr.flush()

