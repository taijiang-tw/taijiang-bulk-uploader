import json
import sys
import os
import unicodecsv as csv
from argparse import RawTextHelpFormatter, ArgumentParser
from ckanuploader import uploader as u


parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
parser.add_argument("-c", metavar="CONFIG_FILE", help="name of the config file", required=True)
parser.add_argument("-f", metavar="META_FILE", help="name of the meta file", required=True)
parser.add_argument("-d", metavar="FILE_FOLDER", help="name of the folder containing files to upload")
args = parser.parse_args()

c = json.load(open(args.c))
uploader = u.Uploader(c)
bulk_file = open(args.f, "r")
bulk_reader = csv.DictReader(bulk_file)

print "Checking data..."
upload_queue = []
for row in bulk_reader:
    upload_queue.extend(uploader.process_row(row))

# Print collected errors.
e_counter = 0
for item in upload_queue:
    if item.get("errors"):
        print u"Error in data/dataset {title}:".format(title=item["name"])
        for error in item["errors"]:
            e_counter += 1
            print "\t" + error

# If there exist errors, don't upload.
if e_counter > 0:
    print "Total {num} error(s).".format(num=e_counter)
    sys.exit()

print "Uploading data..."
data_counter = 0
for upload in upload_queue:
    if "title" in upload.keys():
        # Upload the package.
        print "uploading package: %s..." % (upload["name"])
        returned_package_info = uploader.instance.call_action("package_create", upload)
    if "format" in upload.keys():
        # Upload data of the package.
        print "uploading resource: %s for above package..." % (upload["name"])
        upload.update({"package_id": returned_package_info["id"]})
        if upload.get("file_name"):
            data_counter += 1
            p = os.path.join(args.d, upload.pop("file_name"))
            file_newname=c["name_prefix"] + str(data_counter) + "." + upload["format"]
            uploader.instance.call_action("resource_create", upload,
                    files={"upload": (file_newname, open(p))})
        else:
            uploader.instance.call_action("resource_create", upload)
