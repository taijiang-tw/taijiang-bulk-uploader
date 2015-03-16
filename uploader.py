# -*- coding: UTF-8 -*-

import json
import os
import inspect
import csv
import ckanapi
from argparse import RawTextHelpFormatter, ArgumentParser
from ckanext.scheming import plugins as scheming_plugins


parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
parser.add_argument("-c", metavar="CONFIG_FILE", help="name of the config file", required=True)
parser.add_argument("-f", metavar="META_FILE", help="name of the meta file", required=True)
parser.add_argument("-d", metavar="FILE_FOLDER", help="name of the folder containing files to upload", required=True)
args = parser.parse_args()

c = json.load(open(args.c))
CKAN_INSTANCE = ckanapi.RemoteCKAN(c["api_url"], apikey=c["api_key"])
# we need taijiang.tw instance to get group list
TAIJIANG_INSTANCE = ckanapi.RemoteCKAN("http://taijiang.tw")
TAIJIANG_SCHEMA = "ckanext.taijiang:taijiang_scheming.json"


def main():
    TAIJIANG_DATA_FIELDS = get_field_choices(TAIJIANG_SCHEMA)
    bulk_file = open(args.f, "r")
    bulk_reader = csv.DictReader(bulk_file)

    upload_queue = []
    print "--------- Start checking data ---------"
    for row in bulk_reader:
        if row["標題"] != "":
            upload_queue.append(create_package(row, TAIJIANG_DATA_FIELDS))
        if row["檔案標題"] != "":
            assert ((row["檔案網址"] != "") ^ (row["檔案名稱"] != "")), "錯誤: 檔案網址與檔案名稱僅能擇一"
            upload_queue.append(create_resource(name=row["檔案標題"], url=row["檔案網址"],
                    file_format=row["檔案格式"], file_crs=row["座標參考系統"], file_name=row["檔案名稱"],
                    file_description=row["檔案摘要"]))

    print "--------- Start uploading ---------"
    data_counter = 0
    returned_package_info = dict()
    for upload in upload_queue:
        if "owner_org" in upload.keys():
            # upload package
            print "uploading package: %s..." % (upload["name"])
            returned_package_info = CKAN_INSTANCE.call_action("package_create", upload)
        if "format" in upload.keys():
            # upload data
            print "uploading data: %s for above package..." % (upload["name"])
            upload.update({"package_id": returned_package_info["id"]})
            if upload["file_name"] != "":
                data_counter += 1
                p = os.path.join(args.d, upload.pop("file_name"))
                file_newname=c["name_prefix"] + str(data_counter) + "." + row["檔案格式"]
                CKAN_INSTANCE.call_action("resource_create", upload, files={"upload": (file_newname, open(p))})
            else:
                CKAN_INSTANCE.call_action("resource_create", upload)

def get_field_choices(url):
    schema = scheming_plugins._load_schema(url)
    fields = dict()
    for field in schema['dataset_fields']:
       choices_new = dict()
       if field.get('choices'):
          for choice in field.get('choices'):
             choices_new[choice['label']['zh_TW'] if isinstance(choice['label'], dict) else choice['label']] = choice['value']
       fields[field['label']['zh_TW']] = {"field_name": field["field_name"], "choices": choices_new}

    # get license and group list via ckanapi
    license_list = dict()
    for license in CKAN_INSTANCE.action.license_list():
        license_list[license['title']] = license['id']
    fields[u"授權"] = {"field_name": "license_id", "choices": license_list}
    group_list = dict()
    for group in TAIJIANG_INSTANCE.action.group_list(all_fields=True):
        group_list[group['title']] = group['name']
    fields[u"群組"] = {"field_name": "groups", "choices": group_list}
    return fields

def create_package(row, data_fields):
    print "creating package: %s..." % (row["標題"])
    excludes = ["群組", "標籤", "主題關鍵字", "空間範圍關鍵字", "使用史料", "參考來源"]
    # prevent missing package notes
    r_main = {"notes": ""}

    for k, v in row.iteritems():
        if k in excludes or not v: continue
        decoded_k = k.decode("utf8")
        if data_fields.get(decoded_k):
            decoded_v = v.decode("utf8")
            # validate fields with choices
            if data_fields[decoded_k]["choices"]:
                assert decoded_v in data_fields[decoded_k]["choices"].keys(), \
                        (data_fields[decoded_k]["field_name"], v)
            r_main[data_fields[decoded_k]["field_name"]] = \
                    data_fields[decoded_k]["choices"].get(decoded_v, decoded_v)

    if row["群組"] != "":
        r_main["groups"] = []
        for group in row["群組"].split(";"):
            # validate groups
            assert group.decode("utf8") in data_fields[u"群組"]["choices"].keys(), group
            r_main["groups"].append({"name": data_fields[u"群組"]["choices"][group.decode("utf8")]})
    if row["標籤"] != "":
        r_main["tags"] = []
        for tag in row["標籤"].split(";"):
            if tag == "": continue
            r_main["tags"].append({"name": tag})
    for k in excludes[2:6]:
        decoded_k = k.decode("utf8")
        if row.get(k):
            field_name = data_fields[decoded_k]["field_name"]
            r_main[field_name] = []
            # validate keywords (repeating fields)
            if data_fields[decoded_k]["choices"]:
                for item in row[k].split(";"):
                    assert item.decode("utf8") in data_fields[decoded_k]["choices"].keys(), \
                            (data_fields[decoded_k]["field_name"], item)
            for item in row[k].split(";"):
                decoded_item = item.decode("utf8")
                r_main[field_name].append(data_fields[decoded_k]["choices"].get( \
                        decoded_item, decoded_item))

    if row.get("空間範圍.X.min", "") != "" and row.get("空間範圍.X.max", "") != "" \
            and row.get("空間範圍.Y.min", "") != "" \
            and row.get("空間範圍.Y.max", "") != "" and row.get("空間範圍", "") == "":
        r_main["spatial"] = parcel_corner_to_geojson(row)
    r_main.update({"name": r_main["title"], "owner_org": c["org_name"], "private": "true"})
    return r_main

def create_resource(name, file_format, file_crs="", url="", file_name="", file_description=""):
    data = {"url": url, "name": name, "description": file_description, "resource_crs": file_crs, "format": file_format, "file_name": file_name}
    return data

def parcel_corner_to_geojson(row):
    return "{\"type\": \"Polygon\",\"coordinates\": [[[" +\
            row["空間範圍.X.min"] + "," +\
            row["空間範圍.Y.min"] + "],[" +\
            row["空間範圍.X.min"] + "," +\
            row["空間範圍.Y.max"] + "],[" +\
            row["空間範圍.X.max"] + "," +\
            row["空間範圍.Y.max"] + "],[" +\
            row["空間範圍.X.max"] + "," +\
            row["空間範圍.Y.min"] + "],[" +\
            row["空間範圍.X.min"] + "," +\
            row["空間範圍.Y.min"] + "]]]}"

if __name__ == "__main__":
    main()
