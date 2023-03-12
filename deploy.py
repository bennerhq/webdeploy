#!/usr/bin/python3

import sys
import base64
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

# ---
# Prepare input and output filenames
#
input_filename = "index.html"
output_filename = "deploy." + input_filename

if len(sys.argv) > 1:
    input_filename = sys.argv[1]
if len(sys.argv) > 2:
    output_filename = sys.argv[2]

if input_filename == output_filename:
    sys.exit("Ups, input and output filename are the same!")

now = datetime.now()
now_string = now.strftime("%Y/%m/%d %H:%M:%S")

# Read source file
#
print("<", input_filename)
original_html_text = Path(input_filename).read_text(encoding="utf-8")
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

        file_text = Path(filename).read_text(encoding="utf-8")

        scripts += "\n" + file_text + "\n"
    else:
        print("[script]  <script>")
        scripts += "\n" +  tag.string + "\n"

    tag.extract()

if len(scripts) != 0:
    # insert scripts if they exists
    scripts = "\n/* AUTO GENERATED */\nconst DEPLOY_TIME_STAMP = '" + now_string + "';\n\n" + scripts;

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

    file_text = Path(filename).read_text(encoding="utf-8")

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
        file_text = Path(filename).read_text(encoding="utf-8")

        # replace filename with svg content of the file
        svg = BeautifulSoup(file_text, "xml")
        tag.replace_with(svg)
    else:
        file_content = Path(filename).read_bytes()

        # replace filename with base64 of the content of the file
        base64_file_content = base64.b64encode(file_content)
        tag['src'] = "data:image/png;base64, {}".format(base64_file_content.decode('ascii'))

# ---
# Save onto a single html formattet file
#
print(">", output_filename, '|', now_string)

with open(output_filename, "w", encoding="utf-8") as outfile:
    outfile.write(str(soup))
