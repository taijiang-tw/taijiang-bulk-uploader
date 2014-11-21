# -*- coding: UTF-8 -*-

import urllib2
import urllib
import requests
import json
import csv
import re
from argparse import RawTextHelpFormatter, ArgumentParser
import lists as l
import fields as f
import configs as c


parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
parser.add_argument("-f", metavar="META_FILE", help="name of the meta file", required=True)
parser.add_argument("-d", metavar="FILE_FOLDER", help="name of the folder containing files to upload", required=True)
args = parser.parse_args()


def main():
    bulk_file = open(args.f, "r")
    bulk_reader = csv.DictReader(bulk_file)

    field_data_type = list_to_dict(l.DATA_TYPES)
    field_data_type.update({"id": "data_type"})
    field_proj = list_to_dict(l.PROJS)
    field_proj.update({"id": "proj"})
    field_temp_res = list_to_dict(l.TEMP_RES)
    field_temp_res.update({"id": "temp_res"})
    field_language = list_to_dict(l.LANGUAGES)
    field_language.update({"id": "language"})
    field_encoding = list_to_dict(l.ENCODINGS)
    field_encoding.update({"id": "encoding"})
    field_loc_keyword = list_to_dict(l.LOC_KEYWORDS)
    field_loc_keyword.update({"id": "loc_keyword"})
    global field_names_extras_restricted
    field_names_extras_restricted = {"資料類型": field_data_type, "所屬子計畫": field_proj,
            "時間解析度": field_temp_res, "語言": field_language, "編碼": field_encoding,
            "授權": f.field_license_id, "空間範圍關鍵字": field_loc_keyword}

    counter = 0
    for row in bulk_reader:
        if row["標題"] != "":
            counter += 1
            returned_package_info = process_row(row, counter)
        if row["檔案標題"] != "":
            assert ((row["檔案網址"] != "") ^ (row["檔案名稱"] != "")), "錯誤: 檔案網址與檔案名稱僅能擇一"
            create_resource(package_id=returned_package_info["id"], name=row["檔案標題"],
                    url=row["檔案網址"], file_format=row["檔案格式"], file_name=row["檔案名稱"], file_newname=row["新檔案名稱"])


def process_row(row, n):
    print "creating new package: " + c.name_prefix + str(n) + "..."
    r_main = dict()
    r_main["tags"] = []
    if row["標籤"] != "":
        for tag in re.split(";", row["標籤"]):
            r_main["tags"].append({"name": tag})
    r_extras = []
    if row["使用史料"] != "":
        for option in re.split(";", row["使用史料"]):
            r_extras.append({"key": f.options_hist_material.get(option),
                    "value": "yes"})
    if row["空間範圍.X.min"] != "" and row["空間範圍.X.max"] != "" and row["空間範圍.Y.min"] != "" \
            and row["空間範圍.Y.max"] != "" and row["空間範圍"] == "":
        r_extras.append({"key": "spatial", "value": "{\"type\": \"Polygon\",\"coordinates\": [[[" +\
                row["空間範圍.X.min"] + "," +\
                row["空間範圍.Y.min"] + "],[" +\
                row["空間範圍.X.min"] + "," +\
                row["空間範圍.Y.max"] + "],[" +\
                row["空間範圍.X.max"] + "," +\
                row["空間範圍.Y.max"] + "],[" +\
                row["空間範圍.X.max"] + "," +\
                row["空間範圍.Y.min"] + "],[" +\
                row["空間範圍.X.min"] + "," +\
                row["空間範圍.Y.min"] + "]]]}"})
    r_main["groups"] = []
    if row["群組"] != "":
        for group in re.split(";", row["群組"]):
            r_main["groups"].append({"name": f.groups[group]})

    for k, v in row.iteritems():
        if v == "": continue
        if f.field_names_main.get(k):
            r_main[f.field_names_main.get(k)] = v
        if f.field_names_extras_free.get(k):
            r_extras.append({"key": f.field_names_extras_free.get(k), "value": v})
        if field_names_extras_restricted.get(k):
            r_extras.append({"key": field_names_extras_restricted[k]["id"],
                    "value": field_names_extras_restricted[k][v]})
    returned_package_info = create_package(c.name_prefix + str(n), r_main, r_extras)
    return returned_package_info


def create_resource(package_id, name, file_format, url="", file_name="", file_newname=""):
    data = {"package_id": package_id, "url": url, "name": name, "format": file_format}
    if file_name != "":
        requests.post(c.api_url + "/api/action/resource_create", data=data,
                files=[("upload", (file_newname, file((args.d + "/" + file_name), "r")))],
	        headers={"X-CKAN-API-Key": c.api_key})
    else:
        data_string = urllib.quote(json.dumps(data))
        request = urllib2.Request(c.api_url + "/api/action/resource_create")
        request.add_header("Authorization", c.api_key)
        response = urllib2.urlopen(request, data_string)
        assert response.code == 200


def create_package(name, r_main, r_extras):
    r_main.update({"name": name, "owner_org": c.org_name, "private": "true", "extras": r_extras})
    data_string = urllib.quote(json.dumps(r_main))
    request = urllib2.Request(c.api_url + "/api/action/package_create")
    request.add_header("Authorization", c.api_key)
    response = urllib2.urlopen(request, data_string)
    assert response.code == 200
    
    response_dict = json.loads(response.read())
    assert response_dict['success'] is True
    created_package = response_dict['result']

    return created_package


def list_to_dict(l):
    d = {}
    for item in l:
        d[item[1].encode("utf8")] = item[0]
    return d


if __name__ == "__main__":
    main()
