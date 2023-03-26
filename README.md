The main purpose of the project to make it extreamly easy to upload a 
"web application" by uploading a single .html file

This is done by reading ./index.html and creating one file (./deploy.index.html) 
that containes all external files refarnces (scripts, styles and images).
deploy.index.html is a self containes "application" without any dependecies
or referances to external files.

It's not a "bullet proff" solution, but for simple "web application"
it's okay!

This version is inspired / extended from this stackoverflow post
https://stackoverflow.com/questions/44646481/merging-js-css-html-into-single-html

/benner, March 2023
jens@bennerhq.com
