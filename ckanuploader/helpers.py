# -*- coding: UTF-8 -*-

import json
import ckanapi
import requests
from shapely.geometry import box, mapping
from ckanext.scheming import plugins as scheming_plugins


TAIJIANG_SCHEMA = "ckanext.taijiang:taijiang_scheming.json"

def get_dataset_field_choices(instance):
    schema = scheming_plugins._load_schema(TAIJIANG_SCHEMA)
    fields = dict()
    for field in schema['dataset_fields']:
       fields[field['label']['zh_TW']] = {"field_name": field["field_name"]}
       if field.get('choices'):
          choices_new = dict()
          for choice in field.get('choices'):
              label = choice['label']['zh_TW'] if isinstance(choice['label'], dict) else choice['label']
              choices_new[label] = choice['value']
          fields[field['label']['zh_TW']].update({"choices": choices_new})

    # Get license and group list via ckanapi.
    license_list = dict()
    for license in instance.action.license_list():
        license_list[license['title']] = license['id']
    fields[u"授權"] = {"field_name": "license_id", "choices": license_list}
    group_list = dict()
    # We need taijiang.tw instance to get group list.
    taijiang_instance = ckanapi.RemoteCKAN("http://taijiang.tw")
    for group in taijiang_instance.action.group_list(all_fields=True):
        group_list[group['title']] = group['name']
    fields[u"群組"] = {"field_name": "groups", "choices": group_list}
    return fields

def get_resource_field_choices():
    schema = scheming_plugins._load_schema(TAIJIANG_SCHEMA)
    fields = dict()
    for field in schema["resource_fields"]:
        label = u"檔案" + field['label']['zh_TW'] if field["field_name"] != "resource_ces" \
                else field['label']['zh_TW']
        fields[label] = field["field_name"]
    # Two fields with different labels
    fields[u"檔案標題"] = u"name"
    fields[u"檔案名稱"] = u"file_name"
    return fields

def choice_validator(data_fields, k, v):
    error = ""
    try: t = data_fields[k]["choices"][v]
    except KeyError:
        error = u"{value} not in {key}.".format(value=v, key=k)
    return error

def parcel_corner_to_geojson(package):
    corners = ["x_min", "y_min", "x_max", "y_max"]
    p = {k: float(v) for k, v in package.iteritems() if k in corners}

    if len(p) == 0: return package
    if len(p) != 4:
        error = "The number of parcel corners is not 4 ({num} provided)." \
                .format(num=len(p))
        package["errors"].append(error)
        return package
    for coord in corners[::2]:
        if not -180 <= p[coord] <= 180:
            package["errors"].append("Not a valid long coordinate.")
    for coord in corners[1::2]:
        if not -90 <= p[coord] <= 90:
            package["errors"].append("Not a valid lat coordinate.")
    for pair in [corners[::2], corners[1::2]]:
        if p[pair[0]] > p[pair[1]]:
            package["errors"].append(pair[0] + " > " + pair[1])

    b = box(p["x_min"], p["y_min"], p["x_max"], p["y_max"], ccw=False)
    package["spatial"] = json.dumps(mapping(b))
    return package

def geojson_validator(s):
    error = ""
    validate_endpoint = 'http://geojsonlint.com/validate'
    response = requests.post(validate_endpoint, s).json()
    if response["status"] == "error":
        error = "Spatial: " + response["message"]
    return error
