
# calibrate_adc.py
# Jacqueline Lewis

# This file calibrates an adc for use with a photoreactor following the run.py
# protocol. The values returned from these functions, when operated properly,
# can be added to the initADC function in run.py in order to get accurate
# oxygen and pressure readings. These functions should be run each time a new
# pi, adc, pressure sensor, or oxygen sensor is added to the system.

import time
import adafruit_ads1x15.differential as ads1x15

# This function gets a reading from the ADC
def getreading(adc,channel):
	return adc.read_adc_difference(channel)

# This function builds an ADC. When using this function, make sure to update 
# the ADS1x15 declaration to match the type of ADC being used. Failure to do so
# will result in erroneous data.
def buildADC():
	return ads1x15.ADS1115()

# This function provides the oxygen calibration value. The oxygen sensor must 
# be open to atmosphere for this calibration.
def O2calibrate():
	adc = buildADC()
	sumVals = 0
	for i in range(100):
		time.sleep(0.15)
		val = getreading(adc, 0)
		sumVals += val
		print(val)
	print("O2 calibration value: %f" % (20.9/(sumVals/100.0)))

# This function provides the pressure calibration values. During the 
# calibration, the photoreactor should go from atmospheric to pressured to 
# give the full range of operation.
def Pcalibrate():
	adc = buildADC()
	maxP = None
	minP = None
	for i in range(1000):
		time.sleep(0.15)
		val = getreading(adc, 0)
		print(val)
		if maxP == None or val > maxP: maxP = val
		if minP == None or val < minP: minP = val
	print("Pressure calibration value: %f" % (600/(maxP-minP)))
	print("Pressure zeropoint: %f" % (minP))


# O2calibrate()
# Pcalibrate()