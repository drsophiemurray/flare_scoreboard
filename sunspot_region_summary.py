'''
Created on Aug 26, 2015

@author: smurray
Python Version:    2.7.2 (default, Oct  1 2012, 15:56:20)
Working directory:     /home/smurray/workspace/verification

Description:
This was the beginnings of a code to push the Sunspot Region Summaries to CCMC.
BUT, not being archived anymore so stopped development. 
It needs to be fixed to get rid of the horrible 3-hourly local time part!

Grab latest Sunspot Region Summary from MASS archive
(moose:adhoc/projects/spaceweather/DEV/forecaster/documents/)
Convert to .docx format, then to CCMC xml format
Finally send to CCMC via anonymous ftp as per grab_json.py

Note:
I have locally installed docx for use here as not installed internally

Checking at 6(3+3),12(9+3),18(15+3),00(21+3)
'''

from docx import Document
import xml.etree.cElementTree as ET
import subprocess
import datetime
import os

CENTRAL_DATE = datetime.datetime.utcnow()
FOLDER = "moose:adhoc/projects/spaceweather/DEV/forecaster/documents/" #MOOSE archive location
SAVE_FOLDER = "/data/nwp1/smurray/Data/CCMC/" #where to save the files
FOLDER_DATE = CENTRAL_DATE.strftime("%Y/%m/%d/")
FORMAT = ["Space_Weather_Sunspot_Region_Summary_0200", "Space_Weather_Sunspot_Region_Summary_0800", 
            "Space_Weather_Sunspot_Region_Summary_1400", "Space_Weather_Sunspot_Region_Summary_2000"] #current format of SRS
CONVERT = "libreoffice --headless --convert-to docx --outdir"
CRON_JOB = "/net/home/h05/smurray/cron_jobs/ccmc_anonftp.sh"

def main():
    """fsfd
    """
    ##Get file from MASS
    file_start = grab_data()
    name = [fn for fn in os.listdir(SAVE_FOLDER) if any([fn.startswith(file_start)])]
    ##Get start and end times
    file_date = [fn.strip()[42:62] for fn in name]
    issued_time, start_time, end_time = get_times(file_date)
    ##Convert doc file to docx
    ###note headless prevents libreoffice from actually opening in x window - dont want that in a cron job!
    file_doc = SAVE_FOLDER+name[0]
    sys_call = "".join(['{} {} {}{}'.format(CONVERT, SAVE_FOLDER, SAVE_FOLDER, name[0])])
    subprocess.call(sys_call, shell = True)
    file_docx = file_doc+'x'
    ##Grab data that is needed
    worddoc = Document(file_docx)
    table = worddoc.tables
    ##Header cells
    header_cells = table[0].rows[0].cells
    ##Raw forecast
    raw_cells = table[0].rows[len(table[0].rows)-2].cells
    ##Issued forecast
    issued_cells = table[0].rows[len(table[0].rows)-1].cells
    ##Create XML files
    ###Note in this case I'm just using the raw forecast - could in theory create a file for total issued, 
    ###but for now I've left it since its the same as in the guidance documents.
    xml_file = xml(issued_time, start_time, end_time, raw_cells, table)
    ##Now send to CCMC
    #ftp(xml_file)
    ##Clean up temporary files
    clean_up(file_doc, file_docx, xml_file=None)
    
    
def xml(issued_time, start_time, end_time, raw_cells, table):
    "Write to XML file in CCMC/ISES format"
    message = ET.Element("message")
    forecast = ET.SubElement(message, "forecast")
    ##method
    ET.SubElement(forecast, "method").text= "MO_AR1"
    ##issue time
    ET.SubElement(forecast, "issuetime").text = issued_time
    ##prediction window
    predictionwindow = ET.SubElement(forecast, "predictionwindow")
    ET.SubElement(predictionwindow, "starttime").text = start_time
    ET.SubElement(predictionwindow, "endttime").text = end_time
    ##full disk forecast
    group = ET.SubElement(forecast, "group")
    ET.SubElement(group, "forecasttype").text = "Full Disk"
    ##Create M forecast
    entry = ET.SubElement(group, "entry")
    ET.SubElement(entry, "fluxbin", name="M")
    probability = ET.SubElement(entry, "probability")
    ET.SubElement(probability, "value").text = str(float(raw_cells[9].text)/100.)
    ##Create X forecast
    entry = ET.SubElement(group, "entry")
    ET.SubElement(entry, "fluxbin", name="X")
    probability = ET.SubElement(entry, "probability")
    ET.SubElement(probability, "value").text = str(float(raw_cells[10].text)/100.)
    ##AR forecast
    for i in range(1, len(table[0].rows) - 2):
        ar_cells = table[0].rows[i].cells
        if not ar_cells[0].text:
            print "Nothing here, moving on"
        else:
            print "Writing AR ", i
            group = ET.SubElement(forecast, "group")
            ET.SubElement(group, "forecasttype").text = "Region"
            ##Source region info
            sourceregion = ET.SubElement(group, "sourceregion")
            ET.SubElement(sourceregion, "id", scheme="NOAA_AR_numbering_scheme").text = str(ar_cells[0].text)
            ET.SubElement(sourceregion, "location", time=issued_time).text = str(ar_cells[1].text)
            ##Create M forecast
            entry = ET.SubElement(group, "entry")
            ET.SubElement(entry, "fluxbin", name="M")
            probability = ET.SubElement(entry, "probability")
            ET.SubElement(probability, "value").text = str(float(ar_cells[9].text)/100.)
            ##Create X forecast
            entry = ET.SubElement(group, "entry")
            ET.SubElement(entry, "fluxbin", name="X")
            probability = ET.SubElement(entry, "probability")
            ET.SubElement(probability, "value").text = str(float(ar_cells[10].text)/100.)
    tree = ET.ElementTree(message)
    filename = SAVE_FOLDER + "ftp/MO_AR1_" + issued_time + ".xml" 
    tree.write(filename)    
    return filename

def clean_up(file_doc, file_docx, xml_file):
    """"Cleaning up files that arent needed now ftp finished"""
    ##Can chose to save xml files or not
    if xml_file is None:
        print "No XMLs cleaned up"
    else:
        sys_call = "".join(['rm {}'.format(xml_file)])
        subprocess.call(sys_call, shell = True)  
    ##Delete the doc and docx files as available via MOOSE
    sys_call = "".join(['rm -r {}'.format(file_doc)])
    subprocess.call(sys_call, shell = True)   
    sys_call = "".join(['rm -r {}'.format(file_docx)])
    subprocess.call(sys_call, shell = True)     
    return 

def ftp(xml_file):
    """FTP latest file to CCMC using doftp to bypass firewall:
    HOST: hanna.ccmc.gsfc.nasa.gov; USER: anonymous, PASS: metoffice@blah.com
    DIRECTORY: pub/FlareScoreboard/in/MO_AR1"""
    sys_call = "".join(['{} {} MO_AR1'.format(CRON_JOB, xml_file)])
    subprocess.call(sys_call, shell = True)

def get_times(file_date):
    """Define start (same as issue) and end times for forecast"""
    issued_time = start_time = file_date[0]
    tmp_time = datetime.datetime(int(issued_time[0:4]), int(issued_time[5:7]), int(issued_time[8:10]), 
                             int(issued_time[11:13]), int(issued_time[14:16]), int(issued_time[17:19]))
    end_time = tmp_time + datetime.timedelta(days = 1)
    end_time = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    return issued_time, start_time, end_time

def grab_data():
    """Depending on what time it is grab the relevant SRS.
    If its not the correct time, exit the code to try later."""
    print 'The hour is', CENTRAL_DATE.hour
    if (CENTRAL_DATE.hour == 6) == True:
        sys_call = "".join(['moo get -v {}{}{}* {}.'.format(FOLDER, FOLDER_DATE, FORMAT[0], SAVE_FOLDER)])
        subprocess.call(sys_call, shell = True)  
        file_start = FORMAT[0]
        print 'Getting file', FORMAT[0]
    elif  (CENTRAL_DATE.hour == 12) == True:
        sys_call = "".join(['moo get -v {}{}{}* {}.'.format(FOLDER, FOLDER_DATE, FORMAT[1], SAVE_FOLDER)])
        subprocess.call(sys_call, shell = True)    
        file_start = FORMAT[1]
        print 'Getting file', FORMAT[1]
    elif  (CENTRAL_DATE.hour == 18) == True:
        sys_call = "".join(['moo get -v {}{}{}* {}.'.format(FOLDER, FOLDER_DATE, FORMAT[2], SAVE_FOLDER)])
        subprocess.call(sys_call, shell = True)    
        file_start = FORMAT[2]
        print 'Getting file', FORMAT[2]
    elif  (CENTRAL_DATE.hour == 0) == True:
        sys_call = "".join(['moo get -v {}{}{}* {}.'.format(FOLDER, FOLDER_DATE, FORMAT[3], SAVE_FOLDER)])
        subprocess.call(sys_call, shell = True)   
        file_start = FORMAT[3] 
        print 'Getting file', FORMAT[3]
    else:
        print "You shouldn't be running this cron job now!"
        exit()
    return file_start

if __name__ == '__main__':
    main()
