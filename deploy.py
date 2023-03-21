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
# /benner, 2023
# jens@bennerhq.com
#

import os
import subprocess
import sys
import os.path
import base64
import configparser
import htmlmin
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

def read_file(filename, utf8 = True, res = None):
    try:
        if utf8:
            content = Path(filename).read_text(encoding="utf-8")
        else:
            content = Path(filename).read_bytes()
    except OSError:
        if res != None:
            content = res
        else:
            sys.exit("Ups, can't read " + filename)

    return content

def minify(cli, content):
    if cli:
        result = subprocess.run(cli.split(), 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                text=True, 
                                input=content)
        if result.stderr != "":
            sys.exit("Minify failed " + result.stdout)

        content = result.stdout

    return content

def parse_filename(filename, type):
    filename = filename.strip()

    idx = filename.find("+")
    if idx != -1:
        return False

    idx = filename.find("?")
    if idx != -1:
        filename = filename[:idx]

    type = ("[" + type + "]").ljust(10, " ")

    if filename in exclude_files:
        print(type + filename + bcolors.WARNING + "  excluded" + bcolors.ENDC)
        return False

    print(type + filename)
    return filename

# ---
# Prepare input and output filenames
#
base_dir_pair = os.path.split(sys.argv[0])

minifijs_cli = "uglifyjs"
minificss_cli = "uglifycss"

if len(sys.argv) > 1:
    input_filename = sys.argv[1]
else:
    input_filename = "index.html"

if len(sys.argv) > 2:
    output_filename = sys.argv[2]
else:
    output_filename = base_dir_pair[1] + ".index.html"

# ---
# Handle config file and build number
#
now = datetime.now()
now_string = now.strftime("%Y/%m/%d %H:%M:%S")

config = configparser.ConfigParser()

config_filename = "./." + base_dir_pair[1]
if os.path.exists(config_filename):
    print("< ", config_filename)
else:
    config_filename = base_dir_pair[0] + "/." + base_dir_pair[1]
    if not os.path.exists(config_filename):
        config_filename = None
if config_filename is not None:
    config.read(config_filename)

try:
    exclude_files = config["content"]["exclude"]
    exclude_files = exclude_files.split(":")
except Exception as e:
    exclude_files = []

try:
    minifijs_cli = config["minify"]["js_cli"]
except Exception as e:
    pass

try:
    input_filename = config["files"]["input"]
except Exception as e:
    pass

try:
    output_filename = config["files"]["output"]
except Exception as e:
    pass

try:
    build_no = config["build"]["number"]
except Exception as e:
    build_no = "0"
    config["build"] = {}

build_no = str(int(build_no) + 1)

config["build"]["number"] = build_no
config["build"]["time_stamp"] = now_string

with open(config_filename, 'w') as configfile:
  config.write(configfile)

if input_filename == output_filename:
    sys.exit("Ups, input and output filename are the same!")

# ---
# Read source file
#
print("<", input_filename)
original_html_text = read_file(input_filename)
soup = BeautifulSoup(original_html_text, features="html.parser")

# ---
# Find <script> tags. 
#
# Example: <script src="js/somescript.js"></script> or <script> ... </script>
#
scripts = ""
for tag in soup.find_all('script'):
    if tag.has_attr('src'):
        filename = parse_filename(tag['src'], "script")
        if filename is False:
            continue

        file_text = read_file(filename)

        scripts += "\n" + file_text + "\n"
    else:
        print("[script]  <script>")
        scripts += "\n" +  tag.string + "\n"

    tag.extract()

# insert scripts if they exists
scripts += (
    "\n\n" 
    "/* AUTO GENERATED */\n"
    "DEPOLY_VERSION = true;\n"
    "DEPOLY_BUILD_NO = " + build_no + ";\n"
    "DEPLOY_TIME_STAMP = '" + now_string + "';\n"
    "\n"
)

scripts = minify(minifijs_cli, scripts)

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
    filename = parse_filename(tag['href'], "style")
    if filename is False:
        continue

    file_text = read_file(filename)

    styles += "\n" + file_text + "\n"

    tag.extract()

if len(styles) != 0:
    styles = minify(minificss_cli, styles)

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
        file_text = read_file(filename)

        # replace filename with svg content of the file
        svg = BeautifulSoup(file_text, "xml")
        tag.replace_with(svg)
    else:
        file_content = read_file(filename, False)

        # replace filename with base64 of the content of the file
        base64_file_content = base64.b64encode(file_content)
        tag['src'] = "data:image/png;base64, {}".format(base64_file_content.decode('ascii'))

# ---
# Save onto a single html file
#
print("> " + output_filename + ' | ' + now_string + ", build " + bcolors.BOLD + bcolors.BG_RED + "#" + build_no + bcolors.ENDC)

final_html = str(soup)
final_html = htmlmin.minify(final_html)

try:
    Path(output_filename).write_text(final_html, encoding="utf-8")
except OSError:
    sys.exit("Ups, can't write " + output_filename)
