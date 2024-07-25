#!/usr/bin/python
# db3_procone.py - processing a tilt series which is already in the database: lauch raptor, submit rec...
# to be called from db3_proc.py, submitted to Slurm
# based on db_provone.py and pipeline_procone.py
# 07/09/2020
# 09/03/2020 new brt name format
# 10/02/2020: remove flv
# 03/16/2021: add eman2

import string
import os
import sys
import getopt
import MySQLdb
import fnmatch
import math
import time
import datetime
import db3_inc
import re
import shutil

pr = 1 #print out all cmd
#set these as global for now, can change to local
outputdir = ''
mainlogfile = ''

#check if all submitted jobs are fnished
def check_all_job(mainlogfile, useremail, logstring, keepali):
    alllines = ''
    rerun = 0
    with open(mainlogfile, 'r') as f:
        alllines = f.read()
    if 'main loop has finished' in alllines and 'All jobs finished' not in alllines:
        if 'rerun' in mainlogfile:
            rerun = 1
        cnt1 = alllines.count('Job submitted:')
        cnt2 = alllines.count('Process Done')
        if cnt1 == cnt2:
            logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+']  ********** All jobs finished '
            db3_inc.logwrite(mainlogfile,logs)
            machinename = os.uname()[1]
            if rerun:
                subject = '[Rerun Pipeline3] Your pipeline has finished'
                msg = 'All jobs in your rerun session '+logstring+' have finished. \n\nIf it is successful, you can delete everything under "Pipeline_Proc".'
            else:
                subject = '[Tomography Pipeline3] Your pipeline has finished'
                msg = 'All jobs in your pipeline session '+logstring+' have finished. Your may check your database Inbox for the results. \n\nDo not forget to check your data input directory, delete your raw data which has now been moved under "Done" folder. Please note that raw data which are not under "Done" are not uploaded/processed.\n\nIf this is a FISE or Movie-mode collection, aligned mrc files are uploaded to the database, but your raw tif files are not uploaded.\n\nIf the Pipeline is successful, you can delete everything under "Pipeline_Proc".'
            if keepali:
                msg = msg + '\n\nSince you chose to keep the alignment files, all eman2 files or .ali and .tlt files will be kept under the folder "Pipeline_Proc". This folder "Pipeline_Proc" is not for long term storage. Please remove the files after you copy them to your local computer.'
            db3_inc.email_to(useremail, subject, msg, machinename)


def logwritelocal(logfile,line):
    if line.endswith("\n") == False:
        line = line + '\n'
    try:
        with open(logfile, "a") as p:
            p.write(line)
            p.flush()
    except Exception as e:
        print (e)
        print ("Error in logwritelocal: " + logfile) 
        return 1
    return 0

def logAppend(logfile,file_to_append):
    try:
        with open(file_to_append, 'r') as infile:
            infiletext = infile.read()
            logwritelocal(logfile, infiletext)
    except Exception as e:
        print (e)
        print ("Error in logAppend: " + logfile + ','+file_to_append)
        return 1
    return 0


def getBasename(iname):
    first = iname.split('.')
    basename = first[0]
    return basename


def procone_raptor(exe, tiltseriesid, pixelsize_tilt, inputdir, iname, diameter, thickness, binfactor, markers, orientation, pipelinelogfile):
    adjust_binfactor = 0 # this is used to pass actual binfactor adustment when dimx > 3000 and binfactor is odd, for which actually binned by binfactor-1

    # launch raptor, use database file as input and local outputdir as output dir - /tmp would be deleted
    
    outputpath = outputdir+tiltseriesid+"/"
    inputpath = inputdir
    ipath = inputdir +iname
    if not os.path.exists(ipath):
        print ("Error: mrc file does not exist "+ipath)
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Error: mrc file does not exist '+ipath
        db3_inc.logwrite(mainlogfile,logs)
        return -20, "", -1
    else:
        print ("launching RAPTOR "+ipath)

        # bin tilt if it's 4K
        binfactor1 = binfactor
        result = os.popen('header -size '+ ipath)
        line = result.read()
        dims = line.split()
        try:
            dimx = int(dims[0])
            dimy = int(dims[1])
        except:
            logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Error: can not get size from header: '+ipath
            db3_inc.logwrite(mainlogfile,logs)
            return -20, "", -1
        if dimx > 3000 or dimy > 3000:
            cmd = "newstack -bin 2 -input "+ipath+" -output "+outputpath+iname
            if db3_inc.myexecmd(cmd, exe, pr) != 0:
                logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Failed '+cmd+'Leave tilt unbinned.' 
                db3_inc.logwrite(mainlogfile,logs)
            else:
                if int(binfactor) < 2:
                    binfactor = "2"
                    logs = "4K data must be binned at least 2. change binfactor to 2"
                    logwritelocal(pipelinelogfile,logs)
                    adjust_binfactor = 1
                binfactor1 = str(int(int(binfactor) / 2))
                logs = "4K tilt series binned by 2."
                logwritelocal(pipelinelogfile,logs)
                if int(binfactor) % 2 != 0  and int(binfactor) > 1:
                    adjust_binfactor = -1
                inputpath = outputpath
            diameter = int(float(diameter) / 2)

        diameter_pix = str(int(round(float(diameter)/float(pixelsize_tilt))))
        logs = time.strftime("%H:%M:%S",time.localtime()) + " Starting RAPTOR **********" 
        logwritelocal(pipelinelogfile,logs)
        imodpath  = os.environ.get('IMOD_DIR') 
        if imodpath == None:
            logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] RAPTOR Error: environment variable IMOD_DIR undefined'
            db3_inc.logwrite(mainlogfile,logs)
            sys.exit(1)
        imodpath  = imodpath +'/bin/'
        cmd = imodpath + "RAPTOR -execPath "+ imodpath +" -path " + inputpath + " -diameter " + diameter_pix + " -angles -rec 0" + " -thickness " + thickness + " -bin " + binfactor1 + " -orientation " + orientation + " -verb 1" + " -output " + outputpath + " -input " + iname 
        logwritelocal(pipelinelogfile,cmd)        
        if markers != "0":
            cmd = cmd + " -markers " + markers

        rr = db3_inc.myexecmd(cmd, exe, pr)
        alignpath = outputpath+"align/"
        basename = getBasename(iname)
        # append log
        rrlog = alignpath + basename + "_RAPTOR.log"
        logAppend(pipelinelogfile, rrlog)
        
        if rr != 0:  # RAPTOR failed
            logs = time.strftime("%H:%M:%S",time.localtime()) + " RAPTOR Failed **********" 
            logwritelocal(pipelinelogfile,logs)
            return 5, "", -1
        #check if rec exists
        failed = 1
        for recname in os.listdir(alignpath):
            if fnmatch.fnmatch(recname,"*.rec"):
                oname = recname
                failed = 0
        if failed == 1:
            logs = time.strftime("%H:%M:%S",time.localtime()) + " RAPTOR: No rec found." 
            logwritelocal(pipelinelogfile,logs)
            return 4, "", -1  # RAPTOR completed but no rec

        logs = time.strftime("%H:%M:%S",time.localtime()) + " Finished RAPTOR **********" 
        logwritelocal(pipelinelogfile,logs)

        #if RAPTOR drops more than half of the frames, consifer failed
        temp = oname.split('_part')
        if len(temp) > 1:
            temp1 = temp[1]
            temp2 = re.split('_|\.', temp1)
            numall = int(temp2[0])
            numdrop = int(temp2[1])
            print (numall, numdrop)
            if numdrop > numall/2:
                logs = time.strftime("%H:%M:%S",time.localtime()) + " RAPTOR dropped too many ("+ str(numdrop) +") frames **********" 
                logwritelocal(pipelinelogfile,logs)
                return 3, oname, -1

        # move .rec to upload
        cmd = 'mv ' + alignpath + oname +' ' +outputpath + 'upload/'
        if db3_inc.myexecmd2(cmd, exe, pr) != 0:
            logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Failed: '+cmd
            db3_inc.logwrite(mainlogfile,logs)
            return -4, "", -1
        else:
            voxel_size_full =  float(pixelsize_tilt)*float(int(binfactor) + adjust_binfactor)
            
    return 0, oname, voxel_size_full
#end of procone_raptor



# Batchruntomo precedure: generate .adoc file
def generateDirFile (exepath, inputPath, basename, beadSize, thickness, pixelSize, binFactor, defocus, lightBeads, trial):

    binFactor = int(binFactor)
    #Check and remove old directive file
    if os.path.exists(inputPath + basename + '.adoc'):
        os.rename(inputPath + basename + '.adoc', inputPath + basename + str(trial) +'.adoc')

    #Copy a new directive file to edit
    dirFileUri = exepath + "dirTemplate.adoc"
    newDirFile = inputPath + basename + '.adoc'
    shutil.copy(dirFileUri, newDirFile)
    
    #Open the directive file for editing
    openFile = open(newDirFile, "r")
    fileInfo = openFile.readlines()
    fileLength = len(fileInfo)
       
    
    for i in range(0, fileLength):
        
        if 'runtime.Fiducials.any.trackingMethod=' in fileInfo[i]:
            if trial == 1:
                fileInfo[i] = 'runtime.Fiducials.any.trackingMethod= ' + str(0) + '\r\n'
            if trial == 0:
                fileInfo[i] = 'runtime.Fiducials.any.trackingMethod= ' + str(2) + '\r\n'
            if trial == -1:
                fileInfo[i] = 'runtime.Fiducials.any.trackingMethod= ' + str(1) + '\r\n'

        if 'setupset.copyarg.name=' in fileInfo[i]:
            fileInfo[i] = 'setupset.copyarg.name= ' + basename +'\r\n'
            
        if 'setupset.copyarg.gold=' in fileInfo[i]:
            fileInfo[i] = 'setupset.copyarg.gold= ' + str(beadSize) + '\r\n'
        
        if 'setupset.copyarg.pixel=' in fileInfo[i]:
            fileInfo[i] = 'setupset.copyarg.pixel= ' + str(pixelSize) + '\r\n'
        
        if 'setupset.copyarg.defocus=' in fileInfo[i]:
            fileInfo[i] = 'setupset.copyarg.defocus= ' + str(defocus) + '\r\n'
        
        if 'setupset.datasetDirectory=' in fileInfo[i]:
            fileInfo[i] = 'setupset.datasetDirectory= ' + inputPath + '\r\n'
            
        if 'comparam.prenewst.newstack.BinByFactor=' in fileInfo[i]:
            if binFactor > 1:
                fileInfo[i] = 'comparam.prenewst.newstack.BinByFactor=2\r\n'
            else:
                fileInfo[i] = 'comparam.prenewst.newstack.BinByFactor=1\r\n'
            
        if 'comparam.track.beadtrack.LightBeads=' in fileInfo[i]:
            fileInfo[i] = 'comparam.track.beadtrack.LightBeads= ' + str(lightBeads) + '\r\n'
            
        if 'runtime.AlignedStack.any.binByFactor=' in fileInfo[i]:
            fileInfo[i] = 'runtime.AlignedStack.any.binByFactor= ' + str(binFactor)  + '\r\n'
            
        #if 'comparam.tilt.tilt.THICKNESS=' in fileInfo[i]:
        #    fileInfo[i] = 'comparam.tilt.tilt.THICKNESS= ' + str(thickness) + '\r\n'

        if 'runtime.Reconstruction.any.binnedThickness=' in fileInfo[i]:
            fileInfo[i] = 'runtime.Reconstruction.any.binnedThickness= ' + str(thickness) + '\r\n'
    
    sep = ''
    tiltDirFile = sep.join(fileInfo)
    
    writeFile = open(newDirFile, 'w')
    writeFile. write(tiltDirFile)
    writeFile.close()

#function: prosess one tilt series 
def procone_brt(exe, tiltseriesid, pixelsize_tilt, inputdir, iname, diameter, thickness, binfactor, markers, defocus, orientation, exepath, pipelinelogfile):
        
    # generate .adoc and launch brt, use database file as input and local outputdir as output dir 
    
    outputpath = outputdir+tiltseriesid+"/brt/"
    ipath = inputdir +iname
    if not os.path.exists(ipath):
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Error: mrc file does not exist '+ipath
        db3_inc.logwrite(mainlogfile,logs)
        return -20, "", -1
    
    print ("launching Batchruntomo "+ipath)

    logs = time.strftime("%H:%M:%S",time.localtime()) + " Starting Batchruntomo **********" 
    logwritelocal(pipelinelogfile,logs)
    #create dir
    cmd = "mkdir -p " + outputpath
    if db3_inc.myexecmd2(cmd, 1, pr) != 0:
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Batchruntomo Failed: ' + cmd
        db3_inc.logwrite(mainlogfile,logs)
        return -20, "", -1
    
    #get the base filename
    basename = getBasename(iname)
    #generate .adoc
    generateDirFile(exepath, outputpath, basename, diameter, thickness, pixelsize_tilt, binfactor, defocus, 0, 1)
    adocfile = outputpath + basename + '.adoc'
    print ('!!!!! adocfile=', adocfile)
    if not os.path.exists(adocfile):
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Batchruntomo Failed: cmdDirective file did not copy over for ' + basename
        db3_inc.logwrite(mainlogfile,logs)
        return -20, "", -1

    logs = time.strftime("%H:%M:%S",time.localtime()) +  " Batchruntomo: Directive file made for " + basename + ", starting alignment..."
    logwritelocal(pipelinelogfile,logs)
    opath = outputpath + iname
    shutil.copy(ipath, opath)
 
    brtenv = os.environ.get('BRT_IMOD_DIR')
    brtpath = ''
    if brtenv != None:
        brtpath = brtenv + '/bin/'
        os.environ['IMOD_DIR'] = brtenv
        logs = time.strftime("%H:%M:%S",time.localtime()) + " Batchruntomo: change IMOD_DIR to: " + brtenv
        logwritelocal(pipelinelogfile,logs)
    
    # start imod 4.10, new name format is basename_rec.mrc; can add -style 0 to get old name basename.rec
    # cmd = brtpath + 'batchruntomo -style 0 -di ' + adocfile + ' -gpus 1 -cpus 10'

    cmd = brtpath + 'batchruntomo -di ' + adocfile + ' -gpus 1 -cpus 10'
    rr = db3_inc.myexecmd2(cmd, exe, pr)
    # append log
    rrlog = outputpath+"batchruntomo.log"
    logAppend(pipelinelogfile, rrlog)

    logs = time.strftime("%H:%M:%S",time.localtime()) + " Finished Batchruntomo **********" 
    logwritelocal(pipelinelogfile,logs)
    if  rr != 0: #brt failed
        logs = time.strftime("%H:%M:%S",time.localtime()) + " Batchruntomo Failed **********" 
        logwritelocal(pipelinelogfile,logs)
        return 5, "", -1

    oname = basename+".rec"
    oname1 = basename+"_rec.mrc"
    new_brt_name = 0
    if not os.path.exists(outputpath + oname):
        if os.path.exists(outputpath + oname1):
            new_brt_name = 1
        else:
            logs = time.strftime("%H:%M:%S",time.localtime()) + " Batchruntomo: No rec found." 
            logwritelocal(pipelinelogfile,logs)
            return 4, "", -1
    
    # move .rec to upload
    if new_brt_name:
        cmd = 'mv ' + outputpath+ oname1 +' ' +outputdir+tiltseriesid+ '/upload/' + oname
    else:
        cmd = 'mv ' + outputpath+ oname +' ' +outputdir+tiltseriesid+ '/upload/'
    if db3_inc.myexecmd2(cmd, exe, pr) != 0:
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Failed: '+cmd
        db3_inc.logwrite(mainlogfile,logs)
        return -4, "", -1
    else:
        voxel_size_full = float(pixelsize_tilt)*float(int(binfactor))
         
    return 0, oname,voxel_size_full
#end of procone_brt


def procone_patch(exe, tiltseriesid, pixelsize_tilt, inputdir, iname, patch_sizex, patch_sizey, patch_overlap, patch_trim, binfactor, exepath, pipelinelogfile):
        
    outputpath = outputdir+tiltseriesid+"/"
    ipath = inputdir + iname
    if not os.path.exists(ipath):
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' [ '+tiltseriesid+'] Error: mrc file does not exist '+ipath
        db3_inc.logwrite(mainlogfile,logs)
        return -20, "", -1
    else:
        print ("launching Patch "+ipath)

        # bin tilt before launching autoPatch.py
        if int(binfactor) > 1:
            cmd = "newstack -bin "+binfactor+" -input "+ipath+" -output "+outputpath+iname
            if db3_inc.myexecmd(cmd, exe, pr) != 0:
                logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Failed procone_patch: tilt binning '+cmd
                db3_inc.logwrite(mainlogfile,logs)
                return -20, "", -1
        else:
            cmd = "cp "+ipath+" "+outputpath+iname
            if db3_inc.myexecmd(cmd, exe, pr) != 0:
                logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Failed procone_patch:  cannot copy mrc file '+cmd
                db3_inc.logwrite(mainlogfile,logs)
                return -20, "", -1
        basename = getBasename(iname)
        try:
            os.chdir(outputpath)
            cmd = "mv "+iname+" "+basename+".st"
            #cmd = "mv "+ outputpath + iname+" "+outputpath + basename+".st"
            os.system(cmd)
        except:
                logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Failed procone_patch:  cannot chdir or rename .mrc to .st'
                db3_inc.logwrite(mainlogfile,logs)
                return -20, "", -1

        logs = time.strftime("%H:%M:%S",time.localtime()) + " Starting autoPatch **********" 
        logwritelocal(pipelinelogfile,logs)
        logs = "autoPatch patch_size:("+patch_sizex+","+patch_sizey+") overlap:"+patch_overlap+" trim:"+patch_trim
        logwritelocal(pipelinelogfile,logs)
        cmd = exepath+"Patch/autoPatch.py "+basename+" "+"1"+" "+thickness+" "+patch_sizex+" "+patch_sizey+" "+patch_overlap+" "+patch_trim
        #cmd = exepath+"Patch/autoPatch.py "+outputpath+basename+" "+"1"+" "+thickness+" "+patch_sizex+" "+patch_sizey+" "+patch_overlap+" "+patch_trim

        rr = db3_inc.myexecmd(cmd, exe, pr)
        # append log
        rrlog = outputpath+"autopatch.log"
        logAppend(pipelinelogfile, rrlog)

        logs = time.strftime("%H:%M:%S",time.localtime()) + " Finished autoPatch **********" 
        logwritelocal(pipelinelogfile,logs)
        
        if rr != 0:  # autoPatch failed
            logs = time.strftime("%H:%M:%S",time.localtime()) + " autoPatch Failed **********" 
            logwritelocal(pipelinelogfile,logs)
            return 5, "", -1
        
        # autoPatch has no log
        #check if rec exists
        failed = 1
        oname = basename+".rec"
        if not os.path.exists(outputpath + oname):
            logs = time.strftime("%H:%M:%S",time.localtime()) + " autoPatch: No rec found." 
            logwritelocal(pipelinelogfile,logs)
            return 4, "", -1  #  autoPatch completed but no rec
  
        # move .rec to upload
        cmd = 'mv ' + outputpath+oname +' ' +outputpath + 'upload/'
        if db3_inc.myexecmd2(cmd, exe, pr) != 0:
            logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Failed: '+cmd
            db3_inc.logwrite(mainlogfile,logs)
            return 4, "", -1  #  autoPatch completed but no rec
        else:
            voxel_size_full = float(pixelsize_tilt)*float(int(binfactor))

        return 0, oname, voxel_size_full
#end of procone_patch

def procone_eman2(exe, tiltseriesid, pixelsize_tilt, inputdir, iname, thickness, eman2markers, boxsize, eman2bin, exepath, pipelinelogfile):
# assuming mrc & mrc.mdoc in same inputdir

    outputpath = outputdir+tiltseriesid+"/"
    ipath = inputdir + iname
    basename = getBasename(iname)

    if not os.path.exists(ipath):
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' [ '+tiltseriesid+'] Error: mrc file does not exist '+ipath
        db3_inc.logwrite(mainlogfile,logs)
        return -20, "", -1
    mdocpath = ipath + '.mdoc'
    if not os.path.exists(mdocpath):
        mdocpath = mdocpath.replace('.mrc.mdoc', '.tif.mdoc') 
        if not os.path.exists(mdocpath):
            logs = time.strftime("%H:%M:%S",time.localtime()) + ' [ '+tiltseriesid+'] Error: mdoc file does not exist '+mdocpath
            db3_inc.logwrite(mainlogfile,logs)
            return -21, "", -1
    
    print ("launching EMAN2 "+ipath)
    
    result = os.popen('grep RotationAngle '+ mdocpath)
    lines = result.read().split()
    try:
        tiltangle = float(lines[2]) - 90 - 180
    except:
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Error: can not get RotationAngle from mdoc: '+mdocpath
        db3_inc.logwrite(mainlogfile,logs)
        return -21, "", -1

    logs = time.strftime("%H:%M:%S",time.localtime()) + " Starting EMAN2 **********" 
    logwritelocal(pipelinelogfile,logs)

    rawtltpath = outputpath + basename + '.rawtlt'
    cmd = 'extracttilts -t ' + ipath + ' ' + rawtltpath 
    rr = db3_inc.myexecmd(cmd, exe, pr)
    if rr != 0 or not os.path.exists(rawtltpath):  # failed
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Error: failed '+cmd
        db3_inc.logwrite(mainlogfile,logs)
        return 5, "", -1
    else:
        logs = time.strftime("%H:%M:%S",time.localtime()) + " " + cmd
        logwritelocal(pipelinelogfile,logs)

    # convert mrc to hdf for EMAN2
    mrchdf = outputpath + basename + '.hdf'
    cmd = 'e2proc2d.py ' + ipath + ' ' + mrchdf 
    rr = db3_inc.myexecmd(cmd, exe, pr)
    if rr != 0 or not os.path.exists(mrchdf):  # failed
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Error: failed '+cmd
        db3_inc.logwrite(mainlogfile,logs)
        return 5, "", -1
    else:
        logs = time.strftime("%H:%M:%S",time.localtime()) + " " + cmd
        logwritelocal(pipelinelogfile,logs)

    # collect stdout from slurm .out later
    print('STARTEMAN2STARTEMAN2')
    sys.stdout.flush()
    time.sleep(1)
    try:        
        os.chdir(outputdir)
    except:
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Error: failed chdir '+outputdir
        db3_inc.logwrite(mainlogfile,logs)
        return -20, "", -1
    
    cmd = 'e2tomogram.py ' + mrchdf + ' --rawtlt=' + rawtltpath + ' --tltax=' + str(tiltangle) + ' --npk=' + eman2markers + ' --bxsz=' + boxsize + ' --niter=2,1,1,1 --tltkeep=0.9 --pkkeep=0.9 --pk_mindist=0.125 --filterto=0.45 --rmbeadthr=10 --extrapad --outsize=' + eman2bin + ' --bytile --moretile --notmp --clipz=' + thickness + ' --maxshift=0.35 --compressbits=8 --threads=4'
    logs = time.strftime("%H:%M:%S",time.localtime()) + " " + cmd
    logwritelocal(pipelinelogfile,logs)

    rr = db3_inc.myexecmd(cmd, exe, pr)
    print('ENDEMAN2ENDEMAN2')
    sys.stdout.flush()

    if rr != 0:  # EMAN2 failed
        logs = time.strftime("%H:%M:%S",time.localtime()) + " EMAN2 Failed **********" 
        logwritelocal(pipelinelogfile,logs)
        return 5, "", -1

    outfile = ''
    for f in os.listdir(outputdir):
        if f.startswith(tiltseriesid+'.') and f.endswith('.out'):
            outfile = f

    if outfile != '':
        with open(pipelinelogfile, 'a') as pf, open(outputdir+outfile, 'r') as of :
            alllines = of.read()
            eman2log = alllines.split('STARTEMAN2STARTEMAN2')[1]
            eman2log = eman2log.split('ENDEMAN2ENDEMAN2')[0]
            pf.write('\n*****start eman2 log*****')
            pf.write(eman2log)
            pf.write('\n*****end eman2 log*****')
            pf.flush()

    failed = 1
    rechdf = ''
    for f in os.listdir(outputdir+'tomograms/'):
        if basename+'__bin' in f and f.endswith('.hdf'):
            rechdf = f
            failed = 0
    if failed == 1:
        logs = time.strftime("%H:%M:%S",time.localtime()) + " EMAN2: No result hdf found." 
        logwritelocal(pipelinelogfile,logs)
        return 4, "", -1  # EMAN2 completed but no hdf

    # append json to log
    jsonfile = rechdf.split('__bin')[0] + '_info.json'
    logwritelocal(pipelinelogfile,'\n*****start output json file*****')
    rrlog = outputdir+'info/' + jsonfile
    logAppend(pipelinelogfile, rrlog)
    logwritelocal(pipelinelogfile,'\n*****end json file*****')
    
    logs = time.strftime("%H:%M:%S",time.localtime()) + " Finished EMAN2 **********" 
    logwritelocal(pipelinelogfile,logs)

    oname = basename + '.rec'
    cmd = 'newstack -scale 0,255  -float 4 -mode 0 ' + outputdir+'tomograms/'+rechdf + ' ' + outputpath + oname
    rr = db3_inc.myexecmd(cmd, exe, pr)
    if rr != 0 or not os.path.exists(outputpath + oname):  # no rec
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Error: failed '+cmd
        db3_inc.logwrite(mainlogfile,logs)
        return 4, "", -1
    else:
        logs = time.strftime("%H:%M:%S",time.localtime()) + " " + cmd
        logwritelocal(pipelinelogfile,logs)

    # e2tomogram.py does not set pixel size in IMOD header, adding the info
    voxel_size_full = 0
    result = os.popen('e2iminfo.py -s '+ outputdir+'tomograms/'+rechdf)
    lines = result.read().split()
    for line in lines:
        if 'apix=' in line:
            px = line.split('apix=')
            voxel_size_full = float(px[1])/10.0
    if voxel_size_full == 0: # failed from e2iminfo, get binfactor from hdf name
        binfactor  = rechdf.split('__bin')[1].split('.hdf')[0]
        voxel_size_full = float(pixelsize_tilt)*float(int(binfactor))
        
    cmd = 'alterheader -d ' + str(voxel_size_full)+','+str(voxel_size_full)+','+str(voxel_size_full) + ' ' + outputpath + oname       
    rr = db3_inc.myexecmd(cmd, exe, pr)
    logs = time.strftime("%H:%M:%S",time.localtime()) + " " + cmd
    logwritelocal(pipelinelogfile,logs)
    
    # move .rec to upload
    cmd = 'mv ' + outputpath + oname +' ' +outputpath + 'upload/'
    if db3_inc.myexecmd2(cmd, exe, pr) != 0:
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Failed: '+cmd
        db3_inc.logwrite(mainlogfile,logs)
        return -4, "", -1

    # clean up here due to eman2's special output path
    if keepali == 0 and keepall == 0:
        cmd = 'rm '+ outputdir+'tomograms/'+rechdf
        db3_inc.myexecmd(cmd, exe, pr)
        cmd = 'rm '+ outputdir+'info/' + jsonfile
        db3_inc.myexecmd(cmd, exe, pr)

    return 0, oname, voxel_size_full
#end of procone_eman2


def db3_cleanup(tiltseriesid, keepali, keepall, logfile, exe, pr):
# called by db3_upload
    tiltdir = outputdir+tiltseriesid+'/'
    if keepali:
        # keep .ali and .tlt
        '''
        softwaremethod == "Raptor":
                pathali = outputpath+"align/"+basename+".ali"
                pathtlt = outputpath+"IMOD/"+basename+".tlt"
        softwaremethod == "autoPatch":
                pathali = outputpath+basename+".ali"
                pathtlt = outputpath+basename+".tlt"
        softwaremethod == "Batchruntomo":
                pathali = outputpath+"brt/"+basename+".ali"
                pathtlt = outputpath+"brt/"+basename+".tlt"
        '''
        print(tiltdir)
        for root, dirs, files in os.walk(tiltdir):
            for fname in files:
                if not fname.endswith('.ali') and not fname.endswith('.tlt'):
                    rmpath = os.path.join(root, fname)
                    cmd = 'rm '+rmpath
                    db3_inc.myexecmd(cmd, exe, pr)
        temp = tiltdir+'temp'
        if os.path.exists(temp):
            cmd = 'rm -r '+temp
            if db3_inc.myexecmd(cmd, exe, pr) != 0:
                logs = time.strftime("%H:%M:%S",time.localtime()) + " ["+tiltseriesid+"] Pipeline  Error: cannot remove directory: " + cmd
                db3_inc.logwrite(logfile,logs)
        temp = tiltdir+'upload'
        if os.path.exists(temp):
            cmd = 'rm -r '+temp
            if db3_inc.myexecmd(cmd, exe, pr) != 0:
                logs = time.strftime("%H:%M:%S",time.localtime()) + " ["+tiltseriesid+"] Pipeline  Error: cannot remove directory: " + cmd
                db3_inc.logwrite(logfile,logs)                    
    else: # else remove entire dir
        cmd = 'rm -r '+tiltdir
        if db3_inc.myexecmd(cmd, exe, pr) != 0:
            logs = time.strftime("%H:%M:%S",time.localtime()) + " ["+tiltseriesid+"] Pipeline  Error: cannot remove directory: " + cmd
            db3_inc.logwrite(logfile,logs)
    #remove .job  files
    #cmd = 'rm '+outputdir+tiltseriesid+'.job'
    #db3_inc.myexecmd(cmd, exe, pr) 
    #cmd = 'rm '+outputdir+tiltseriesid+'.*.out'
    #db3_inc.myexecmd(cmd, exe, pr)
    #remove .err file if empty or contains only 'Python PID: xxx'
    keeperr = 0
    for f in os.listdir(outputdir):
        if f.startswith(tiltseriesid) and f.endswith('.err'):
            fpath = outputdir + '/' + f
            fsize = os.path.getsize(fpath)
            #if fsize > 160:
            # current .err
            #slurmstepd: error: couldn't chdir to `/net/jcontrol4/jensen7/jdatabase/tomography/data': No such file or directory: going to /tmp instead
            #Python PID: 65580
            if fsize > 30: # Python PID only
                keeperr = 1
            elif fsize > 0 and 'Python PID' not in open(fpath).read():
                keeperr = 1
            if keeperr == 0:
                cmd = 'rm '+ fpath
                db3_inc.myexecmd(cmd, exe, pr)
           
    return 0
#end db3_cleanup

def db3_upload(tiltseriesid, tilt_status, method, voxel_size_full, keepali, keepall, logfile, rsync_username, server_ssh, exe, pr) :
    # check if valid tiltid
    sql = "SELECT COUNT(1) FROM tomography.TiltSeriesData WHERE tiltseriesID='" + tiltseriesid + "'"
    status, cursor = db3_inc.myexesql(hostip, sql, 1, pr)
    if status != 0 or cursor[0][0] == 0:
        logs = time.strftime("%H:%M:%S",time.localtime()) + " ["+tiltseriesid+"] Pipeline3 upload Error: cannot find in database: " + tiltseriesid 
        db3_inc.logwrite(logfile,logs)
        sys.exit(1)

    # tiltid is valid
    print ('uploading', tiltseriesid)
    uploadto = dbpath+tiltseriesid
    uploadpath = outputdir+tiltseriesid+'/'+'upload/'
    keyimg = 0
    keymov = 0
    hasrec = 0
    pipeline_status = tilt_status

    # key img/mov
    keyimgname = uploadpath+'/keyimg_'+tiltseriesid+'_s.jpg'
    keyimgname1 = uploadpath+'/keyimg_'+tiltseriesid+'.jpg'
    keymovname = uploadpath+'/keymov_'+tiltseriesid+'.mp4'
    if os.path.exists(keymovname):
        keymov = 1
    if os.path.exists(keyimgname) and os.path.exists(keyimgname1):
        keyimg = 1
        if pipeline_status == 2:  # case for norec
            keyimg = 2

    #check rec
    if tilt_status==0:
        recname = ''
        for filename in os.listdir(uploadpath):
            if filename.endswith(".rec"):
                recname = filename
                #create db record for rec
                if voxel_size_full > 0:
                    sql = "INSERT INTO tomography.ThreeDFile (`REF|TiltSeriesData|tiltseries`, status, tag, pixel_size, classify, filename, software_process)  VALUES ( \""+tiltseriesid+"\", 0, 1, "+str(voxel_size_full)+", \"reconstruction\", \""+recname+"\", \""+method+"\")"
                else:
                    sql = "INSERT INTO tomography.ThreeDFile (`REF|TiltSeriesData|tiltseries`, status, tag, classify, filename, software_process)  VALUES ( \""+tiltseriesid+"\", 0, 1, \"reconstruction\", \""+recname+"\", \""+method+"\")"
                status, cursor = db3_inc.myexesql(hostip, sql, exe, pr)
                if status != 0:
                    logs = time.strftime("%H:%M:%S",time.localtime()) + " ["+tiltseriesid+"] MySQL Error: " + sql
                    db3_inc.logwrite(logfile,logs)
                    print ('Pipeline could not upload the reconstruction for '+tiltseriesid+' to  Database. .')
                    sys.exit(1)
                # get insert id  and move .rec to upload location
                # no loger have conn to get last id, fetch it from mysql with given tiltid and recname
                # sort by timestamp and take the newest one, needed for rerun
                sql = "SELECT DEF_id FROM ThreeDFile WHERE `REF|TiltSeriesData|tiltseries`='"+tiltseriesid+"' AND filename='"+recname+"' AND status != 2 ORDER BY DEF_timestamp DESC"
                status, cursor = db3_inc.myexesql(hostip, sql, exe, pr)
                error = 0
                imageid = 0
                if status != 0:
                    error = 1
                elif len(cursor) == 0:
                    error = 1
                else:
                    imageid = cursor[0][0]
                if error:
                    logs = time.strftime("%H:%M:%S",time.localtime()) + " ["+tiltseriesid+"] MySQL Error: " + sql
                    db3_inc.logwrite(logfile,logs)
                    sys.exit(1)
                #move .rec in correct subdir
                recpath = uploadpath+'3dimage_'+str(imageid)
                cmd = 'mkdir -p '+recpath
                if db3_inc.myexecmd(cmd, exe, pr) != 0:
                    logs = time.strftime("%H:%M:%S",time.localtime()) + " ["+tiltseriesid+"] Pipeline  Error: cannot create rec directory " + recpath
                    db3_inc.logwrite(logfile,logs)
                    sys.exit(1)
                cmd = 'chmod 755 '+recpath 
                db3_inc.myexecmd(cmd, exe, 0) 
                cmd = 'chmod 644 '+uploadpath+recname
                db3_inc.myexecmd(cmd, exe, 0) 
                cmd = 'mv '+uploadpath+recname+' '+recpath
                if db3_inc.myexecmd(cmd, exe, pr) != 0:
                    logs = time.strftime("%H:%M:%S",time.localtime()) + " ["+tiltseriesid+"] Pipeline  Error: cannot move rec: " + cmd
                    db3_inc.logwrite(logfile,logs)
                    sys.exit(1)
                hasrec = 1
        if hasrec:
            pipeline_status = 1
        else:
            pipeline_status = 4

    if pipeline_status != 0 and pipeline_status != 1 and pipeline_status != 2:
        logs = time.strftime("%H:%M:%S",time.localtime()) + " ["+tiltseriesid+"] Pipeline failed to produce reconstruction: " + tiltseriesid + ", " + str(tilt_status)
        db3_inc.logwrite(logfile,logs)

    #rsync all files under upload directory 
    if db3_inc.myexersync(uploadpath, uploadto, rsync_username, server_ssh, 0, exe, pr) != 0:
        sql = "UPDATE tomography.TiltSeriesData SET pipeline=\"7\" WHERE tiltseriesID=\""+tiltseriesid+"\""
        db3_inc.myexesql(hostip, sql, exe, pr)                
        logs = time.strftime("%H:%M:%S",time.localtime()) + " ["+tiltseriesid+"] Pipeline Error: failed rsync: " + uploadpath +" to "+ uploadto
        db3_inc.logwrite(logfile,logs)
        print ('Pipeline failed to rsync results for '+tiltseriesid+' to the database. ')
        sys.exit(1)

    if server_ssh !=0 and server_ssh !='0':
        cmd = 'ssh '+ rsync_username + '@' + server_ssh + ' "chmod 755 ' + uploadto + '"'
    else:
        cmd = 'chmod 755 ' + uploadto 
    db3_inc.myexecmd(cmd, exe, 0) 

    #all files rsynced, final sql update
    if hasrec:
        sql = "UPDATE tomography.TiltSeriesData SET keyimg="+str(keyimg)+", keymov="+str(keymov)+", pipeline="+str(pipeline_status)+", software_process=\""+method+"\" WHERE tiltseriesID=\""+tiltseriesid+"\""
    else: #no rec
        if keyimg == 1:
            keyimg = 2
        sql = "UPDATE tomography.TiltSeriesData SET keyimg="+str(keyimg)+", keymov="+str(keymov)+", pipeline="+str(pipeline_status)+" WHERE tiltseriesID=\""+tiltseriesid+"\""
    status, cursor = db3_inc.myexesql(hostip, sql, exe, pr)
    if status != 0:
        logs = time.strftime("%H:%M:%S",time.localtime()) + " ["+tiltseriesid+"] MySQL Error: " + sql
        db3_inc.logwrite(logfile,logs)
        sys.exit(1)

    logs = time.strftime("%H:%M:%S",time.localtime()) + " ["+tiltseriesid+"] uploaded: " + tiltseriesid
    db3_inc.logwrite(logfile,logs)

    # if keepali and eman2, move tilt series hdf to subdirectory tiltseries/ 
    if keepali and method=='EMAN2':
        if not os.path.exists( outputdir+'tiltseries/'):
            cmd = "mkdir -p " + outputdir+'tiltseries/'
            if db3_inc.myexecmd2(cmd, 1, pr) != 0:
                logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Failed for eman2: ' + cmd
                db3_inc.logwrite(mainlogfile,logs)

        cmd = 'mv '+ outputdir+tiltseriesid+'/*.hdf ' + outputdir+'tiltseries/'
        if db3_inc.myexecmd2(cmd, exe, pr) != 0:
            logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Failed: '+cmd
            db3_inc.logwrite(mainlogfile,logs)

    
    #    if pipeline_status == 0 or pipeline_status == 1 or pipeline_status == 2: #!!!!!! temp for testing, remove later
    #        watch_cleanup(tiltseriesid, keepali, keepall, logfile, exe, pr)

    if keepall == 0:
        if keepali and method=='EMAN2':
            db3_cleanup(tiltseriesid, 0, keepall, logfile, exe, pr)
        else:
            db3_cleanup(tiltseriesid, keepali, keepall, logfile, exe, pr)
    return 0
#end def db3_upload    



###### main function
if len(sys.argv) <= 9:
    print ('Automatic processing a tilt series which is already in database')
    print ('Called by db3_proc.py')
    print ('  exe: 0 = test only,  1 = execute')
    print ('  server: 0 = charon,  1 = jupiter')
    print ('quit')
    sys.exit(0)


try:
    options, remainder = getopt.getopt(sys.argv[1:], 'e:ip:id:in:de:px:mk:bi:d:th:wa:al:ka:rc:q1:q2:q3:px:py:po:pt:eb:em:es:or:ep:out:log:un:um:in', ['exe=','serverip=','tiltseriesid=','iname=','defocus=','pixelsizetilt=','markers=','binfactor=','diameter=','thickness=','wait=','keepali=','keepall=','recon=','seq1=','seq2=','seq3=','patchx=','patchy=','patchoverlap=','patchtrim=','eman2bin=','eman2markers=','eman2boxsize=','orientation=','exepath=','outputdir=','logstring=','username=','useremail=','inputdir='])
except getopt.GetoptError as err:
    print ("Error: db3_proc.py input error. Quit.", err)
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
    if opt in ('id', '--tiltseriesid'):
        tiltseriesid = arg
    if opt in ('-in', '--iname'):
        iname = arg
    if opt in ('-de', '--defocus'):
        defocus = arg
    if opt in ('-px', '--pixelsizetilt'):
        pixelsize_tilt = arg
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
    if opt in ('-ka', '--keepall'):
        keepall = int(arg)
    if opt in ('-al', '--keepali'):
        keepali = int(arg)
    if opt in ('-rc', '--recon'):
        recon = int(arg)
    if opt in ('-q1', '--seq1'):
        seq1 = arg
    if opt in ('-q2', '--seq2'):
        seq2 = arg
    if opt in ('-q3', '--seq3'):
        seq3 = arg
    if opt in ('-px', '--patchx'):
        patch_sizex = arg
    if opt in ('-py', '--patchy'):
        patch_sizey = arg
    if opt in ('-po', '--patchoverlap'):
        patch_overlap = arg
    if opt in ('-pt', '--patchtrim'):
        patch_trim  = arg
    if opt in ('-eb', '--eman2bin'):
        eman2bin = arg
    if opt in ('-em', '--eman2markers'):
        eman2markers = arg
    if opt in ('-es', '--eman2boxsize'):
        eman2boxsize = arg
    if opt in ('-or', '--orientation'):
        orientation = arg
    if opt in ('-ep', '--exepath'):
        exepath = arg
    if opt in ('-out', '--outputdir'):
        outputdir = arg
    if opt in ('-log', '--logstring'):
        logstring = arg
    if opt in ('-un', '--username'):
        rsync_username = arg
    if opt in ('-um', '--useremail'):
        useremail = arg
    if opt in ('-in', '--inputdir'):
        inputdir = arg

# added: outputdir  inputdir  logstring


adjust_binfactor = 0
rawpath = inputdir +iname


if exe == 0:
    print ("****** Running db3_procone in TEST ONLY mode", tiltseriesid)
else:
    print ("****** Running db3_procone", tiltseriesid)

mainlogfile = outputdir + "db3_proc."+logstring+".log"

outputpath = outputdir+tiltseriesid+'/'
uploadpath = outputpath+'upload/'
pipelinelogfile = uploadpath + 'pipeline.log'
basename = getBasename(iname)

logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Starting process in '+ outputpath
if db3_inc.logwrite(mainlogfile,logs) != 0:
    msg = '['+tiltseriesid+'] Pipeline Error: cannot write to log file '+mainlogfile+': '+logs
    print (msg)
    logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Process Done'
    db3_inc.logwrite(mainlogfile,logs) 
    sys.exit(1)

# check if mrc exist - pre-processing failure handled here 
ipath = inputdir +iname
if not os.path.exists(ipath):
    print ("Error: mrc file does not exist "+ipath)
    logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Error: mrc file does not exist '+ipath
    db3_inc.logwrite(mainlogfile,logs)
    sql = "UPDATE tomography.TiltSeriesData SET pipeline=\"-6\" WHERE tiltseriesID=\""+tiltseriesid+"\""
    db3_inc.myexesql(hostip, sql, exe, pr)
    sql = "UPDATE tomography.ThreeDFile SET status=2 WHERE `REF|TiltSeriesData|tiltseries`=\""+tiltseriesid+"\" AND classify=\"rawdata\""
    db3_inc.myexesql(hostip, sql, exe, pr)
    logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Process Done'
    db3_inc.logwrite(mainlogfile,logs) 
    sys.exit(1)


cmd = "mkdir -p " + uploadpath
if db3_inc.myexecmd2(cmd, 1, pr) != 0:
    logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Failed: '+cmd
    db3_inc.logwrite(mainlogfile,logs)
    logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Process Done'
    db3_inc.logwrite(mainlogfile,logs) 
    sys.exit(1)
       
if recon == 0:
    # generate img from raw data
    if db3_inc.gen_keyimg_raw (rawpath, outputpath, uploadpath, tiltseriesid, exe, pr) != 0:
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Generating key img from raw data failed'
    else:
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Generated key img from raw data'
    db3_inc.logwrite(mainlogfile,logs)
    
    db3_upload(tiltseriesid, 2, 'norec', -1, 0, 0, mainlogfile, rsync_username, server_ssh, exe, pr) 

    logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Process Done'
    db3_inc.logwrite(mainlogfile,logs) 

    print ("Done db3_procone: "+tiltseriesid)
    logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Process Done'
    db3_inc.logwrite(mainlogfile,logs) 
    time.sleep(1)
    check_all_job(mainlogfile, useremail, logstring, 0)
    sys.exit(0)

def procone_sequence(seq):
    pp = 5
    oname = ''
    softwaremethod = ''
    if seq == 'raptor':
        pp, oname, voxel_size_full = procone_raptor(exe, tiltseriesid, pixelsize_tilt, inputdir, iname, diameter, thickness, binfactor, markers, orientation, pipelinelogfile)
        softwaremethod = "Raptor"
    elif seq == 'brt':
        pp, oname, voxel_size_full = procone_brt(exe, tiltseriesid, pixelsize_tilt, inputdir, iname, diameter, thickness, binfactor, markers, defocus, orientation, exepath, pipelinelogfile)
        softwaremethod = "Batchruntomo"
    elif seq == 'patch':
        pp, oname, voxel_size_full = procone_patch(exe, tiltseriesid, pixelsize_tilt, inputdir, iname, patch_sizex, patch_sizey, patch_overlap, patch_trim, binfactor, exepath, pipelinelogfile )
        softwaremethod = "autoPatch"
    elif seq == 'eman2':
        pp, oname, voxel_size_full = procone_eman2(exe, tiltseriesid, pixelsize_tilt, inputdir, iname, thickness, eman2markers, eman2boxsize, eman2bin, exepath, pipelinelogfile )
        softwaremethod = "EMAN2"
    if pp == 0:
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] '+ softwaremethod + ' succeeded'
    else:
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] '+ softwaremethod + ' failed'
    db3_inc.logwrite(mainlogfile,logs)
    return pp, oname, softwaremethod, voxel_size_full


softwaremethod = ''
pp, oname, softwaremethod, voxel_size_full = procone_sequence(seq1)
if pp != 0 and seq2 != 'none':
    pp, oname, softwaremethod, voxel_size_full = procone_sequence(seq2)
    if pp != 0 and seq3 != 'none':
        pp, oname, softwaremethod, voxel_size_full = procone_sequence(seq3)

# mainlogfile updated
logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Finished process in '+ outputpath
if db3_inc.logwrite(mainlogfile,logs) != 0:
    msg = '['+tiltseriesid+'] Pipeline Error: cannot write to log file '+mainlogfile+': '+logs
    print (msg)
    sys.exit(1)

# generate key img/mov
opath = uploadpath + oname
if pp == 0:
    # if .rec exist, generate img/mov
    if db3_inc.gen_keyimg (opath, outputpath, uploadpath, tiltseriesid, exe, pr) != 0:
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Generating key img and mov failed'
        db3_inc.logwrite(mainlogfile,logs)
    else:
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Generated key img'
        db3_inc.logwrite(mainlogfile,logs)
        if db3_inc.gen_keymov (opath, outputpath, uploadpath, tiltseriesid, exe, pr) != 0:
            logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Generating key mov failed'
        else:
            logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Generated key mov'
        db3_inc.logwrite(mainlogfile,logs)
else:
    logs = time.strftime("%H:%M:%S",time.localtime()) + " Failed to produce reconstruction." 
    logwritelocal(pipelinelogfile,logs)
    logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Failed to produce reconstruction.'
    db3_inc.logwrite(mainlogfile,logs)
    # generate img from raw data
    if db3_inc.gen_keyimg_raw (rawpath, outputpath, uploadpath, tiltseriesid, exe, pr) != 0:
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Generating key img from raw data failed'
    else:
        logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Generated key img from raw data'
    db3_inc.logwrite(mainlogfile,logs)

                
cmd = 'chmod 644 '+pipelinelogfile
db3_inc.myexecmd(cmd, exe, 0) 
db3_upload(tiltseriesid, pp, softwaremethod, voxel_size_full, keepali, keepall, mainlogfile, rsync_username, server_ssh, exe, pr) 


logs = time.strftime("%H:%M:%S",time.localtime()) + ' ['+tiltseriesid+'] Process Done'
db3_inc.logwrite(mainlogfile,logs) 
print ("Done db3_procone: "+tiltseriesid)
time.sleep(1)
check_all_job(mainlogfile, useremail, logstring, keepali)

sys.exit(0)


