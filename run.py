#!/usr/bin/env python3

##################################
## HOW TO SET-UP A RASPBERRY PI ##
##################################

# 1. Change password from default raspberry:
#		from command line, input passwd
# 2. Enable camera and ssh:
#		preferences -> raspberry pi configuration -> interfaces
# 3. Install fswebcam: 
#		sudo apt-get install fswebcam
#		check that camera works: from command line, input fswebcam "image.jpg"
# 4. (Optional) to run from startup, edit /etc/rc.local (before the exit command)
#		python /home/pi/<path to file>/run.py &


import RPi.GPIO as GPIO
import serial
import string
import time
import os
import subprocess
from tkinter import *


# file reading/writing from 15-112 

def writeFile(path, contents):
    with open(path, "wt") as f:
        f.write(contents)

def readFile(path):
    with open(path, "rt") as f:
        return f.read()


####################################
# UI
####################################

def init(data):
	
	# Initialization of user interface

	data.lights = [False]*8 # Number of lights connected
	data.picTime = "1" 
	data.edit = [False,False,[False]*8,[False]*8] # run and cycle edits
	data.error = ""
	data.pipe = [False,False,[False]*8,[False]*8] # run and cycle edits
	data.time = 0
	data.lastPic = time.time()
	data.folder = "test"
	data.running = False
	data.mode = "run"
	data.picFolder = data.folder
	data.newPicTime = int(float(data.picTime)*60)

	data.ser = serial.Serial('/dev/ttyACM0', 9600) # , 8, 'N', 1, timeout=1
	data.pressure = "----"

	# Initializes cycles

	data.times = [[""]*8, [0]*8] # editing and non-editing
	data.cycles = [[""]*8, [0]*8] # editing and non-editing
	data.cycling = False
	data.edited = False

	# Initializes Raspberry Pi to communicate with relay board

	GPIO.setmode(GPIO.BCM)
	data.pins = [4,17,27,22,5,6,13,19]
	data.lightPins = data.pins[:2]
	data.picPins = data.pins[2:]
	GPIO.setup(data.pins, GPIO.OUT)
	data.off = GPIO.HIGH
	data.on = GPIO.LOW

	for pin in data.pins:
		GPIO.output(pin, data.off)


####################################
# run mode
####################################

# When the user presses any of the buttons on the left side of the UI
# this function will operate the lights and cause the UI to display
# any change.

def pressLight(data, light):
	
	if light == 8: pass # dummy index
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
	if index == 1 and not data.edit[1]: data.edit[0] = True
	if index == 2 and not data.edit[0]: data.edit[1] = True
	if index == 3: 
		# starts/stops the main testing system
		data.running = not data.running
		if data.running:
			data.time = 0
			data.lastPic = time.time()
			data.startTime = time.time()
			for i in range(len(data.lightPins)):
				GPIO.output(data.lightPins[i], data.on)
				data.lights[i] = True
			for i in range(len(data.picPins)):
				GPIO.output(data.picPins[i], data.off)
				data.lights[i+2] = False
		# turns everything off
		else:
			for i in range(len(data.pins)):
				GPIO.output(data.pins[i], data.off)
				data.lights[i] = False
	if index == 4 and not data.running: takePics(data)
	if index == 5 and not data.running and not data.lights[0]: takeAPic(data)
	if index == 10: data.mode = "setCycle"


# This function reacts to mouse clicks and reacts if a button is pressed

def runMousePressed(event, data):
	
	margin = 20
	center = data.width/2
	bheight = (data.height-margin*6)/9
	bwidth = data.width/3
	left = center/2-bwidth/4-margin
	right = center*3/2-bwidth*3/4+margin
	index = int((event.y-bheight)//(margin+bheight))
	top = bheight+index*(margin+bheight)

	# left column clicks
	if event.x > left and event.x < (left+bwidth):
		if event.y > top and event.y < top+bheight: 
			pressLight(data, index+2)
	# right column clicks
	if event.x > right and event.x < (right+bwidth):
		if event.y > top and event.y < top+bheight: 
			press(data, index)
	# far right clicks
	if event.x > right+bwidth+margin and event.x < right+bwidth*5/4+margin:
		if event.y > bheight+(margin+bheight) and event.y < 2*bheight+(margin+bheight):
			press(data, 10)


# This function determines if the path given is a folder

def isValidFolder(data):
	return os.path.isdir(data.folder)


# This function reacts to user key strokes and responds accordingly.

def runKeyPressed(event, data):

	# If the picture time is being edited, only valid times can be entered
	if data.edit[0]:
		if event.keysym == "Return": 
			if float(data.picTime) >= 0.5 and float(data.picTime) <= 100.0: #add time constraints here 
				data.edit[0] = False
				data.pipe[0] = False
				data.newPicTime = int(float(data.picTime)*60)
				data.cycling = False
			else: data.error = "Must enter valid picture time"
		elif event.keysym.isdecimal(): 
			data.error = ""
			data.picTime += event.keysym
			if len(data.picTime)>7: data.picTime = data.picTime[:-1]
		elif event.keysym == "BackSpace": 
			data.picTime = data.picTime[:-1]
		elif event.keysym == "period" and (data.picTime.isdecimal() or data.picTime == ""):
			data.picTime += "."
	# if the folder name is being edited, only valid folder names can be entered
	if data.edit[1]:
		if event.keysym == "Return":
			if isValidFolder(data):
				data.edit[1] = False
				data.pipe[1] = False
				data.picFolder = data.folder
				data.error = ""
			else: data.error = "Must enter valid folder name"
		elif event.keysym == "BackSpace":
			data.folder = data.folder[:-1]
		else:
			data.error = ""
			data.folder += event.char
		if len(data.folder) > 18: data.folder = data.folder[:-1]


# This function takes a single picture of the testing system

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
            subprocess.check_call(["fswebcam",address+foldName[-1]+letter+picName,"-r 2592x1944"])
    # no light on has no differentiating letter in pic name
    if data.lights == [False]*8: 
        subprocess.check_call(["fswebcam",address+foldName[-1]+picName,"-r 2592x1944"])    


# This function takes 6 picures of the testing system, one for each
# different picture light available.

def takePics(data):

	# develops a name for the picture
	date = time.localtime(time.time())
	picName = time.strftime(":y%ym%md%dH%HM%M.jpg",date)
	address = data.picFolder + "/"
	
	# makes sure all lights are off initially
	for i in range(len(data.pins)):
		GPIO.output(data.pins[i], data.off)
		data.lights[i] = False

	# ensures that any subfolders aren't re-called
	foldName = data.picFolder.split("/") 
	alphabet = ["A","B","C","D","E","F"]
	for i in range(len(data.picPins)):
		letter = alphabet[i]
		# turn pic lights on
		GPIO.output(data.picPins[i], data.on)
		# take picture
		subprocess.check_call(["fswebcam",address+foldName[-1]+letter+picName,"-r 2592x1944"])
		# turn pic lights off
		GPIO.output(data.picPins[i], data.off)


# This function maintains the timing of the system.

def runTimerFired(data):

	# checks if the amount of time between pictures that was set has passed
	if data.running:
		if (time.time() - data.lastPic) >= data.newPicTime:
			takePics(data)
			# turn lights on
			data.lastPic = time.time()
			for i in range(len(data.lightPins)):
				GPIO.output(data.lightPins[i], data.on)
				data.lights[i] = True
			if data.cycling: 
				data.numCycles += 1
				if data.numCycles >= data.cycles[1][data.cIndex]:
					nextCycle(data)
	# updates the blinking cursor for editing
	if data.edit[0]:
		if data.time % 5 == 0: data.pipe[0] = not data.pipe[0]
	if data.edit[1]:
		if data.time % 5 == 0: data.pipe[1] = not data.pipe[1]
	data.time += 1


# Provides a user-readable description of a light's status

def isOn(data, light):
    if data.lights[light]: return "Off"
    else: return "On"


# Creates a cursor from true/false data

def piping(data, index):
	if index: return "|"
	else: return ""


# Draws the icons and words on the UI

def drawButtons(canvas, data):

	# sizing for buttons
	lights = ["White","Blue","Green","Yellow","Red","UV"]
	margin = 20
	center = data.width/2
	bheight = (data.height-margin*6)/9
	bwidth = data.width/3
	left = center/2-bwidth/4-margin
	right = center*3/2-bwidth*3/4+margin

	# creates all buttons
	for i in range(6):
		text = lights[i]+" Light "+ isOn(data,i+2)
		top = bheight+i*margin+i*bheight
		bottom = top+bheight
		canvas.create_rectangle(left,top,left+bwidth,bottom,fill="lightgray")
		if (i == 1 or i == 2): color="lightblue"
		else: color="lightgray"
		canvas.create_text(left+bwidth/2,top+bheight/2,text=text,font="Arial 20 bold")
		canvas.create_rectangle(right,top,right+bwidth,bottom,fill=color)    
		fill="black"
		if i == 0: 
			text2 = "Illumination " + isOn(data,0)
			font2 = "Arial 20 bold"
		if i == 1:
			text2 = "Pic Time: " + data.picTime + piping(data,data.pipe[0]) + " minute(s)"
			font2 = "Arial 15 bold"
			corner = right+bwidth+margin
			canvas.create_rectangle(corner,top,corner+bwidth/4,bottom,fill="lightgray")
			canvas.create_text(corner+bwidth/8,top+bheight/2,text="Set\nCycle",font="Arial 15 bold")
		if i == 2:
			text2 = "Folder: " + data.folder + piping(data,data.pipe[1])
			font2 = "Arial 15 bold"
		if i == 3:
			if data.running: text2,fill = "End run","red"  
			else: text2,fill = "Start run","black"
			font2 = "Arial 20 bold"
			corner = right+bwidth+margin+2
			if data.cycling: canvas.create_text(corner+bwidth/8,top+bheight/2,text="Cycle Set",font="Arial 15 bold")
		if i == 4: text2 = "Take Pictures"
		if i == 5: text2 = "Take a Picture"
		canvas.create_text(right+bwidth/2,top+bheight/2,text=text2,font=font2,fill=fill)


# This function creates the clocks visible at the bottom of the
# screen while the system is running. One keeps track of how 
# long until the next pictuer is taken and the other keeps track
# of how long the system has been running.

def drawTimes(canvas, data):

	# sizes to place clocks below all buttons
    margin = 20
    center = data.width/2
    bheight = (data.height-margin*6)/9
    bwidth = data.width/3
    left = center/2-bwidth/4-margin
    right = center*3/2-bwidth*3/4+margin
    top = bheight+6*margin+6*bheight
    bottom = top+bheight

    # draws the clocks when running
    if data.running:
        tim = time.time()-data.startTime
        m,s = divmod(tim,60)
        h,m = divmod(m,60)
        text = ("Time running: " + "%d:%02d:%02d") % (h,m,s)
        tim = data.newPicTime - (time.time()-data.lastPic)
        m,s = divmod(tim,60)
        h,m = divmod(m,60)
        text2 = ("Next pic in: " + "%d:%02d:%02d") % (h,m,s)
        canvas.create_text(right+bwidth/2,top+bheight/2,text=text,font="Arial 15 bold")
        canvas.create_rectangle(right,top,right+bwidth,bottom)
        canvas.create_text(left+bwidth/2,top+bheight/2,text=text2,font="Arial 15 bold")
        canvas.create_rectangle(left,top,left+bwidth,bottom)


# This function connects to the Arduino and prints the pressure output.

def drawSensors(canvas, data):

	# sizes to place pressure display below all buttons
	margin = 20
	center = data.width/2
	bheight = (data.height-margin*6)/9
	bwidth = data.width/3
	left = center/2-bwidth/4-margin
	right = center*3/2-bwidth*3/4+margin
	top = bheight+6*margin+6*bheight
	bottom = top+bheight

	if data.time % 5 == 0: 
		# read from serial port
		data.pressure = data.ser.readline()

	sensorData = str(data.pressure)[2:-5].split(",")
	if len(sensorData) != 2: sensorData = [""]*2
	text = "Pressure: " + sensorData[0]
	text2 = "Oxygen: " + sensorData[1]
	canvas.create_text(left+bwidth/2,data.height-bheight/4,text=text,font="Arial 20 bold")
	canvas.create_text(right+bwidth/2,data.height-bheight/4,text=text2,font="Arial 20 bold")


# This function draws the UI every frame.

def runRedrawAll(canvas, data):
    
    canvas.create_rectangle(0,0,data.width+5,data.height+5,fill="lightblue")
    drawButtons(canvas, data)
    drawTimes(canvas, data)
    drawSensors(canvas,data)
    canvas.create_text(data.width/2,20,text=data.error,font="Arial 20 bold",fill="red")


####################################
# setCycle mode
####################################

# This function edits the cycle system when editing.

def writeCycle(event, data, index, col):

	data.error = ""
	data.edited = True # allows the user to look at the cycle without resetting it
	if col == 2: lst = data.times
	if col == 3: lst = data.cycles

	# verifies that any data entered is within the allowable limits
	if event.keysym == "Return": 
		if lst[0][index] == "" or (float(lst[0][index]) >= 0.5 and float(lst[0][index]) <= 100.0): #add time constraints here 
			data.edit[col][index] = False
			data.pipe[col][index] = False
			if lst[0][index] == "": lst[1][index] = 0
			else: 
				if col == 2: lst[1][index] = int(float(lst[0][index])*60)
				# cycle numbers can only be integers
				else: lst[1][index] = int(lst[0][index])
		else: data.error = "Must enter valid picture time"
	elif event.keysym.isdecimal(): 
		lst[0][index] += event.keysym
		if len(lst[0][index])>7: lst[0][index] = lst[0][index][:-1]
	elif event.keysym == "BackSpace": 
		lst[0][index] = lst[0][index][:-1]
	elif event.keysym == "period" and (lst[0][index].isdecimal() or lst[0][index] == ""):
		lst[0][index] += "."
	else: data.edited = False


# This function reacts to mouse clicks in the set cycle mode.

def setCycleMousePressed(event, data):

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
	# repeats the cycle at the end
	if data.cIndex > 7:
		startCycle(data)
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
			if data.edit[2][i] or data.edit[3][i]: data.error = "Must complete edit"
			elif data.times[0][i] != "" and data.cycles[0][i] == "": data.error = "Must complete edit"
			elif data.times[0][i] == "" and data.cycles[0][i] != "": data.error = "Must complete edit"
		if data.error == "": 
			data.mode = "run"
			if data.edited and data.times[0] != [""]*8:
				data.cycling = True
				startCycle(data)


# This function updates every clock cycle and takes pictures at intervals.

def setCycleTimerFired(data):

	# checks if the time between pictures has elapsed
	if data.running:
		if (time.time() - data.lastPic) >= data.newPicTime:
			takePics(data)
			# turn lights on
			data.lastPic = time.time()
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
		canvas.create_text(left+bwidth/2,(i+3/2)*bheight,text=text1,font="Arial 20 bold")
		canvas.create_text(center+bwidth/2,(i+3/2)*bheight,text=text2,font="Arial 20 bold")
		if i == 0: 
			canvas.create_text(left+bwidth/2,3/2*bheight,text="Time", font="Arial 20 bold")
			canvas.create_text(center+bwidth/2,3/2*bheight,text="Number of Cycles",font="Arial 20 bold")
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

runUI(800, 600)
