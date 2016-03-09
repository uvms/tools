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

rootDir = ''
licenseTextFile = ''
for i in range(1, len(sys.argv), 2):
	arg = sys.argv[i]
	print([i, arg])
	if arg.startswith('-r'):
		rootDir = sys.argv[i+1]
		print(rootDir)
	if arg.startswith('-l'):
		licenseTextFile = sys.argv[i+1]
		print(licenseTextFile)

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
			if file.endswith('.java'):
				prependJava(subdir, file)
			if file.endswith('.xsd') or file.endswith('.wsdl'):
				prependXML(subdir, file)

def prependJava(subdir, file):
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

def prependXML(subdir, file):
	fileToSearch = os.path.join(subdir, file)
	print('Looking at %s' % (fileToSearch))
	with open(fileToSearch, 'r') as original:
		data = original.read()
		data = data.strip()
		if data.startswith('<!--\n' + licenseText + '\n-->\n'):
			print('%s already contains license text' % fileToSearch)
			return
		with open(fileToSearch, 'w') as modified:
			modified.write('<!--\n' + licenseText + '\n-->\n' + data)

licenseText = readLicenseText(licenseTextFile)
prependLicense(rootDir, licenseText)