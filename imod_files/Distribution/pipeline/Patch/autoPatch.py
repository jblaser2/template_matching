#!/usr/bin/python
# autoPatch.py - call etomo patch reconstruction
# add python exe path to PATH in .tcshrc
# 10/17/12
# last updates 11/05/12

import string
import os
import sys
import time

pr = 1 #print out all cmd

def logfilewrite(logfile,line):
    try:
        print (line)
        logfile.write(line+"\n")
        logfile.flush()
    except:
        print ("Error in writtng to logfile!!!: " + line)

def write_xcorr_pt(basename,patch_sizex,patch_sizey,patch_overlapx,patch_overlapy,patch_trimx,patch_trimy):
    fin = open("xcorr.com", "r")
    for line in fin:
        if line.find('RotationAngle') == 0:
            rotationangle = line
        if line.find('FilterSigma1') == 0:
            filtersigma1 = line
        if line.find('FilterRadius2') == 0:
            filterradius2 = line
        if line.find('FilterSigma2') == 0:
            filtersigma2 = line
    fin.close()

    
    f = open("xcorr_pt.com", "w")
    f.write("$tiltxcorr -StandardInput\n")
    f.write("TiltFile   "+basename+".rawtlt\n")
    f.write("InputFile  "+basename+".preali\n")
    f.write("OutputFile "+basename+".fid\n")
    f.write(rotationangle)
    f.write(filterradius2)
    f.write(filtersigma1)
    f.write(filtersigma2)
    f.write("BordersInXandY      "+patch_trimx+","+patch_trimy+"\n")
    f.write("SizeOfPatchesXandY      "+patch_sizex+","+patch_sizey+"\n")
    f.write("OverlapOfPatchesXandY   "+patch_overlapx+","+patch_overlapy+"\n")
    f.write("IterateCorrelations     1\n")
    f.write("PrealignmentTransformFile "+basename+".prexg\n")
    f.write("ImagesAreBinned 1\n")
    f.close()


def write_tilt(basename,thickness,dimx,dimy):
    f = open("tilt.com", "w")
    f.write("$tilt -StandardInput\n")
    f.write("InputProjections "+basename+".ali\n")
    f.write("OutputFile "+basename+"_full.rec\n")
    f.write("IMAGEBINNED 1\n")
    f.write("TILTFILE "+basename+".tlt\n")
    f.write("THICKNESS "+thickness+"\n")
    f.write("RADIAL 0.35 0.05\n")
    f.write("XAXISTILT 0.0\n")
    f.write("LOG 0.0\n")
    f.write("SCALE 0.0 700.0\n")
    f.write("PERPENDICULAR\n")
    f.write("MODE 1\n")
    f.write("FULLIMAGE "+dimx+" "+dimy+"\n")
    f.write("SUBSETSTART 0 0\n")
    f.write("AdjustOrigin\n")
    f.write("ActionIfGPUFails 1,2\n")
    f.write("OFFSET 0.0\n")
    f.write("SHIFT 0.0 0.0\n")
    f.write("XTILTFILE "+basename+".xtilt\n")
    f.write("$if (-e ./savework) ./savework\n")
    f.close()


def main():
    if len(sys.argv) <= 3:
        print ('Usage: 7 arguments accepted, first 3 required')
        print ('  autoPatch.py  basename binfactor thickness patch_sizex patch_sizey patch_overlap patch_trim ')
        print ('  default: autoPatch.py  basename binfactor thickness 250 250 0.16 50 ')
        print ('quit')
        sys.exit(1)

    basename = sys.argv[1]
    binfactor = int(sys.argv[2])
    thickness = sys.argv[3]    
    patch_sizex = "250"
    patch_sizey = "250"
    patch_overlapx = "0.16"
    patch_overlapy = "0.16"
    patch_trimx = "50"
    patch_trimy = "50"
    if len(sys.argv) > 4:
        patch_sizex = sys.argv[4]
    if len(sys.argv) > 5:
        patch_sizey = sys.argv[5]
    if len(sys.argv) > 6:
        patch_overlap = sys.argv[6]
    if len(sys.argv) > 7:
        patch_trim = sys.argv[7]

    filename = "autopatch.log"
    try:
        logfile = open(filename, 'w')
    except:
        print ("Error in creating logfile!!!: " + filename)
        return
    logs = time.strftime("%H:%M:%S",time.localtime())+" autoPatch "+basename+" start: size("+patch_sizex+","+patch_sizey+"), trim("+patch_trimx+","+patch_trimy+")"
    logfilewrite(logfile,logs)

    dimsresult = os.popen("header -size "+ basename + ".st")
    dimsline = dimsresult.read()
    dims = dimsline.split()
    if dims[0].isdigit()== False or dims[1].isdigit()== False:
        print ("Error: NOT RECOGNIZABLE AS MRC ", basename)
        logfilewrite(logfile,"Error in autoPatch: NOT RECOGNIZABLE AS MRC:"+basename+".st")
        print ('quit')
        sys.exit(1)
        
    dimx = dims[0]
    dimy = dims[1]
    if binfactor > 1:
        dimx = str(int(float(dims[0])/ binfactor))
        dimy = str(int(float(dims[1])/ binfactor))
        patch_sizex = str(int(float(patch_sizex)/ binfactor))
        patch_sizey = str(int(float(patch_sizey)/ binfactor))
        patch_trimx = str(int(float(patch_trimx)/ binfactor))
        patch_trimy = str(int(float(patch_trimy)/ binfactor))

    
    cmd = "autoStartIMOD.py "+basename
    os.system(cmd)
    logfilewrite(logfile,cmd)
    write_xcorr_pt(basename,patch_sizex,patch_sizey,patch_overlapx,patch_overlapy,patch_trimx,patch_trimy)
    cmd = "submfg xcorr_pt.com"
    os.system(cmd)
    logfilewrite(logfile,cmd)
    cmd = "autoAlign.py "+basename
    os.system(cmd)
    logfilewrite(logfile,cmd)
    cmd = "newstack -input "+basename+".st -output "+basename+".ali -size "+dimx+","+dimy+" -offset 0,0 -xform "+basename+".xf -origin -taper 1,0"
    os.system(cmd)
    logfilewrite(logfile,cmd)
    write_tilt(basename,thickness,dimx,dimy)
    cmd = "submfg tilt.com"
    os.system(cmd)
    logfilewrite(logfile,cmd)
    cmd = "trimvol -rx "+basename+"_full.rec "+basename+".rec"
    os.system(cmd)
    logfilewrite(logfile,cmd)
    logs = time.strftime("%H:%M:%S",time.localtime())+" Finished. "
    logfilewrite(logfile,logs)

main() 
