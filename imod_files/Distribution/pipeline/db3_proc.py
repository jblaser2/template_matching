#!/usr/bin/python
# db3_proc.py - auto processing, input a directory, wait for mrc, submit to database, move to "Done", then SLURM launch raptor and submision rec to database
# based on db_proc created 09/15/11 and pipeline_start created 11/06/18
# created 06/30/2020
# modified 08/06/2020
# 10/02/2020: add pre-processing for fise and movie-mode; remove pbs, flv; move raw mrc rsync to _procone
# 03/18/2021: add eman2 v2021-04-10
# 07/29/2021: moved gain reference check to .ini. now same types for movie mode and fise


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
        finalmsg = '\n\nYour pipeline session '+logstring+' has finished. There is no raw data detected under you given data directory.'
    else:
        finalmsg = '\n\nAll jobs in your pipeline session '+logstring+' have finished. Your may check your database Inbox for the results. \n\nDo not forget to check your data input directory, delete your raw data which has now been moved under "Done" folder. Please note that raw data which are not under "Done" are not uploaded/processed.\n\nIf this is a FISE or Movie-mode collection, aligned mrc files are uploaded to the database, but your raw tif files are not uploaded.\n\nIf the Pipeline is successful, you can delete everything under "Pipeline_Proc".'
        if keepali == "1":
            finalmsg = finalmsg + '\n\nSince you chose to keep the alignment files, all eman2 files or .ali and .tlt files will be kept under the folder "Pipeline_Proc". When all jobs are finished, please copy the files you want and then delete those temporary tilt folders. This folder is not for long term storage. Please remove the files after you copy them to your local computer.'
    if status == -1: # notify admin 
        subject = '[Tomography Pipeline3] Fatal Error from pipeline'
        msg = msg + ' . Something went wrong. Administrator has been notified. Do not delete anything until administrator finishes checking.'
        db3_inc.email_to(useremail, subject, msg, machinename)
        db3_inc.email_to(db3_inc.admin_email, subject, msg, machinename)
        sys.exit(1)
    elif status >= 0:
        if count == 0:
            subject = '[Tomography Pipeline3] Your pipeline has finished - no data uploaded'
        else:
            subject = '[Tomography Pipeline3] Your pipeline has finished'
        msg = msg + finalmsg
        db3_inc.email_to(useremail, subject, msg, machinename)
    sys.exit(0)

#function to check if mrc file is completed and valid tilt, returns mrc-status
#for movie mode, returns mrc-status, gain-reference, moviedir
#for no-wait, only fails if detected not a tilt, still returns 0 if header is non-standard
#for fise & movie-mode, check if required files are present, existence of gain reference already checked in _start.py
def checkfile(filename, wait_for_new_tilt, recon, moviemode):
    if not os.path.exists(filename):
        return -1, '', '' 

    if moviemode == 'fise':
        if not os.path.exists(filename+'.angles') or not os.path.exists(filename+'.mdoc'):
            return 1, '', ''
        savename = filename.split('.tif')[0] + '_saved.txt'
        if not os.path.exists(savename):
            return 1, '', ''
        return 0, '', ''
    elif moviemode == 'movies':
        idir, ifile = os.path.split(filename)
        dm4file = ''
        moviedir = ''
        basename = ifile.replace('.mrc.mdoc', '')

        dm4file = db3_inc.checkgainref(idir)
        if dm4file != '':
            dm4file = idir + '/' + dm4file
        else:
            if os.path.exists(idir+'/Movies'):
                dm4file = db3_inc.checkgainref(idir+'/Movies')
            if dm4file != '':
                dm4file = idir + '/Movies/' + dm4file
            else:
                if os.path.exists(idir+'/movies'):
                    dm4file = db3_inc.checkgainref(idir+'/movies')
                if dm4file != '':
                    dm4file = idir + '/movies/' + dm4file
                        
        for fname in os.listdir(idir):
            if fname.startswith(basename+'_') and fname.endswith('.tif'):
                moviedir = idir + '/'
        if moviedir == '':
            if os.path.exists(idir+'/Movies'):
                for fname in os.listdir(idir+'/Movies'):
                    if fname.startswith(basename+'_') and fname.endswith('.tif'):
                        moviedir = idir + '/Movies/' 
            elif os.path.exists(idir+'/movies'):
                for fname in os.listdir(idir+'/movies'):
                    if fname.startswith(basename+'_') and fname.endswith('.tif'):
                        moviedir = idir + '/movies/' 
                        
        if dm4file == '' or moviedir == '':
            return 1, dm4file, moviedir
        return 0, dm4file, moviedir


    if wait_for_new_tilt==0 and recon=="0": # will not check mrc header if no reconstruction
        return 0, '', ''
    try:
        if wait_for_new_tilt != 0:
            with open(filename, 'a') as f:
                pass
        result = os.popen('extracttilts -TiltAngles '+ filename)
        # result = os.popen('extracttilts -all '+ filename) # this will work with wrong header case, but we may not want to process those wrong ones
        # make sure extracttilts contains at least 10 angles, all digits, and last few are not the same
        lines = result.read().split()
        if 'ERROR:' in lines:
            return 1, '', ''
        num = len(lines)
        if num < 10:
            return 1, '', ''
        else:
            for i in range(num-10, num):
                try:
                    float(lines[i])
                    if lines[num-1] == lines[num-2] and lines[num-2] == lines[num-3]:
                        return 1, '', ''
                except:
                    if wait_for_new_tilt == 0:
                        return 0, '', ''
                    else:
                        return 1, '', ''
        return 0, '', ''
    except Exception as e:
        if wait_for_new_tilt == 0:
            return 0, '', ''
        else:
            return 1, '', ''


machinename = os.uname()[1]
if len(sys.argv) <= 3:
    print ('!! RUN as USER on Pipeline Machine!')
    print ('you are using '+machinename)
    print ('Automatic processing and uploading tilt series under one directory into database')
    print ('Called by cluster script')
    print ('quit')
    sys.exit(1)


try:
    options, remainder = getopt.getopt(sys.argv[1:], 'e:ip:u:in:td:mi:ma:ts:do:de:sa:mg:px:mk:bi:d:th:wa:um:al:rc:q1:q2:q3:px:py:po:pt:eb:em:es:cd:or:si:sc:pr:ka:tc:mm:sk:id:ti:nt:co:tr:sp:ep:vv', ['exe=','serverip=','userid=','inputdir=','tomodate=','tiltmin=','tiltmax=','tiltstep=','dosage=','defocus=','softwareacquisition=','magnification=','pixelsizetilt=','markers=','binfactor=','diameter=','thickness=','wait=','useremail=','keepali=','recon=','seq1=','seq2=','seq3=','patchx=','patchy=','patchoverlap=','patchtrim=','eman2bin=','eman2markers=','eman2boxsize=','changedatatype=','orientation=','singledual=','scope=','pr=','keepall=','tiltconstant=','moviemode=','skipframe=','specieid=','titlemain=','notes=','collaborators=','treatment=','sampleprep=','exepath=','version='])
except getopt.GetoptError as err:
    print ("!!! db3_proc.py input error. Quit.", err)
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
    if opt in ('-in', '--inputdir'):
        INPUTDIR  = arg
    if opt in ('-td', '--tomodate'):
        tomodate = arg
    if opt in ('-mi', '--tiltmin'):
        tiltmin = arg
    if opt in ('-ma', '--tiltmax'):
        tiltmax = arg
    if opt in ('-ts', '--tiltstep'):
        tiltstep = arg
    if opt in ('-do', '--dosage'):
        dosage = arg
    if opt in ('-de', '--defocus'):
        defocus = arg
    if opt in ('-sa', '--softwareacquisition'):
        softwareacquisition = arg
    if opt in ('-mg', '--magnification'):
        magnification = arg
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
    if opt in ('-wa', '--wait'):
        wait_for_new_tilt = int(arg)
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
    if opt in ('-si', '--singledual'):
        singledual = arg
    if opt in ('-sc', '--scope'):
        scope = arg
    if opt in ('-pr', '--pr'):
        pr = int(arg)
    if opt in ('-ka', '--keepall'):
        keepall = arg
    if opt in ('-tc', '--tiltconstant'):
        tiltconstant = arg
    if opt in ('-mm', '--moviemode'):
        moviemode = arg
    if opt in ('-sk', '--skipframe'):
        skipframe = arg
    if opt in ('-id', '--specieid'):
        specie_id = arg
    if opt in ('-ti', '--titlemain'):
        titlemain = arg
    if opt in ('-nt', '--notes'):
        notes = arg
    if opt in ('-co', '--collaborators'):
        collaborators = arg
    if opt in ('-tr', '--treatment'):
        treatment  = arg
    if opt in ('-sp', '--sampleprep'):
        sampleprep = arg
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

#special characters handling: when reading variables from file, \n changed to \\n in php. need to change back
#can use <br> here or in .script, but for now let's not use newline except for notes
titlemain = titlemain.replace("\\n", ". ")
notes = notes.replace("\\n", "\n")
collaborators = collaborators.replace("\\n", ". ")
treatment = treatment.replace("\\n", ". ")
sampleprep = sampleprep.replace("\\n", ". ")


if wait_for_new_tilt == 0:
    timeout_sec = 5
    wait_sec_nomrc = 1
else:
    timeout_sec = 14400 #4 hours # Pipeline terminates if no new mrc files appears after this time period
    wait_sec_nomrc = 300

print (exe, serverip, wait_for_new_tilt, timeout_sec, wait_sec_nomrc)

if exe == 0:
    print ("Running in TEST ONLY mode")

INPUTDIR = INPUTDIR.strip()
if INPUTDIR[-1] != '/':
    INPUTDIR = INPUTDIR +'/'
exepath = exepath.strip()
if exepath[-1] != '/':
    exepath = exepath +'/'
tomodate = tomodate.strip()

outputdir = os.path.expanduser('~') + '/Pipeline_Proc/'
cmd = 'mkdir -p ' + outputdir
#if db3_inc.myexecmd(cmd, exe, pr) != 0:
if db3_inc.myexecmd(cmd, 1, pr) != 0:
    msg = '[Main] Pipeline Error: cannot create output directory '+outputdir
    db3_exit(-1, '', '', msg)

cmd = "mkdir -p "+INPUTDIR+"Done" 
if db3_inc.myexecmd(cmd, exe, pr) != 0:
    msg = '[Main] Pipeline Error: Failed to create directory '+cmd
    db3_exit(-1, '', '', msg)
if moviemode == 'fise':
    cmd = "mkdir -p "+INPUTDIR+"PreProcessing" 
    if db3_inc.myexecmd(cmd, exe, pr) != 0:
        msg = '[Main] Pipeline Error: Failed to create directory '+cmd
        db3_exit(-1, '', '', msg)

now = datetime.datetime.now()
logstring = tomodate+'.'+str(now.year)+str(now.month)+str(now.day)+str(now.hour)+str(now.minute)+str(now.second)
logfile = outputdir + "db3_proc."+logstring+".log"

logs = "[Main] " +sys.argv[0]+" "+sys.argv[1]+" "+INPUTDIR+" "+tomodate+" "+moviemode+"\nLogs:" ####### better description
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
if moviemode == 'fise':
    loadpath = 'autofise_'+str(row_tm)
if moviemode == 'movies':
    loadpath = 'automovies_'+str(row_tm)
else:
    loadpath = 'autoprocref_'+str(row_tm)

#get user info from database
sql = "SELECT var, username FROM UserData WHERE DEF_id="+ userid
status, cursor = db3_inc.myexesql(hostip, sql, 1, pr)
if status != 0:
    db3_exit(-1, outputdir, logstring, '[Main] MySQL Error: '+sql)
row_user = cursor[0]
if row_user == None:
    msg = '[Main] MySQL Error: can not find user in the database. Contact your admin'
    db3_exit(-1, outputdir, logstring, msg)
uvar = row_user[0]
rsync_username = row_user[1]

list_3dpat = ['*.mrc', '*.st']
if moviemode == 'fise':
    list_3dpat = ['*.tif']
elif moviemode == 'movies':
    list_3dpat = ['*.mrc.mdoc']

if moviemode == 'fise': 
    #copy gain reference to PreProcessing
    cmd = "cp -p "+ INPUTDIR + "*dm4 " + INPUTDIR + "Count* " +INPUTDIR+"PreProcessing" 
    db3_inc.myexecmd2(cmd, exe, pr)
    db3_inc.logwrite(logfile,time.strftime("%H:%M:%S",time.localtime())+" [Main] "+cmd)


time0 = time.mktime(time.localtime())
time2 = time.mktime(time.localtime())
print (time0)

count = 0
while True:
    time1 = time.mktime(time.localtime())
    if time1 - time0 > timeout_sec:
        print ('Time out waiting for new input. Exit.')
        msg = '********** Pipeline main loop has finished' # "main loop has finished" will be used in _procone for job count
        db3_inc.logwrite(logfile,time.strftime("%H:%M:%S",time.localtime())+" [Main] "+msg)
        time.sleep(1)
        if wait_for_new_tilt != 0: 
            msg = 'No new tilt series for 4 hours.'
            db3_exit(0, outputdir, logstring, msg)
        else:
            msg = ''
            sys.exit(0) #not send any email if not real-time
    if time1 - time0 > 7200 and time1 - time2 > 7200 and useremail!='': #send out warning email
        time2 = time.mktime(time.localtime())
        subject = '[Tomography Pipeline] Warning: no new tilt series for past 120 minutes'
        msg = ''
        db3_inc.email_to(useremail, subject, msg, machinename)

    mrc_flag = 0
    dirs = os.listdir(INPUTDIR)
    for iname in dirs:
        if iname[0] != '.':
            for pattern in list_3dpat:
                if fnmatch.fnmatch(iname,pattern):
                    ipath = INPUTDIR + iname  
                    ss, dm4file, moviedir = checkfile(ipath, wait_for_new_tilt, recon, moviemode)
                    if ss == 0:
                        time.sleep(5)
                        db3_inc.logwrite(logfile,time.strftime("%H:%M:%S",time.localtime())+" [Main] ********** New mrc detected: "+iname)
                        count = count + 1
                        mrc_flag = 1
                        # process this mrc file
                        # determine the last digit of tiltseriesID
                        tiltnum = 0
                        tiltseriesid = uvar+tomodate+"-1"
                        sql = "SELECT tiltseriesID FROM TiltSeriesData WHERE `REF|UserData|user`='"+userid+"' AND tomo_date='"+tomodate+"'"
                        status, cursor = db3_inc.myexesql(hostip, sql, 1, pr)
                        if status != 0:
                            db3_exit(-1, outputdir, logstring, '[Main] MySQL Error: '+sql)
                        for row in cursor:
                            temp = row[0].split('-')
                            tiltnum_temp = int(temp[3])
                            if tiltnum < tiltnum_temp:
                                tiltnum = tiltnum_temp
                                tiltseriesid = temp[0]+"-"+temp[1]+"-"+temp[2]+"-"+str(tiltnum+1)
                        #print ("tiltseriesid =", tiltseriesid)
                        #upload information to mysql
                        sql = "SELECT now()"
                        status, cursor = db3_inc.myexesql(hostip, sql, 1, 0)
                        if status != 0:
                            db3_exit(-1, outputdir, logstring, '[Main] MySQL Error: '+sql)
                        if len(cursor) == 0:
                            msg = '[Main] MySQL Error: can not find now()'
                            db3_exit(-1, outputdir, logstring, msg)
                        row_tm = cursor[0][0]
                        time_modified = str(row_tm)                

                        # create new tilt series record in database
                        ## old
                        ## sql = "INSERT INTO tomography.TiltSeriesData (time_modified, tiltseriesID, `REF|SpeciesData|specie`, status, `REF|UserData|user`, tomo_date, single_dual, tilt_min, tilt_max, tilt_step, tilt_constant, dosage, defocus, magnification, software_acquisition, software_process, loadmethod, loadpath, pipeline ) VALUES ( \""+time_modified+"\", \""+tiltseriesid+"\", \""+speciesid +"\", 1, \""+userid+"\", \"" +tomodate+"\", "+singledual+", "+tiltmin+", "+tiltmax+", \""+tiltstep+"\", 1, "+dosage+", "+ defocus+", "+ magnification+", \"" +softwareacquisition+"\", \"Raptor\", \"pipeline\", \""+loadpath+"\", -10 )"

                        sql_insert = "INSERT INTO tomography.TiltSeriesData (time_modified, tiltseriesID, `REF|SpeciesData|specie`, status, `REF|UserData|user`, tomo_date, single_dual, tilt_min, tilt_max, tilt_step, tilt_constant, dosage, defocus, magnification, software_acquisition, loadmethod, loadpath, pipeline, scope, title, TXT_notes, roles, treatment, sample) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                        sql_values = (time_modified, tiltseriesid, specie_id, 1, userid, tomodate, singledual, tiltmin, tiltmax, tiltstep, 1, dosage, defocus, magnification, softwareacquisition, "pipeline", loadpath, -10, scope, titlemain, notes, collaborators, treatment, sampleprep)
                        status, cursor = db3_inc.myexesql_tuple(hostip, sql_insert, sql_values, exe, pr)
                        if status != 0:
                            db3_exit(-1, outputdir, logstring, '[Main] MySQL Error: tuple '+sql_insert+' '+str(sql_values))
                        db3_inc.logwrite(logfile,time.strftime("%H:%M:%S",time.localtime())+" [Main] TiltSeriesId: "+tiltseriesid)

                        if moviemode != '0': 
                            mrcdir = outputdir+tiltseriesid+'/'
                            mrcname = ''
                            cmd = "mkdir -p " + mrcdir
                            if db3_inc.myexecmd(cmd, exe, pr) != 0:
                                msg = '[Main] Pipeline Error: Failed to create directory '+cmd
                                db3_exit(-1, outputdir, logstring, '[Main] mkdir Error: '+cmd)
                            cmd = 'chmod 755 '+mrcdir
                            db3_inc.myexecmd(cmd, exe, 0) 
                        else:
                            mrcdir = ''
                            mrcname = iname

                        jobfile = outputdir + tiltseriesid + ".sbatch"
                        prejobfile = ''

                        if moviemode == '0': 
                            # change data type if requested
                            if changedatatype == "1":  
                                db3_inc.logwrite(logfile,"[Main] Changing datatype." )
                                cmd = "newstack -mode 6 " + ipath + " " + ipath
                                if db3_inc.myexecmd2(cmd, exe, pr) != 0:                                
                                    db3_inc.logwrite(logfile, '[Main] Failed '+cmd )
                                db3_inc.logwrite(logfile,time.strftime("%H:%M:%S",time.localtime())+" [Main] "+cmd)
                                cmd = "rm -f " + ipath + "~"
                                db3_inc.myexecmd(cmd, exe, pr)

                            # upload mrc & mrc.mdoc to database
                            # rsync raw data from ipath and add to mysql
                            cmd = 'chmod 644 '+ipath
                            db3_inc.myexecmd(cmd, exe, 0) 
                            path_to = dbpath+tiltseriesid+"/"+"rawdata"
                            if db3_inc.myexersync(ipath, path_to, rsync_username, server_ssh, 1, exe, pr) != 0:
                                sql = "UPDATE tomography.TiltSeriesData SET pipeline=\"-4\" WHERE tiltseriesID=\""+tiltseriesid+"\""
                                db3_inc.myexesql(hostip, sql, exe, pr)
                                db3_exit(-1, outputdir, logstring, '[Main] Pipeline Error: myexersync '+ipath+' '+path_to)
                            sql = "INSERT INTO tomography.ThreeDFile (`REF|TiltSeriesData|tiltseries`, status, pixel_size, classify, filename)  VALUES ( \""+tiltseriesid+"\", 1, "+pixelsizetilt+", \"rawdata\", \""+iname+"\")"
                            status, cursor = db3_inc.myexesql(hostip, sql, exe, pr)
                            if status != 0:
                                db3_exit(-1, outputdir, logstring, '[Main] MySQL Error: '+sql)
                            db3_inc.logwrite(logfile,time.strftime("%H:%M:%S",time.localtime())+" [Main] uploaded "+ipath)

                            mdocpath = ipath + '.mdoc'
                            if os.path.exists(mdocpath):
                                mdocname = iname + '.mdoc'
                                cmd = 'chmod 644 '+ mdocpath
                                db3_inc.myexecmd(cmd, exe, 0) 
                                if db3_inc.myexersync(mdocpath, path_to, rsync_username, server_ssh, 0, exe, pr) != 0:
                                    sql = "UPDATE tomography.TiltSeriesData SET pipeline=\"-4\" WHERE tiltseriesID=\""+tiltseriesid+"\""
                                    db3_inc.myexesql(hostip, sql, exe, pr)
                                    db3_exit(-1, outputdir, logstring, '[Main] Pipeline Error: myexersync '+mdocpath+' '+path_to)
                                sql = "INSERT INTO tomography.DataFile (`REF|TiltSeriesData|tiltseries`, status, filetype, filename)  VALUES ( \""+tiltseriesid+"\", 1, \"mdoc\", \""+mdocname+"\")"
                                status, cursor = db3_inc.myexesql(hostip, sql, exe, pr)
                                if status != 0:
                                    db3_exit(-1, outputdir, logstring, '[Main] MySQL Error: '+sql)
                                db3_inc.logwrite(logfile,time.strftime("%H:%M:%S",time.localtime())+" [Main] uploaded "+mdocpath)

                            # move mrc* to Done
                            time.sleep(3)
                            mrcdir = INPUTDIR+"Done/"
                            cmd = "mv "+INPUTDIR+iname+"* "+mrcdir
                            if db3_inc.myexecmd2(cmd, exe, pr) != 0:
                                sql = "UPDATE tomography.TiltSeriesData SET pipeline=\"-3\" WHERE tiltseriesID=\""+tiltseriesid+"\""
                                db3_inc.myexesql(hostip, sql, exe, pr)                
                                db3_exit(-1, outputdir, logstring, '[Main] Pipeline Error: '+cmd)
                            db3_inc.logwrite(logfile,time.strftime("%H:%M:%S",time.localtime())+" [Main] "+cmd)
                        elif moviemode == 'movies':
                            # upload .mrc.mdoc then move to Done
                            path_to = dbpath+tiltseriesid+'/rawdata'
                            mdocpath = ipath
                            mdocname = iname
                            basename = iname.replace('.mrc.mdoc', '')
                            cmd = 'chmod 644 '+ mdocpath
                            db3_inc.myexecmd(cmd, exe, 0) 
                            if db3_inc.myexersync(mdocpath, path_to, rsync_username, server_ssh, 1, exe, pr) != 0:
                                sql = "UPDATE tomography.TiltSeriesData SET pipeline=\"-6\" WHERE tiltseriesID=\""+tiltseriesid+"\""
                                db3_inc.myexesql(hostip, sql, exe, pr)
                                db3_exit(-1, outputdir, logstring, '[Main] Pipeline Error: myexersync '+mdocpath+' '+path_to)
                            sql = "INSERT INTO tomography.DataFile (`REF|TiltSeriesData|tiltseries`, status, filetype, filename)  VALUES ( \""+tiltseriesid+"\", 1, \"mdoc\", \""+mdocname+"\")"
                            status, cursor = db3_inc.myexesql(hostip, sql, exe, pr)
                            if status != 0:
                                db3_exit(-1, outputdir, logstring, '[Main] MySQL Error: '+sql)
                            db3_inc.logwrite(logfile,time.strftime("%H:%M:%S",time.localtime())+" [Main] uploaded "+mdocpath)

                            cmd = "mv "+ ipath +"* "+INPUTDIR+"Done" 
                            if db3_inc.myexecmd2(cmd, exe, pr) != 0:
                                sql = "UPDATE tomography.TiltSeriesData SET pipeline=\"-6\" WHERE tiltseriesID=\""+tiltseriesid+"\""
                                db3_inc.myexesql(hostip, sql, exe, pr)                
                                db3_exit(-1, outputdir, logstring, '[Main] Pipeline Error: '+cmd)
                            db3_inc.logwrite(logfile,time.strftime("%H:%M:%S",time.localtime())+" [Main] "+cmd)

                            # insert .mrc to mysql (rsync in prejobfile) 
                            mrcname = basename + '.mrc'
                            sql = "INSERT INTO tomography.ThreeDFile (`REF|TiltSeriesData|tiltseries`, status, pixel_size, classify, filename)  VALUES ( \""+tiltseriesid+"\", 1, "+pixelsizetilt+", \"rawdata\", \""+mrcname+"\")"
                            status, cursor = db3_inc.myexesql(hostip, sql, exe, pr)
                            if status != 0:
                                db3_exit(-1, outputdir, logstring, '[Main] MySQL Error: '+sql)
                            db3_inc.logwrite(logfile,time.strftime("%H:%M:%S",time.localtime())+" [Main] inserted "+mrcname)

                            # generate pre-processing job file
                            # already created mrcdir = outputdir+tiltseriesid+'/'
                            # dm4file, moviedir already defined by checkfile
                            jobname = 'mov-' + tiltseriesid
                            prejobfile = outputdir + '/' + jobname + '.job'
                            qq = open(prejobfile, 'w')
                            qq.write('#!/bin/bash' +'\n')
                            if db3_inc.sbatch_partition != "":
                                qq.write('#SBATCH --partition='+db3_inc.sbatch_partition+'\n')
                            qq.write('#SBATCH --job-name='+jobname+'\n')
                            qq.write('#SBATCH --time=72:00:00' +'\n')
                            qq.write('#SBATCH --output='+outputdir+'/'+jobname+'.%j.out' +'\n')
                            qq.write('#SBATCH --error='+outputdir+'/'+jobname+'.%j.err' +'\n')
                            qq.write('' +'\n')
                            if db3_inc.source_script_bash != "":
                                qq.write('source '+ db3_inc.source_script_bash +'\n')
                            if skipframe == "1":
                                cmd='alignframes -gpu 0 -gain ' + dm4file + ' -rotation -1 -truncate 5 -StartingEndingFrames 2,150 -AntialiasFilter 4 -PairwiseFrames -1 -AlignAndSumBinning -1,2 -refine 5 -vary 0.02,0.03,0.04,0.05,0.06 -meansd 500,100 -mdoc ' + INPUTDIR+'Done/' + mdocname + ' -output ' + mrcdir+mrcname + ' -PathToFramesInMdoc ' + moviedir
                            else:
                                cmd='alignframes -gpu 0 -gain ' + dm4file + ' -rotation -1 -truncate 5 -AntialiasFilter 4 -PairwiseFrames -1 -AlignAndSumBinning -1,2 -refine 5 -vary 0.02,0.03,0.04,0.05,0.06 -meansd 500,100 -mdoc ' + INPUTDIR+'Done/' + mdocname + ' -output ' + mrcdir+mrcname + ' -PathToFramesInMdoc ' + moviedir
                            qq.write(cmd +'\n')
                            # rsync .mrc to database
                            cmd = 'chmod 644 '+mrcdir+mrcname
                            qq.write(cmd +'\n')
                            cmd = 'rsync -ave "ssh -o \'StrictHostKeyChecking no\'" ' +  mrcdir+mrcname + ' ' + rsync_username + '@' + server_ssh + ':' + path_to
                            qq.write(cmd +'\n')
                            # mv .tifs to Done
                            cmd = 'mv ' + moviedir + basename + '_*.tif ' + INPUTDIR+'Done/'
                            qq.write(cmd +'\n')
                            # for eman2
                            cmd = 'cp ' + INPUTDIR+'Done/' + mdocname + ' ' + mrcdir
                            qq.write(cmd +'\n')
                            qq.write('echo "Starting ' + jobfile + '"\n')
                            qq.write('sbatch ' + jobfile +'\n')
                            qq.write('' +'\n')
                            qq.close()                            
                        elif moviemode == 'fise':
                            path_to = dbpath+tiltseriesid+'/rawdata'
                            
                            # insert .mrc to mysql (rsync in prejobfile) 
                            sql = "UPDATE tomography.TiltSeriesData SET pipeline=\"-6\" WHERE tiltseriesID=\""+tiltseriesid+"\""
                            db3_inc.myexesql(hostip, sql, exe, pr)
                            mrcname = iname.replace('.tif', '.mrc')
                            sql = "INSERT INTO tomography.ThreeDFile (`REF|TiltSeriesData|tiltseries`, status, pixel_size, classify, filename)  VALUES ( \""+tiltseriesid+"\", 1, "+pixelsizetilt+", \"rawdata\", \""+mrcname+"\")"
                            status, cursor = db3_inc.myexesql(hostip, sql, exe, pr)
                            if status != 0:
                                db3_exit(-1, outputdir, logstring, '[Main] MySQL Error: '+sql)
                            db3_inc.logwrite(logfile,time.strftime("%H:%M:%S",time.localtime())+" [Main] inserted "+mrcname)

                            # move .tif, angles, etc to PreProcessing
                            cmd = "mv "+ ipath +"* "+ ipath.replace('.tif', '_saved.txt') +" " +INPUTDIR+"PreProcessing" 
                            if db3_inc.myexecmd2(cmd, exe, pr) != 0:
                                sql = "UPDATE tomography.TiltSeriesData SET pipeline=\"-6\" WHERE tiltseriesID=\""+tiltseriesid+"\""
                                db3_inc.myexesql(hostip, sql, exe, pr)                
                                db3_exit(-1, outputdir, logstring, '[Main] Pipeline Error: '+cmd)
                            db3_inc.logwrite(logfile,time.strftime("%H:%M:%S",time.localtime())+" [Main] "+cmd)
                            
                            # generate pre-processing job file
                            # already created mrcdir = outputdir+tiltseriesid+'/'
                            jobname = 'fise-' + tiltseriesid
                            prejobfile = outputdir + '/' + jobname + '.job'
                            qq = open(prejobfile, 'w')
                            qq.write('#!/bin/bash' +'\n')
                            if db3_inc.sbatch_partition != "":
                                qq.write('#SBATCH --partition='+db3_inc.sbatch_partition+'\n')
                            qq.write('#SBATCH --job-name='+jobname+'\n')
                            qq.write('#SBATCH --time=72:00:00' +'\n')
                            qq.write('#SBATCH --output='+outputdir+'/'+jobname+'.%j.out' +'\n')
                            qq.write('#SBATCH --error='+outputdir+'/'+jobname+'.%j.err' +'\n')
                            qq.write('' +'\n')
                            if db3_inc.source_script_fise != "":
                                qq.write('source '+ db3_inc.source_script_fise +'\n')
                            qq.write('runfise.sh  2  ' + INPUTDIR+'PreProcessing ' +  mrcdir + ' ' + iname +'\n')
                            # rsync .mrc to database
                            cmd = 'chmod 644 '+mrcdir+mrcname
                            qq.write(cmd +'\n')
                            cmd = 'rsync -ave "ssh -o \'StrictHostKeyChecking no\'" --rsync-path="mkdir -p ' + path_to + ' && rsync" '  + mrcdir+mrcname + ' ' + rsync_username + '@' + server_ssh + ':' + path_to
                            qq.write(cmd +'\n')
                            # mv raw data from PreProcessing to Done
                            cmd = 'mv ' + INPUTDIR+'PreProcessing/'+iname +"* "+' '+ INPUTDIR+'PreProcessing/'+iname.replace('.tif', '_saved.txt') + ' ' + INPUTDIR+'Done/'
                            qq.write(cmd +'\n')
                            # for eman2
                            cmd = 'cp ' + INPUTDIR+'Done/' + iname + '.mdoc' + ' ' + mrcdir
                            qq.write(cmd +'\n')
                            qq.write('echo "Starting ' + jobfile + '"\n')
                            qq.write('sbatch ' + jobfile +'\n')
                            qq.write('' +'\n')
                            qq.close()



                        if recon == "0": # no reconstruction
                            sql = "UPDATE tomography.TiltSeriesData SET pipeline=\"2\" WHERE tiltseriesID=\""+tiltseriesid+"\""
                            procone_cmd = exepath+"db3_procone.py --exe "+str(exe)+" --serverip "+str(serverip)+" --tiltseriesid "+tiltseriesid+"  --iname "+mrcname+" --outputdir "+outputdir+" --logstring "+logstring+" --inputdir "+mrcdir+" --username "+rsync_username+" --useremail "+useremail+" --recon 0"
                        else: 
                            sql = "UPDATE tomography.TiltSeriesData SET pipeline=\"-1\" WHERE tiltseriesID=\""+tiltseriesid+"\""
                            procone_cmd = exepath+"db3_procone.py --exe "+str(exe)+" --serverip "+str(serverip)+" --tiltseriesid "+tiltseriesid+" --pixelsizetilt "+pixelsizetilt+" --iname "+mrcname+" --thickness "+thickness+" --binfactor "+binfactor+" --seq1 "+seq1+" --seq2 "+seq2+" --seq3 "+seq3+" --diameter "+diameter+" --markers "+markers+" --defocus "+defocus+" --patchx "+patchx+" --patchy "+patchy+" --patchoverlap "+patchoverlap+" --patchtrim "+patchtrim+" --eman2bin "+eman2bin+" --eman2markers "+eman2markers+" --eman2boxsize "+eman2boxsize+" --keepali "+keepali+" --keepall "+keepall+" --orientation "+orientation +" --exepath "+exepath+" --outputdir "+outputdir+" --logstring "+logstring+" --inputdir "+mrcdir+" --username "+rsync_username+" --useremail "+useremail+" --recon 1"
                        status, cursor = db3_inc.myexesql(hostip, sql, exe, pr)                
                        if status != 0:
                            db3_exit(-1, outputdir, logstring, '[Main] MySQL Error: '+sql)
                                
                        print("CALLING procone... "+tiltseriesid)
                        db3_inc.logwrite(logfile,time.strftime("%H:%M:%S",time.localtime())+" [Main] "+procone_cmd)

                        #generate sbatch file
                        #jobfile = outputdir + tiltseriesid + ".sbatch"
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
                        if moviemode == 'fise' or moviemode == 'movies':
                            cmd = 'sbatch ' + prejobfile 
                        else:
                            cmd = 'sbatch ' + jobfile  
                        if exe == 1:
                            os.system(cmd)
                        print ("Done " + cmd)
                        # "Job submitted" in main log will be used in _procone for job count
                        db3_inc.logwrite(logfile,time.strftime("%H:%M:%S",time.localtime())+" [Main] Job submitted: "+cmd)


    if exe == 1:
        if mrc_flag == 1:    
            time0 = time.mktime(time.localtime())
            print (time0)
        else:
            time.sleep(wait_sec_nomrc) 
    else:
        time.sleep(timeout_sec+1) 

                        










