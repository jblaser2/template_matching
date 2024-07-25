#!/usr/bin/python
# db3_start.py - script for starting Pipeline3. takes .ini file and data directory as inputs, create 
# db3_start.py <this file>  <data directory>
# created 06/30/2020, last modified 08/06/2020
# modified 09/10/2020: add fise-tilt handling, remove pbs option; 9/21: add movie-mode
# 10/02/2020: move pre-processing to _proc
# 03/18/2021: add eman2, v2021-04-10
# 05/17/2021: added skipframe for CDS movies
# 07/29/2021: moved gain reference check to .ini. now same types for movie mode and fise

import string
import os
import sys
import ntpath
import db3_inc

thisversion = "v2021-04-10"
pr = 0
exe = 1

machinename = os.uname()[1]
if len(sys.argv) <= 2:
    print ('Tomography Pipeline3: automatic processing tomographic data and uploading into the Tomography Database')
    print ('Version '+thisversion)
    print ('you are using '+machinename)
    print ('Usage: at least 2 arguments required. 3rd one is optional.')
    print ('  runpipeline <initial file generated from database website>  <raw data directory>  -option')
    print ('    option: fise or movies')
    print ('    raw data directory should be full path starting with / containing...')
    print ('        raw tilt series .mrc or *.st, for regular collection')
    print ('        frame files *tif, *.tif.angles, *tif.mdoc, *_saved.txt, and gain reference, for FISE collection')
    print ('        *mrc.mdoc files, for movie-mode collection, with *tif frame files and gain reference under the same directory or subdir "Movies"')
    print ('')
    print ('  e.g.,  runpipeline  /home/hding/data/pipeline-2018-10-20.ini  /jscope/Jane/2020-06-20/')
    print ('         runpipeline  /home/hding/data/pipeline-2018-10-20.ini  /jscope/Jane/2020-06-20/  -fise')
    print ('         runpipeline  /home/hding/data/pipeline-2018-10-20.ini  /jscope/Jane/2020-06-20/  -movies')
    print ('    if movies are collected in the K3 CDS mode, use options below to skip the initial bad frame:')
    print ('         runpipeline  /home/hding/data/pipeline-2018-10-20.ini  /jscope/Jane/2020-06-20/  -movies  -skip')
    print ('         runpipeline  /home/hding/data/rerun-2018-10-20-1.ini  -rerun')
    print ('  alias runpipeline="db3_start.py"')
    print ('Quit')
    sys.exit(0)

moviemode = '0'
skip = '0'
if len(sys.argv) >= 4:
    if '-fise' in sys.argv[3] or '-FISE' in sys.argv[3]:
        moviemode = 'fise'
        print ('FISE collection')
    elif '-movie' in sys.argv[3] or '-MOVIE' in sys.argv[3]:
        moviemode = 'movies'
        print ('Movie-mode collection')
    else:
        print ('!! Not a valid option:', sys.argv[3], '. Quit.')
        sys.exit(1)
if len(sys.argv) == 5:
    if '-skip' in sys.argv[4]:
        skip = '1'
        print ('Skip 1st CDS frame')
    
if len(sys.argv) == 3:
    if '-rerun' in sys.argv[2]:
        moviemode = 'rerun'
        print ('RERUN')

# check basic permissions. some will be checked again in db3_proc.py
ini_file = sys.argv[1]
try:
    inputs = open(ini_file, 'r')
except:
    print ('Pipeline Error! can not open pipeline initial file: '+ini_file+' . Quit.')
    sys.exit(1)

# check directory existance and permissions
if moviemode != 'rerun':
    inputdir = sys.argv[2].strip()
    if not os.path.exists(inputdir):
        print ('Pipeline Error! can not find data directory: '+inputdir+' . Please double check. Quit.')
        sys.exit(1)
    if not inputdir.startswith('/'):
        print ('Pipeline Error! you must use full path for the data directory. "'+inputdir+'" is not accepted. Please correct. Quit.')
        sys.exit(1)

    cmd = "mkdir -p "+inputdir+"/Done" 
    if os.system(cmd) != 0:
        print ('Pipeline Error! Failed to create directory: '+cmd+' . Please contact your admin. Quit.')
        sys.exit(1)

outputdir = os.path.expanduser('~') + '/Pipeline_Proc'
cmd = 'mkdir -p ' + outputdir
if os.system(cmd) != 0:
    print ('Pipeline Error! Failed to create directory: '+cmd+' . Please contact your admin. Quit.')
    sys.exit(1)


if moviemode == 'fise' or moviemode == 'movies':
    cmd = "mkdir -p "+inputdir+"/PreProcessing" 
    if os.system(cmd) != 0:
        print ('Pipeline Error! Failed to create directory: '+cmd+' . Please contact your admin. Quit.')
        sys.exit(1)

#check gain reference
if moviemode == 'fise':
    reffile = db3_inc.checkgainref(inputdir)
    if reffile == '':
        print ('Pipeline Error! you must have a gain reference file .dm4 or CountCDSRef*mrc or CountRef*mrc under the data directory. "'+inputdir+'" . Quit.')
        sys.exit(1)

if moviemode == 'movies':
    reffile = db3_inc.checkgainref(inputdir)
    if reffile == '':
        if os.path.exists(inputdir+'/Movies'):
            reffile = db3_inc.checkgainref(inputdir+'/Movies')
        if reffile == '':
            if os.path.exists(inputdir+'/movies'):
                reffile = db3_inc.checkgainref(inputdir+'/movies')
    if reffile == '':
        print ('Pipeline Error! you must have a gain reference file .dm4 or CountCDSRef*mrc or CountRef*mrc under the data directory "'+inputdir+'" or subdirectory "movies" or "Movies". Quit.')
        sys.exit(1)
    
# generating sbatch job file
inipath, inifile = os.path.split(ini_file)

jobfile = outputdir + '/' + inifile + '.job'
jobname = 'Pipeline-'+inifile.split('.')[0]
qq = open(jobfile, 'w')
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
qq.write('####################################' +'\n')
qq.write('#ADD HEADER ABOVE' +'\n')
qq.write('####################################' +'\n')
qq.write('' +'\n')

if moviemode == 'rerun':
    startcopy = 0
    pp = open(ini_file, 'r')
    for line in pp:
        line = line.strip()
        if startcopy:
            qq.write(line +'\n')
        if 'END tiltseries' in line:
            startcopy = 1
    pp.close()

    qq.write('' +'\n')
    qq.write('####################################' +'\n')
    qq.write('#ADD CALL BELOW' +'\n')
    qq.write('####################################' +'\n')
    qq.write('exepath="'+db3_inc.exepath+'"' +'\n')
    qq.write('INIFILE="'+ ini_file +'"' +'\n')
    qq.write('' +'\n')
    qq.write('$exepath/db3_rerun.py  --exe $exe --serverip $serverip --userid $userid --defocus $defocus --pixelsizetilt $pixelsizetilt --markers $markers --binfactor $binfactor --diameter $diameter --thickness $thickness --useremail $useremail --keepali $keepali --recon $recon --seq1 $seq1 --seq2 $seq2 --seq3 $seq3 --patchx $patchx --patchy $patchy --patchoverlap $patchoverlap --patchtrim $patchtrim --eman2bin $eman2bin --eman2markers $eman2markers --eman2boxsize $eman2boxsize --changedatatype $changedatatype --orientation $orientation --pr $pr --keepall $keepall --tiltconstant $tiltconstant --inifile $INIFILE --exepath $exepath --version $version' +'\n')
else:
    pp = open(ini_file, 'r')
    for line in pp:
        line = line.strip()
        qq.write(line +'\n')
    pp.close()

    qq.write('' +'\n')
    qq.write('####################################' +'\n')
    qq.write('#ADD CALL BELOW' +'\n')
    qq.write('####################################' +'\n')
    qq.write('exepath="'+db3_inc.exepath+'"' +'\n')
    qq.write('INPUTDIR="'+ inputdir +'"' +'\n')
    qq.write('moviemode="'+ moviemode +'"' +'\n')
    qq.write('skipframe="'+ skip +'"' +'\n')
    qq.write('' +'\n')
    qq.write('$exepath/db3_proc.py  --exe $exe --serverip $serverip --userid $userid --inputdir $INPUTDIR --tomodate $tomodate --tiltmin $tiltmin --tiltmax $tiltmax --tiltstep $tiltstep --dosage $dosage --defocus $defocus --softwareacquisition "$softwareacquisition" --magnification $magnification --pixelsizetilt $pixelsizetilt --markers $markers --binfactor $binfactor --diameter $diameter --thickness $thickness --wait $wait --useremail $useremail --keepali $keepali --recon $recon --seq1 $seq1 --seq2 $seq2 --seq3 $seq3 --patchx $patchx --patchy $patchy --patchoverlap $patchoverlap --patchtrim $patchtrim --eman2bin $eman2bin --eman2markers $eman2markers --eman2boxsize $eman2boxsize --changedatatype $changedatatype --orientation $orientation  --singledual $singledual --scope "$scope" --pr $pr --keepall $keepall --tiltconstant $tiltconstant --moviemode $moviemode --skipframe $skipframe --specieid $specie_id --titlemain "$titlemain" --notes "$notes" --collaborators "$collaborators" --treatment "$treatment" --sampleprep "$sampleprep" --exepath $exepath --version $version' +'\n')

qq.close()

cmd = 'sbatch ' + jobfile 
if exe == 1:
    os.system(cmd)
    print("Done " + cmd)
else:
    print("Test: " + cmd)
