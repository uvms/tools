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

def getProjectRoot():
	if len(sys.argv) > 1:
		print("Root path specified")
		rootDir = r'%s' % (sys.argv[1])
		return rootDir
	else:
		print("No root path specified. Using current directory")
		return os.getcwd()

def readLicenseText(rootDir):
	if len(sys.argv) == 3:
		print("License text file specified")
		licenseTextFile = r'%s' % (sys.argv[2])
	else:
		print("No license text file specified. Assuming it is located in project root")
		licenseTextFile = r'%s\%s' % (rootDir, 'licenseText.txt')
	
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
				fileToSearch = os.path.join(subdir, file)
				with open(fileToSearch, 'r') as original:
					data = original.read()
					if data.startswith(licenseText):
						print('%s already contains license text' % fileToSearch)
						continue
					else:
						for templateHeader in templateHeaders:
							if data.startswith(templateHeader):
								print('%s starts with template header. Removing it.' % fileToSearch)
								data = data.replace(templateHeader, '')
					if '@author' in data:
						print('%s contains @author tag. Removing it.' % fileToSearch)
						data = re.sub('\s*\*\s*@author[a-zA-Z\s]*', '',data)
				with open(fileToSearch, 'w') as modified:
					modified.write(licenseText + '\n' + data)

rootDir = getProjectRoot()
licenseText = readLicenseText(rootDir)
prependLicense(rootDir, licenseText)