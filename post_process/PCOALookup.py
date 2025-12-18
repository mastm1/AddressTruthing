import argparse
from collections import namedtuple
from database.sqlite3db import DB
import util.levenshtein as lev
import re
from collections import defaultdict
import sys
import yaml
import os
from typing import List, DefaultDict, Tuple
from util.decorators import timer

YAML_FILE = 'PCOALookup'
with open(f'post_process' + os.sep + f'{YAML_FILE}.yml', 'r') as f:
    yml_data = yaml.safe_load(f)

LEV_DISTANCE_0 = yml_data['MAX_DISTANCE'][0]
LEV_DISTANCE_1 = yml_data['MAX_DISTANCE'][1]
LEV_DISTANCE_2 = yml_data['MAX_DISTANCE'][2]
LEV_DISTANCE_3 = yml_data['MAX_DISTANCE'][3]
LEV_DISTANCE_4 = yml_data['MAX_DISTANCE'][4]
LEV_DISTANCE_5 = yml_data['MAX_DISTANCE'][5]

(IMAGE_ID, RESULT, ZIP, PRIMARY, PREDIRECTIONAL, PRIMARY_NAME, SUFFIX, POSTDIRECTIONAL,
 SECONDARY_RANGE, SECONDARY_NUMBER, NAME, CFSSITEID, SEQUENCENUMBER, MOVECODE) = \
    ('IMAGE_ID', 'RESULT', 'ZIP', 'PRIMARY', 'PREDIRECTIONAL', 'PRIMARY_NAME', 'SUFFIX', 'POSTDIRECTIONAL',
     'SECONDARY_ABREV', 'SECONDARY_NUMBER', 'NAME', 'CFSSITEID', 'SEQUENCENUMBER', 'MOVECODE')
(FIRSTNAME, MIDDLENAME, LASTNAME, PREFIXNAME, SUFFIXNAME, BUSINESSNAME, OLDZIP,
 OLDADDON, OLDDPBC, NEWZIP, NEWADDON, NEWDPBC) = \
    ('FIRSTNAME', 'MIDDLENAME', 'LASTNAME', 'PREFIXNAME', 'SUFFIXNAME',
     'BUSINESSNAME', 'OLDZIP', 'OLDADDON', 'OLDDPBC', 'NEWZIP', 'NEWADDON', 'NEWDPBC')

(ADDRESS_RESULT, RS_RESULT) = ('ADDRESS_RESULT', 'RS_RESULT')

Field = namedtuple('Fields',
                   [IMAGE_ID, RESULT, ZIP, PRIMARY, PREDIRECTIONAL, PRIMARY_NAME, SUFFIX, POSTDIRECTIONAL,
                    SECONDARY_RANGE,
                    SECONDARY_NUMBER, NAME])

RSField = namedtuple('RSFields',
                     [MOVECODE, FIRSTNAME, MIDDLENAME, LASTNAME, PREFIXNAME, SUFFIXNAME, BUSINESSNAME, CFSSITEID,
                      SEQUENCENUMBER, OLDZIP,
                      OLDADDON, OLDDPBC, NEWZIP, NEWADDON, NEWDPBC])
Match = namedtuple('Matches', [ADDRESS_RESULT, RS_RESULT])

current = yml_data['CURRENT']
clean_lists = yml_data['CLEAN']

nickname_dict = defaultdict(list, {})
print_correct = True


##############################################################################
def clean_txt(txt: str) -> str:
    for w in clean_lists:
        s = r'\b' + w + r'\b'
        txt = re.sub(s, ' ', txt)
    return txt


##############################################################################

def match_found(matched_dict: defaultdict, image_id: str, address_result: List[str], rs_data: List[str],
                name_match_ctr: int):
    matched_dict[image_id] = Match._make([address_result,
                                          rs_data])
    return True, name_match_ctr + 1


##############################################################################
def get_name(rs_data: List[str]) -> str:
    if rs_data is None or len(rs_data) == 0:
        return ""
    if rs_data.LASTNAME.strip() == "":
        return rs_data.BUSINESSNAME
    else:
        nm = rs_data.PREFIXNAME + " " + rs_data.FIRSTNAME + " " + rs_data.MIDDLENAME + " " + rs_data.LASTNAME + " " + rs_data.SUFFIXNAME
        nm = re.sub("\\s+", " ", nm)
        return nm.strip()

##############################################################################

def parse_zipcode_result(result: str) -> Tuple[str, str, str] | None:
    result = re.sub('-', '', result)
    if len(result) == 11:
        return result[0:5], result[5:-2], result[-2:]
    elif len(result) == 9:
        return result[0:5], result[:-4], ""
    elif len(result) == 5:
        return result[0:5], "", ""
    return None

##############################################################################

def is_current_resident(address) -> bool:
    for w in current:
        word = r'\b' + w + r'\b'
        if not re.search(word, address) is None:
            return True
    return False


##############################################################################

def is_unresolvable(address_array) -> bool:
    for s in address_array:
        if not re.search('UNRESOLVABLE', s) is None:
            return True
    return False


##############################################################################

def is_levenshtein_match(s, t) -> bool:
    MAX_DISTANCE = 5
    l = len(t)

    match l:
        case l if yml_data['MAX_DISTANCE'][-1]['LOW'] <= l <= yml_data['MAX_DISTANCE'][-1]['HIGH']:
            MAX_DISTANCE = -1
        case l if yml_data['MAX_DISTANCE'][0]['LOW'] <= l <= yml_data['MAX_DISTANCE'][0]['HIGH']:
            MAX_DISTANCE = 0
        case l if yml_data['MAX_DISTANCE'][1]['LOW'] <= l <= yml_data['MAX_DISTANCE'][1]['HIGH']:
            MAX_DISTANCE = 1
        case l if yml_data['MAX_DISTANCE'][5]['LOW'] <= l <= yml_data['MAX_DISTANCE'][5]['HIGH']:
            MAX_DISTANCE = 5
        case l if yml_data['MAX_DISTANCE'][4]['LOW'] <= l <= yml_data['MAX_DISTANCE'][4]['HIGH']:
            MAX_DISTANCE = 4
        case l if yml_data['MAX_DISTANCE'][3]['LOW'] <= l <= yml_data['MAX_DISTANCE'][3]['HIGH']:
            MAX_DISTANCE = 3
        case l if yml_data['MAX_DISTANCE'][2]['LOW'] <= l <= yml_data['MAX_DISTANCE'][2]['HIGH']:
            MAX_DISTANCE = 2

    if lev.getLevenshteinDistance(s, t, MAX_LEVENSHTEIN_DISTANCE=MAX_DISTANCE) <= MAX_DISTANCE:
        return True
    return False


##############################################################################

def print_result(old_address: List[str], new_array: List[str], ies_data: List[str], ctr: int):
    iterations = max(len(old_address), len(new_array))
    for i in range(iterations):
        if i < len(new_array) and i < len(old_address):
            print("{0:<50} {1}".format(new_array[i], old_address[i]))
        elif i < len(new_array):
            print("{0:<50} {1}".format(new_array[i], ""))
        elif i < len(old_address):
            print("{0:<50} {1}".format("", old_address[i]))
    if not ies_data is None:
        print(','.join(ies_data))
    print(ctr, "-------------------------------------------------------------------------")


##############################################################################
@timer
def process(sqliteDB: DB, address_matcher_lines: list[str], nicknames_file: str, original_address: DefaultDict,
            is_return_address: bool = False):
    global total_time, pcoa_time, clean_time, lev_time, resident_time
    with (open(nicknames_file) as fp):
        for line in fp:
            l = line.split('\t')
            nicknames = l[-1].split(',')
            key_names = l[0].split('/')
            for key_name in key_names:
                for nickname in nicknames:
                    nickname_dict[key_name.strip().upper()].append(nickname.strip().upper())
                    nickname_dict[nickname.strip().upper()].append(key_name.strip().upper())
                    for nickname2 in nicknames:
                        if nickname2 != nickname:
                            nickname_dict[nickname.strip().upper()].append(nickname2.strip().upper())

    #    for k, v in nickname_dict.items():
    #        print(k, v)
    pcoa_db = DB(sqliteDB)
    matched_dict = defaultdict(list, {})
    name_match_ctr = current_resident_ctr = unresolvable_ctr = 0
    sys.stderr.write("0")
    for ctr, line in enumerate(address_matcher_lines):
        if line.strip() == "":
            continue
        if ctr % 100 == 0:
            sys.stderr.write("\n" + str(ctr))
            sys.stderr.flush()
        elif ctr % 10 == 0:
            sys.stderr.write(".")
            sys.stderr.flush()

        l = line.split(',')
        l = [v.strip() for v in l]
        address_result = Field._make(l)
        image_id = address_result.IMAGE_ID
        if is_return_address:
            matched_dict[image_id] = Match._make([address_result, None])
            continue
        if len(l) < 11:
            continue
        name_original = address_result.NAME.replace("\n", " ")
        name_original = name_original.replace(':', ' ')
        name_original = clean_txt(name_original)
        name_split = name_original.split(' ')
        lastname_two_words = ""
        name_whole = name_original.replace(" ", "")
        lastname = name_split[-1]

        if len(name_split) > 2:
            lastname_two_words = name_split[-2] + name_split[-1]
        # start = timer()
        rs = pcoa_db.select(
            "SELECT MOVECODE,FIRSTNAME,MIDDLENAME ,LASTNAME,PREFIXNAME, SUFFIXNAME,BUSINESSNAME,CFSSITEID,SEQUENCENUMBER,OLDZIP,OLDADDON,OLDDPBC, NEWZIP, NEWADDON,NEWDPBC FROM PCOA WHERE OLDZIP = ? and OLDPRIMARYNUMBER = ? and OLDPRIMARYNAME = ? and OLDSUFFIX = ? and OLDPOSTDIRECTION = ? and OLDPREDIRECTiON = ?",
            (address_result.ZIP, address_result.PRIMARY, address_result.PRIMARY_NAME, address_result.SUFFIX,
             address_result.POSTDIRECTIONAL, address_result.PREDIRECTIONAL))

        is_found = False
        for coa in rs:
            coa = (str(v).strip() for v in coa)
            rs_data = RSField._make(coa)
            coa_last = clean_txt(rs_data.LASTNAME).strip()
            coa_business = clean_txt(rs_data.BUSINESSNAME).strip()
            coa_whole = rs_data.FIRSTNAME.strip() + rs_data.MIDDLENAME.strip() + coa_last
            coa_whole_split = (rs_data.FIRSTNAME.strip() + " " + rs_data.LASTNAME).split(' ')
            coa_whole = coa_whole.replace(" ", "")
            if rs_data.MOVECODE == "I":
                matches = 0
                for c in coa_whole_split:
                    if c.strip() == '':
                        continue
                    for n in name_split:
                        if is_levenshtein_match(n, c) or n in nickname_dict[c]:
                            matches += 1
                            break
                if matches == len(coa_whole_split):
                    is_found, name_match_ctr = match_found(matched_dict, image_id, address_result, rs_data,
                                                           name_match_ctr)
            if not is_found and rs_data.MOVECODE == "I" and (is_levenshtein_match(name_whole, coa_whole)):
                is_found, name_match_ctr = match_found(matched_dict, image_id, address_result, rs_data, name_match_ctr)
            elif rs_data.MOVECODE == "F" and (
                    is_levenshtein_match(lastname, coa_last) or is_levenshtein_match(lastname_two_words, coa_last)):
                is_found, name_match_ctr = match_found(matched_dict, image_id, address_result, rs_data, name_match_ctr)
            elif rs_data.MOVECODE == "B" and is_levenshtein_match(name_whole, coa_business.replace(" ", "")):
                is_found, name_match_ctr = match_found(matched_dict, image_id, address_result, rs_data, name_match_ctr)
            elif rs_data.MOVECODE == "B":
                if coa_business in name_original:
                    is_found, name_match_ctr = match_found(matched_dict, image_id, address_result, rs_data,
                                                           name_match_ctr)
                else:
                    coa_business_split = coa_business.split(' ')
                    matches = 0
                    for c in coa_business_split:
                        if c.strip() == '':
                            continue
                        for n in name_split:
                            if is_levenshtein_match(c, n):
                                matches += 1
                                break
                    if (matches == 1 and len(coa_business_split) <= 3) or matches > 1:
                        is_found, name_match_ctr = match_found(matched_dict, image_id, address_result, rs_data,
                                                               name_match_ctr)
            elif rs_data.MOVECODE == "I" and len(name_split) > 2:
                if is_levenshtein_match(lastname, coa_last):
                    for n in name_split[:-1]:
                        if is_levenshtein_match(n, rs_data.FIRSTNAME):
                            is_found, name_match_ctr = match_found(matched_dict, image_id, address_result, rs_data,
                                                                   name_match_ctr)
                        elif n in nickname_dict[rs_data.FIRSTNAME]:
                            is_found, name_match_ctr = match_found(matched_dict, image_id, address_result, rs_data,
                                                                   name_match_ctr)
                        else:
                            continue
            if is_found:
                break
        if not is_found:
            matched_dict[image_id] = Match._make([address_result, None])
    ctr = 0
    for image_id in original_address.keys():
        ctr += 1
        new_array = [""] * yml_data['NEW_ARRAY_LENGTH']
        ies_data = [""] * yml_data['IES_DATA_LENGTH']
        result = ""
        old_address = original_address[image_id]
        if print_correct:
            if is_unresolvable(old_address):
                ies_data[:2] = [image_id, result]
                ies_data[-1] = "UNRESOLVABLE"
                unresolvable_ctr += 1
                print_result(old_address, new_array, ies_data, ctr)
                continue
            match = matched_dict[image_id]
            if not len(match) == 0:
                address_result = match.ADDRESS_RESULT
                result = address_result.RESULT
                #                print(result)
                new_street_line = address_result.PRIMARY + " " + address_result.PREDIRECTIONAL + " " + address_result.PRIMARY_NAME + \
                                  " " + address_result.SUFFIX + " " + address_result.POSTDIRECTIONAL + " " + address_result.SECONDARY_ABREV + " " + \
                                  " " + address_result.SECONDARY_NUMBER

                re.sub('-', '', result)
                rs_data = match.RS_RESULT
                result = re.sub('-', '', address_result.RESULT)
                name = get_name(rs_data)
                new_name = name
                if not rs_data is None:
                    new_name += " ( " + rs_data.MOVECODE + " ) [ " + rs_data.SEQUENCENUMBER + " ]"
                else:
                    new_name = "( ) [ ]"
                if name == "":
                    ies_data[:2] = [address_result.IMAGE_ID, result]

                else:
                    ies_data = [address_result.IMAGE_ID, result, rs_data.CFSSITEID, rs_data.SEQUENCENUMBER, name,
                                rs_data.OLDZIP, rs_data.OLDADDON, rs_data.OLDDPBC[:2],
                                rs_data.NEWZIP, rs_data.NEWADDON, rs_data.NEWDPBC[:2], rs_data.MOVECODE, ""]
                ies_data[-1] = "X"
                new_array = [new_name, new_street_line, address_result.RESULT]
            else:
                ies_data[:2] = [image_id, result]
                ies_data[-1] = "X"
        if is_current_resident(' '.join(old_address)):
            ies_data[-1] = "CURRENT"
            current_resident_ctr += 1
        #           print_result(old_address, new_array, ies_data, ctr)
        #           continue
        print_result(old_address, new_array, ies_data, ctr)

    add_match_perc = "{:10.2f} %".format(len(address_matcher_lines) / len(original_address) * 100)
    name_match_perc = "{:10.2f} %".format(name_match_ctr / len(original_address) * 100)
    current_resident_perc = "{:10.2f} %".format(current_resident_ctr / len(original_address) * 100)
    unresolvable_perc = "{:10.2f} %".format(unresolvable_ctr / len(original_address) * 100)

    print("TOTAL IMAGES TRUTHED", len(original_address))
    print("ADDRESS MATCHES", len(address_matcher_lines), add_match_perc)
    print("NAME/BUSINESS MATCHES", name_match_ctr, name_match_perc)
    print("CURRENT ADDRESS", current_resident_ctr, current_resident_perc)
    print("UNRESOLVABLE", unresolvable_ctr, unresolvable_perc)


##############################################################################

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-a", "--addressmatcher results", help="addressmatcher results")
    ap.add_argument("-n", "--nicknames", help="nicnames txt file")
    ap.add_argument("-p", "--pcoa", help="PCOA SQLITE database")
    nicknames_file = None
    args = vars(ap.parse_args())
    if args["pcoa"]:
        sqliteDB = args["pcoa"]
    else:
        print("ERROR: valid pcoa sqlite db required...")
        ap.print_help()
        quit()
    if args["addressmatcher results"]:
        add_results_file = args["addressmatcher results"]
    else:
        print("ERROR: valid address matcher results file required...")
        ap.print_help()
        quit()
    if args["nicknames"]:
        nicknames_file = args["nicknames"]

    address_matcher_lines = []
    with open(add_results_file) as fp:
        for line in fp:
            address_matcher_lines.append(line)
    fp.close()
    process(sqliteDB, address_matcher_lines, nicknames_file, defaultdict())
