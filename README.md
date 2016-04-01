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

Most common usage would be: py release.py -ruvms-VERSION-SPRINT -b -p

```
Usage: py release.py -rreleaseName [-c./] [-d] [-p] [-j8] [-s] [-m"module1 module2 ... moduleN"] [-b] [-vx.y.z] [-na.b.c-SNAPSHOT]
-r Release name or version for branching and checkout dir.
-d Dry run, only checkout, prepare and rollback run. Only works on existing branch.
-p Paranoia flag. Must be set to actually perform anything. If not set, svn revert and svn update will be run at the end.
-j8 If present, javadoc lint errors are ignored.
-m Module list, format is "module1 module2 ... moduleN". If left out, all modules are released.
-e Plugin list, format is "plugin1 plugin2 ... pluginN". If left out, all plugins are released.
-x Proxy list, format is "module/PROXY/proxy1 module/PROXY/proxy2 ... module/PROXY/proxyN". If left out, all plugins are released.
-l Library list, format is "library1 library2 ... libraryN". If left out, all libraries are released.
-c Check out root dir. Defaults to "C:".
-s Do not replace SNAPSHOT versions with matching release version. If set, Maven will ask for versions during prepare step.
-b Maven prepare batch, non interactive prepare. This will force the use of the next version.
-v Release version.
-n Next SNAPSHOT version.
```
