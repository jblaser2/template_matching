The Caltech Tomography Database & Automatic Processing Pipeline
Admin Guide
v2021.04.10
written by H. Jane Ding  
last update 2021-11-4
Contact: Grant Jensen at caltech.edu

===================================================================================
PUBLICATION:
Ding H.J., Oikonomoua C.M., Jensen G.J.  "The Caltech Tomography Database and Automatic Processing Pipeline", Journal of Structural Biology (2015)

DISCLAIMER
This software package is intended for research purpose only

===================================================================================

Package download: http://www.jensen.caltech.edu/Clipboard/jane/DATABASE/
It contains the following files:

README_ADMIN_GUIDE.txt (this file)
README_USER_GUIDE.txt
tomography.sql.gz  (MySQL database structure)
tomography  (directory, tomography database web php code)
pipeline  (directory, processing pipeline python code)
ffmpeg  (directory, instruction and saple for installing ffmpeg)
RAPTOR.tgz  (zipped directory, code for compling customized RAPTOR)
grabDatabase.ini (IMOD 'Grab with Notes' plugin config file)
AdminTools (directory)


This document contains following topics:
- General Setup / Requirements
- Database Setup
- Pipeline Setup
- Data Input Requirements
- Back up
- Admin Tools & Notes
- "Grab with Notes" IMOD plugin

===================================================================================
GENERAL SETUP / REQUIREMENTS

1. Equipment Requirements:

You will need two computers with Linux OS, one as SERVER COMPUTER (for
http / MySQL servers) and another as PROCESSING COMPUTER (for pipeline
and other Python scripts).

You will also need a disk array big enough for storing all your tomographic data.

The server computer does not have to be extremely powerful as long as
it can run http server and MySQL server. Faster processors can increase
the speed of searching/browsing.

The processing computer should be powerful enough to run multiple reconstruction
software (e.g., RAPTOR, EMAN2). 128Gb or more of memory is recommended.

All code are tested on linux RHEL7 and CentOS8, and expected to work
on other linux systems as well.


2. Disk Space & Permission Setup

Set up enough disk space for storing all your tomographic data. The
drive must be visible to both server computer and processing computer.
It should be also visible for lab members' computers so that they
can open files from the disk directly without downloading them,
or uploading additional files when needed. (e.g. mount as /jdatabase/data/
on all computers, we will refer this as DATA DIRECTORY below.)
This will be where the actual image files (tilt series, reconstructions,
key images, movies, etc) are hosted.

The Data Directory will contain subdirectories with the same names as
the tilt series IDs in the DB, they are created by the Pipeline or
scripts automatically and they will look like:
    
            abd2012-05-15-1
            mdc2011-08-04-1
            mdc2011-08-04-2
            ......

File ownership/permission: files under the Data Directory (/jdatabase/data/)
are owned by the individual users who uploaded them (by running the Pipeline
or uploading scripts).

(1) * mount /jdatabase/data/ on both server computer and processing computer.

(2) * Data Directory (/jdatabase/data/) should be writable for all users who
upload files.

(3) * create subdirectory "Caps" under Data Directory (e.g., /jdatabase/data/Caps/)
and make it writable for all users. This is for holding the snapshots from IMOD
"Grab with Notes" plugin.


3. Web (HTTP) Servers & Security

General users will access the database through web browsers. For convenience,
the database code itself does not enforce strict security. It does not require
a login. Everyone who can browse the database can edit notes or mark data as
"delete" (the data owner will receive an email notification when his/her data
is flagged as "delete"). Thus, the database website should be restricted to
authorized users only through the web server setting (e.g., with .htpasswd).

You may wish to share web links to certain data files with collaborators without
giving them full permission to browse/edit the entire DB. So we set the
separated web paths to the DB display and file sharing.

You may choose to use only one web/http server. In our case, we used two
separated servers in order to handle security as well as easy data sharing.
One is the main web server (e.g., yourdomain.com) for the database
main display (password protected); another (e.g., yourdatadomain.com or
data.yourdomain.com) points to the Data Directory (/jdatabase/data/) with
no password so individual file URL can be shared with collaborators (who
have no access to the database but can download the shared files). For
better security, no directory itself should be readable to public, while
all individual files should be set readable.


4. MySQL server

The MySQL server can be hosted on the same computer as the web server.

you will need a way for MySQL administration, e.g., install phpMyAdmin
or other tools, or use MySQL commands

A text file, tables.txt, is located under the web code directory, which
lists all MySQL tales in details.


===================================================================================
TOMOGRAPHY DATABASE (DB) SETUP
On Server Computer

The database front-end is written in PHP (code is written PHP7 compatible,
tested on PHP5.4.) The back-end uses MySQL (tested on version 5.6).

  INSTALLATION
  - Pre-install
    * set up 2 - 4 mentioned in above section.

  - Database web (php) code
    * unzip tomography.tgz. it contains a directory named "tomography".
    put the directory "tomography" under your web server. this is your DB web directory  
    (main file: index.php). Make sure the sub-directories "tmp" and "workbox"
    are writable for all users

    The database display can be viewed by a browser at  <yourdomain.com>/tomography
    

  - Database structure (MySQL)
    * import tomography.sql.gz into MySQL (e.g., import through phpMyAdmin) to
    create a database with the name "tomography". (note: the MySQL DB name
    must be kept as "tomography")

  - Configuration
    modify the following php files to reflect your local settings:
    (1) Private/msql_ini.php
        * move this file to a location not visible to web, e.g., to /var/www/Private/msql_ini.php
        * input MySQL DB login information to the file
    (2) in msql_connect.php
        * modify the path to msql_ini.php in msql_connect.php
    (3) in msql_db.php:
        * setup the following paths in msql_db.php:
          $dbpath:  Data Directory (e.g., /jdatabase/data/), it should be the location where
                    the real data files will be located as seen on processing computers,
                    server computer, and users' own computers. this variable is used for  
                    generating uploading scripts as well as for Pipeline processing
          $webpath: the web address pointing to $dbpath (Data Directory.
                    e.g., http://yourdatadomain.com or http://data.yourdomain.com)
          $keypath and $moviepath: should be as same as $webpath
          also modify the following accordingly:
          $date_start (earliest data date), $year_start, $adminemail, $pagetitle, $pagefooter.


  PRE-SETTING
  - after installation, before inputting any tomographic data to the DB, several
    things need to be manually input in MySQL structure (use phpMyAdmin, for example)

    (1) * Add Groups and Users
     Groups and Users have to be manually added (using phpMyAdmin, for example). the tables are
     already in the DB, groups and users need to be added BEFORE the database can be used

     Note: although GroupData can be recorded, currently in the web display code
     there is no filter for different groups.

     Please leave all "auto" fields empty.

        GroupData
        ----------------
        DEF_id (auto)
        DEF_timestamp (auto)
        name [text] (no space in the name, e.g., jensen)
        description [text] (some text, optional)

        UserData
        ----------------
        DEF_id (auto)
        DEF_timestamp (auto)
        username [text] (e.g. johnd, no space in the name. this should  be same as
                     the username of the person's account on the processing machine)
        fullname [text] (e.g. John Doe)
        var [text]      (must be 3 LETTERS, e.g., jdh, then all tilt series IDs for John Doe
                         will have the format like jdh2018-05-15-11. NOTE: no two users
                         should use the same "var" )
        email [text]    (used for deletion notifications when a file is deleted by
                         using database's delete function. It should be the email
                 of the active lab member, and change to admin's email address
                         after the member leaves the lab/group)
        count [int(15)] (auto. temporary record of tilt count)
        REF|GroupData|group [text]  (group id number, i.e., DEF_id in GroupData, e.g., 1)

    (2) * Add Microscope
        manually add microscopes, e.g, "Krios", "Caltech Polara", "UCLA Titan", etc.

        ScopeData
        ----------------
        DEF_id (auto)
        DEF_timestamp (auto)
        scopename [text]
        TXT_notes [text]

    (3) * Add Acquisition Software
        manually add acquisition software, e.g, "Seriel EM", "UCSF Tomo", "FEI Tomo", etc.

        AcquisitionData
        ----------------
        DEF_id (auto)
        DEF_timestamp (auto)
        acquisitionname [text]
        TXT_notes [text]


    The following items can be added through a browser on HELP page of the database display:

    (4) * Add Species/Specimen
        Species/Specimen can be added through browser. link can be found on DB's Help page.
        e.g.
        Species/Specimen Name: Caulobacter crescentus  (required)
        Strain Name: NA1000 (optional)
        Taxonomy ID: 565050 (optional)

    (5) lists of Features and Publications also need to be added before
        the features can be used. links can be seen on DB's Help page

    Now your database is ready to use! You may upload your tomographic data (tilt series
    and reconstruction) to the database by using "UPLOAD" function without setting up
    the auto-processing pipeline (below).

===================================================================================
If you have done above steps, your database is ready to use. You may upload data
to it manually, and use browse/search/workbox, etc..

The instructions below are for setting up an auto-processing Pipeline which
will automatically produce reconstructions from raw data and input them
(both tilt series and reconstructions) into the database.

===================================================================================
PIPELINE SETUP
On Processing Computer

The auto-processing Pipeline is written in Python (tested with Python2 & 3). The installation
of the Pipeline code itself is trivial, but it requires several other software packages
to be installed.


  INSTALLATION
  - Pre-install
    (1) * mount Data Directory (e.g., /jdatabase/data/)
        /jdatabase/data/ should be writable for all users of Pipeline on the processing computer.
    (2) * install SLURM workload manager on the processing computer,
        and set up a limit for how many jobs allowed to run simultaneously.
        Recommend to set the limit as 8 if the computer has 128Gb of memory.
    The number should not be less than 4.
    (3) * install Python/MySQLdb

    The following packages are for 3D reconstructions
    (4) * install IMOD (https://bio3d.colorado.edu/imod/)
        * replace RAPTOR which comes with IMOD with a customized one
      (unzip and compile RAPTOR from the included RAPTOR.tgz, and
      replace the RAPTOR under IMOD/bin/ with the newly compiled RAPTOR)
    (5) * install EMAN2 (https://blake.bcm.edu/emanwiki/EMAN2/Install)

    The following packages are for making key images and movies
    (6) * install convert (it's a function of ImageMagick,
                           can install ImageMagick via yum, for example)
    (7) * install mencoder (MPlayer includes mencoder)
    (8) * install ffmpeg - must be compiled with H.264 video encoder and must
          have mp4 support. please read ffmpeg/README-ffmpeg.txt for instructions
          on installation and testing

  - Install/Setup
    * unzip pipeline.tgz somewhere on the pipeline processing computer(s)
      (e.g. under /software/pipeline/ )
      It contains the following items:

           db3_inc.py  - pipeline variables and functions definitions
           db3_start.py - lunching new pipeline or re-run  
           db3_proc.py - pipeline main loop over new tilt series
           db3_rerun.py - main loop for rerun reconstructions on tilt series already in DB
           db3_procone.py - pipeline individual tilt series processing
           dirTemplate.adoc - used for IMOD's Batchruntomo and automatic fiducial seeding and tracking
           Patch (directory) - code for patch reconstruction (it does not
                           give high quality reconstruction but usually
                           will produce at least a reconstruction if RAPTOR fails)
       jpath.shrc - sample PATH setting file (optional)

  - Configuration
    (1) PATH and LD_LIBRARY_PATH
        * PATH variable $IMOD_DIR must be defined
        If IMOD is installed with the default location, $IMOD_DIR should be already
          defined automatically at /usr/local/IMOD/ . If it is installed at a
          different location, $IMOD_DIR needs to be defined to the location
          (e.g., /software/IMOD)

    * The following software/packages must be in users' PATH:
      - $IMOD_DIR/bin
      - EMAN2's executable bin
      - convert
      - mencoder
      - ffmpeg

      If you would like to add these paths only when running the pipeline, you may
      set them in a file specified during the pipeline setup (see jpath.shrc below)

    (2) * modify the sample jpath.shrc (under the pipeline code directory) if some of
    the paths mentioned above are not already in users' PATH
      
    (3) * modify db3_inc.py with your local settings  
        in db3_inc.py, please go through the configuration part and modify ALL items
    according to your local settings.

  - Shortcut
    It is recommended you set up a shortcut "runpipeline" pointing to db3_start.py.
    e.g., make an alias runpipeline='/software/pipeline/db3_start.py'
    Users will call "runpipeline" to start the pipeline.
    

===================================================================================
DATA INPUT REQUIREMENTS FOR PIPELINE

Raw data files from the same data collection session should be put under one directory
on the processing computer (local or mounted drives). It is important this directory
is readable and writable for all pipeline users. For example, if the raw data is under
raw data directory, /jscope/Jane/2020-09-28/ , the Pipeline will create a subfolder
"Done", and the raw data will be moved tob/jscope/Jane/2021-10-31/Done/ after
being processed.

Raw data input directory should contain:
     - for regular data collection: raw tilt series *.mrc or *.st (*mrc.mdoc are optional)
     - for movie mode collection: *mrc.mdoc files, *tif frame files, and gain reference
     - for FISE collection (FISE processing must be installed on processing computer): 
             frame files *tif, *.tif.angles, *tif.mdoc, *_saved.txt, and gain reference
gain reference must be in the format of *.dm4 or CountCDSRef*.mrc or CountRef*.mrc

The pipeline has been tested with regular data collected by Seriel EM and UCSFTomo,
as well as movie mode data collected by Seriel EM.

For a real-time session, currently the code has been tested for Seriel EM collection
with live data being transferred by Robocopy from Windows to Linux. Minor modifications
on how to detect completion of a tilt series may be needed if used with a different
acquisition software/method (modify function "checkfile" in db3_proc.py).


===================================================================================
If you have done above steps, your Pipeline is ready to use.
Please refer README_USER_GUIDE.txt for the usage.

Pipeline logs are located under "Pipeline_Proc" under user's home directory.
Related temporary logs will remain there for diagnosis if the pipeline fails.
It is recommended to clean up the old log files periodically. If a process is
successful, the corresponding temporary directories will be automatically deleted.

If you decide to use the Pipeline/database after running some tests, please read below.


===================================================================================
BACK UP

The database package does not include any backup function. You shall set up
your own back up of MySQL database, entire data directory (e.g., /jdatabase/data), 
and workbox files (<web code directory>/workbox/ ).


===================================================================================
ADMIN TOOLS & NOTES

Some additional Python scripts for admin are available:
(1) generate key images/movies if data is uploaded manually.
(2) cleanly remove related DB records and files for datasets marked as "delete".

Please see README-ADMINTOOLS.txt under "AdminTools".
       


===================================================================================
"Grab with Notes" IMOD plugin

The plugin allows user to grab a screenshot in 3dmod (Zap or Slicer), add some notes, and directly save into the database.

1. install IMOD 4.7.0 or later.

2. modify grabDatabase.ini (comes with the pipeline code) and modify it with
   your local MySQL database setup

3. create directory /usr/local/ImodCalib/ and copy grabDatabase.ini into it

4. may need to install additional libs

- for Linux user, check if there is any missing lib files by running
   ldd $IMOD_DIR/lib/imodplug/sqldrivers/libqsqlmysql.so

in general RHLE6 has all the libs. Ubuntu may need to install libmysqlclient

- for Mac user, need to find libmysqlclient.18.dylib  and copy into
  /usr/local/lib

Contact David Mastronarde mast@Colorado.edu for support.


===================================================================================


