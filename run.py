#!/usr/bin/env python3

##################################
## HOW TO SET-UP A RASPBERRY PI ##
##################################

# 1. Determine wlan0 address:
#		>>> ifconfig
# 2. Change password from default raspberry:
#		>>> passwd
# 3. Enable camera and ssh:
#		preferences -> raspberry pi configuration -> interfaces
# 3. Set time zone and keyboard:
#		preferences -> raspberry pi configuration -> localisation
#			keyboard is Macintosh
# 4. Install modules: 
#       fswebcam:
#       >>> sudo apt-get update
#		>>> sudo apt-get install fswebcam
#		check that camera works: from command line, input fswebcam "image.jpg"
#       pyexiv2:
#       >>> sudo apt-get install python-pyexiv2
#       adc:
#       >>> sudo pip install Adafruit_ADS1x15
# 5. (Optional) to run from startup, edit /etc/rc.local (before the exit command)
#		python /home/pi/<path to file>/run.py &

##################################

# Jacqueline Lewis
# run.py


# This file defines the user interface and operation of a photoreactor,
# designed for use in the Bernhard Lab. The companion file 
# calibrate_adc.py can be used to calibrate the sensors to provide 
# accurate readings.

# Features:
# - runs photoreaction with/without illumination
# 	- takes pictures under different lights at a designated interval
#	- specified metadata is added to each picture in addition to
#	  writing on the picture itself
#	- all data is saved to a file designated by the user
# 	- supports cycle functionality where picture time will change based on 
#	  input from the user 
# - runs quenching experiment where pictures are taken at approx. each
#	oxygen percentage change
# - metadata can be updated through an external file 
# - degases the system


import RPi.GPIO as GPIO
import string
import time
import os
import subprocess
from Tkinter import *
import Tkinter, Tkconstants, tkFileDialog
import pyexiv2
# from picamera import PiCamera

import Adafruit_ADS1x15 as ads1x15

# file reading/writing from 15-112: 
# http://www.kosbie.net/cmu/spring-16/15-112/notes/
#		notes-strings.html#basicFileIO

def writeFile(path, contents):
    with open(path, "wt") as f:
        f.write(contents)

def readFile(path):
    with open(path, "rt") as f:
        return f.read()

####################################
# UI
####################################

# Initial data for each piece of code.

def initRun(data):
	# for the overall process
	data.lights = [False]*8 # Number of lights connected
	data.picTime = "1" 
	data.edit = [False,False,[False]*8,[False]*8,False] # run and cycle edits
	data.error = ""
	data.pipe = [False,False,[False]*8,[False]*8,False] # run and cycle edits
	data.time = 0
	data.lastPic = time.time()
	data.folder = "test"
	makeFolder("test") # makes the test folder if it does not exist
	data.running = False
	data.mode = "run"
	data.picFolder = data.folder
	data.newPicTime = int(float(data.picTime)*60)
	data.illTime = 0
	data.noLight = False
	data.selected = [True]*6

def initQuenching(data):
	# for the quenching mode
	data.quenching = False
	data.hanging = False
	data.start = 0
	data.nextO2 = range(20,10,-2)+range(10,0,-1)+[.5,.1,0]
	data.count0 = None
	data.taken = False

def initADC(data):
	# for the adc setup
	# bulbasaur: ADS1115
	# ivysaur: ADS1015
	data.adc = ads1x15.ADS1115()
	# bulbasaur: (0.07777,0.001289),(21500,1300)
	# ivysaur: (1,0.030511),(1300,1300)
	data.cal = (0.07777,0.001289) # for each ndew adc/pi/sensor, calibrate.py
	data.zero = (21500,1300) # read value, desired value
	data.pressure = "----"
	data.O2vals = []
	data.lastO2 = 0
	data.lastPressure = 0
	data.pZero = 1523
	data.degas = False

def initPins(data):
	# Initializes Raspberry Pi to communicate with relay board
	GPIO.setmode(GPIO.BCM)
	data.pins = [4,17,27,22,5,6,13,19]
	data.lightPins = data.pins[:2]
	data.picPins = data.pins[2:]
	data.gasPin = 25
	GPIO.setup(data.pins, GPIO.OUT)
	GPIO.setup(data.gasPin, GPIO.OUT)
	data.off = GPIO.HIGH
	data.on = GPIO.LOW

	for pin in data.pins:
		GPIO.output(pin, data.off)
	GPIO.output(data.gasPin, data.off)

def initCycle(data):
	# Initializes cycles
	data.times = [[""]*8, [0]*8] # editing and non-editing
	data.cycles = [[""]*8, [0]*8] # editing and non-editing
	data.cycling = False
	data.edited = False

def initMeta():
	# sets the blank metadata
	lines = [""]*34
	lines[0] = "Illumination Time:"
	lines[1] = "Pressure:"
	lines[2] = "Oxygen:"
	for i in range(13,25):
		lines[i] = str(i-12) + ":"
	for i in range(26,34):
		lines[i] = list(string.ascii_uppercase)[i-26] + ":"
	return "\n".join(lines)

def init(data):
	# Initialization of user interface
	initRun(data)
	initADC(data)
	initQuenching(data)

	# Metadata editing
	data.index = (0,0)
	data.mEdit = initMeta()
	data.metadata = initMeta()

	# camera init
	# data.camera = PiCamera()
	# data.camera.annotate_text_size = 64
	# data.camera.resolution = (2592, 1944)

	initCycle(data)
	initPins(data)


####################################
# run mode
####################################


# This function defines the size and specifications of the user interface.

def sizeSpecs(data):
	# creates a well-spaced UI
	margin = 20
	center = data.width/2
	bheight = (data.height-margin*9)/12
	bwidth = data.width/3
	left = center/2-bwidth/4-margin
	right = center*3/2-bwidth*3/4+margin
	return margin,center,bheight,bwidth,left,right


# When the user presses any of the buttons on the left side of the UI
# this function will operate the lights and cause the UI to display
# any change.

def pressLight(data, light):
	
	if light >= 8: pass # dummy index
	elif not data.running:
		# if the light is on, it turns off
		if data.lights[light]:
			if light == 0: 
				GPIO.output(data.pins[1],data.off)
				data.lights[1] = False
			GPIO.output(data.pins[light],data.off)
			data.lights[light] = False
		# if the light is off, it turns on
		else:
			for i in range(len(data.pins)):
				# no other light can run at the same time
				GPIO.output(data.pins[i], data.off)
				data.lights[i] = False
			if light == 0: 
				GPIO.output(data.pins[1],data.on)
				data.lights[1] = True
			GPIO.output(data.pins[light],data.on)
			data.lights[light] = True


# This function reacts to a user clicking on a button on the right side
# of the screen and implents the expected outcome.

def press(data, index):
	if index == 0 and not data.running: pressLight(data, index)
	if index == 1 and not data.edit[1] and not data.edit[4]: data.edit[0] = True
	if index == 2 and not data.edit[0] and not data.edit[4]: data.edit[1] = True
	if index == 3: 
		# starts/stops the main testing system
		data.running = not data.running
		if data.running:
			data.time = 0
			data.illTime = 0
			data.lastPic = time.time()
			data.startTime = time.time()
			if not data.noLight:
				for i in range(len(data.lightPins)):
					GPIO.output(data.lightPins[i], data.on)
					data.lights[i] = True
			for i in range(len(data.picPins)):
				GPIO.output(data.picPins[i], data.off)
				data.lights[i+2] = False
		# turns everything off
		else:
			data.illTime = 0
			for i in range(len(data.pins)):
				GPIO.output(data.pins[i], data.off)
				data.lights[i] = False
	# can't take pictures during run
	if index == 4 and not data.running: takePics(data)
	if index == 5 and not data.running and not data.lights[0]: takeAPic(data)
	if index == 10: data.mode = "setCycle"
	if index == 11: # quenching button
		data.quenching = not data.quenching
		if not data.quenching: initQuenching(data) # resets data
	if index == 12: data.degas = not data.degas
	if index == 13: data.noLight = not data.noLight


def gasOn(data):
	# turn gas on
	GPIO.output(data.gasPin, data.on)

def gasOff(data):
	# turn gas off
	GPIO.output(data.gasPin, data.off)


# This function allows the user to choose a file from a pop-up browser.

def fileExplorer():
    location = os.getcwd() # chooses a start folder for the browser
    name = tkFileDialog.askopenfilename(initialdir = location,
        title = "Select file",filetypes = (("TEXT","*.txt"),("all files","*.*")))
    if name == (): name = "" # prevents type error
    return name


# This function returns the contents of a file chosen by fileExplorer.

def convToMeta(file):
	if file == "": # ensures the file exists
		return None
	else:
		contents = readFile(file)
		return contents


# This function reacts to mouse clicks and reacts if a button is pressed.

def runMousePressed(event, data):
	
	# defines sizing specifications
	margin,center,bheight,bwidth,left,right = sizeSpecs(data)
	index = int((event.y-bheight)//(margin+bheight))
	top = bheight+index*(margin+bheight)
	column = ((2*margin+2*bwidth)//6)

	# left column clicks
	if event.x > left and event.x < (left+bwidth):
		# checkbox clicks
		if ((left+bwidth-1.25*margin < event.x < left+bwidth-margin/4) and
			(top+margin/4 < event.y < top+margin*1.25)):
			data.selected[index-3] = not data.selected[index-3]
		elif event.y > top and event.y < top+bheight and 3 <= index <= 8: 
			pressLight(data, index-1)
	# right column clicks
	if event.x > right and event.x < (right+bwidth):
		if event.y > top and event.y < top+bheight and 3 <= index <= 8: 
			press(data, index-3)
	# edit metedata block
	if event.x > left and event.x < (right+bwidth):
		if event.y > bheight and event.y < (bheight*4+margin*2):
			if not data.edit[0] and not data.edit[1]:
				data.edit[4] = True
				# finds where to start the cursor
				idx = int((event.y-bheight)//((bheight*3+margin*2)//12))
				if event.x > center+column: idx += 26
				elif event.x > center-column: idx += 13
				lines = data.metadata.split("\n")
				if len(lines) <= idx: idx = len(lines)-1
				data.index = (idx,len(lines[idx]))
	# metadata button
	if event.x > center-bwidth//2 and event.x < center+bwidth//2:
		if event.y > 10 and event.y < bheight-10:
			if not data.edit[0] and not data.edit[1] and not data.edit[4]:
				contents = convToMeta(fileExplorer())
				if contents != None: data.metadata,data.mEdit = contents,contents
	# far right clicks
	if event.x > right+bwidth+margin and event.x < right+bwidth*5/4+margin:
		if event.y > bheight+3*(margin+bheight) and event.y < 2*bheight+3*(margin+bheight):
			press(data, 12)
		if event.y > bheight+4*(margin+bheight) and event.y < 2*bheight+4*(margin+bheight):
			press(data, 10)
		if event.y > bheight+6*(margin+bheight) and event.y < 2*bheight+6*(margin+bheight):
			press(data, 11)
		if event.y > bheight+8*(margin+bheight) and event.y < 2*bheight+8*(margin+bheight):
			press(data, 13)


# These functions determine if a path is a valid folder or file.

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


# This function backspaces out the character before the cursor in the metadata.

def removeChar(data):
    # determines which line of the multiline metadata is being edited
    lines = data.mEdit.split("\n")
    idx1,idx2 = data.index
    line = lines[idx1]
    # ensures no array access errors, removes elem from end of string
    if idx2 >= len(line) and len(line) > 0: 
        line = line[:-1]
        data.index = (idx1,idx2-1)
        lines[idx1] = line
    # removes element from middle of string
    elif idx2 > 0: 
        line = line[:idx2-1]+line[idx2:]
        data.index = (idx1,idx2-1)
        lines[idx1] = line
    # deletes newline separation between line before and current
    elif idx1 != 0: 
        data.index = (idx1-1,len(data.mEdit.split("\n")[idx1-1]))
        newLine = lines[idx1-1]+lines[idx1]
        # joins the two lines into one
        if idx1+1 < len(lines):
            lines = lines[:idx1-1]+[newLine]+lines[idx1+1:]
        else: lines = lines[:idx1-1]+[newLine]
    return "\n".join(lines)


# This function adds a character to the metadata.

def addChar(data,event):
    # determines which line is being edited
    lines = data.mEdit.split("\n")
    idx1,idx2 = data.index
    line = lines[idx1]
    # ensures no array access errors
    if idx2 >= len(line): line = line + event.char
    elif idx2 >= 0: line = line[:idx2]+event.char+line[idx2:]
    # ensures all newline removing gets all carriage returns
    lines[idx1] = line.replace("\r","\n")
    # adding a newline changes the line number
    if event.keysym == "Return": data.index = (idx1+1,0)
    else: data.index = (data.index[0],data.index[1]+1)
    return "\n".join(lines)


# This function moves the cursor horizontally in metadata editing mode.

def horiz(data,direction):
    lines = data.mEdit.split("\n")
    if direction == "Left":
        # moves cursor left with wraparound, if possible
        if data.index[1] != 0: data.index = (data.index[0],data.index[1]-1)
        elif data.index[0] != 0: 
            index = data.index[0]-1
            data.index = (index,len(lines[index]))
    elif direction == "Right":
        # moves cursor right with wraparound, if possible
        if data.index[1] != len(lines[data.index[0]]):
            data.index = (data.index[0],data.index[1]+1)
        elif data.index[0] < len(lines)-1: 
            index = data.index[0]+1
            data.index = (index,0)


# This function moves the cursor vertically in metadata editing mode.

def vert(data,direction):
    lines = data.mEdit.split("\n")
    if direction == "Up":
        # moves cursor up, if possible
        if data.index[0] != 0:
            idx = data.index[0]-1
            lineLength = len(lines[idx])
            if data.index[1] > lineLength: data.index = (idx,lineLength)
            else: data.index = (idx,data.index[1])
    elif direction == "Down":
        # moves cursor down, if possible
        if data.index[0] < len(lines)-1:
            idx = data.index[0]+1
            lineLength = len(lines[idx])
            if data.index[1] > lineLength: data.index = (idx,lineLength)
            else: data.index = (idx,data.index[1])


# This function ends the editing operation for metadata and folder.

def finishEditing(data,textType):
    # the index is reset and the overall variable is set as the edited
    if textType == "metadata":
        data.metadata = data.mEdit
        data.index = (0,0)
        index = 4
    # the editing operation is over
    data.edit[index] = False
    data.pipe[index] = False


# This function reacts to user key strokes and responds accordingly.

def runKeyPressed(event, data):

	# If the picture time is being edited, only valid times can be entered
	if data.edit[0]:
		if event.keysym == "Return": 
			# time constraints of picture interval
			if float(data.picTime) >= 0.05 and float(data.picTime) <= 100.0:  
				data.edit[0] = False
				data.pipe[0] = False
				data.newPicTime = int(float(data.picTime)*60)
				data.cycling = False
			else: data.error = "Must enter valid picture time"
		# ensures valid keystrokes
		elif event.keysym in map(str,range(10)): 
			data.error = ""
			data.picTime += event.keysym
			if len(data.picTime)>7: data.picTime = data.picTime[:-1]
		elif event.keysym == "BackSpace": data.picTime = data.picTime[:-1]
		elif event.keysym == "period" and (data.picTime in map(str,range(10))
				or data.picTime == ""):
			data.picTime += "."
	# if the folder name is being edited only valid folder names can be entered
	if data.edit[1]:
		if event.keysym == "Return":
			makeFolder(data.folder)
			data.edit[1] = False
			data.pipe[1] = False
			data.picFolder = data.folder
		elif event.keysym == "BackSpace": data.folder = data.folder[:-1]
		else:
			data.error = ""
			data.folder += event.char
		if len(data.folder) > 18: data.folder = data.folder[:-1]
	# editing metadata
	if data.edit[4]:
		if event.keysym == "Escape": finishEditing(data,"metadata")
		elif event.keysym == "BackSpace": data.mEdit = removeChar(data)
		elif event.keysym == "Left" or event.keysym == "Right": 
			horiz(data,event.keysym)
		elif event.keysym == "Up" or event.keysym == "Down":
			vert(data,event.keysym)
		else: data.mEdit = addChar(data,event)


# This function returns a list with no empty string elements.

def clearFluff(lst):
    return [x for x in lst if x != ""]


# This function takes the picture and writes data onto it.

def picture(data,address,foldName,letter,picName):

	# creates writing on the picture and metadata to convey information
	title = ("Total Illumination: " + 
		str(round(data.illTime/60.0,2)) + " minutes")
	pressure,oxygen = readData(data)
	name = address+foldName[-1]+letter+picName
	# time.sleep(1)
	# data.camera.annotate_text = title + "\n" + pressure + "\n" + oxygen
	# data.camera.capture(name)
	subprocess.check_call(["fswebcam","--title",title,"--subtitle",pressure,
		"--info",oxygen,"--font",'"sans:60"',name,"-r 2592x1944"])
	metadata = pyexiv2.ImageMetadata(name)
	metadata.read()
	userdata = "\n".join(clearFluff(data.metadata.split("\n")))
	userdata = (pressure).join(userdata.split("Pressure:"))
	userdata = (oxygen).join(userdata.split("Oxygen:"))
	userdata = (title).join(userdata.split("Illumination Time:"))
	metadata['Exif.Image.XPComment'] = (
		pyexiv2.utils.string_to_undefined(userdata.encode('utf-16')))
	metadata.write()


# This function takes a single picture of the testing system.

def takeAPic(data):

    # develops a name for the picture
    date = time.localtime(time.time())
    picName = time.strftime(":y%ym%md%dH%HM%MS%S.jpg",date)
    address = data.picFolder + "/"

    # ensures that any subfolders aren't re-called
    foldName = data.picFolder.split("/")    
    alphabet = ["A","B","C","D","E","F"]

    # takes a picture and names it for the light that is on
    for i in range(len(data.lights)):
        if data.lights[i] and i != 0 and i != 1:
            letter = alphabet[i-2]
            # take picture
            picture(data,address,foldName,letter,picName)
    # no light on has no differentiating letter in pic name
    if data.lights == [False]*8: 
        picture(data,address,foldName,"",picName)


# This function takes 6 picures of the testing system, one for each
# different picture light available.

def takePics(data):

	# makes sure all lights are off initially
	for i in range(len(data.pins)):
		GPIO.output(data.pins[i], data.off)
		data.lights[i] = False

	# ensures that any subfolders aren't re-called
	foldName = data.picFolder.split("/") 
	alphabet = ["A","B","C","D","E","F"]
	for i in range(len(data.picPins)):
		if data.selected[i]:
			# develops a name for the picture
			date = time.localtime(time.time())
			picName = time.strftime(":y%ym%md%dH%HM%MS%S.jpg",date)
			address = data.picFolder + "/"
			letter = alphabet[i]
			# turn pic lights on
			GPIO.output(data.picPins[i], data.on)
			# take picture
			picture(data,address,foldName,letter,picName)
			# turn pic lights off
			GPIO.output(data.picPins[i], data.off)


# This function maintains the timing of the system.

def runTimerFired(data):

	# checks if the amount of time between pictures that was set has passed
	if data.running and ((time.time() - data.lastPic) >= data.newPicTime):
		if not data.noLight: data.illTime += data.newPicTime
		takePics(data)
		# turn lights on
		data.lastPic = time.time()
		if not data.noLight:
			for i in range(len(data.lightPins)):
				GPIO.output(data.lightPins[i], data.on)
				data.lights[i] = True
		if data.cycling: 
			data.numCycles += 1
			if data.numCycles >= data.cycles[1][data.cIndex]: nextCycle(data)
	# flashes the cursor if in edit mode
	if data.edit[0] and data.time % 5 == 0: data.pipe[0] = not data.pipe[0]
	if data.edit[1] and data.time % 5 == 0: data.pipe[1] = not data.pipe[1]
	if data.edit[4] and data.time % 5 == 0: data.pipe[4] = not data.pipe[4]
	# takes a quenching photo at the proper time according to the pattern
	if data.hanging and ((time.time()-data.start) > (data.nextO2[0]*60)): 
		pressLight(data,7)
		takeAPic(data)
		pressLight(data,7)
		data.hanging = False
		data.nextO2 = filter(lambda x: x < (data.lastO2), data.nextO2)
	# stops gas during picture wait
	if data.quenching and len(data.nextO2) < 5 and not data.taken:
		if data.pressure[1] == 0 and data.count0 == None:
			data.count0 = time.time()
		# takes final 0 picture
		elif data.pressure[1] <= 0.2 and data.count0 != None:
			if time.time()-data.count0 > 300 and data.pressure[1] == 0:
				pressLight(data,7)
				takeAPic(data)
				pressLight(data,7)
				data.taken = True
		else: data.count0 = None
	# updates the timer for repetitive actions
	data.time += 1


# Provides a user-readable description of a light's status

def isOn(data, light):
    if data.lights[light]: return "Off"
    else: return "On"


# Provides a color based on whether a light is selected.

def selected(data, i):
	if data.selected[i]: return "red"
	else: return "lightgray"


# Creates a cursor from true/false data

def piping(data, index):
	if index: return "|"
	else: return ""


# Draws the icons and words on the UI

def drawButtons(canvas, data):

	# sizing for buttons
	lights = ["White","Blue","Green","Yellow","Red","UV"]
	margin,center,bheight,bwidth,left,right = sizeSpecs(data)

	# creates all buttons
	for i in range(6):
		text = lights[i]+" Light "+ isOn(data,i+2)
		top = bheight+(3+i)*margin+(3+i)*bheight
		bottom = top+bheight
		corner = right+bwidth+margin
		canvas.create_rectangle(left,top,left+bwidth,bottom,fill="lightgray")
		canvas.create_text(left+bwidth/2,top+bheight/2,text=text,
			font="Arial 20 bold")
		canvas.create_rectangle(left+bwidth-1.25*margin,top+margin/4,
			left+bwidth-margin/4,top+margin*1.25,fill=selected(data,i))
		if (i == 1 or i == 2): color="lightblue"
		else: color="lightgray"
		canvas.create_rectangle(right,top,right+bwidth,bottom,fill=color)
		if i != 2 and i != 4: canvas.create_rectangle(corner,top,
			corner+bwidth/4,bottom,fill="lightgray")    
		fill2=fill3="black"
		font2 = font3 = "Arial 15 bold"
		text3 = ""
		if i == 0: 
			text2 = "Illumination " + isOn(data,0)
			font2 = "Arial 20 bold"
			if data.degas: fill3 = "red"
			text3 = "Degas"
		if i == 1:
			if data.picTime == "1": mins = " minute"
			else: mins = " minutes"
			text2 = ("Pic Time: "+data.picTime+piping(data,data.pipe[0])+mins)
			text3 = "Set\nCycle"
		if i == 2:
			text2 = "Folder: " + data.folder + piping(data,data.pipe[1])
			if data.cycling: text3 = "Cycle Set"
		if i == 3:
			if data.running: text2,fill2 = "End run","red"  
			else: text2,fill2 = "Start run","black"
			font2 = "Arial 20 bold"
			if data.quenching: fill3 = "red"
			else: fill3 = "black"
			font3 = "Arial 12 bold"
			text3 = "Quench"
		if i == 4: 
			text2 = "Take Pictures"
			if data.hanging: text3 = "Hanging"
			font3 = "Arial 10 bold"
		if i == 5: 
			text2 = "Take a Picture"
			if data.noLight: fill3 = "red"
			text3 = "No\nLight"
			font3 = "Arial 12 bold"

		canvas.create_text(right+bwidth/2,top+bheight/2,text=text2,font=font2,
			fill=fill2)
		canvas.create_text(corner+2+bwidth/8,top+bheight/2,text=text3,
				font=font3,fill=fill3)


# This function creates the clocks visible at the bottom of the
# screen while the system is running. One keeps track of how 
# long until the next pictuer is taken and the other keeps track
# of how long the system has been running.

def drawTimes(canvas, data):

	# sizes to place clocks below all buttons
    margin,center,bheight,bwidth,left,right = sizeSpecs(data)
    top = bheight+9*margin+9*bheight
    bottom = top+bheight

    # draws the clocks when running
    if data.running:
        tim = time.time()-data.startTime
        # calculates time stamps
        m,s = divmod(tim,60)
        h,m = divmod(m,60)
        text = ("Time running: " + "%d:%02d:%02d") % (h,m,s)
        tim = data.newPicTime - (time.time()-data.lastPic)
        m,s = divmod(tim,60)
        h,m = divmod(m,60)
        text2 = ("Next pic in: " + "%d:%02d:%02d") % (h,m,s)
        # draws clock
        canvas.create_text(right+bwidth/2,top+bheight/2,text=text,
        	font="Arial 15 bold")
        canvas.create_rectangle(right,top,right+bwidth,bottom)
        canvas.create_text(left+bwidth/2,top+bheight/2,text=text2,
        	font="Arial 15 bold")
        canvas.create_rectangle(left,top,left+bwidth,bottom)


# This function computes the average of a list and rounds it.

def average(lst):
	total = 0
	for i in range(len(lst)):
		total += lst[i]
	return round(total/(len(lst)),2)


# This function translates raw pressure and oxygen data into legible 
# information.

# oxygen calibration number 0.014064
# pressure calibration number 0.400900

def readData(data):

	# does not update to out-of-bounds values
	if 1300 < data.pressure[0] < 1900:
		data.lastPressure = data.pressure[0]
	text = "Pressure: " + str(int(data.lastPressure))
	# computes oxygen values at valid pressures
	if data.pressure[0] < 1800:
		data.O2vals.append(data.pressure[1])
		if len(data.O2vals) == 15:
			data.lastO2 = average(data.O2vals)
			data.O2vals = []
	text2 = "Oxygen: " + str(data.lastO2)
	if (not data.hanging) and data.degas:
		if data.pressure[0] < data.pZero: 
			gasOn(data)
		else: gasOff(data)
	else: gasOff(data)
	# checks if the gas should stop during quench experiments
	if (not data.hanging) and data.quenching:
		if data.nextO2 != []:
			if ((data.nextO2[0] > 1 and data.lastO2 <= (data.nextO2[0]-.7)) or
					(1 >= data.nextO2[0] > .1 and data.lastO2 <= 
						(data.nextO2[0]-.3)) or (data.nextO2 <= .1 and 
							data.lastO2 <= (data.nextO2[0]-.08))):
				data.start = time.time()
				print("Hanging")
				data.hanging = True
	return text,text2


# This function reads data from the adc and converts it to meaningful 
# pressure and oxygen readings.

def getReading(data):
	raw = (data.adc.read_adc_difference(3),data.adc.read_adc_difference(0))
	return ((raw[0]-data.zero[0])*data.cal[0]+data.zero[1]),raw[1]*data.cal[1]

# This function connects to the adc and prints the pressure output.

def drawSensors(canvas, data):

	# sizes to place pressure display below all buttons
	margin,center,bheight,bwidth,left,right = sizeSpecs(data)

	if data.time % 5 == 0: 
		# read from adc
		data.pressure = getReading(data)
	# displays pressure and oxygen values
	text,text2 = readData(data)
	canvas.create_text(left+bwidth/2,data.height-bheight/4,text=text,
		font="Arial 20 bold")
	canvas.create_text(right+bwidth/2,data.height-bheight/4,text=text2,
		font="Arial 20 bold")


# This function displays the metadata in the top box.

def drawMeta(canvas, data):
	# initializes size and editing data
	margin,center,bheight,bwidth,left,right = sizeSpecs(data)
	text = data.mEdit
	text1 = ""
	text2 = ""
	pipe = ""
	# adds the blinking cursor to the correct space in the header
	if data.edit[4]: 
		canvas.create_text(center,.5*bheight,text="Press escape to end edit",
			font="Arial 20 bold")
		if data.pipe[4]: pipe = "|"
		else: pipe = " "
	else:
		# if not editing, the button appears
		canvas.create_rectangle(center-bwidth//2,10,center+bwidth//2,
			bheight-10,fill="lightgray")
		canvas.create_text(center,.5*bheight,text="Import Metadata",
			font="Arial 15 bold")
	lines = text.split("\n")
	if len(lines) == 0: text = pipe
	# writes lines appropriately
	else:
		line = lines[data.index[0]]
		if data.index[1] < len(line):
		    line = line[:data.index[1]]+pipe+line[data.index[1]:]
		else: line = line+pipe
		lines[data.index[0]] = line
		if len(lines) > 26:
			text = "\n".join(lines[:13])
			text1 = "\n".join(lines[13:26])
			text2 = "\n".join(lines[26:])
		elif len(lines) > 13:
			text = "\n".join(lines[:13])
			text1 = "\n".join(lines[13:])
		else: text = "\n".join(lines)
	# draws all text 
	canvas.create_rectangle(left,bheight,right+bwidth,bheight*4+margin*2)
	canvas.create_text(left+5,bheight,text=text,font="Arial 10 bold",
		anchor="nw")
	canvas.create_text(center+5-(2*margin+2*bwidth)//6,bheight,text=text1,
		font="Arial 10 bold",anchor="nw")
	canvas.create_text(center+5+(2*margin+2*bwidth)//6,bheight,text=text2,
		font="Arial 10 bold",anchor="nw")


# This function draws the UI every frame.

def runRedrawAll(canvas, data):
    
    canvas.create_rectangle(0,0,data.width+5,data.height+5,fill="lightblue")
    drawButtons(canvas, data)
    drawTimes(canvas, data)
    drawSensors(canvas,data)
    drawMeta(canvas,data)
    canvas.create_text(data.width/2,20,text=data.error,font="Arial 20 bold",
    	fill="red")


####################################
# setCycle mode
####################################


# This function edits the cycle system in setCycle mode.

def writeCycle(event, data, index, col):

	data.error = ""
	data.edited = True 
	if col == 2: lst = data.times
	if col == 3: lst = data.cycles

	# verifies that any data entered is within the allowable limits
	if event.keysym == "Return": 
		# sets time constraints for inputs
		if lst[0][index] == "" or (float(lst[0][index]) >= 0.5 and 
				float(lst[0][index]) <= 100.0):  
			data.edit[col][index] = False
			data.pipe[col][index] = False
			if lst[0][index] == "": lst[1][index] = 0
			else: 
				if col == 2: lst[1][index] = int(float(lst[0][index])*60)
				# cycle numbers can only be integers
				else: lst[1][index] = int(lst[0][index])
		else: data.error = "Must enter valid picture time"
	# allowable keystrokes
	elif event.keysym in map(str,range(10)): 
		lst[0][index] += event.keysym
		if len(lst[0][index])>7: lst[0][index] = lst[0][index][:-1]
	elif event.keysym == "BackSpace": 
		lst[0][index] = lst[0][index][:-1]
	elif event.keysym == "period" and (lst[0][index] in map(str,range(10)) or lst[0][index] == ""):
		lst[0][index] += "."
	# allows the user to look at the cycle w/o resetting it
	else: data.edited = False


# This function reacts to mouse clicks in the set cycle mode.

def setCycleMousePressed(event, data):

	# size info
	margin = 20
	center = data.width/2
	bheight = data.height/9
	bwidth = data.width/3
	left = center-bwidth
	index = int(event.y//bheight)
	off = True

	# checks that the click is within the table
	if index >= 2 and index < 8:
		# left column
		if event.x > left and event.x < center:
			for i in range(8):
				if i == index and not data.edit[3][i]: continue
				if data.edit[2][i] or data.edit[3][i]: off = False
			if off: 
				data.edit[2][index] = True
			else: data.edit[2][index] = False
		# right column
		if event.x > center and event.x < center+bwidth:
			for i in range(8):
				if i == index and not data.edit[2][i]: continue
				if data.edit[2][i] or data.edit[3][i]: off = False
			if off: data.edit[3][index] = True
			else: data.edit[3][index] = False


# This function initiates the cycle stage.

def startCycle(data):

	data.cIndex = 1
	nextCycle(data)


# This function transitions between phases of the cycle.

def nextCycle(data):

	data.cIndex += 1
	# stops the cycle at the end
	if data.cIndex > 7:
		data.cycling = False
		return
	data.numCycles = 0
	# checks that the cycle moves to a non-empty state
	if data.times[1][data.cIndex] != 0 and data.cycles[1][data.cIndex] != 0:
		data.newPicTime = data.times[1][data.cIndex]
	else: nextCycle(data)


# This function responds to keystrokes by the user.

def setCycleKeyPressed(event, data):

	# edits the table values
	for i in range(8):
		if data.edit[2][i]: writeCycle(event, data, i, 2)
		if data.edit[3][i]: writeCycle(event, data, i, 3)
	# returns to the main screen if all inputs are valid and complete
	if (event.keysym) == "Escape":
		for i in range(8):
			if data.edit[2][i] or data.edit[3][i]: 
				data.error = "Must complete edit"
			elif data.times[0][i] != "" and data.cycles[0][i] == "": 
				data.error = "Must complete edit"
			elif data.times[0][i] == "" and data.cycles[0][i] != "": 
				data.error = "Must complete edit"
		# if no errors were generated, exits edit
		if data.error == "": 
			data.mode = "run"
			if data.edited and data.times[0] != [""]*8:
				data.cycling = True
				startCycle(data)


# This function maintains the picture timing of the run function even during
# the editing process of the cycle.

def setCycleTimerFired(data):

	# checks if the time between pictures has elapsed
	if data.running:
		if (time.time() - data.lastPic) >= data.newPicTime:
			if not data.noLight: data.illTime += data.newPicTime
			takePics(data)
			# turn lights on
			data.lastPic = time.time()
			if not data.noLight:
				for i in range(len(data.lightPins)):
					GPIO.output(data.lightPins[i], data.on)
					data.lights[i] = True
	# causes the editing cursor to oscillate
	for i in range(8):
		if data.edit[2][i]:
			if data.time % 5 == 0: data.pipe[2][i] = not data.pipe[2][i]
		if data.edit[3][i]:
			if data.time % 5 == 0: data.pipe[3][i] = not data.pipe[3][i]
	data.time += 1


# This function draws the setCycle table, including the values entered.

def drawTable(canvas, data):

	margin = 20
	center = data.width/2
	bheight = data.height/9
	bwidth = data.width/3
	left = center-bwidth
	# draws the grid and text
	canvas.create_text(center,bheight/2,text="Press escape to return to the run screen",font="Arial 20 bold")
	for i in range(7):
		canvas.create_rectangle(left, (i+1)*bheight, center, (i+2)*bheight,fill="white")
		canvas.create_rectangle(center, (i+1)*bheight, center+bwidth, (i+2)*bheight,fill="white")
		text1 = data.times[0][i+1]
		text2 = data.cycles[0][i+1]
		# adds an editing cursor if that cell is being edited
		if data.edit[2][i+1]: text1 += piping(data,data.pipe[2][i+1])
		if data.edit[3][i+1]: text2 += piping(data,data.pipe[3][i+1])
		canvas.create_text(left+bwidth/2,(i+1.5)*bheight,text=text1,font="Arial 20 bold")
		canvas.create_text(center+bwidth/2,(i+1.5)*bheight,text=text2,font="Arial 20 bold")
		if i == 0: 
			canvas.create_text(left+bwidth/2,1.5*bheight,text="Time", font="Arial 20 bold")
			canvas.create_text(center+bwidth/2,1.5*bheight,text="Number of Cycles",font="Arial 20 bold")
	canvas.create_text(data.width/2,data.height-bheight/2,text=data.error,font="Arial 20 bold",fill="red")


# This function redraws the canvas every clock cycle.

def setCycleRedrawAll(canvas, data):
	canvas.create_rectangle(0,0,data.width+5,data.height+5,fill="lightgreen")
	drawTable(canvas, data)


####################################
# mode dispatcher
####################################

def mousePressed(event, data):
    if (data.mode == "run"): runMousePressed(event, data)
    if (data.mode == "setCycle"): setCycleMousePressed(event, data)

def keyPressed(event, data):
    if (data.mode == "run"): runKeyPressed(event, data)
    if (data.mode == "setCycle"): setCycleKeyPressed(event, data)

def timerFired(data):
	if (data.mode == "run"): runTimerFired(data)
	if (data.mode == "setCycle"): setCycleTimerFired(data)

def redrawAll(canvas, data):
    if (data.mode == "run"): runRedrawAll(canvas, data)
    if (data.mode == "setCycle"): setCycleRedrawAll(canvas, data)

####################################
# runUI function # from 15-112 #
# http://www.kosbie.net/cmu/spring-16/15-112/notes/
#		notes-animations-examples.html#modeDemo
####################################

def runUI(width=300, height=300):
    def redrawAllWrapper(canvas, data):
        canvas.delete(ALL)
        redrawAll(canvas, data)
        canvas.update()    

    def mousePressedWrapper(event, canvas, data):
        mousePressed(event, data)
        redrawAllWrapper(canvas, data)

    def keyPressedWrapper(event, canvas, data):
        keyPressed(event, data)
        redrawAllWrapper(canvas, data)

    def timerFiredWrapper(canvas, data):
        timerFired(data)
        redrawAllWrapper(canvas, data)
        # pause, then call timerFired again
        canvas.after(data.timerDelay, timerFiredWrapper, canvas, data)
    # Set up data and call init
    class Struct(object): pass
    data = Struct()
    data.width = width
    data.height = height
    data.timerDelay = 100 # milliseconds
    init(data)
    # create the root and the canvas
    root = Tk()
    canvas = Canvas(root, width=data.width, height=data.height)
    canvas.pack()
    # set up events
    root.bind("<Button-1>", lambda event:
                            mousePressedWrapper(event, canvas, data))
    root.bind("<Key>", lambda event:
                            keyPressedWrapper(event, canvas, data))
    timerFiredWrapper(canvas, data)
    # and launch the app
    root.mainloop()  # blocks until window is closed
    GPIO.cleanup()

runUI(800, 800)
