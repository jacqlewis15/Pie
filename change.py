import string
import os
from shutil import copyfile

def writeFile(path, contents):
    with open(path, "wt") as f:
        f.write(contents)

def readFile(path):
    with open(path, "rt") as f:
        return f.read()

def change():
	path = os.getcwd()+"/values.txt"
	read = readFile(path).split("\n")
	phaseTxt = ""
	initLightTime = read[1]
	initDarkTime = read[2]
	initPicTime = read[3]
	while(phaseTxt != "on" and phaseTxt != "off"):
		phaseTxt = input("Enter phase(on/off):\n")
	if phaseTxt == "on":
		lightTime = ""
		while((not lightTime.isdecimal()) and lightTime != "same"):
			lightTime = input("Enter light time in minutes or same to stay at %s minutes:\n" % initLightTime)
		if lightTime == "same": lightTime = initLightTime
		darkTime = ""
		while((not darkTime.isdecimal()) and darkTime != "same"):
			darkTime = input("Enter dark time in minutes or same to stay at %s minutes:\n" % initDarkTime)
		if darkTime == "same": darkTime = initDarkTime
		picTime = ""
		while((not picTime.isdecimal()) and picTime != "same"):
			picTime = input("Enter pic time in minutes or same to stay at %s minutes:\n" % initPicTime)
		if picTime == "same": picTime = initPicTime
	else:
		lightTime = initLightTime
		darkTime = initDarkTime
		picTime = initPicTime
	contents = phaseTxt+"\n"+lightTime+"\n"+darkTime+"\n"+picTime
	writeFile(path,contents)
	copyfile(path, "/var/www/html/values.txt")
	print("Phase: %s\nLight Time: %s\nDark Time: %s\nPic Time: %s" % (phaseTxt,lightTime,darkTime,picTime))

change()
