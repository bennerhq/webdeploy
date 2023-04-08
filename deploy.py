#!/usr/bin/python3

#
# The main purpose of the project to make it extreamly easy to upload a
# "web application" by uploading a single .html file
#
# This is done by reading ./index.html and creating one file (./deploy.index.html) 
# that containes all external files refarnces (scripts, styles and images).
# deploy.index.html is a self containes "application" without any dependecies
# or referances to external files.
#
# It's not a "bullet proff" solution, but for simple "web application"
# it's okay!
#
# This version is inspired / extended from this stackoverflow post
# https://stackoverflow.com/questions/44646481/merging-js-css-html-into-single-html
#
# /benner, Marts, 2023
# jens@bennerhq.com
#

import os
import subprocess
import sys
import os.path
import base64
import json
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

class bcolors:
    HEADER      = '\033[95m'
    OKBLUE      = '\033[94m'
    OKCYAN      = '\033[96m'
    OKGREEN     = '\033[92m'
    WARNING     = '\033[93m'
    YELLOW      = '\033[93m'
    MAGENTA     = '\033[95m'
    WHITE       = '\u001b[37m'
    FAIL        = '\033[91m'
    ENDC        = '\033[0m'
    BOLD        = '\033[1m'
    UNDERLINE   = '\033[4m'
    BG_YELLOW   = '\u001b[43;1m'
    BG_RED      = '\u001b[41;1m'

def read_file(ref, info, is_uft8_ext = None):
    filename = ref.strip()

    idx = filename.find("?")
    if idx != -1:
        filename = filename[:idx]

    idx = filename.find("[-]")
    if idx != -1:
        filename = filename[:idx]

    info = ("[" + info + "]").ljust(10, " ") + filename
    if idx != -1 or filename in json_config["exclude"]:
        print(info + bcolors.WARNING + "  excluded" + bcolors.ENDC)
        return False
    print(info)

    uft8 = True
    if is_uft8_ext != None and filename.endswith(is_uft8_ext) == False:
        uft8 = False

    try:
        if uft8:
            file_content = Path(filename).read_text(encoding="utf-8")
        else:
            file_content = Path(filename).read_bytes()
    except OSError:
        sys.exit("Ups, can't read " + filename)

    return file_content, uft8

def minify(cli, content, type, attach = None):
    if cli != "" and content != "":
        count_lines = content.count("\n")

        info = ("[" + type + "]").ljust(10, " ")
        print(info + bcolors.MAGENTA + str(count_lines) + bcolors.ENDC + " lines minified")

        result = subprocess.run(cli.split(), 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                text=True, 
                                input=content)
        if result.stderr != "":
            sys.exit("Minify failed " + result.stderr)

        content = result.stdout

        if attach != None:
            tag = soup.new_tag(type)
            tag.string = content
            attach.append(tag)

    return content

# ---
# House keeping ...
#
base_filename = os.path.basename(sys.argv[0])

# ---
# Prepare input and output filenames fra args
#
input_filename = "index.html"
output_filename = base_filename + ".index.html"

if len(sys.argv) > 1:
    input_filename = sys.argv[1]

if len(sys.argv) > 2:
    output_filename = sys.argv[2]

# ---
# Handle config file and build number / date stamp
#
json_config = {
    "build_no": 0,
    "exclude": [],
    "js_cli": "uglifyjs --toplevel --rename --no-annotations",
    "css_cli": "uglifycss",
    "html_cli": "html-minifier --remove-comments --remove-tag-whitespace --collapse-whitespace",
    "silence": False,
    "input_filename": input_filename,
    "output_filename": output_filename,
    "hot_fix_html": {}
}

config_filename = "." + base_filename + ".json"

try:
    f = open(config_filename)
    json_loaded = json.load(f)

    json_config = {**json_config, **json_loaded}
except Exception as e:
    pass

if json_config["input_filename"] == json_config["output_filename"]:
    sys.exit("Ups, input and output filename are equal!")

if json_config["silence"] is True:
    sys.stdout = open(os.devnull, 'w')

# Update config file with the next build number
json_config["build_no"] = json_config["build_no"] + 1
json_config["build_timestamp"] = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

with open(config_filename, "w") as outfile:
    try:
        json.dump(json_config, outfile, indent=4)
    except OSError:
        sys.exit("Ups, can't write " + config_filename)

# ---
# Read source file
#
try:
    print("<", json_config["input_filename"])
    original_html_text = Path(json_config["input_filename"]).read_text(encoding="utf-8")
except OSError:
    sys.exit("Ups, can't read " + json_config["input_filename"])

soup = BeautifulSoup(original_html_text, features="html.parser")

# ---
# Find <script> tags. 
#
# Example: <script src="js/somescript.js"></script> or <script> ... </script>
#
scripts = ""
for tag in soup.find_all('script'):
    if tag.has_attr('src'):
        file_content, utf8 = read_file(tag['src'], "script")

        scripts += "\n" + file_content + "\n"
    else:
        print("[script]  <script>")
        scripts += "\n" +  tag.string + "\n"

    tag.extract()

scripts += (
    "DEPOLY_VERSION = true;"
    "DEPOLY_BUILD_NO = " + str(json_config["build_no"]) + ";"
    "DEPLOY_TIME_STAMP = '" + json_config["build_timestamp"] + "';"
    "if (DEPLOY_PRODUCTION === true) {"
    "    console.log = function() {};"
    "    console.warn = function() {};"
    "    console.error = function() {};"
    "}"
)

minify(json_config["js_cli"], scripts, "script", soup.html.body)

# ---
# Find <link> tags.
#
# # Example: <link rel="stylesheet" href="css/somestyle.css">
#
styles = ""
for tag in soup.find_all('link', rel="stylesheet", href=True):
    file_content, utf8 = read_file(tag['href'], "style")

    styles += "\n" + file_content + "\n"

    tag.extract()

minify(json_config["css_cli"], styles, "style", soup.html.head)

# ---
# Find <img> tags. 
#
# Example: <img src="img/example.svg">
#
for tag in soup.find_all('img', src=True):
    file_content, utf8 = read_file(tag['src'], "image", ".svg")

    if utf8:
        # replace filename with svg content of the file
        svg = BeautifulSoup(file_content, "xml")
        tag.replace_with(svg)
    else:
        # replace filename with base64 of the content of the file
        try:
            base64_file_content = base64.b64encode(file_content)
            base64_ascii = base64_file_content.decode('ascii')
            tag['src'] = "data:image/png;base64, {}".format(base64_ascii)
        except TypeError:
            print(bcolors.WARNING + "[image]   Can't encode " + tag['src'] + bcolors.ENDC)

# ---
# Minifing html
#
html_text = str(soup)
minified_html = minify(json_config["html_cli"], html_text, "html")

if "hot_fix_html" in json_config:
    hot_fix = json_config["hot_fix_html"]
    for (key, value) in hot_fix.items():
        minified_html = minified_html.replace(key, value)

# ---
# Save onto a single html file
#
if json_config["output_filename"] != "":
    try:
        Path(json_config["output_filename"]).write_text(minified_html, encoding="utf-8")
    except IOError:
        sys.exit("Ups, can't write " + json_config["output_filename"])
else:
    print(minified_html)

print((
    "> " + json_config["output_filename"] + ' | ' + json_config["build_timestamp"] + 
    ", build " + bcolors.BOLD + bcolors.YELLOW + 
    "#" + str(json_config["build_no"]) + bcolors.ENDC
))
