import subprocess
import sys
import os
import shutil
import fileinput
import xml.etree.ElementTree as ET
import getpass
import time
startTime = time.time()

release = ''
java8 = False
dryRun = False
perform = False
replaceSnaphots = True
checkOutRoot = "C:"
modList = []
pluginList = []
proxyList = []
libraryList = []
batch = False
releaseVersion = ''
devVersion = ''
tempDevDir = 'temp-dev'

for arg in sys.argv:
    if arg.startswith('-c'):
        checkOutRoot = arg.replace('-c', '', 1)
    if arg.startswith('-p'):
        perform = True
    if arg.startswith('-d'):
        print(arg)
        dryRun = True
    if arg.startswith('-r'):
        release = arg.replace('-r', '', 1)
    if arg.startswith('-j8'):
        java8 = True
    if arg.startswith('-m'):
        print(arg)
        tmpList = arg.replace('-m', '', 1)
        modList = tmpList.split(' ')
    if arg.startswith('-e'):
        print(arg)
        tmpList = arg.replace('-e', '', 1)
        pluginList = tmpList.split(' ')
    if arg.startswith('-x'):
        print(arg)
        tmpList = arg.replace('-x', '', 1)
        proxyList = tmpList.split(' ')
    if arg.startswith('-l'):
        print(arg)
        tmpList = arg.replace('-l', '', 1)
        libraryList = tmpList.split(' ')
    if arg.startswith('-s'):
        replaceSnaphots = False
    if arg.startswith('-b'):
        batch = True
    if arg.startswith('-v'):
        releaseVersion = arg.replace('-v', '', 1)
    if arg.startswith('-n'):
        devVersion = arg.replace('-n', '', 1)

def printHelp():
    print('py release.py -rreleaseName [-c./] [-d] [-p] [-j8] [-s] [-m"module1 module2 ... moduleN"] [-b] [-vx.y.z] [-na.b.c-SNAPSHOT]')
    print('-r Release name or version for branching and checkout dir.')
    print('-d Dry run, only checkout, prepare and rollback run. Only works on existing branch.')
    print('-p Paranoia flag. Must be set to actually perform anything. If not set, svn revert and svn update will be run at the end.')
    print('-j8 If present, javadoc lint errors are ignored.')
    print('-m Module list, format is "module1 module2 ... moduleN". If left out, all modules are released.')
    print('-e Plugin list, format is "plugin1 plugin2 ... pluginN". If left out, all plugins are released.')
    print('-x Proxy list, format is "module/PROXY/proxy1 module/PROXY/proxy2 ... module/PROXY/proxyN". If left out, all plugins are released.')
    print('-l Library list, format is "library1 library2 ... libraryN". If left out, all libraries are released.')
    print('-c Check out root dir. Defaults to "C:".')
    print('-s Do not replace SNAPSHOT versions with matching release version. If set, Maven will ask for versions during prepare step.')
    print('-b Maven prepare batch, non interactive prepare. This will force the use of the next version.')
    print('-v Release version.')
    print('-n Next SNAPSHOT version.')

if release == '':
    print('No release specified')
    printHelp()
    sys.exit(-1)
if len(releaseVersion) == 0 and not batch:
    print('No release version specified')
    printHelp()
    sys.exit(-1)
if len(devVersion) == 0 and not batch:
    print('No development version specified')
    printHelp()
    sys.exit(-1)
if len(releaseVersion) == 0 and len(devVersion) == 0 and not batch:
    print('Maven batch prepare not set and not versions set')
    printHelp()
    sys.exit(-1)

svnDev = 'https://webgate.ec.europa.eu/CITnet/svn/UNIONVMS/branches/dev'
svnBranch = 'https://webgate.ec.europa.eu/CITnet/svn/UNIONVMS/branches/releases/%s' % (release)

if len(modList) == 0:
    modList = ['Config', 'Asset', 'Audit', 'Exchange', 'MobileTerminal', 'Movement', 'Rules']
if len(pluginList) == 0:
    pluginList = ['ais', 'email', 'flux', 'naf', 'siriusone', 'swagencyemail', 'twostage']
if len(proxyList) == 0:
    proxyList = ['Asset/PROXY/eu-vessel-proxy', 'Asset/PROXY/hav-vessel-proxy']
if len(libraryList) == 0:
    libraryList = ['usm4uvms', 'uvms-config', 'uvms-commons', 'uvms-longpolling']

appPaths = []
dbPaths = []
modelPaths = []
for module in modList:
    path = r'%s/%s/Modules/%s/APP' % (checkOutRoot, release, module)
    appPaths.append(path)
    path = r'%s/%s/Modules/%s/DB' % (checkOutRoot, release, module)
    dbPaths.append(path)
    path = r'%s/%s/Modules/%s/APP/model' % (checkOutRoot, release, module)
    modelPaths.append(path)

pluginPaths = []
for plugin in pluginList:
    path = r'%s/%s/Modules/Exchange/PLUGIN/%s' % (checkOutRoot, release, plugin)
    pluginPaths.append(path)

proxyPaths = []
for proxy in proxyList:
    path = r'%s/%s/Modules/%s' % (checkOutRoot, release, proxy)
    proxyPaths.append(path)

libraryPaths = []
for library in libraryList:
    path = r'%s/%s/Libraries/%s' % (checkOutRoot, release, library)
    libraryPaths.append(path)

def externalError(process, path, stage):
    print("Error during stage '%s'" % (stage))
    print("Process '%s' returned code %s" % (process.args, process.returncode))
    print("Path was %s" % (path))
    print("Run time: %s " % (time.time() - startTime))
    sys.exit(process.returncode)

def branch():
    process = subprocess.Popen(['svn', 'ls', svnBranch, '--depth', 'empty'], shell=False)
    process.wait()
    if process.returncode != 0:
        branchMessage = 'Branching from dev to %s' % (release)
        print(branchMessage)
        runSubProcess(['svn', 'copy', svnDev, svnBranch, '-m', branchMessage], False, '', 'branch')
    else:
        print('Branch %s already exits. No new branch created' % (release))

def checkOut(svnPath, checkOutPath):
    newpath = r'%s/%s' % (checkOutRoot, checkOutPath)
    if os.path.exists(newpath):
        revertPath = r'%s/%s' % (newpath, '*')
        print('Reverting %s in %s' % (checkOutPath, revertPath))
        runSubProcess(['svn', 'revert', '--recursive', revertPath], False, '', 'revert')
        print('Updating %s in %s' % (checkOutPath, newpath))
        runSubProcess(['svn', 'update', newpath], False, '', 'update')
    else:
        os.makedirs(newpath)
        print('Checking out %s to %s' % (checkOutPath, newpath))
        runSubProcess(['svn', 'co', svnPath, newpath], False, '', 'checkout')
    print('Check out done')

def commit(commitPath, commitMessage, add):
    newpath = r'%s/%s' % (checkOutRoot, commitPath)
    if add:
        addPath = r'%s/*' % (newpath)
        runSubProcess(['svn', 'add', addPath, '--force'], False, '', 'add')
    print('Commiting changes with message:')
    print(commitMessage)
    runSubProcess(['svn', 'ci', '-m', commitMessage, newpath], False, '', 'commit')

def commentSysOut(paths):
    textToSearch = "System.out"
    textToReplace = "//System.out"
    for path in paths:
        print("Replacing sysouts in %s" % (path))
        for subdir, dirs, files in os.walk(path):
            for file in files:
                if file.endswith('.java'):
                    fileToSearch = os.path.join(subdir, file)
                    with fileinput.FileInput(fileToSearch, inplace=True) as file:
                        for line in file:
                            print(line.replace(textToReplace, textToSearch), end='')
                    with fileinput.FileInput(fileToSearch, inplace=True) as file:
                        for line in file:
                            print(line.replace(textToSearch, textToReplace), end='')

def updatePoms(paths):
    print("Updating poms")
    ET.register_namespace("", "http://maven.apache.org/POM/4.0.0")
    for path in paths:
        path = path + "/pom.xml"
        tree = ET.parse(path)
        root = tree.getroot()
        hasScm = False
        for scm in root.iter('{http://maven.apache.org/POM/4.0.0}scm'):
            hasScm = True
            break
        if hasScm:
            for prop in root.iter('{http://maven.apache.org/POM/4.0.0}properties'):
                hasBranchProp = False
                for child in prop:
                    if child.tag == '{http://maven.apache.org/POM/4.0.0}release.branch.name':
                        hasBranchProp = True
                    if child.text is not None and '-SNAPSHOT' in child.text:
                        print("Replacing SNAPSHOT version for %s with release version" % (child.tag))
                        child.text = child.text.replace('-SNAPSHOT','')
                if not hasBranchProp:
                    print("No branch Tag in %s" % (path))
                    branchElement = ET.Element('{http://maven.apache.org/POM/4.0.0}release.branch.name');
                    branchElement.text = release
                    prop.append(branchElement)
            for branchName in root.iter('{http://maven.apache.org/POM/4.0.0}release.branch.name'):
                if branchName.text is None or branchName.text != release:
                    print("Replacing release version in %s" % (path))
                    branchName.text = release
            for connection in root.iter('{http://maven.apache.org/POM/4.0.0}connection'):
                if '{release.branch.name}' not in connection.text and 'releases/' in connection.text:
                    print("Replacing SCM tag in %s" % (path))
                    parts = connection.text.split('releases/')
                    if len(parts) != 2:
                        connection.text = connection.text.replace('dev', 'releases')
                        parts = connection.text.split('releases/')
                        print(connection.text)
                    lastParts = parts[1].split('/')
                    newScmText = parts[0] + '${release.branch.name}'
                    for i in range(1, len(lastParts)):
                        newScmText = newScmText + '/' + lastParts[i]
                    connection.text = newScmText
                elif '{release.branch.name}' not in connection.text and 'dev/' in connection.text:
                    print("Replacing SCM tag in %s" % (path))
                    connection.text = connection.text.replace('dev', 'releases/${release.branch.name}')
            tree.write(path)

def updateLogback(paths, logbackLocation):
    print("Updating logback")
    for path in paths:
        path = path + logbackLocation
        tree = ET.parse(path)
        root = tree.getroot()
        for rootTag in root.iter('root'):
            if rootTag.get('level') != 'INFO':
                print("Setting log level in %s" % (path))
                rootTag.set('level', 'INFO')
        tree.write(path)

def generateSources():
    print("Generating from WSDL")
    for path in modelPaths:
        pomPath = path + '/pom.xml'
        sourcePath = path + '/src'
        runSubProcess(['mvn', 'clean', 'install', '-Pgenerate-from-wsdl', '-f', pomPath], True, pomPath, 'generateSources')
        runSubProcess(['svn', 'add', sourcePath, '--force', '--no-ignore'], False, sourcePath, 'add')

def releasePrepare(path):
    path = path + '/pom.xml'
    print('Preparing release %s' % (path))
    if batch:
        runSubProcess(['mvn', 'release:prepare', '-f', path, '-B'], True, path, 'prepare')
    else:
        runSubProcess(['mvn', 'release:prepare', '-f', path, '-DreleaseVersion=%s'%(releaseVersion), '-DdevelopmentVersion=%s'%(devVersion)], True, path, 'prepare')

def releaseRollback(path):
    path = path + '/pom.xml'
    print('Rollback release %s' % (path))
    runSubProcess(['mvn', 'release:rollback', '-f', path], True, path, 'rollback')

def releasePerform(path):
    path = path + '/pom.xml'
    print('Performing release %s' % (path))
    if java8:
        runSubProcess(['mvn', 'release:perform', '-Darguments="-Dmaven.javadoc.failOnError=false"', '-f', path], True, path, 'perform')
    else:
        runSubProcess(['mvn', 'release:perform', '-f', path], True, path, 'perform')

def doRelease(paths):
    for path in paths:
        releasePrepare(path)
        releasePerform(path)

def performDryRun(paths):
    for path in paths:
        releasePrepare(path)
        releaseRollback(path)

def merge():
    checkOut(svnDev, tempDevDir)
    copy(libraryPaths)
    copy(modelPaths)
    copy(appPaths)
    copy(dbPaths)
    copy(pluginPaths)
    copy(proxyPaths)
    commit(tempDevDir, "'@Review %s Merged back poms'" % (getpass.getuser()), True)

def copy(paths):
    for path in paths:
        for subdir, dirs, files in os.walk(path):
            for file in files:
                if file.endswith('pom.xml') and 'target' not in subdir:
                    fileToCopy = os.path.join(subdir, file)
                    target = fileToCopy.replace(release, tempDevDir)
                    print('%s -> %s' % (fileToCopy, target))
                    shutil.copy2(fileToCopy, target)

def clean():
    newpath = r'%s/%s' % (checkOutRoot, release)
    shutil.rmtree(newpath)
    tempPath = r'%s/%s' % (checkOutRoot, tempDevDir)
    shutil.rmtree(tempPath)

def runSubProcess(command, shell, path, stage):
    process = subprocess.Popen(command, shell=shell)
    process.wait()
    if process.returncode != 0:
        externalError(process, path, stage)

if dryRun:
    print("Dry run!")
    checkOut(svnBranch, release)
    performDryRun(libraryPaths)
    performDryRun(modelPaths)
    performDryRun(appPaths)
    performDryRun(dbPaths)
    performDryRun(pluginPaths)
    performDryRun(proxyPaths)
    checkOut(svnBranch, release)
else:
    print("Real!")
    if perform:
        print('Really for real!')
        branch()
    checkOut(svnBranch, release)
    commentSysOut(libraryPaths)
    commentSysOut(modelPaths)
    commentSysOut(appPaths)
    commentSysOut(dbPaths)
    commentSysOut(pluginPaths)
    commentSysOut(proxyPaths)
    generateSources()
    updatePoms(libraryPaths)
    updatePoms(modelPaths)
    updatePoms(appPaths)
    updatePoms(dbPaths)
    updatePoms(pluginPaths)
    updatePoms(proxyPaths)
    updateLogback(appPaths, '/service/src/main/resources/logback.xml')
    updateLogback(dbPaths, '/domain/src/main/resources/logback.xml')
    updateLogback(pluginPaths, '/service/src/main/resources/logback.xml')
    updateLogback(proxyPaths, '/service/src/main/resources/logback.xml')
    if perform:
        print('Really for real!')
        commit(release, "'@Review %s Build Dtos from model and change to releasebranch in poms'" % (getpass.getuser()), True)
        doRelease(modelPaths)
        doRelease(libraryPaths)
        doRelease(appPaths)
        doRelease(dbPaths)
        doRelease(pluginPaths)
        doRelease(proxyPaths)
        merge()
        clean()
    else:
        checkOut(svnBranch, release)

print("Done! Run time: %s " % (time.time() - startTime))
