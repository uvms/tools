import subprocess
import sys
import os
import shutil
import fileinput
import xml.etree.ElementTree as ET
import getpass
import time
import stat
from collections import OrderedDict
startTime = time.time()

release = ''
replaceSnaphots = True
checkOutRoot = "C:"
modList = []
pluginList = []
proxyList = []
libraryList = []
batch = True
releaseVersion = ''
devVersion = ''
tempDevDir = 'temp-dev'
step = '1-models.AssetModule'
currentStep = step
validateBuild = False

user = 'USER'
password = 'PASSWORD'

gitHubBase = "https://%s:%s@github.com/UnionVMS/UVMS-" % (user, password)

unorderedSteps = {
    '1-models': ['AssetModule', 'ConfigModule', 'AuditModule', 'ExchangeModule', 'RulesModule', 'MovementModule', 'MobileTerminalModule'],
    '2-libs': ['UVMSConfigLibrary', 'UVMSLongPollingLibrary', 'USM4UVMSLibrary'],
    '3-apps': ['ConfigModule', 'AssetModule', 'AuditModule', 'ExchangeModule', 'RulesModule', 'MovementModule', 'MobileTerminalModule'],
    '4-db': ['ConfigModule', 'AssetModule', 'AuditModule', 'ExchangeModule', 'RulesModule', 'MovementModule', 'MobileTerminalModule'],
    '5-proxies': ['AssetModule-PROXY-EU', 'AssetModule-PROXY-HAV']
    #'6-ra': ['Exchange/PLUGIN/ais/ais-ra'],
    #'7-plugins': ['ais', 'email', 'flux', 'naf', 'siriusone', 'swagencyemail', 'twostage'],
    #'8-frontend': ['unionvms-web']
}
steps = OrderedDict(sorted(unorderedSteps.items(), key=lambda t: t[0]))

for arg in sys.argv:
    if arg.startswith('-c'):
        checkOutRoot = arg.replace('-c', '', 1)
    if arg.startswith('-r'):
        release = arg.replace('-r', '', 1)
    if arg.startswith('-s'):
        step = arg.replace('-s', '', 1)
    if arg.startswith('-v'):
        validateBuild = True

svnBranch = 'https://webgate.ec.europa.eu/CITnet/svn/UNIONVMS/branches/releases/%s' % (release)

def del_rw(action, name, exc):
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)

def externalError(process, path, stage):
    print("Error during stage '%s'" % (stage))
    print("Process '%s' returned code %s" % (process.args, process.returncode))
    print("Path was %s" % (path))
    print("Run time: %s " % (time.time() - startTime))
    print("Error occured during step %s." % (currentStep))
    print("Please fix any errors and commit your changes before re-running with -s%s to continue." % (currentStep))
    sys.exit(process.returncode)

def checkOut(repo, checkOutPath):
    if os.path.exists(checkOutPath):
        shutil.rmtree(checkOutPath, onerror=del_rw)
    os.makedirs(checkOutPath)
    os.chdir(checkOutPath)
    print('Checking out %s to %s' % (repo, checkOutPath))
    runSubProcess(['git', 'clone', repo, checkOutPath], False, '', 'checkout')
    runSubProcess(['git', 'checkout', '-b', release], False, '', 'checkout')
    runSubProcess(['git', 'push', 'origin', release], False, '', 'checkout')
    print('Check out done')

def commit(repo, message):
    print('Commiting')
    #runSubProcess(['git', 'reset'], False, repo, 'reset')
    runSubProcess(['git', 'commit', '-am', message], False, repo, 'commit')

def commentSysOut(path):
    textToSearch = "System.out"
    textToReplace = "//System.out"
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

def updatePoms(path):
    print("Updating poms")
    ET.register_namespace("", "http://maven.apache.org/POM/4.0.0")
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

def updateLogback(path, logbackLocation):
    print("Updating logback")
    path = path + logbackLocation
    tree = ET.parse(path)
    root = tree.getroot()
    for rootTag in root.iter('root'):
        if rootTag.get('level') != 'INFO':
            print("Setting log level in %s" % (path))
            rootTag.set('level', 'INFO')
    tree.write(path)

def generateSources(path):
    print("Generating from WSDL")
    pomPath = path + '/pom.xml'
    runSubProcess(['mvn', 'clean', 'install', '-Pgenerate-from-wsdl', '-q', '-f', pomPath], True, pomPath, 'generateSources')
    runSubProcess(['git', 'add', '--force', '.'], False, path, 'add')

def runSubProcess(command, shell, path, stage, stdout=None):
    process = subprocess.Popen(command, shell=shell, stdout=stdout)
    process.wait()
    if process.returncode != 0:
        externalError(process, path, stage)
    return process;

def releasePrepare(path):
    path = path + '/pom.xml'
    print('Preparing release %s' % (path))
    runSubProcess(['mvn', 'release:prepare', '-q', '-f', path, '-B'], True, path, 'prepare')

def releasePerform(path):
    path = path + '/pom.xml'
    print('Performing release %s' % (path))
    runSubProcess(['mvn', 'release:perform', '-q', '-f', path], True, path, 'perform')
    runSubProcess(['git', 'stash'], False, path, 'stash changes')
    runSubProcess(['git', 'checkout', 'master'], False, path, 'chechout master')
    runSubProcess(['git', 'cherry-pick', '--strategy=recursive', '-X', 'theirs', release], False, path, 'cherry pick last')
    runSubProcess(['git', 'push', 'origin', '--delete', release], True, path, 'remove branch')
    runSubProcess(['git', 'push', 'origin', 'master'], True, path, 'push')

def build(path):
    path = path + '/pom.xml'
    print('Building module %s' % (path))
    runSubProcess(['mvn', 'clean', 'install', '-q', '-f', path], True, path, 'build')

def releaseGeneric(svnPath, coPath):
    print(coPath)
    checkOut(svnPath, coPath)
    commentSysOut(coPath)
    updatePoms(coPath)

def releaseModel(module):
    repoPath = '%s%s-MODEL.git' % (gitHubBase, module)
    coPath = r'%s/%s/models/%s' % (checkOutRoot, release, module)
    releaseGeneric(repoPath, coPath)
    generateSources(coPath)
    return coPath

def releaseLibs(module):
    repoPath = '%s%s.git' % (gitHubBase, module)
    coPath = r'%s/%s/libraries/%s' % (checkOutRoot, release, module)
    releaseGeneric(repoPath, coPath)
    return coPath

def releaseApp(module):
    repoPath = '%s%s-APP.git' % (gitHubBase, module)
    coPath = r'%s/%s/apps/%s' % (checkOutRoot, release, module)
    releaseGeneric(repoPath, coPath)
    updateLogback(coPath, '/service/src/main/resources/logback.xml')
    return coPath

def releaseDB(module):
    repoPath = '%s%s-DB.git' % (gitHubBase, module)
    coPath = r'%s/%s/db/%s' % (checkOutRoot, release, module)
    releaseGeneric(repoPath, coPath)
    updateLogback(coPath, '/domain/src/main/resources/logback.xml')
    return coPath

def releaseProxy(module):
    repoPath = '%s%s.git' % (gitHubBase, module)
    coPath = r'%s/%s/proxies/%s' % (checkOutRoot, release, module)
    releaseGeneric(repoPath, coPath)
    updateLogback(coPath, '/service/src/main/resources/logback.xml')
    return coPath

def releasePlugin(module):
    svnPath = '%s/Modules/Exchange/PLUGIN/%s' % (svnDev, module)
    coPath = r'%s/%s/plugins/%s' % (checkOutRoot, release, module)
    releaseGeneric(svnPath, coPath)
    updateLogback(coPath, '/service/src/main/resources/logback.xml')
    return coPath

def releaseRa(module):
    svnPath = '%s/Modules/%s' % (svnDev, module)
    coPath = r'%s/%s/ra/%s' % (checkOutRoot, release, module)
    releaseGeneric(svnPath, coPath)
    return coPath

def releaseFrontend(module):
    svnPath = '%s/%s' % (svnDev, module)
    coPath = r'%s/%s/frontend/%s' % (checkOutRoot, release, module)
    releaseGeneric(svnPath, coPath)
    return coPath

def copy(paths):
    for subdir, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('pom.xml') and 'target' not in subdir:
                fileToCopy = os.path.join(subdir, file)
                target = fileToCopy.replace(release, tempDevDir)
                print('%s -> %s' % (fileToCopy, target))
                shutil.copy2(fileToCopy, target)

#Config

skipSteps = True
print("Start step: " + step)
for list in steps:
    if list == '0-branch' and step == '0-branch':
        print("Stage: " + list)
        branch()
        if currentStep != step and skipSteps:
            print("Skipping step: " + currentStep)
            continue
        elif currentStep == step:
            skipSteps = False
    else:
        print("Stage: " + list)
        for module in steps[list]:
            print("module: " + module)
            currentStep = '%s.%s' % (list, module)
            if currentStep != step and skipSteps:
                print("Skipping step: " + currentStep)
                continue
            elif currentStep == step:
                skipSteps = False

            print("Current step: " + currentStep)
            coPath = ""
            if list == '1-models':
                coPath = releaseModel(module)
            if list == '2-libs':
                coPath = releaseLibs(module)
            if list == '3-apps':
                coPath = releaseApp(module)
            if list == '4-db':
                coPath = releaseDB(module)
            if list == '5-proxies':
                coPath = releaseProxy(module)
            if list == '6-ra':
                coPath = releaseRa(module)
            if list == '7-plugins':
                coPath = releasePlugin(module)
            if list == '8-frontend':
                coPath = releaseFrontend(module)

            #if validateBuild:
            #   build(coPath)
            print("coPath: " + coPath)
            commit(coPath, "Review by %s Build Dtos from model and change to releasebranch in poms" % (getpass.getuser()))
            releasePrepare(coPath)
            releasePerform(coPath)

#merge()
print("Done! Run time: %s " % (time.time() - startTime))
