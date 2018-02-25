#!/usr/bin/env python3

import RPi.GPIO as GPIO
import time
import os
import subprocess

def writeFile(path, contents):
    with open(path, "wt") as f:
        f.write(contents)

def readFile(path):
    with open(path, "rt") as f:
        return f.read()

def getPicValue():
	read = readFile("/home/pi/Documents/values.txt")
	return int(read.split("\n")[1])

def getPhaseValue():
	read = readFile("/home/pi/Documents/values.txt")
	return (read.split("\n")[0] == "on")

def run():


	# FIX THE CAMERA! Reset it after each picture?

	# to run from startup, edit /etc/rc.local

	# turns the system on 
	path = "/home/pi/Documents/values.txt"
	contents = readFile(path).split("\n")
	contents[0] = "on"
	writeFile(path,"\n".join(contents))

	# initializes pins
	GPIO.setmode(GPIO.BCM)
	pins = [4,17,27,22,5,6,13,19]
	lightPins = pins[:2]
	picPins = pins[2:]
	GPIO.setup(pins, GPIO.OUT)
	
	off = GPIO.HIGH
	on = GPIO.LOW

	for pin in pins:
		GPIO.output(pin, off)

	# tests picture folder for validity
	while(True):
		picFolder = input("Enter picture storage folder:\n")
		directory = os.path.dirname("/var/www/html/"+picFolder+"/")
		if (os.path.isdir(directory)):
			writeFile("/var/www/html/folder.txt",picFolder)
			break

	# runs the system
	while True:

		inWhile = False #included so the pins are all turned off when off
		phase = getPhaseValue()
		
		# initialize the on phase
		if phase:
			initTime = time.time()
			lastPic = initTime
			picTime = 60*getPicValue()
			
			for pin in lightPins:
				GPIO.output(pin, on)
			
			for pin in picPins:
				GPIO.output(pin, off)

		# only run when in "on" phase
		while phase:

			inWhile = True
			
			#reads from file with multi-access
			try:
				phase = getPhaseValue()
				picTime = 60*getPicValue()
				currTime = time.time()
	
			except:
				continue

			if (currTime - lastPic) >= picTime:
				lastPic = currTime
				date = time.localtime(currTime)
				picName = time.strftime(":y%ym%md%dH%HM%M.jpg",date)
				address = "/var/www/html/" + picFolder + "/"
				# turn lights off
				for pin in lightPins:
					GPIO.output(pin, off)
				
				alphabet = ["A","B","C","D","E","F"]
				for i in range(len(picPins)):
					letter = alphabet[i]
					# turn pic lights on
					GPIO.output(picPins[i], on)
					# take picture
					subprocess.check_call(["fswebcam",address+picFolder+letter+picName])
					# turn pic lights off
					GPIO.output(picPins[i], off)

				# turn lights on
				for pin in lightPins:
					GPIO.output(pin, on)
				
				
		if inWhile: 
			for pin in pins:
				GPIO.output(pin, off)


from tkinter import *
import os

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
    data.folder = "test"
    data.running = False
    data.pins = [4,17,27,22,5,6,13,19]
    data.off = GPIO.HIGH
	data.on = GPIO.LOW

def pressLight(data, light):
	if data.lights[light]:
		GPIO.output(data.pins[light],data.off)
	else:
		GPIO.output(data.pins[light],data.on)
    data.lights[light] = not data.lights[light]
    

def press(data, index):
    if index == 0: pressLight(data, index)
    if index == 1 and not data.edit[1]: data.edit[0] = True
    if index == 2 and not data.edit[0]: data.edit[1] = True
    if index == 3: data.running = not data.running

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
            pressLight(data, index+1)
    if event.x > right and event.x < (right+bwidth):
        if event.y > top and event.y < top+bheight: 
            press(data, index)

def isValidFolder(data):
    return os.path.isdir(data.folder)

def keyPressed(event, data):
    # use event.char and event.keysym
    if data.edit[0]:
        if event.keysym == "Return": 
            if data.picTime.isdecimal(): #add time constraints here
                data.edit[0] = False
                data.pipe[0] = False
            else: data.error = "Must enter valid picture time"
        elif event.keysym.isdecimal(): 
            data.error = ""
            data.picTime += event.keysym
        elif event.keysym == "BackSpace": 
            data.picTime = data.picTime[:-1]
    if data.edit[1]:
        if event.keysym == "Return":
            if isValidFolder(data):
                data.edit[1] = False
                data.pipe[1] = False
            else: data.error = "Must enter valid folder name"
        elif event.keysym == "BackSpace":
            data.folder = data.folder[:-1]
        else:
            data.error = ""
            data.folder += event.char

def timerFired(data):
    if data.edit[0]:
        data.time += 1
        if data.time % 5 == 0: data.pipe[0] = not data.pipe[0]
    if data.edit[1]:
        data.time += 1
        if data.time % 5 == 0: data.pipe[1] = not data.pipe[1]

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

runUI(800, 600)
# try: run()
# except:
# 	print("oops!")
# 	GPIO.cleanup()