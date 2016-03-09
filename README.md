# Tools
## prependLicense.py
This script is used to prepend license text to java files. It also strips any '@author' tags.
Usage:
py prependLicense.py "path to project" "path to license text file"

"path to project" is the directory to start looking for java files in. All subdirectories of this directory will be scanned. If this is left out, the current working directory is used and "path to license text file" must be left out.
"path to license text file" is the location of a file containing the text that will be prepended to the java files. If this is left out, the script will assume that a file called 'licenseText.txt' is present in "path to project" or the current working directory.
