#!/usr/bin/python
# db3_rerun.py - run reconstruction on a list of given tilt series from the database (saved from Inbox/Workbox), SLURM launch raptor and submision rec to database
# based on db3_proc and db_run_reconstruction.py created 04/06/13
# created 04/21/2021


import string
import os
import sys
import getopt
import MySQLdb
import fnmatch
import math
import time
import db3_inc
import datetime

thisversion = "v2021-04-10"

outputdir = ''
logstring = ''
useremail = ''
machinename = ''
keepali = "0"
count = 0

#function to exit the program cleanly  
def db3_exit(status, outputdir, logstring, msg):
    msg = time.strftime("%H:%M:%S",time.localtime())+' '+msg+' Exit. '
    if logstring == '':
        print (msg)
        sys.exit(1)
    if count == 0:
        finalmsg = '\n\nYour rerun session '+logstring+' has finished. 0 tilt series found to be reconstructed.'
    else:
        finalmsg = '\n\nAll jobs in your rerun session '+logstring+' have been submitted. Please wait until all submitted jobs to finish. After that you can delete everything under "Pipeline_Proc".'
        if keepali == "1":
            finalmsg = finalmsg + '\n\nSince you chose to keep the alignment files, all eman2 files or .ali and .tlt files will be kept under the folder "Pipeline_Proc". This folder is not for long term storage. Please remove the files after you copy them to your local computer.'
    if status == -1: # notify admin 
        subject = '[Rerun Pipeline3] Fatal Error from rerun'
        msg = msg + ' . Something went wrong. Administrator has been notified. Do not delete anything until administrator finishes checking.'
        db3_inc.email_to(useremail, subject, msg, machinename)
        db3_inc.email_to(db3_inc.admin_email, subject, msg, machinename)
        sys.exit(1)
    elif status >= 0:
        if count == 0:
            subject = '[Rerun Pipeline3] 0 tilt series found'
        else:
            subject = '[Rerun Pipeline3] Notice'
        msg = msg + finalmsg
        db3_inc.email_to(useremail, subject, msg, machinename)
    sys.exit(0)



machinename = os.uname()[1]
if len(sys.argv) <= 3:
    print ('!! RUN as USER on Pipeline Machine!')
    print ('you are using '+machinename)
    print ('Automatic processing and uploading tilt series under one directory into database')
    print ('Called by cluster script')
    print ('quit')
    sys.exit(1)


try:
    options, remainder = getopt.getopt(sys.argv[1:], 'e:ip:u:de:px:mk:bi:d:th:um:al:rc:q1:q2:q3:px:py:po:pt:eb:em:es:cd:or:pr:ka:tc:in:ep:vv', ['exe=','serverip=','userid=','defocus=','pixelsizetilt=','markers=','binfactor=','diameter=','thickness=','useremail=','keepali=','recon=','seq1=','seq2=','seq3=','patchx=','patchy=','patchoverlap=','patchtrim=','eman2bin=','eman2markers=','eman2boxsize=','changedatatype=','orientation=','pr=','keepall=','tiltconstant=','inifile=','exepath=','version='])
except getopt.GetoptError as err:
    print ("!!! db3_rerun.py input error. Quit.", err)
    sys.exit(0)

for opt, arg in options:
    if opt in ('-e', '--exe'):
        exe = int(arg)
    elif opt in ('-ip', '--serverip'):
        serverip = int(arg)
        if serverip == 1:
            hostip = db3_inc.hostip_real
            dbpath = db3_inc.dbpath_real
            server_ssh = db3_inc.rsync_server_real
        else:
            hostip = db3_inc.hostip_test
            dbpath = db3_inc.dbpath_test
            server_ssh = db3_inc.rsync_server_test
    if opt in ('-u', '--userid'):
        userid = arg
    if opt in ('-de', '--defocus'):
        defocus = arg
    if opt in ('-px', '--pixelsizetilt'):
        pixelsizetilt = arg
    if opt in ('-mk', '--markers'):
        markers = arg
    if opt in ('-bi', '--binfactor'):
        binfactor = arg
    if opt in ('-d', '--diameter'):
        diameter = arg
    if opt in ('-th', '--thickness'):
        thickness = arg
    if opt in ('-um', '--useremail'):
        useremail = arg
    if opt in ('-al', '--keepali'):
        keepali = arg
    if opt in ('-rc', '--recon'):
        recon = arg
    if opt in ('-q1', '--seq1'):
        seq1 = arg
    if opt in ('-q2', '--seq2'):
        seq2 = arg
    if opt in ('-q3', '--seq3'):
        seq3 = arg
    if opt in ('-px', '--patchx'):
        patchx = arg
    if opt in ('-py', '--patchy'):
        patchy = arg
    if opt in ('-po', '--patchoverlap'):
        patchoverlap = arg
    if opt in ('-pt', '--patchtrim'):
        patchtrim  = arg
    if opt in ('-eb', '--eman2bin'):
        eman2bin = arg
    if opt in ('-em', '--eman2markers'):
        eman2markers = arg
    if opt in ('-es', '--eman2boxsize'):
        eman2boxsize = arg
    if opt in ('-cd', '--changedatatype'):
        changedatatype = arg
    if opt in ('-or', '--orientation'):
        orientation = arg
    if opt in ('-pr', '--pr'):
        pr = int(arg)
    if opt in ('-ka', '--keepall'):
        keepall = arg
    if opt in ('-tc', '--tiltconstant'):
        tiltconstant = arg
    if opt in ('-in', '--inifile'):
        inifile = arg
    if opt in ('-ep', '--exepath'):
        exepath = arg
    if opt in ('-vv', '--version'):
        version = arg

#check version to ensure users are using correct .pbs
if version != thisversion:
    print ("Error: Starting config file version ("+version+") not matching program's ("+thisversion+"). Quit.")
    subject = '[Tomography Pipeline] Error: wrong version'
    msg = "You are using an old version of the starting config script. Please generate a new one and restart your pipeline. "
    db3_inc.email_to(useremail, subject, msg, machinename)
    sys.exit(1)

if exe == 0:
    print ("Running in TEST ONLY mode")

exepath = exepath.strip()
if exepath[-1] != '/':
    exepath = exepath +'/'

outputdir = os.path.expanduser('~') + '/Pipeline_Proc/'
cmd = 'mkdir -p ' + outputdir
#if db3_inc.myexecmd(cmd, exe, pr) != 0:
if db3_inc.myexecmd(cmd, 1, pr) != 0:
    msg = '[Main] Pipeline Error: cannot create output directory '+outputdir
    db3_exit(-1, '', '', msg)

now = datetime.datetime.now()
# keep 'rerun.' in logstring, used in _procone
logstring = 'rerun.'+str(now.year)+str(now.month)+str(now.day)+str(now.hour)+str(now.minute)+str(now.second)
logfile = outputdir + "db3_proc."+logstring+".log"

logs = "[Main] " +sys.argv[0]+" "+sys.argv[1]+" "+inifile+"\nLogs:" ####### better description
if db3_inc.logwrite(logfile,logs) != 0:
    msg = '[Main] Pipeline Error: cannot write to log file '+logfile+': '+logs
    db3_exit(-1, '', '', msg)

logs = time.strftime("%H:%M:%S",time.localtime()) + "[Main] Connecting Database at "+ hostip + "." 
if db3_inc.logwrite(logfile,logs) != 0:
    msg = '[Main] Pipeline Error: cannot write to log file '+logfile+': '+logs
    db3_exit(-1, '', '', msg)

#record unixtime for session referece, also serve as test for sql connection
sql = "select unix_timestamp(now())"
status, cursor = db3_inc.myexesql(hostip, sql, 1, 0)
if status != 0:
    db3_exit(-1, outputdir, logstring, '[Main] MySQL Error: '+sql)
if len(cursor) == 0:
    msg = '[Main] MySQL Error: can not find timestamp'
    db3_exit(-1, outputdir, logstring, msg)
row_tm = cursor[0][0]
loadpath = 'rerun_'+str(row_tm)

#get user info from database
sql = "SELECT var, username FROM UserData WHERE DEF_id="+ userid
status, cursor = db3_inc.myexesql(hostip, sql, 1, pr)
if status != 0:
    db3_exit(-1, outputdir, logstring, '[Main] MySQL Error: '+sql)
row_user = cursor[0]
if row_user == None:
    msg = '[Main] MySQL Error: can not find user in the database. Contact your admin'
    db3_exit(-1, outputdir, logstring, msg)
rsync_username = row_user[1]

skip = 0
pini = open(inifile, 'r')
for line in pini:
    line = line.strip()
    if line == '##END tiltseries##':
        print ('All '+str(count)+' tilt series sent to process. Exit.')
        # "main loop has finished" will be used in _procone for job count
        msg = '********** rerun main loop has finished. '+str(count)+' tilt series sent to process. '+str(skip)+' skipped.'
        db3_inc.logwrite(logfile,time.strftime("%H:%M:%S",time.localtime())+" [Main] "+msg)
        time.sleep(1)
        pini.close()
        if skip: #
            msg = 'Some tilt series rerun are skipped. Please check "Skip" in logfile: '+ logfile
            db3_exit(0, outputdir, logstring, msg)
        else:
            sys.exit(0) #quit without sending any email 
    
    tiltseriesid = line
    # get raw tilt
    sql = "SELECT filename FROM ThreeDFile WHERE status != 2 AND `REF|TiltSeriesData|tiltseries`='" + tiltseriesid +"' AND classify='rawdata'"
    status, cursor = db3_inc.myexesql(hostip, sql, exe, pr)
    if status != 0:
        db3_exit(-1, outputdir, logstring, '[Main] MySQL Error: '+sql)
    elif len(cursor) == 0:
        logs = time.strftime("%H:%M:%S",time.localtime()) + " ["+tiltseriesid+"] no raw data found in the database skip. Skip." 
        db3_inc.logwrite(logfile,logs)
        skip = skip + 1
    else:
        mrcname = cursor[0][0]
        if server_ssh == 0:
            mrcdir = dbpath+tiltseriesid+"/"+"rawdata"+"/"
        else:
            mrcdir = outputdir+tiltseriesid+'/'
            mrcpath = dbpath+tiltseriesid+"/"+"rawdata"+"/"+mrcname
            cmd = "mkdir -p " + mrcdir
            if db3_inc.myexecmd(cmd, exe, pr) != 0:
                msg = '[Main] Pipeline Error: Failed to create directory '+cmd
                db3_exit(-1, outputdir, logstring, '[Main] mkdir Error: '+cmd)
            cmd = 'chmod 755 '+mrcdir
            db3_inc.myexecmd(cmd, exe, 0) 
            cmd = 'rsync -ave "ssh -o \'StrictHostKeyChecking no\'" '  + rsync_username + '@' + server_ssh + ':' + mrcpath  + ' ' + mrcdir
            db3_inc.logwrite(logfile,cmd)
            if os.system(cmd) != 0:
                msg = '[Main] Pipeline Error: Failed to rsync file '+cmd
                db3_exit(-1, outputdir, logstring, '[Main] mkdir Error: '+cmd)            
            
        if not os.path.exists(mrcdir+mrcname):
            logs = time.strftime("%H:%M:%S",time.localtime()) + " ["+tiltseriesid+"] raw data file is not found at " + mrcdir+mrcname + " Skip. " 
            db3_inc.logwrite(logfile,logs)
            skip = skip + 1
        else: # raw mrc in place, now processing
            count = count + 1
            procone_cmd = exepath+"db3_procone.py --exe "+str(exe)+" --serverip "+str(serverip)+" --tiltseriesid "+tiltseriesid+" --pixelsizetilt "+pixelsizetilt+" --iname "+mrcname+" --thickness "+thickness+" --binfactor "+binfactor+" --seq1 "+seq1+" --seq2 "+seq2+" --seq3 "+seq3+" --diameter "+diameter+" --markers "+markers+" --defocus "+defocus+" --patchx "+patchx+" --patchy "+patchy+" --patchoverlap "+patchoverlap+" --patchtrim "+patchtrim+" --eman2bin "+eman2bin+" --eman2markers "+eman2markers+" --eman2boxsize "+eman2boxsize+" --keepali "+keepali+" --keepall "+keepall+" --orientation "+orientation +" --exepath "+exepath+" --outputdir "+outputdir+" --logstring "+logstring+" --inputdir "+mrcdir+" --username "+rsync_username+" --useremail "+useremail+" --recon 1"

            print("CALLING procone... "+tiltseriesid)
            db3_inc.logwrite(logfile,time.strftime("%H:%M:%S",time.localtime())+" [Main] "+procone_cmd)

            #generate sbatch file
            jobfile = outputdir + tiltseriesid + ".sbatch"
            pp = open(jobfile, 'w')
            line = "#!/bin/bash"
            pp.write(line+"\n")
            if db3_inc.sbatch_partition != "":
                line = "#SBATCH --partition="+db3_inc.sbatch_partition
                pp.write(line+"\n")
            line = "#SBATCH --job-name=" + tiltseriesid
            pp.write(line+"\n")
            line = "#SBATCH --time=04:00:00"
            pp.write(line+"\n")
            line = "#SBATCH --output="+outputdir+tiltseriesid+".%j.out"
            pp.write(line+"\n")
            line = "#SBATCH --error="+outputdir+tiltseriesid+".%j.err"
            pp.write(line+"\n")
            if db3_inc.source_script_bash != "":
                pp.write('source '+ db3_inc.source_script_bash +'\n')
            line = procone_cmd
            pp.write(line+"\n")
            pp.close()

            time.sleep(1)
            cmd = 'sbatch ' + jobfile  
            if exe == 1:
                os.system(cmd)
            print ("Done " + cmd)
            # "Job submitted" in main log will be used in _procone for job count
            db3_inc.logwrite(logfile,time.strftime("%H:%M:%S",time.localtime())+" [Main] Job submitted: "+cmd)

            time.sleep(2) 

                        










