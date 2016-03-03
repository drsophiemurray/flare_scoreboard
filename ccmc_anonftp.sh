#!/bin/bash
# script expects two arguments: filename (can include full path to filename) and target foldername on the ftp site (method shortname)
#examples:   
# bash anonftp.sh file.txt MO_AR1
# bash anonftp.sh file.txt MO_TOT1
#put $FILE


HOST='hanna.ccmc.gsfc.nasa.gov'
USER='anonymous'
PASSWD='someone@somewhere.com'
INFILE=$1
FOLDER=$2
echo hello from anonftp.sh
FPATH=`dirname $INFILE`
FILE=`basename $INFILE`
cd $FPATH
if [ -r $FILE ]
then
echo file exists - start uploading
doftp -host $HOST -user $USER -pass $PASS <<END_SCRIPT

cd pub/FlareScoreboard/in/$FOLDER
put $FILE
quit
END_SCRIPT
echo file exists - done uploading
fi
echo goodbye from anonftp.sh
exit 0