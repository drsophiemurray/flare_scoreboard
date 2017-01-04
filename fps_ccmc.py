"""
Created:						2016 December 15
@author:						somurray
Python Version:			Python 2.7.12 |Anaconda 4.2.0 (64-bit)| (default, Jul  2 2016, 17:42:40)
Working directory:	/home/somurray/Dropbox/tcd/
Description:				- Grab latest Flare Prediction Sysytem AR forecasts from https://solarmonitor.org/forecast.php
							- Convert to CCMC XML format.
							- Send to CCMC via anonymous ftp.
							- Keep XML or delete
"""

import datetime
import numpy as np
import re
import subprocess
import sys
import urllib2 
import xml.etree.cElementTree as ET

CENTRAL_DATE = datetime.datetime.utcnow()
FCAST_REGEX = '^[^\(]+'
SAVE_FOLDER = '/home/somurray/ccmc_test/'
CRON_JOB = "/home/somurray/Dropbox/tcd/projects/ccmc/ccmc_anonftp.sh"

def main():
	"""Main script for sending AR forecasts. Steps are as follows:
			- Grab the latest FPS forecast,
			- Convert to xml,
			- Put info into xml file,
			- ftp the xml file to CCMC,
			- Archive (or not).
	"""
	## Set up time
	year = CENTRAL_DATE.year
	month = CENTRAL_DATE.month
	day = CENTRAL_DATE.day
	## Get forecasts
	noaa_no, c_prob, m_prob, x_prob = grab_data(year, month, day)
	## Create full disk forecast
	c_full, m_full, x_full = full_disk(c_prob, m_prob, x_prob)
	## Get issued time
	issue_time = grab_time(year, month, day)
	## Create start and end times based on NOAA SRS time
	start_time = datetime.datetime(year, month, day, 00, 30)
	end_time = start_time + datetime.timedelta(days = 1)
	## Create xml
	xml_file = xml(issue_time, start_time, end_time, 
					noaa_no, c_prob, m_prob, x_prob,
					c_full, m_full, x_full)
	## Send to CCMC
	#ftp(xml_file)
	## Clean up
	#sys_call = "".join(['rm -r {}'.format(xml_file)])
	#subprocess.call(sys_call, shell = True) 	


def grab_data(year, month, day):
	"""Grab forecast from solarmonitor data repository
	"""
	## Create filename to get, ensuring leading zeroes are included
	filename = "".join(['arm_forecast_{}{}{}'.
					 format(year, str(month).zfill(2), str(day).zfill(2))])
	weblink = "".join(['https://solarmonitor.org/data/{}/{}/{}/meta/{}.txt'.
					format(year, str(month).zfill(2), str(day).zfill(2), filename)])
	forecast_data = []
	## Open file or exit if doesnt exist
	try:
		for line in urllib2.urlopen(weblink):
		##ARNO, McIntosh, C(C), M(M), X()
			forecast_data.append(line.split())
	except IOError:
		print "No forecast available for", CENTRAL_DATE.strftime("%Y-%m-%d")
		sys.exit()
	## Create output lists
	noaa_no = [""]*len(forecast_data)
	c_prob, m_prob, x_prob = [np.zeros(len(forecast_data)) for i in range(3)]
	for i in range(0, len(forecast_data)):
		noaa_no[i]  = str(forecast_data[i][0])
		c_prob[i] = int((re.findall('^[^\(]+', forecast_data[i][2])[0]))
		m_prob[i] = int((re.findall('^[^\(]+', forecast_data[i][3])[0]))
		x_prob[i] = int((re.findall('^[^\(]+', forecast_data[i][4])[0]))
	return noaa_no, c_prob, m_prob, x_prob


def full_disk(c_prob, m_prob, x_prob):
	"""Only AR forecasts are published by FPS,
	therefore need to calculate a full disk forecast
	"""
	c_full = 1 - (np.prod([1-i for i in c_prob/100.]))
	m_full = 1 - (np.prod([1-i for i in m_prob/100.]))
	x_full = 1 - (np.prod([1-i for i in x_prob/100.]))
	return c_full, m_full, x_full


def grab_time(year, month, day):
	"""Grab issue time from a separate file than the forecast
	in solarmonitor data repository
	"""
	## Create filename to get, ensuring leading zeroes are included
	filename = "".join(['arm_last_update_{}{}{}'.format(
											year, str(month).zfill(2), str(day).zfill(2))])
	weblink = "".join(['https://solarmonitor.org/data/{}/{}/{}/meta/{}.txt'.format(
										year, str(month).zfill(2), str(day).zfill(2), filename)])
	issue_time = []
	## Grab time or define as 00:30UT if file doesnt exist
	try:
		for line in urllib2.urlopen(weblink):
			##[['DD-Mon-YYYY', 'HH:MM', 'UT']]
			issue_time.append(line.split())
		issue_time = datetime.datetime.strptime((issue_time[0][0] + ' ' + issue_time[0][1]), '%d-%b-%Y %H:%M')
	except IOError:
		print "No issue time available for", CENTRAL_DATE.strftime("%Y-%m-%d")
		issue_time = datetime.datetime(year, month, day, 00, 30)
	return issue_time


def grab_locations():
	"""Grab noaa locations and times from the NOAA SRS themselves
	since SolarMonitor seems to convert to time issued
	"""
	return noaa_loc


def xml(issue_time, start_time, end_time, noaa_no, c_prob, m_prob, x_prob, c_full, m_full, x_full):
	"""Write to XML file in CCMC/ISES format
	"""
	message = ET.Element("message")
	forecast = ET.SubElement(message, "forecast")
	# Method
	ET.SubElement(forecast, "method").text= "SOLMON_1"
	# Issue time
	ET.SubElement(forecast, "issuetime").text = issue_time.strftime("%Y-%m-%dT%H:%MUT")
	# Prediction window
	predictionwindow = ET.SubElement(forecast, "predictionwindow")
	ET.SubElement(predictionwindow, "starttime").text = start_time.strftime("%Y-%m-%dT%H:%MUT")
	ET.SubElement(predictionwindow, "endttime").text = end_time.strftime("%Y-%m-%dT%H:%MUT")
	#----
	# Full disk forecast
	group = ET.SubElement(forecast, "group")
	ET.SubElement(group, "forecasttype").text = "Full Disk"
	# Create C full-disk forecast
	entry = ET.SubElement(group, "entry")
	ET.SubElement(entry, "fluxbin", name="C")
	probability = ET.SubElement(entry, "probability")
	ET.SubElement(probability, "value").text = str(format(round(c_full, 2), '.2f'))
	# Create M full-disk forecast
	entry = ET.SubElement(group, "entry")
	ET.SubElement(entry, "fluxbin", name="M")
	probability = ET.SubElement(entry, "probability")
	ET.SubElement(probability, "value").text = str(format(round(m_full, 2), '.2f'))
	# Create X full-disk forecast
	entry = ET.SubElement(group, "entry")
	ET.SubElement(entry, "fluxbin", name="X")
	probability = ET.SubElement(entry, "probability")
	ET.SubElement(probability, "value").text = str(format(round(x_full, 2), '.2f'))
	#----
	# AR forecast
	for i in range(0, len(noaa_no)):
		print "Writing AR ", i
		group = ET.SubElement(forecast, "group")
		ET.SubElement(group, "forecasttype").text = "Region"
		# Source region info
		sourceregion = ET.SubElement(group, "sourceregion")
		ET.SubElement(sourceregion, "id", scheme="NOAA_AR_numbering_scheme").text = str(noaa_no[i])
		#ET.SubElement(sourceregion, "location", time = issued_time).text = str(ar_cells[1].text)
		# Create C forecast
		entry = ET.SubElement(group, "entry")
		ET.SubElement(entry, "fluxbin", name="C")
		probability = ET.SubElement(entry, "probability")
		ET.SubElement(probability, "value").text = str(float(c_prob[i]/100.))
		# Create M forecast
		entry = ET.SubElement(group, "entry")
		ET.SubElement(entry, "fluxbin", name="M")
		probability = ET.SubElement(entry, "probability")
		ET.SubElement(probability, "value").text = str(float(m_prob[i]/100.))
		# Create X forecast
		entry = ET.SubElement(group, "entry")
		ET.SubElement(entry, "fluxbin", name="X")
		probability = ET.SubElement(entry, "probability")
		ET.SubElement(probability, "value").text = str(float(x_prob[i]/100.))
	#----
	tree = ET.ElementTree(message)
	filename = SAVE_FOLDER + "SOLMON_1_" + issue_time.strftime("%Y-%m-%dT%H:%MUT") + ".xml" 
	tree.write(filename)    
	return filename


def ftp(xml_file):
	"""FTP latest file to CCMC using doftp to bypass firewall:
	HOST: hanna.ccmc.gsfc.nasa.gov; USER: anonymous, PASS: solmon
	DIRECTORY: pub/FlareScoreboard/in/SOLMON_1
	"""
	sys_call = "".join(['{} {} SOLMON_1'.format(CRON_JOB, xml_file)])
	subprocess.call(sys_call, shell = True)

if __name__ == '__main__':
	main()
