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

release = ''
checkOutRoot = "C:"
tempDevDir = 'temp-dev'
step = '1-models.AssetModule'
currentStep = step
validateBuild = False
dateLimit = datetime.now(timezone.utc) - timedelta(days=21)
branch = 'dev'

user = ''
password = ''
dockerUser = 'focus-docker'
dockerPassword = 'docker'

dockerPullFrom = ''#'nexus.focus.fish:9081/'
dockerPushTo = 'nexus.focus.fish:9081/'

dockerVersion = ''

gitHubBase = "https://%s:%s@github.com/UnionVMS/UVMS-" % (user, password)

unorderedSteps = {
    '1-models': ['ConfigModule', 'RulesModule', 'ExchangeModule', 'MovementModule', 'AssetModule', 'AuditModule', 'MobileTerminalModule'],
    '2-libs': ['UVMSTestLibrary', 'UVMSCommonsLibrary', 'UVMSLongPollingLibrary', 'USM4UVMSLibrary', 'UVMSConfigLibrary'],
    '3-apps': ['ConfigModule', 'AssetModule', 'AuditModule', 'ExchangeModule', 'RulesModule', 'MovementModule', 'MobileTerminalModule'],
    '4-db': ['ConfigModule', 'AssetModule', 'AuditModule', 'ExchangeModule', 'RulesModule', 'MovementModule', 'MobileTerminalModule'],
    '5-proxies': ['AssetModule-PROXY-EU', 'AssetModule-PROXY-HAV', 'AssetModule-PROXY-HAV-CACHE'],
    '6-ra': ['AIS'],
    '7-plugins': ['AIS', 'Email', 'FLUX', 'NAF', 'SiriusOne', 'SWAgencyEmail', 'TwoStage'],
    '8-frontend': ['Frontend'],
    '9-docker': ['release']
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

def checkOut(repo, checkOutPath, otherBranch=''):
    if os.path.exists(checkOutPath):
        shutil.rmtree(checkOutPath, onerror=del_rw)
    os.makedirs(checkOutPath)
    os.chdir(checkOutPath)
    print('Checking out %s to %s' % (repo, checkOutPath))
    runSubProcess(['git', 'clone', repo, checkOutPath], False, '', 'checkout')
    runSubProcess(['git', 'fetch'], False, '', 'fetch')
    if otherBranch == '':
        runSubProcess(['git', 'checkout', branch], False, '', 'checkout')
    else:
        runSubProcess(['git', 'checkout', otherBranch], False, '', 'checkout')
    print('Check out done')

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
    runSubProcess(['mvn', 'clean', 'install', '-Pgenerate-from-wsdl', '-q', '-f', pomPath], True, pomPath, 'generateSources')
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
    runSubProcess(['mvn', 'release:prepare', '-q', '-f', path, '-B'], True, path, 'prepare')

def releasePerform(path, releaseModel = False):
    path = path + '/pom.xml'
    print('Performing release %s' % (path))
    runSubProcess(['mvn', 'release:perform', '-q', '-f', path], True, path, 'perform')
    if releaseModel:
        runSubProcess(['git', 'stash'], False, path, 'stash changes')
        runSubProcess(['git', 'checkout', branch], False, path, 'checkout master')
        runSubProcess(['git', 'cherry-pick', '--strategy=recursive', '-X', 'theirs', release], False, path, 'cherry pick last')
        runSubProcess(['git', 'push', 'origin', '--delete', release], True, path, 'remove branch')
        runSubProcess(['git', 'push', 'origin', branch], True, path, 'push')

def build(path):
    path = path + '/pom.xml'
    print('Building module %s' % (path))
    runSubProcess(['mvn', 'clean', 'package', '-q', '-f', path], True, path, 'build')

def releaseGeneric(svnPath, coPath, otherBranch = ''):
    print(coPath)
    checkOut(svnPath, coPath, otherBranch)
    if checkLastCommit(coPath):
        commentSysOut(coPath)
        nextPomVersion = updatePoms(coPath)
        releaseFile = r'%s/%s/%s' % (checkOutRoot, release, 'releases.txt')
        with open(releaseFile, "a") as myfile:
            myfile.write("Releasing: " + svnPath + "\t" + nextPomVersion + "\n")
        return nextPomVersion
    else:
        return 'break'

def releaseModel(module):
    repoPath = '%s%s-MODEL.git' % (gitHubBase, module)
    coPath = r'%s/%s/models/%s' % (checkOutRoot, release, module)

    checkOutModel(repoPath, coPath)
    if checkLastCommit(coPath):
        commentSysOut(coPath)
        nextPomVersion = updatePoms(coPath)
        releaseFile = r'%s/%s/%s' % (checkOutRoot, release, 'releases.txt')
        with open(releaseFile, "a") as myfile:
            myfile.write("Releasing: " + repoPath + "\t" + nextPomVersion + "\n")
        generateSources(coPath)
        return coPath
    else:
        return 'break'

def releaseLibs(module):
    repoPath = '%s%s.git' % (gitHubBase, module)
    coPath = r'%s/%s/libraries/%s' % (checkOutRoot, release, module)
    if releaseGeneric(repoPath, coPath) != 'break':
        return coPath
    else:
        return 'break'

def releaseApp(module):
    repoPath = '%s%s-APP.git' % (gitHubBase, module)
    coPath = r'%s/%s/apps/%s' % (checkOutRoot, release, module)
    if releaseGeneric(repoPath, coPath) != 'break':
        updateLogback(coPath, '/service/src/main/resources/logback.xml')
        return coPath
    else:
        return 'break'

def releaseDB(module):
    repoPath = '%s%s-DB.git' % (gitHubBase, module)
    coPath = r'%s/%s/db/%s' % (checkOutRoot, release, module)
    if releaseGeneric(repoPath, coPath) != 'break':
        updateLogback(coPath, '/domain/src/main/resources/logback.xml')
        return coPath
    else:
        return 'break'

def releaseProxy(module):
    repoPath = '%s%s.git' % (gitHubBase, module)
    coPath = r'%s/%s/proxies/%s' % (checkOutRoot, release, module)
    if releaseGeneric(repoPath, coPath) != 'break':
        updateLogback(coPath, '/service/src/main/resources/logback.xml')
        return coPath
    else:
        return 'break'

def releasePlugin(module):
    repoPath = '%s%s-PLUGIN.git' % (gitHubBase, module)
    coPath = r'%s/%s/plugins/%s' % (checkOutRoot, release, module)
    if releaseGeneric(repoPath, coPath) != 'break':
        updateLogback(coPath, '/service/src/main/resources/logback.xml')
        return coPath
    else:
        return 'break'

def releaseRa(module):
    repoPath = '%s%s-RESOURCE-ADAPTER.git' % (gitHubBase, module)
    coPath = r'%s/%s/ra/%s' % (checkOutRoot, release, module)
    if releaseGeneric(repoPath, coPath) != 'break':
        return coPath
    else:
        return 'break'

def releaseFrontend(module):
    repoPath = '%s%s' % (gitHubBase, module)
    coPath = r'%s/%s/frontend/%s' % (checkOutRoot, release, module)
    nextPomVersion = releaseGeneric(repoPath, coPath)
    if nextPomVersion != 'break':
        updateJSONVersion(coPath, nextPomVersion)
        return coPath
    else:
        return 'break'

def releaseDocker(module):
    if dockerVersion == '':
        print("No version set for Docker images, will not release them.")
        return 'break'
    repoPath = '%sDocker.git' % (gitHubBase)
    coPath = r'%s/%s/Docker/%s' % (checkOutRoot, release, module)
    checkOut(repoPath, coPath, 'master')
    runSubProcess(['docker', 'login', '-u', dockerUser, '-p', dockerPassword, dockerPushTo], True, coPath, 'pull postgres-base')
    runSubProcess(['docker', 'pull', '%suvms/postgres:9.3' % (dockerPullFrom)], True, coPath, 'pull postgres')
    runSubProcess(['docker', 'build', '-t', '%suvms/postgres-release:%s' % (dockerPushTo, dockerVersion), '-t', '%suvms/postgres-release:latest' % (dockerPushTo), 'postgres-release'], True, coPath, 'build postgres-base')
    runSubProcess(['docker', 'push', '%suvms/postgres-release:%s' % (dockerPushTo, dockerVersion)], True, coPath, 'push postgres-base:%s' % (dockerVersion))
    runSubProcess(['docker', 'push', '%suvms/postgres-release:latest' % (dockerPushTo)], True, coPath, 'coPath postgres-base:latest')

    runSubProcess(['docker', 'pull', '%suvms/wildfly:8.2.0' % (dockerPullFrom)], True, coPath, 'pull wildfly')
    runSubProcess(['docker', 'build', '-t', '%suvms/wildfly-release:%s' % (dockerPushTo, dockerVersion), '-t', '%suvms/wildfly-release:latest' % (dockerPushTo), 'wildfly-release'], True, coPath, 'build wildfly-base')
    runSubProcess(['docker', 'push', '%suvms/wildfly-release:%s' % (dockerPushTo, dockerVersion)], True, coPath, 'push wildfly-base:%s' % (dockerVersion))
    runSubProcess(['docker', 'push', '%suvms/wildfly-release:latest' % (dockerPushTo)], True, coPath, 'push wildfly-base:latest')

    runSubProcess(['git', 'tag', dockerVersion], True, coPath, 'tag release')
    runSubProcess(['git', 'push', 'origin', dockerVersion], True, coPath, 'push tag')
    return coPath

def copy(paths):
    for subdir, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('pom.xml') and 'target' not in subdir:
                fileToCopy = os.path.join(subdir, file)
                target = fileToCopy.replace(release, tempDevDir)
                print('%s -> %s' % (fileToCopy, target))
                shutil.copy2(fileToCopy, target)


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
        if list == '9-docker':
            coPath = releaseDocker(module)

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
