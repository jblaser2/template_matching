#!/usr/bin/python

import re
import os
import sys
import subprocess
from optparse import OptionParser

def write_eraser(basename):
    f = open("eraser.com", "w")
    f.write("$ccderaser -StandardInput\n")
    f.write("InputFile	"+basename+".st\n")
    f.write("OutputFile	"+basename+"_fixed.st\n")
    f.write("FindPeaks	\n")
    f.write("PeakCriterion	10.\n")
    f.write("DiffCriterion	8.\n")
    f.write("GrowCriterion	4.\n")
    f.write("EdgeExclusionWidth	4\n")
    f.write("PointModel	"+basename+"_peak.mod\n")
    f.write("MaximumRadius	3.6\n")
    f.write("AnnulusWidth	2.0\n")
    f.write("XYScanSize	100\n")
    f.write("ScanCriterion	3.\n")
    f.write("BorderSize	2\n")
    f.write("PolynomialOrder	2\n")
    f.close()

def write_xcorr(basename):
    f = open("xcorr.com", "w")
    f.write("$tiltxcorr -StandardInput\n")
    f.write("InputFile	"+basename+".st\n")
    f.write("OutputFile	"+basename+".prexf\n")
    f.write("TiltFile	"+basename+".rawtlt\n")
    f.write("RotationAngle	0.0\n")
    f.write("FilterSigma1	0.03\n")
    f.write("FilterRadius2	0.25\n")
    f.write("FilterSigma2	0.05\n")
    f.write("$if (-e ./savework) ./savework\n")
    f.close()

def write_prenewst(basename):
    f = open("prenewst.com", "w")
    f.write("$xftoxg\n")
    f.write("0	global fit\n")
    f.write(basename+".prexf\n")
    f.write(basename+".prexg\n")
    f.write("$newstack -fl 2 -xf "+basename+".prexg "+basename+".st "+basename+".preali\n")
    f.write("$if (-e ./savework) ./savework\n")
    f.close()

def main():
    parser = OptionParser("usage: %prog <basename>")
    (options,args) = parser.parse_args()
    if len(args) != 1:
        parser.error("Incorrect number of parameters!\n")
        sys.exit(1)
    basename   = args[0]

    # --------

    cmd = "extracttilts "+basename+".st "+basename+".rawtlt"
    os.system(cmd)
    print("autoStartIMOD:", cmd)
    write_eraser(basename)
    os.system("submfg eraser.com")
    write_xcorr(basename)
    os.system("submfg xcorr.com")
    write_prenewst(basename)
    os.system("submfg prenewst.com")
    os.system("rm *_fixed.st")


main()

   
