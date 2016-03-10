# Tools
## prependLicense.py
This script is used to prepend license text to java, xsd and wsdl files. It also strips any '@author' tags from java files.

###Usage:
 
```
Usage: prependLicense.py [options]
-c      Ignore C style files ['java', 'js', 'css']
-a      Do not break before performing search and prepend
-x      Ignore XML style files ['xsd', 'wsdl', 'html', 'xml']
-l      -l <path> Text file containing license text
-help   Display this help
-h      Display this help
-r      -r <path> Root directory of search
Example: py prependLicense.py -r "c:\dev\modules" -l "c:\dev\license.txt" -x -a
```