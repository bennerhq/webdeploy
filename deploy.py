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
# /benner, 2023
# jens@bennerhq.com
#

import os
import sys
import base64
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import configparser

def read_file(filename, utf8 = True, res = None):
    try:
        if utf8:
            file_content = Path(filename).read_text(encoding="utf-8")
        else:
            file_content = Path(filename).read_bytes()
    except OSError:
        if res == None:
            sys.exit("Ups, can't read " + filename)
        else:
            file_content = res

    return file_content

# ---
# Prepare input and output filenames
#
basename = os.path.basename(sys.argv[0])
config_filename = "." + basename

input_filename = "index.html"
output_filename = basename + ".index.html"
if len(sys.argv) > 1:
    input_filename = sys.argv[1]
if len(sys.argv) > 2:
    output_filename = sys.argv[2]

# ---
# Handle confile file and build number
#
now = datetime.now()
now_string = now.strftime("%Y/%m/%d %H:%M:%S")

try:
    config = configparser.ConfigParser()
    config.read(config_filename)
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
    build_no = str(int(build_no) + 1)
except Exception as e:
    build_no = "0"
    config["build"] = {}

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
        filename = tag['src'].strip()
        print("[script] ", filename)

        file_text = read_file(filename)

        scripts += "\n" + file_text + "\n"
    else:
        print("[script]  <script>")
        scripts += "\n" +  tag.string + "\n"

    tag.extract()

# insert scripts if they exists
scripts += "\n\n/* AUTO GENERATED */\nDEPOLY_VERSION = true;\nDEPOLY_BUILD_NO = " + build_no + ";\nDEPLOY_TIME_STAMP = '" + now_string + "';\n\n";

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
    filename = tag['href'].strip()
    print("[style]  ", filename)

    file_text = read_file(filename)

    styles += "\n" + file_text + "\n"

    tag.extract()

if len(styles) != 0:
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
    filename = tag['src'].strip()
    print("[image]  ", filename)

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
print("> " + output_filename + ' | ' + now_string + ", build #" + build_no)

try:
    Path(output_filename).write_text(str(soup), encoding="utf-8")
except OSError:
    sys.exit("Ups, can't write " + output_filename)
