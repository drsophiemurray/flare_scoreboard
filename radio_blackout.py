'''
Created on Jun 24, 2015

@author: smurray 

Python Version:    2.7.2 (default, Oct  1 2012, 15:56:20)
Working directory:     /home/smurray/workspace/verification

Description:
- Grab latest full disk forecast from space weather guidance documents
- Then convert to XML format for CCMC 
    (http://ccmc.gsfc.nasa.gov/challenges/flare.php)
- Then doftp to 
    ftp://hanna.ccmc.gsfc.nasa.gov/pub/FlareScoreboard/in/MO_TOT1/

Notes:
- MASS files are in form YYYY-MM-DDThh-mm-ss.json
- Comment out 'put' line in anonftp.sh or the ftp part below 
    for testing purposes if you dont want it sent to CCMC.
'''

import json
import datetime
import subprocess
import xml.etree.cElementTree as ET
#import glob
import os

CENTRAL_DATE = datetime.datetime.utcnow()
DAY_BEFORE = CENTRAL_DATE - datetime.timedelta(days=1)
TODAY = "".join(("moose:/adhoc/projects/spaceweather/forecaster/bulletins/",
                 CENTRAL_DATE.strftime("%Y/%m/%Y-%m-%d*")))   
YESTERDAY = "".join(("moose:/adhoc/projects/spaceweather/forecaster/bulletins/",
                     DAY_BEFORE.strftime("%Y/%m/%Y-%m-%d*")))   
FOLDER = "/data/nwp1/smurray/Data/CCMC/"
CRON_JOB = "/net/home/h05/smurray/cron_jobs/ccmc_anonftp.sh"

def main():
    """Determine if its day or night, 
       then run correct code to convert to XML format,
       and ftp to CCMC.
       """
    # Get all of todays and yesterdays data
    grab_data()
    # Now find latest file
    names = [fn for fn in os.listdir(FOLDER) if any([fn.endswith('json')])]
    sorted_file = sorted(names, 
                         key=lambda x: datetime.datetime.strptime(x.strip()[0:19], 
                         '%Y-%m-%dT%H-%M-%S'))
    newest = FOLDER + sorted_file[len(sorted_file) - 1]
    print "Newest file is", newest
    # Get the data
    json_data = open(newest).read()
    data = json.loads(json_data)    
    flare_forecast = data["categories"][3]    
    # Check it isnt the same file as was grabbed last time
    previous = open(FOLDER + 'ftp/latest.json').read()
    previous = json.loads(previous)    
    previous_issued_time =  previous["categories"][3]["saved_dt"]
    issued_time = flare_forecast["saved_dt"]
    #  Note, this issued time is also in data["overview"]["saved_dt"]
    if (issued_time == previous_issued_time) == True:
        print "No new files to ftp"
        xml_file = []
        # Some housekeeping at the end to remove temporary files
        clean_up(newest, xml_file=None, keep=sorted_file[len(sorted_file) - 1])
    else:   
        print "Forecast issued:", issued_time
        # Grab probabilities (format: day1,day2,day3,day4)
        m_probs = flare_forecast["probabilities"][0] 
        x_probs = flare_forecast["probabilities"][1]
        print "M forecast:", m_probs
        print "X forecast:", x_probs 
        # Create XML for each day forecasted and send to CCMC
        for i in range(0, len(m_probs)):
            day = 'day' + str(i + 1)
            print "Working on forecast for", day
            m_prob = m_probs[day]
            x_prob = x_probs[day]
            start_time = get_end(issued_time, i)
            end_time = get_end(start_time, 1)
            xml_file = xml(issued_time, start_time, end_time, 
                           m_prob, x_prob, day)
            print "The following file will be ftp-ed to CCMC:"
            print xml_file
#            ftp(xml_file)
            # Some housekeeping at the to remove temporary files
        clean_up(newest, xml_file=None, 
                 keep=sorted_file[len(sorted_file) - 1])
    print "All done!"

    
def xml(issued_time, start_time, end_time, m_prob, x_prob, prefix):
    """Write to XML file in CCMC/ISES format.
       """
#    ET.SubElement(entry, "field2", name="asdfasd").text = "some value2"
    message = ET.Element("message")
    forecast = ET.SubElement(message, "forecast")
    # method
    ET.SubElement(forecast, "method").text= "MO_TOT1"
    # issue time
    ET.SubElement(forecast, "issuetime").text = issued_time
    # prediction window
    predictionwindow = ET.SubElement(forecast, "predictionwindow")
    ET.SubElement(predictionwindow, "starttime").text = start_time
    ET.SubElement(predictionwindow, "endtime").text = end_time
    # input data
#   ET.SubElement(forecast, "input_data").text= "----"
    ##full disk forecast
    group = ET.SubElement(forecast, "group")
    ET.SubElement(group, "forecasttype").text = "Full Disk"
#    ET.SubElement(group, "sourceregion").text = "Full Disk"
    # Create M forecast
    entry = ET.SubElement(group, "entry")
    ET.SubElement(entry, "fluxbin", name="M")
    probability = ET.SubElement(entry, "probability")
    ET.SubElement(probability, "value").text = str(m_prob/100.)
#    ET.SubElement(probability, "uncertainty")
#    ET.SubElement(probability, "value_lower")
#    ET.SubElement(probability, "value_upper")
#    ET.SubElement(entry, "level")
    # Create X forecast
    entry = ET.SubElement(group, "entry")
    ET.SubElement(entry, "fluxbin", name="X")
    probability = ET.SubElement(entry, "probability")
    ET.SubElement(probability, "value").text = str(x_prob/100.)
#    ET.SubElement(probability, "uncertainty")
#    ET.SubElement(probability, "value_lower")
#    ET.SubElement(probability, "value_upper")
#    ET.SubElement(entry, "level")
    tree = ET.ElementTree(message)
    filename = FOLDER + "ftp/MO_TOT1_" + issued_time + "_" + prefix + ".xml" 
    tree.write(filename)    
    return filename

    
def get_end(issued_time, i):
    """Add 24hours to issued time for end time of prediction window.
       """
    tmp_time = datetime.datetime(int(issued_time[0:4]), int(issued_time[5:7]),
                                 int(issued_time[8:10]), int(issued_time[11:13]),
                                 int(issued_time[14:16]), int(issued_time[17:19]))
    end_time = tmp_time + datetime.timedelta(days=i)
    end_time = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    return end_time

        
def grab_data():
    """Grabbing whole days worth of data for now.
       Too complicated otherwise with the varying times the forecasters issue it
       (plus sometimes they issue multiple times).
       Need to check if there's a MOOSE command I could use instead...
       """
    sys_call = "".join(['moo get -v {} {}.'.format(YESTERDAY, FOLDER)])
    subprocess.call(sys_call, shell = True)    
    sys_call = "".join(['moo get -v {} {}.'.format(TODAY, FOLDER)])
    subprocess.call(sys_call, shell = True)    
    return


def ftp(xml_file):
    """FTP latest file to CCMC using doftp to bypass firewall:
       HOST: hanna.ccmc.gsfc.nasa.gov; USER: anonymous, PASS: metoffice@blah.com
       DIRECTORY: pub/FlareScoreboard/in/MO_TOT1
       """
    sys_call = "".join(['{} {} MO_TOT1'.format(CRON_JOB, xml_file)])
    subprocess.call(sys_call, shell = True)


def clean_up(newest, xml_file, keep):
    """"Cleaning up now all done.
        """
    # Copy to latest file for later
    if xml_file is None:
        print "No XMLs cleaned up"
    else:
        # Delete the xml files
        sys_call = "".join(['rm {}'.format(xml_file)])
        subprocess.call(sys_call, shell = True)  
    # copy newest file to latest to check in next script call  
    sys_call = "".join(['cp {} {}ftp/latest.json'.format(newest, FOLDER)])
    subprocess.call(sys_call, shell = True)
    # copy same keeping its name for my archiving  
    sys_call = "".join(['cp {} {}ftp/{}'.format(newest, FOLDER, keep)])
    subprocess.call(sys_call, shell = True)
    # Delete the json files
    sys_call = "".join(['rm -r {}*.json'.format(FOLDER)])
    subprocess.call(sys_call, shell = True)    
    return 


if __name__ == '__main__':
    main()
