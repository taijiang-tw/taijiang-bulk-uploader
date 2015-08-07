# -*- coding: UTF-8 -*-

import ckanapi
import helpers as h


# The repeating fields
EXCLUDES = [u"群組", u"標籤", u"主題關鍵字", u"空間範圍關鍵字", u"使用史料", u"參考來源"]

class Uploader:
    def __init__(self, config):
        self._config = config
        self.instance = ckanapi.RemoteCKAN(config["api_url"], apikey=config["api_key"])
        self.data_fields = h.get_dataset_field_choices(self.instance)
        self.res_fields = h.get_resource_field_choices()

    def process_row(self, row):
        processed_rows = []
        if row[u"標題"] != "":
            processed_rows.append(self.create_package(row))
        if row[u"檔案標題"] != "":
            processed_rows.append(self.create_resource(row))
        return processed_rows

    def create_package(self, row):
        # Initialize the pacakge dictionary with error flag
        # and notes to prevent missing package notes.
        p = {"errors": [], "notes": ""}

        # Find the intersection of fields defined by meta file
        # and taijiang site separately and exclude the repeating fields.
        to_process = [field for field in row.keys() \
                if field in self.data_fields.keys() and field not in EXCLUDES]

        for k in to_process:
            v = row[k]
            if not v: continue
            if self.data_fields[k].get("choices"):
                error = h.choice_validator(self.data_fields, k, v)
                if error:
                    p["errors"].append(error)
                    continue
                p[self.data_fields[k]["field_name"]] = \
                        self.data_fields[k]["choices"].get(v)
            else: p[self.data_fields[k]["field_name"]] = v
 
        if row.get(u"群組"):
            p["groups"] = []
            for group in row[u"群組"].split(";"):
                error = h.choice_validator(self.data_fields, u"群組", group)
                if error:
                    p["errors"].append(error)
                    continue
                p["groups"].append({"name": self.data_fields[u"群組"]["choices"][group]})

        if row.get(u"標籤"):
            tags = filter(None, row.get(u"標籤").split(";"))
            p["tags"] = [{"name": tag} for tag in tags]

        for k in EXCLUDES[2:6]:
            if row.get(k):
                field_name = self.data_fields[k]["field_name"]
                if self.data_fields[k].get("choices"):
                    p[field_name] = []
                    for item in row[k].split(";"):
                        error = h.choice_validator(self.data_fields, k, item)
                        if error:
                            p["errors"].append(error)
                            continue
                        p[field_name].append(self.data_fields[k]["choices"].get(item))
                else: p[field_name] = filter(None, row[k].split(";"))
        
        # Validate spatial field.
        if p.get("spatial"):
            error = h.geojson_validator(p["spatial"])
            if error: p["errors"].append(error)
        
        # Validate parcel corner and convert it to geojson.
        p = h.parcel_corner_to_geojson(p)

        # Update basic info.
        p.update({"name": p["title"], "owner_org": self._config["org_name"], \
            "private": self._config["visibility"]})
        return p

    def create_resource(self, row):
        # Initialize the resource dictionary with error flag.
        r = {"errors": []}
        # Find the intersection of fields defined by meta file and taijiang site separately.
        to_process = [field for field in row.keys() if field in self.res_fields.keys()]
        r.update({self.res_fields[field]: row[field] for field in to_process})
        if r.get("url") and r.get("file_name"):
            r["errors"].append("Url and file_name can not exist at the same time.")
        return r
