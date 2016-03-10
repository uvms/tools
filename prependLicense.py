import sys
import os
import re

templateHeader1 = "/*\n"
templateHeader1 += " * To change this license header, choose License Headers in Project Properties.\n"
templateHeader1 += " * To change this template file, choose Tools | Templates\n"
templateHeader1 += " * and open the template in the editor.\n"
templateHeader1 += " */\n"

templateHeader2 = "/*\n"
templateHeader2 += " * To change this template, choose Tools | Templates\n"
templateHeader2 += " * and open the template in the editor.\n"
templateHeader2 += " */\n"

templateHeader3 = "/**\n"
templateHeader3 += " *\n"
templateHeader3 += " */\n"

templateHeaders = [templateHeader1, templateHeader2, templateHeader3]

cStyleFiles = ['java', 'js', 'css']
xmlStyleFiles = ['xsd', 'wsdl', 'html', 'xml']

argList = {'-r': '-r <path> Root directory of search','-l': '-l <path> Text file containing license text', '-a': 'Do not break before performing search and prepend', '-c': 'Ignore C style files %s'%(cStyleFiles), '-x': 'Ignore XML style files %s'%(xmlStyleFiles), '-h': 'Display this help', '-help': 'Display this help'}

rootDir = ''
licenseTextFile = ''
auto = False
doCStyle = True
doXMLStyle = True
for i in range(1, len(sys.argv)):
	arg = sys.argv[i]
	if not arg.startswith('-'):
		continue

	if arg not in argList.keys():
		print("Argument not recognized: %s\nValid arguments are: %s" % (arg, argList.keys()))
		sys.exit(-1)

	if arg == '-r':
		rootDir = sys.argv[i+1]
	if arg == '-l':
		licenseTextFile = sys.argv[i+1]
	if arg == '-a':
		auto = True
	if arg == '-c':
		doCStyle = False
	if arg == '-x':
		doXMLStyle = False
	if arg == '-h' or arg == '-help':
		print("Usage: py prependLicense.py [options]")
		for key in argList.keys():
			print('%s\t%s' % (key, argList[key]))
		print('Example: py prependLicense.py -r "c:\dev\modules" -l "c:\dev\license.txt" -x -a')
		sys.exit(0)

if rootDir == '':
	print("No root path specified. Using current directory")
	rootDir = os.getcwd()

if licenseTextFile == '':
	print("No license text file specified. Assuming it is located in project root")
	licenseTextFile = r'%s\%s' % (rootDir, 'licenseText.txt')

def readLicenseText(licenseTextFile):
	try:
		with open(licenseTextFile, 'r') as license:
			return license.read();
	except:
		print("No license text found. Is the file '%s' present?" % (licenseTextFile))
		sys.exit(-1)

def prependLicense(rootDir, licenseText):
	for subdir, dirs, files in os.walk(rootDir):
		for file in files:
			if '.' in file:
				parts = file.split('.');
				end = parts[len(parts) - 1]
				if end in cStyleFiles and doCStyle:
					prependCStyleComment(subdir, file)
				elif end in xmlStyleFiles and doXMLStyle:
					prependXMLStyleComment(subdir, file)

def prependCStyleComment(subdir, file):
	fileToSearch = os.path.join(subdir, file)
	with open(fileToSearch, 'r') as original:
		data = original.read()
		data = data.strip()
		if data.startswith('/*\n' + licenseText + '\n */\n'):
			print('%s already contains license text' % fileToSearch)
			return
		else:
			for templateHeader in templateHeaders:
				if data.startswith(templateHeader):
					print('%s starts with template header. Removing it.' % fileToSearch)
					data = data.replace(templateHeader, '')
		if '@author' in data:
			print('%s contains @author tag. Removing it.' % fileToSearch)
			data = re.sub('\s*\*\s*@author[a-zA-Z\s]*', '',data)
		with open(fileToSearch, 'w') as modified:
			modified.write('/*\n' + licenseText + '\n */\n' + data)

def prependXMLStyleComment(subdir, file):
	fileToSearch = os.path.join(subdir, file)
	with open(fileToSearch, 'r') as original:
		data = original.read()
		data = data.strip()
		if data.startswith('<!--\n' + licenseText + '\n-->\n'):
			print('%s already contains license text' % fileToSearch)
			return
		with open(fileToSearch, 'w') as modified:
			modified.write('<!--\n' + licenseText + '\n-->\n' + data)

print('Root directory for replace is %s' % (rootDir))
print('The text contained in %s will be prepended' % (licenseTextFile))
print('The following file types will be prepended:')
if doXMLStyle:
	print(xmlStyleFiles)
if doCStyle:
	print(cStyleFiles)
if not auto:
	input("Press Enter to continue...")

licenseText = readLicenseText(licenseTextFile)
prependLicense(rootDir, licenseText)