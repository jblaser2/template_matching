#!/usr/bin.python
#
#
# Module to automate reconstruction
#

import sys
import subprocess
import re
import os

def make(outputFiles,dependencyFiles, verbose=True):
    # Returns true if any of the output files don't exist or are
    # older than any of the dependency files
    for dependencyFile in dependencyFiles:
        if not os.path.exists(dependencyFile):
            sys.stderr.write("ERROR: Required file "+dependencyFile+" not found! Aborting!\n")
            sys.exit(1)
    for outputFile in outputFiles:
        if not os.path.exists(outputFile):
            if verbose:
                sys.stdout.write("Need to make "+" ".join(outputFiles)+"\n")
            return True
        for dependencyFile in dependencyFiles:
            print ("Found "+dependencyFile)
            if os.path.getmtime(outputFile) < os.path.getmtime(dependencyFile):
                if verbose:
                    sys.stdout.write("Need to make "+" ".join(outputFiles)+"\n")
                return True
    if verbose:
        sys.stdout.write("No need to make "+" ".join(outputFiles)+"\n")
    return False

def execute(commands):
    #
    # Run external commands and quit on error
    #
    error_re = re.compile("ERROR")
    process  = subprocess.Popen(commands, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sys.stdout.write("-------------------------------------------\n")
    sys.stdout.write("Running command '"+" ".join(commands)+"'...\n")
    stdout, stderr = process.communicate()
    sys.stdout.write(stdout)
    sys.stderr.write(stderr)
    if process.returncode != 0:
        sys.stderr.write("ERROR! Aborting!!\n")
        sys.exit(1)

    lines = stdout.split("\n")
    for line in lines:
        m = error_re.search(line)
        if m:
            sys.stderr.write("ERROR MESSAGE DETECTED IN STDOUT! Aborting!!\n")
            sys.exit(1)

    sys.stdout.write("Completed OK.\n")
    return (stderr,stdout)
