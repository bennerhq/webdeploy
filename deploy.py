#!/usr/bin/python3

from bs4 import BeautifulSoup
from pathlib import Path
import base64

start_filename = "index.html"
final_filename = "deploy." + start_filename

# ------
# Read source file
#
print("<", start_filename)
original_html_text = Path(start_filename).read_text(encoding="utf-8")
soup = BeautifulSoup(original_html_text, features="html.parser")

# ------
# Find script tags. example: <script src="js/somescript.js"></script>
#
scripts = ""
for tag in soup.find_all('script'):
    if tag.has_attr('src'):
        filename = tag['src'].strip()
        print("+ script  ", filename)

        file_text = Path(filename).read_text(encoding="utf-8")

        # remove the tag from soup

        scripts += "\n" + file_text + "\n"
    else:
        print("+ script   <script>")
        scripts += "\n" +  tag.string + "\n"

    tag.extract()

# insert script element
if len(scripts) != 0:
    new_script = soup.new_tag('script')
    new_script.string = scripts
    soup.html.body.append(new_script)

# ------
# Find link tags. example: <link rel="stylesheet" href="css/somestyle.css">
#
styles = ""
for tag in soup.find_all('link', href=True):
    if tag["rel"][0] == "stylesheet":
        filename = tag['href'].strip()
        print("+ style   ", filename)

        file_text = Path(filename).read_text(encoding="utf-8")

        # remove the tag from soup
        tag.extract()

        styles += "\n" + file_text + "\n"

# insert style element
if len(styles) != 0:
    new_style = soup.new_tag('style')
    new_style.string = styles
    soup.html.head.append(new_style)

# ------
# Find image tags.
#
for tag in soup.find_all('img', src=True):
    filename = tag['src'].strip()
    print("+ image   ", filename)

    if filename.endswith('.svg'):
        file_text = Path(filename).read_text(encoding="utf-8")

        svg = BeautifulSoup(file_text, "xml")
        tag.replace_with(svg)
    else:
        file_content = Path(filename).read_bytes()

        # replace filename with base64 of the content of the file
        base64_file_content = base64.b64encode(file_content)
        tag['src'] = "data:image/png;base64, {}".format(base64_file_content.decode('ascii'))

# ------
# Save into one file
#
print(">", final_filename)

with open(final_filename, "w", encoding="utf-8") as outfile:
    outfile.write(str(soup))
