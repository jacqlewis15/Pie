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
# 4. (Optional) to run from startup, edit /etc/rc.local

import RPi.GPIO as GPIO
import time
import os
import subprocess
from tkinter import *

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
	# load data.xyz as appropriate
	data.lights = [False]*8
	data.picTime = "1" # change to 5 later
	data.edit = [False]*2
	data.error = ""
	data.pipe = [False]*2
	data.time = 0
	data.lastPic = 0
	data.folder = "test"
	data.running = False
	# data.phase = False
	data.picFolder = data.folder
	data.newPicTime = int(float(data.picTime)*400)

	GPIO.setmode(GPIO.BCM)
	data.pins = [4,17,27,22,5,6,13,19]
	data.lightPins = data.pins[:2]
	data.picPins = data.pins[2:]
	GPIO.setup(data.pins, GPIO.OUT)
	data.off = GPIO.HIGH
	data.on = GPIO.LOW

	for pin in data.pins:
		GPIO.output(pin, data.off)

def pressLight(data, light):
	if not data.running:
		# if light == 0:
		# 	GPIO.output(data.pins[0],data.off)
		if data.lights[light]:
			if light == 0: 
				GPIO.output(data.pins[1],data.off)
				data.lights[1] = False
			GPIO.output(data.pins[light],data.off)
			data.lights[light] = False
		else:
			for i in range(len(data.pins)):
				GPIO.output(data.pins[i], data.off)
				data.lights[i] = False
			if light == 0: 
				GPIO.output(data.pins[1],data.on)
				data.lights[1] = True
			GPIO.output(data.pins[light],data.on)
			data.lights[light] = True


def press(data, index):
	if index == 0 and not data.running: pressLight(data, index)
	if index == 1 and not data.edit[1]: data.edit[0] = True
	if index == 2 and not data.edit[0]: data.edit[1] = True
	if index == 3: 
		data.running = not data.running
		if data.running:
			data.time = 0
			for i in range(len(data.lightPins)):
				GPIO.output(data.lightPins[i], data.on)
				data.lights[i] = True
			for i in range(len(data.picPins)):
				GPIO.output(data.picPins[i], data.off)
				data.lights[i+2] = False
		else:
			for i in range(len(data.pins)):
				GPIO.output(data.pins[i], data.off)
				data.lights[i] = False
	if index == 4 and not data.running: takePics(data)

def mousePressed(event, data):
	# use event.x and event.y
	margin = 20
	center = data.width/2
	bheight = (data.height-margin*5)/8
	bwidth = data.width/3
	left = center/2-bwidth/4-margin
	right = center*3/2-bwidth*3/4+margin
	index = int((event.y-bheight)//(margin+bheight))
	top = bheight+index*(margin+bheight)
	if event.x > left and event.x < (left+bwidth):
		if event.y > top and event.y < top+bheight: 
			pressLight(data, index+2)
	if event.x > right and event.x < (right+bwidth):
		if event.y > top and event.y < top+bheight: 
			press(data, index)

def isValidFolder(data):
	return os.path.isdir(data.folder)

def keyPressed(event, data):
	# use event.char and event.keysym
	if data.edit[0]:
		if event.keysym == "Return": 
			if float(data.picTime) >= 0.5 and float(data.picTime) <= 100.0: #add time constraints here 
				data.edit[0] = False
				data.pipe[0] = False
				data.newPicTime = int(float(data.picTime)*400)
			else: data.error = "Must enter valid picture time"
		elif event.keysym.isdecimal(): 
			data.error = ""
			data.picTime += event.keysym
			if len(data.picTime)>7: data.picTime = data.picTime[:-1]
		elif event.keysym == "BackSpace": 
			data.picTime = data.picTime[:-1]
		elif event.keysym == "period" and (data.picTime.isdecimal() or data.picTime == ""):
			data.picTime += "."
	if data.edit[1]:
		if event.keysym == "Return":
			if isValidFolder(data):
				data.edit[1] = False
				data.pipe[1] = False
				data.picFolder = data.folder
			else: data.error = "Must enter valid folder name"
		elif event.keysym == "BackSpace":
			data.folder = data.folder[:-1]
		else:
			data.error = ""
			data.folder += event.char
		if len(data.folder) > 18: data.folder = data.folder[:-1]

def takePics(data):

	date = time.localtime(time.time())
	picName = time.strftime(":y%ym%md%dH%HM%M.jpg",date)
	address = data.picFolder + "/"
	
	for i in range(len(data.pins)):
		GPIO.output(data.pins[i], data.off)
		data.lights[i] = False

	alphabet = ["A","B","C","D","E","F"]
	for i in range(len(data.picPins)):
		letter = alphabet[i]
		# turn pic lights on
		GPIO.output(data.picPins[i], data.on)
		# take picture
		subprocess.check_call(["fswebcam",address+data.picFolder+letter+picName,"-S 1"])
		# time.sleep(1)
		# turn pic lights off
		GPIO.output(data.picPins[i], data.off)

def timerFired(data):
	if data.running:
		if (data.time - data.lastPic) >= data.newPicTime:
			data.lastPic = data.time
			takePics(data)
			# turn lights on
			for i in range(len(data.lightPins)):
				GPIO.output(data.lightPins[i], data.on)
				data.lights[i] = True
	if data.edit[0]:
		# data.time += 1
		if data.time % 5 == 0: data.pipe[0] = not data.pipe[0]
	if data.edit[1]:
		# data.time += 1
		if data.time % 5 == 0: data.pipe[1] = not data.pipe[1]
	data.time += 1

def isOn(data, light):
    if data.lights[light]: return "Off"
    else: return "On"

def drawButtons(canvas, data):
    lights = ["White","Blue","Green","Yellow","Red","UV"]
    margin = 20
    center = data.width/2
    bheight = (data.height-margin*5)/8
    bwidth = data.width/3
    left = center/2-bwidth/4-margin
    right = center*3/2-bwidth*3/4+margin
    for i in range(6):
        text = lights[i]+" Light "+ isOn(data,i+2)
        top = bheight+i*margin+i*bheight
        bottom = top+bheight
        canvas.create_rectangle(left,top,left+bwidth,bottom,fill="lightgray")
        canvas.create_text(left+bwidth/2,top+bheight/2,text=text,font="Arial 20 bold")
        canvas.create_rectangle(right,top,right+bwidth,bottom,fill="lightgray")    
        if i == 0: 
            text2 = "Illumination " + isOn(data,0)
            font2 = "Arial 20 bold"
        if i == 1:
            if data.pipe[0]: pipe = "|"
            else: pipe = ""
            text2 = "Pic Time: " + data.picTime + pipe + " minute(s)"
            font2 = "Arial 15 bold"
        if i == 2:
            if data.pipe[1]: pipe = "|"
            else: pipe = ""
            text2 = "Folder: " + data.folder + pipe
            font2 = "Arial 15 bold"
        if i == 3:
            if data.running: text2 = "End run"
            else: text2 = "Start run"
            font2 = "Arial 20 bold"
        if i == 4:
            text2 = "Take Pictures"
        if i == 5:
        	text2 = ""
        canvas.create_text(right+bwidth/2,top+bheight/2,text=text2,font=font2)

def redrawAll(canvas, data):
    # draw in canvas
    
    canvas.create_rectangle(0,0,data.width+5,data.height+5,fill="lightblue")
    drawButtons(canvas, data)
    # if data.edit[0]: canvas.create_text()
    canvas.create_text(data.width/2,20,text=data.error,font="Arial 20 bold",fill="red")

####################################
# runUI function
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
# try: runUI(800,600)
# except:
# 	print("oops!")
# 	GPIO.cleanup()