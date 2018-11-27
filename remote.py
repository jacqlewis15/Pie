
import subprocess
import os
import time
import pyexiv2
import sys

# These functions determine if a path is a folder or a file.

def isValidFolder(folder):
	return os.path.isdir(folder)

def isValidFile(file):
	return os.path.isfile(file)

# This function makes the folder as specified, if it does not exist.

def makeFolder(foldName):
	folders = foldName.split("/")
	for i in range(len(folders)):
		if not isValidFolder("/".join(folders[:i+1])):
			subprocess.check_call(["mkdir","/".join(folders[:i+1])])

# This function returns a list with no empty string elements.
def clearFluff(lst):
    return [x for x in lst if x != ""]

# This function takes the picture and writes data onto it.

def picture(illTime,address,foldName,letter,picName):

	title = "Total Illumination: " + str(round(illTime/60.0,2)) + " minutes"
	name = address+foldName[-1]+letter+picName
	subprocess.check_call(["fswebcam","--title",title,"--font",'"sans:60"',name,"-r 2592x1944"])
	metadata = pyexiv2.ImageMetadata(name)
	metadata.read()
	userdata = title
	metadata['Exif.Image.XPComment']=pyexiv2.utils.string_to_undefined(userdata.encode('utf-16'))
	metadata.write()

# This function takes a single picture of the testing system

def takeAPic(folder, illTime):

    # develops a name for the picture
    date = time.localtime(time.time())
    picName = time.strftime(":y%ym%md%dH%HM%MS%S.jpg",date)
    address = folder + "/"

    # ensures that any subfolders aren't re-called
    foldName = folder.split("/")    

    picture(illTime,address,foldName,"",picName)
    
def start(picTime=1):
	print("Starting")
	folder = "pictures"
	startTime = time.time()
	lastPic = time.time()
	picTime = float(picTime) * 60.0
	if not isValidFolder(folder):
		makeFolder(folder)
	while(True):
		curr = time.time()
		if curr - lastPic >= picTime:
			lastPic = curr
			print("Picture taking")
			takeAPic(folder, curr - startTime)

if len(sys.argv) > 1:
	start(sys.argv[1])
else: start()
