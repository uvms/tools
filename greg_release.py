import subprocess
import sys
import os
import shutil
import fileinput
import xml.etree.ElementTree as ET
import getpass
import time
import stat
import json
from datetime import timedelta
from datetime import datetime
from datetime import timezone
from collections import OrderedDict
startTime = time.time()

release = 'uvms-3.0.2-GREGORIAN'
checkOutRoot = "/Users/andreasw/Code/hav/release"
tempDevDir = '/Users/andreasw/Code/hav/release/temp-dev'
step = '1-models.MovementModule'
currentStep = step
validateBuild = False
dateLimit = datetime.now(timezone.utc) - timedelta(days=21)
branch = 'dev'

user = 'ebrygg'
password = 'EvoW4000'
dockerUser = 'focus-docker'
dockerPassword = 'docker'

dockerPullFrom = ''#'nexus.focus.fish:9081/'
dockerPushTo = 'nexus.focus.fish:9081/'

dockerVersion = ''

gitHubBase = "https://%s:%s@github.com/UnionVMS/UVMS-" % (user, password)

unorderedSteps = {
    #'1-models': ['ConfigModule', 'RulesModule', 'ExchangeModule', 'MovementModule', 'AssetModule', 'AuditModule', 'MobileTerminalModule'],
    '1-models': ['MovementModule'],
}
steps = OrderedDict(sorted(unorderedSteps.items(), key=lambda t: t[0]))

for arg in sys.argv:
    if arg.startswith('-c'):
        checkOutRoot = arg.replace('-c', '', 1)
        continue
    if arg.startswith('-r'):
        release = arg.replace('-r', '', 1)
        continue
    if arg.startswith('-s'):
        step = arg.replace('-s', '', 1)
        continue
    if arg.startswith('-u'):
        user = arg.replace('-u', '', 1)
        continue
    if arg.startswith('-p'):
        password = arg.replace('-p', '', 1)
        step = arg.replace('-s', '', 1)
        continue
    if arg.startswith('-du'):
        dockerUser = arg.replace('-du', '', 1)
        continue
    if arg.startswith('-dp'):
        dockerPassword = arg.replace('-dp', '', 1)
        continue
    if arg.startswith('-dv'):
        dockerVersion = arg.replace('-dv', '', 1)
        continue
    if arg.startswith('-v'):
        validateBuild = True
        continue
    if arg.startswith('-d'):
        dateLimit = datetime.strptime(arg.replace('-d', '', 1) + ' +0000', '%y%m%d %z')
        continue
    if arg.startswith('-b'):
        branch = arg.replace('-b', '', 1)
        continue

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

def cleanUp():
    coPath = r'%s/%s' % (checkOutRoot, release)
    if os.path.exists(coPath):
        shutil.rmtree(coPath, onerror=del_rw)

def checkOutModel(repo, checkOutPath):
    if os.path.exists(checkOutPath):
        shutil.rmtree(checkOutPath, onerror=del_rw)
    os.makedirs(checkOutPath)
    os.chdir(checkOutPath)
    print('Checking out %s to %s' % (repo, checkOutPath))
    runSubProcess(['git', 'clone', repo, checkOutPath], False, '', 'checkout')
    runSubProcess(['git', 'fetch'], False, '', 'fetch')
    runSubProcess(['git', 'checkout', '-b', release, 'origin/' + branch], False, '', 'checkout')
    print('Check out done')

def commit(repo, message):
    print('Commiting')
    runSubProcess(['git', 'commit', '-am', message], False, repo, 'commit')

def checkLastCommit(path):
    p = runSubProcess(['git', 'log', '--pretty=format:"%ad"', '-1'], False, '', 'checkout', stdout=subprocess.PIPE, universal_newlines=True)
    out, err = p.communicate()
    date = out.replace('"','')
    date_object = datetime.strptime(date, '%a %b %d %H:%M:%S %Y %z')
    print("%s > %s = %s" % (date_object, dateLimit, (date_object > dateLimit)))
    return date_object > dateLimit

def updatePoms(path):
    print("Updating poms")
    ET.register_namespace("", "http://maven.apache.org/POM/4.0.0")
    path = path + "/pom.xml"
    tree = ET.parse(path)
    root = tree.getroot()
    hasScm = False
    nextPomVersion = ''
    for version in root.iter('{http://maven.apache.org/POM/4.0.0}version'):
        currentPomVersion = version.text
        nextPomVersion = currentPomVersion.replace('-SNAPSHOT','')
        print(nextPomVersion)
        break
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
    return nextPomVersion

def updateJSONVersion(path, nextPomVersion):
    with open(path + '/bower.json', 'r+') as bower:
        data = json.load(bower)
        print("Updating version in bower.json from " + data['version'] + " to " + nextPomVersion)
        data['version'] = nextPomVersion
        bower.seek(0)
        json.dump(data, bower, indent=4, sort_keys=True)
        bower.truncate()

    with open(path + '/package.json', 'r+') as package:
        data = json.load(package)
        print("Updating version in package.json from " + data['version'] + " to " + nextPomVersion)
        data['version'] = nextPomVersion
        package.seek(0)
        json.dump(data, package, indent=4, sort_keys=True)
        package.truncate()

def updateLogback(path, logbackLocation):
    try:
        print("Updating logback")
        path = path + logbackLocation
        tree = ET.parse(path)
        root = tree.getroot()
        for rootTag in root.iter('root'):
            if rootTag.get('level') != 'INFO':
                print("Setting log level in %s" % (path))
                rootTag.set('level', 'INFO')
        tree.write(path)
    except FileNotFoundError as e:
        print("No logback.xml found at " + path + logbackLocation)

def generateSources(path):
    print("Generating from WSDL")
    pomPath = path + '/pom.xml'
    runSubProcess(['mvn', 'clean', 'install', '-Pgenerate-from-wsdl', '-Pxmlgregoriancalendar', '-f', pomPath], False, pomPath, 'generateSources')
    runSubProcess(['git', 'add', '--force', '.'], False, path, 'add')

def runSubProcess(command, shell, path, stage, stdout=None, universal_newlines=False):
    process = subprocess.Popen(command, shell=shell, stdout=stdout, universal_newlines=universal_newlines)
    process.wait()
    if process.returncode != 0:
        externalError(process, path, stage)
    return process;

def releasePrepare(path):
    path = path + '/pom.xml'
    print('Preparing release %s' % (path))
    runSubProcess(['mvn', 'release:prepare', '-f', path, '-B'], False, path, 'prepare')

def releasePerform(path, releaseModel = False):
    path = path + '/pom.xml'
    print('Performing release %s' % (path))
    #runSubProcess(['mvn', 'release:perform', '-q', '-f', path], False, path, 'perform')
    runSubProcess(['mvn', 'release:perform', '-f', path], False, path, 'perform')
    if releaseModel:
        runSubProcess(['git', 'stash'], False, path, 'stash changes')
        runSubProcess(['git', 'checkout', branch], False, path, 'checkout master')
        runSubProcess(['git', 'cherry-pick', '--strategy=recursive', '-X', 'theirs', release], False, path, 'cherry pick last')
        runSubProcess(['git', 'push', 'origin', '--delete', release], False, path, 'remove branch')
        runSubProcess(['git', 'push', 'origin', branch], False, path, 'push')

def build(path):
    path = path + '/pom.xml'
    print('Building module %s' % (path))
    runSubProcess(['mvn', 'clean', 'package', '-q', '-f', path], False, path, 'build')

def releaseModel(module):
    repoPath = '%s%s-MODEL.git' % (gitHubBase, module)
    coPath = r'%s/%s/models/%s' % (checkOutRoot, release, module)

    checkOutModel(repoPath, coPath)
    if checkLastCommit(coPath):
        #commentSysOut(coPath)
        nextPomVersion = updatePoms(coPath)
        releaseFile = r'%s/%s/%s' % (checkOutRoot, release, 'releases.txt')
        with open(releaseFile, "a") as myfile:
            myfile.write("Releasing: " + repoPath + "\t" + nextPomVersion + "\n")
        generateSources(coPath)
        return coPath
    else:
        return 'break'

skipSteps = True
print("Start step: " + step)
for list in steps:
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

        if coPath == 'break':
            print("Last commit for " + currentStep + " was before current release cycle")
            continue
        if validateBuild:
           build(coPath)
        print("coPath: " + coPath)
        commit(coPath, "Review by %s Build Dtos from model and change to releasebranch in poms" % (getpass.getuser()))
        releasePrepare(coPath)
        releasePerform(coPath, list == '1-models')

#cleanUp()
print("Done! Run time: %s " % (time.time() - startTime))
