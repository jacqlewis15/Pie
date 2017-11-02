#!/usr/bin/env python3
import picamera
import RPi.GPIO as GPIO
import time

def readFile(path):
    with open(path, "rt") as f:
        return f.read()

def getLightValue():
	read = readFile("values.txt")
	return int(read.split("\n")[1])

def getDarkValue():
	read = readFile("values.txt")
	return int(read.split("\n")[2])

def getPicValue():
	read = readFile("values.txt")
	return int(read.split("\n")[3])

def getPhaseValue():
	read = readFile("values.txt")
	return (read.split("\n")[0] == "on")

def run():

	GPIO.setmode(GPIO.BCM)
	lightPin,picPin,stirPin = 26,20,21
	pins = [lightPin,picPin,stirPin]
	GPIO.setup(pins, GPIO.OUT)
	
	camera = picamera.PiCamera()
	off = GPIO.HIGH
	on = GPIO.LOW

	GPIO.output(lightPin, off)
	GPIO.output(stirPin, off)
	GPIO.output(picPin, off)

	while True:

		inWhile = False
		print("nothing works")
		phase = getPhaseValue()
		
		if phase:
			initTime = time.time()
			light = True
			dark = False

			lastLight = initTime
			lastDark = initTime
			lastPic = initTime

			print("before getting values")
			# convert from minutes to seconds
			lightTime = 60*getLightValue() 
			darkTime = 60*getDarkValue()
			picTime = 60*getPicValue()
			print("after getting values")

			# GPIO.setmode(GPIO.BCM)
			# lightPin,picPin,stirPin = 26,20,21
			# pins = [lightPin,picPin,stirPin]
			# GPIO.setup(pins, GPIO.OUT)
			
			# camera = picamera.PiCamera()
			# off = GPIO.HIGH
			# on = GPIO.LOW
			
			GPIO.output(lightPin, on)
			GPIO.output(stirPin, off)
			GPIO.output(picPin, off)

		# only run when in "on" phase
		while phase:

			inWhile = True

			print("before loop values")
			phase = getPhaseValue()
			print("after phase")
			lightTime = 60*getLightValue()
			print("after light") 
			darkTime = 60*getDarkValue()
			print("after dark")
			picTime = 60*getPicValue()
			print("after pic")
			currTime = time.time()
			print("after loop values")
			# print("after getting values in loop")

			if light and ((currTime - lastDark) >= lightTime):
				lastLight = currTime
				light = False
				dark = True
				# turn lights off
				GPIO.output(lightPin, off)
				# turn stir bar on
				GPIO.output(stirPin, on)
			if dark and ((currTime - lastLight) >= darkTime):
				lastDark = currTime
				light = True
				dark = False
				# turn lights on
				GPIO.output(lightPin, on)
				# turn stir bar off
				GPIO.output(stirPin, off)
			if (currTime - lastPic) >= picTime:
				lastPic = currTime
				date = time.localtime(currTime)
				picName = time.strftime("y%ym%md%dH%HM%M.jpg",date)
				picName = "pics/"+picName
				if light:
					# turn lights off
					GPIO.output(lightPin, off)
					# turn pic lights on
					GPIO.output(picPin, on)
					# take picture
					camera.capture(picName)
					# turn pic lights off
					GPIO.output(picPin, off)
					# turn lights on
					GPIO.output(lightPin, on)
				if dark:
					# turn stir bar off
					GPIO.output(stirPin, off)
					# turn pic lights on
					GPIO.output(picPin, on)
					# take picture
					camera.capture(picName) 
					# turn pic lights off
					GPIO.output(picPin, off)
					# turn stir bar on
					GPIO.output(stirPin, on)
		if inWhile: 
			GPIO.output(lightPin, off)
			GPIO.output(stirPin, off)
			GPIO.output(picPin, off)

try: run()
except:
	print("oops!") 
	GPIO.cleanup()