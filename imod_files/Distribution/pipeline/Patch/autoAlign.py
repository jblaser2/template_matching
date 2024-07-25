#!/usr/bin/python

import re
import os
import sys
import subprocess
from optparse import OptionParser
import automation

def write_alignCom(basename,width,height,rotationAngle):
    f = open("align.com", "w")
    f.write("# THIS IS A COMMAND FILE TO RUN TILTALIGN\n")
    f.write("#\n")
    f.write("####CreatedVersion#### 3.10.4\n")
    f.write("#\n")
    f.write("# To exclude views, add a line \"ExcludeList view_list\" with the list of views\n")
    f.write("#\n")
    f.write("# To specify sets of views to be grouped separately in automapping, add a line\n")
    f.write("# \"SeparateGroup view_list\" with the list of views, one line per group\n")
    f.write("#\n")
    f.write("$tiltalign -StandardInput\n")
    f.write("ModelFile	"+basename+".fid\n")
    f.write("ImageFile	"+basename+".preali\n")
    f.write("#ImageSizeXandY	"+str(width)+" "+str(height)+"\n")
    f.write("ImagesAreBinned	1\n")
    f.write("OutputModelFile	"+basename+".3dmod\n")
    f.write("OutputResidualFile	"+basename+".resid\n")
    f.write("OutputFidXYZFile	"+basename+"fid.xyz\n")
    f.write("OutputTiltFile	"+basename+".tlt\n")
    f.write("OutputXAxisTiltFile	"+basename+".xtilt\n")
    f.write("OutputTransformFile	"+basename+".tltxf\n")
    f.write("RotationAngle	"+str(rotationAngle)+"\n")
    f.write("# WROTE: RotationAngle	"+str(rotationAngle)+"\n")
    f.write("TiltFile	"+basename+".rawtlt\n")
    f.write("#\n")
    f.write("# ADD a recommended tilt angle change to the existing AngleOffset value\n")
    f.write("#\n")
    f.write("AngleOffset	0.0\n")
    f.write("RotOption	1\n")
    f.write("RotDefaultGrouping	5\n")
    f.write("#\n")
    f.write("# TiltOption 0 fixes tilts, 2 solves for all tilt angles; change to 5 to solve\n")
    f.write("# for fewer tilts by grouping views by the amount in TiltDefaultGrouping\n")
    f.write("#\n")
    f.write("TiltOption	5\n")
    f.write("TiltDefaultGrouping	5\n")
    f.write("MagReferenceView	1\n")
    f.write("MagOption	1\n")
    f.write("MagDefaultGrouping	4\n")
    f.write("#\n")
    f.write("# To solve for distortion, change both XStretchOption and SkewOption to 3;\n")
    f.write("# to solve for skew only leave XStretchOption at 0\n")
    f.write("#\n")
    f.write("XStretchOption	0\n")
    f.write("SkewOption	0\n")
    f.write("XStretchDefaultGrouping	7\n")
    f.write("SkewDefaultGrouping	11\n")
    f.write("# \n")
    f.write("# Criterion # of S.D's above mean residual to report (- for local mean)\n")
    f.write("#\n")
    f.write("ResidualReportCriterion	3.0\n")
    f.write("SurfacesToAnalyze	2\n")
    f.write("MetroFactor	0.25\n")
    f.write("MaximumCycles	100000\n")
    f.write("#\n")
    f.write("# ADD a recommended amount to shift up to the existing AxisZShift value\n")
    f.write("#\n")
    f.write("AxisZShift	0.0\n")
    f.write("#\n")
    f.write("# Set to 1 to do local alignments\n")
    f.write("#\n")
    f.write("LocalAlignments	0\n")
    f.write("OutputLocalFile	"+basename+"local.xf\n")
    f.write("#\n")
    f.write("# Target size of local patches to solve for in X and Y\n")
    f.write("#\n")
    f.write("TargetPatchSizeXandY	700,700\n")
    f.write("MinSizeOrOverlapXandY	0.5,0.5\n")
    f.write("#\n")
    f.write("# Minimum fiducials total and on one surface if two surfaces\n")
    f.write("#\n")
    f.write("MinFidsTotalAndEachSurface	8,3\n")
    f.write("FixXYZCoordinates	0\n")
    f.write("LocalOutputOptions	1,0,1\n")
    f.write("LocalRotOption	3\n")
    f.write("LocalRotDefaultGrouping	6\n")
    f.write("LocalTiltOption	5\n")
    f.write("LocalTiltDefaultGrouping	6\n")
    f.write("LocalMagReferenceView	1\n")
    f.write("LocalMagOption	3\n")
    f.write("LocalMagDefaultGrouping	7\n")
    f.write("LocalXStretchOption	0\n")
    f.write("LocalXStretchDefaultGrouping	7\n")
    f.write("LocalSkewOption	0\n")
    f.write("LocalSkewDefaultGrouping	11\n")
    f.write("BeamTiltOption	0\n")
    f.write("#\n")
    f.write("# COMBINE TILT TRANSFORMS WITH PREALIGNMENT TRANSFORMS\n")
    f.write("#\n")
    f.write("$xfproduct -StandardInput\n")
    f.write("InputFile1	"+basename+".prexg\n")
    f.write("InputFile2	"+basename+".tltxf\n")
    f.write("OutputFile	"+basename+"_fid.xf\n")
    f.write("$b3dcopy -p "+basename+"_fid.xf "+basename+".xf\n")
    f.write("$b3dcopy -p "+basename+".tlt "+basename+"_fid.tlt\n")
    f.write("#\n")
    f.write("# CONVERT RESIDUAL FILE TO MODEL\n")
    f.write("#\n")
    f.write("$if (-e "+basename+".resid) patch2imod -s 10 "+basename+".resid "+basename+".resmod\n")
    f.write("$if (-e ./savework) ./savework\n")
    f.close()

def getRotationAngle(inputStack):
    size_re = re.compile("\s+Tilt axis rotation angle =\s+([\-\.0-9]+)")
    commands   = ['header', inputStack]
    try:
        process = subprocess.Popen(commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except:
        sys.stderr.write("ERROR: executing 'header': is it installed?\n")
        sys.exit(1)
    stdout, stderr = process.communicate()
    #lines = stdout.rsplit("\n")
    try:
        stdout1 = str(stdout, 'utf-8')
    except:
        stdout1 = stdout
    lines = stdout1.rsplit("\n")
    for line in lines:
        m = size_re.search(line)
        if m:
            return m.group(1)
    sys.stderr.write("1: Couldn't determine stack size when running 'header "+inputStack+"'!\n")
    sys.exit(1)

def getStackSize(inputStack):
    size_re = re.compile("\s+Number of columns, rows, sections .....\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)")

    commands   = ['header', inputStack]
    try:
        process = subprocess.Popen(commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except:
        sys.stderr.write("ERROR: executing 'header': is it installed?\n")
        sys.exit(1)
    stdout, stderr = process.communicate()
    #lines = stdout.rsplit("\n")
    try:
        stdout1 = str(stdout, 'utf-8')
    except:
        stdout1 = stdout
    lines = stdout1.rsplit("\n")
    for line in lines:
        m = size_re.search(line)
        if m:
            return [m.group(1),m.group(2)]
    sys.stderr.write("2: Couldn't determine stack size when running 'header "+inputStack+"'!\n")
    sys.exit(1)

def main():
    parser = OptionParser("usage: %prog <basename>")
    (options,args) = parser.parse_args()
    if len(args) != 1:
        parser.error("Incorrect number of parameters!\n")
        sys.exit(1)
    basename     = args[0]

    rotationAngle = getRotationAngle(basename+".st")

    # --------

    if automation.make([basename+".xf"], [basename+".fid",basename+".preali"]):
        width,height = getStackSize(basename+".preali")
        write_alignCom(basename, width, height, rotationAngle)
        automation.execute(["submfg", "align.com"])

main()

