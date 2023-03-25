#!/usr/bin/python3

#
# The main purpose of the project to make it extreamly easy to upload a
# "web application" by uploading a single .html file
#
# This is done by reading ./index.html and creating one fil (./index.deploy.html) 
# that containes all external files refarnces (scripts, styles and images).
# index.deploy.html is a self containes "application" without any dependecies
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
import htmlmin
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

def parse_filename(filename, info):
    filename = filename.strip()

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
    return filename

def read_file(ref, type):
    filename = parse_filename(ref, type)
    if filename is False:
        return False

    try:
        file_content = Path(filename).read_text(encoding="utf-8")
    except OSError:
        sys.exit("Ups, can't read " + filename)

    return file_content

def minify(cli, content):
    if cli and cli != "":
        result = subprocess.run(cli.split(), 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                text=True, 
                                input=content)
        if result.stderr != "":
            sys.exit("Minify failed " + result.stdout)

        content = result.stdout

    return content

base_dir_pair = os.path.split(sys.argv[0])

# ---
# Prepare input and output filenames
#
if len(sys.argv) > 1:
    input_filename = sys.argv[1]
else:
    input_filename = "index.html"

if len(sys.argv) > 2:
    output_filename = sys.argv[2]
else:
    output_filename = base_dir_pair[1] + ".index.html"

# ---
# Handle config file and build number / date stamp
#
config_filename = "." + base_dir_pair[1] + ".json"
if os.path.exists(config_filename) is False:
    config_filename_home = base_dir_pair[0] + "/." + base_dir_pair[1] + ".json"
    if os.path.exists(config_filename_home):
        config_filename = config_filename_home

try:
    f = open(config_filename)
    json_config = json.load(f)

    print("<", config_filename)
except Exception as e:
    print("+", config_filename)
    json_config = {}

if json_config.get("build_no") is None:
    json_config["build_no"] = 0

if json_config.get("exclude") is None:
    json_config["exclude"] = []

if json_config.get("js_cli") is None:
    json_config["js_cli"] = "uglifyjs"

if json_config.get("css_cli") is None:
    json_config["css_cli"] = "uglifycss"

if json_config.get("input_filename") != None:
    input_filename = json_config["input_filename"]

if json_config.get("output_filename") != None:
    output_filename = json_config["output_filename"]

if input_filename == output_filename:
    sys.exit("Ups, input and output filename are the same!")

# Update config file with the next build number
json_config["build_no"] = json_config["build_no"] + 1
json_config["build_timestamp"] = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

with open(config_filename, "w") as outfile:
    json.dump(json_config, outfile, indent=4)

# ---
# Read source file
#
print("<", input_filename)
try:
    original_html_text = Path(input_filename).read_text(encoding="utf-8")
except OSError:
    sys.exit("Ups, can't read " + input_filename)
soup = BeautifulSoup(original_html_text, features="html.parser")

# ---
# Find <script> tags. 
#
# Example: <script src="js/somescript.js"></script> or <script> ... </script>
#
scripts = ""
for tag in soup.find_all('script'):
    if tag.has_attr('src'):
        file_text = read_file(tag['src'], "script")

        scripts += "\n" + file_text + "\n"
    else:
        print("[script]  <script>")
        scripts += "\n" +  tag.string + "\n"

    tag.extract()

scripts += (
    "\n\n" 
    "/* AUTO GENERATED */\n"
    "DEPOLY_VERSION = true;\n"
    "DEPOLY_BUILD_NO = " + str(json_config["build_no"]) + ";\n"
    "DEPLOY_TIME_STAMP = '" + json_config["build_timestamp"] + "';"
)

scripts = minify(json_config["js_cli"], scripts)

new_script = soup.new_tag('script')
new_script.string = scripts
soup.html.body.append(new_script)

# ---
# Find <link> tags.
#
# # Example: <link rel="stylesheet" href="css/somestyle.css">
#
styles = ""
for tag in soup.find_all('link', rel="stylesheet", href=True):
    file_text = read_file(tag['href'], "style")

    styles += "\n" + file_text + "\n"

    tag.extract()

if len(styles) != 0:
    styles = minify(json_config["css_cli"], styles)

    # insert styles if they exists
    new_style = soup.new_tag('style')
    new_style.string = styles
    soup.html.head.append(new_style)

# ---
# Find <img> tags. 
#
# Example: <img src="img/example.svg">
#
for tag in soup.find_all('img', src=True):
    filename = parse_filename(tag['src'], "image")
    if filename is False:
        continue

    if filename.endswith('.svg'):
        try:
            file_text = Path(filename).read_text(encoding="utf-8")
        except OSError:
            sys.exit("Ups, can't read " + filename)

        # replace filename with svg content of the file
        svg = BeautifulSoup(file_text, "xml")
        tag.replace_with(svg)
    else:
        try:
            file_content = Path(filename).read_bytes
        except OSError:
            sys.exit("Ups, can't read " + filename)

        # replace filename with base64 of the content of the file
        base64_file_content = base64.b64encode(file_content)
        base64_ascii = base64_file_content.decode('ascii')
        tag['src'] = "data:image/png;base64, {}".format(base64_ascii)

# ---
# Save onto a single html file
#
print((
    "> " + output_filename + ' | ' + json_config["build_timestamp"] + 
    ", build " + bcolors.BOLD + bcolors.YELLOW + 
    "#" + str(json_config["build_no"]) + bcolors.ENDC
))

final_html = str(soup)
final_html = htmlmin.minify(final_html)

try:
    Path(output_filename).write_text(final_html, encoding="utf-8")
except OSError:
    sys.exit("Ups, can't write " + output_filename)
