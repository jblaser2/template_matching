The Caltech Tomography Database & Automatic Processing Pipeline
User Guide
written by H. Jane Ding  
last update 2021-11-5
Contact: Grant Jensen at caltech.edu

===================================================================================
PUBLICATION:
Ding H.J., Oikonomoua C.M., Jensen G.J.  "The Caltech Tomography Database and Automatic Processing Pipeline",  Journal of Structural Biology (2015)

DISCLAIMER
This software package is intended for research purpose only

This document contains following topics:

- Using Tomography Database
- Uploading Data Through Auto Processing Pipeline
- "Rerun Reconstruction" from Inbox or Workbox


===================================================================================
USING TOMOGRAPHY DATABASE (DB)


  USAGE
    The Tomography Database is MySQL-based and can be accessed through a web browser.     

    Most functions are straightforward for users such as Browse, Search, and Edit.

    Snapshots are automatically imported through "Grab with Notes" IMOD plugin (after
    grabDatabase.ini is configured).

  MANUAL UPLOAD
    when an user uploads new files through a browser, the file names (and other associated
    parameters) are recorded in MySQL but the actual files (usually big) are not uploaded.
    Instead, a script is generated and the user needs to run it in a terminal to actually
    upload the files. The script consists "mkdir" and "rsync" commands for file transfer.
    Database data directory must be mountd on user's computer. If the automatic processing 
    pipeline is used then the above steps are taken care automatically.
    

  WORKBOX
    Workboxes are designed for organizing projects. A workbox list may contain any user's 
    data. Deleting a dataset from a workbox list or deleting a workbox does not delete
    the files from the database.

  INBOX
    If running Processing Pipeline, the result will be under user's Inbox. After deleting
    unwanted data, use "Accept in Database" or "Accept in Database & Add to Workbox List"    
    to move the "good" data out of Inbox.


===================================================================================
UPLOADING DATA THROUGH AUTO PROCESSING PIPELINE

The Pipeline is used for automatically processing and uploading a collection of tilt series 
from a microscope session.

1. Data Input Requirements:
     Raw data files from the same data collection session should be put under one
     directory on the processing computer (local or mounted drives). The pipeline
     will create a folder named "Done" under the raw data directory, and the raw 
     data will be moved to "Done" after being processed.

     Raw data input directory should contain:
     - for regular data collection: raw tilt series *.mrc or *.st (*mrc.mdoc are optional)
     - for movie mode collection: *mrc.mdoc files, *tif frame files, and gain reference
     - for FISE collection: frame files *tif, *.tif.angles, *tif.mdoc,  *_saved.txt, and gain reference                          
gain reference must be in the format of *.dm4 or CountCDSRef*.mrc or CountRef*.mrc


2. Steps For Using Pipeline

  (1) create a pipeline initial file from the Tomography Database (the link can be found at the
     Database Help webpage). Download the .ini file and put it on the pipeline processing computer.

  (2) on the processing computer, start the pipeline by

      runpipeline  '.ini file'  'raw data directory'  -option
      ("runpipeline" is an alias to <pipeline code>/db3_start.py, which can be set by your admin)
      running "runpipeline" without any parameter will list the menu.

      Below are examples on starting pipeline for data collected in regular mode,
      movie mode, or FISE:
           runpipeline  /xxxx/pipeline-jdh-2020-09-28.ini  /jscope/Jane/2020-09-28/
           runpipeline  /xxxx/pipeline-jdh-2020-09-28.ini  /jscope/Jane/2020-09-28/ -movies
           runpipeline  /xxxx/pipeline-jdh-2020-09-28.ini  /jscope/Jane/2020-09-28/ -fise
      if movies are collected in the K3 CDS mode, use options below to skip the initial bad frame:
           runpipeline  /xxxx/pipeline-jd-2020-09-28.ini  /jscope/Jane/2020-09-28/ -movies -skip

      You may check what jobs of yours are running by normal SLURM commands, such as squeue and sinfo.
      You don't have to keep login to the processing computer once the pipeline starts. You can view 
      processed data at your database Inbox. You will be notified by email when the pipeline finishes.    

  (3) clean up after pipeline is finished

      After a tilt series is processed, the raw data files will be moved to 'raw data directory'/Done.

      For a Movie mode or FISE collection: only aligned *mrc files and reconstructions will be      
      uploaded, not the *tif frame files.

      The pipeline log files are placed under the folder "Pipeline_Proc" of your home directory.
      They are for debugging purpose. If your pipeline failed unexpectedly, your admin can check
      the log files. If your pipeline run is successful, all the log files/directories under 
      "Pipeline_Proc" can be deleted.


===================================================================================
"RERUN RECONSTRUCTION" FROM INBOX OR WORKBOX

You may rerun reconstruction (e.g., you initially ran a Pipeline with Raptor and now you would like to use EMAN2) for a collection of tilt series which have the same defocus value and pixel size. "Rerun Reconstruction" function from Inbox or Workbox will let you choose reconstruction option and parameters, and generate a rerun initial file. Download the .ini file and put it on the processing computer.


Start a batch rerun on the processing computer by

     runpipeline  '.ini file'  -rerun
     e.g.,
     runpipeline  /xxxx/rerun-jdh-2020-09-28.ini  -rerun


Rerun will not remove any existing reconstruction from the database.


===================================================================================
