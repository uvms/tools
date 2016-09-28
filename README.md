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

## release.py
This script releases the following modules: hav-vessel-proxy, eu-vessel-proxy, twostage, sweagencyemail, siriusone, naf, flux, email, ais, rules-dbaccess, movement-dbaccess, mobileterminal-dbaccess, exchange-dbaccess, audit-dbaccess, asset-dbaccess, config-dbaccess, rules, movement, mobileterminal, exchange, audit, asset, config, uvms-longpolling, uvms-commons, uvms-config, usm4uvms, rules-model, movement-model, mobileterminal-model, exchange-model, audit-model, asset-model, config-model

Most common usage on Windows would be:
```
py release.py -ruvms-VERSION-SPRINT
```
Most common usage on Linux/OSX would be:
```
py release.py -ruvms-VERSION-SPRINT -c~/
```

```
Usage: py release.py -rreleaseName 
-r Release name or version for branching and checkout dir.
-s Starting step
-c Check out root, ie ~/ or c:\temp
-v Validate build
-d date limit, format is YYMMDD, ie 160930
```
