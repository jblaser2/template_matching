#!/usr/bin/python
# db3_inc.py - basic configuration and collection of basic functions for mysql/db
# v2021-04-10, updated 07/29/2021
# last modified 11/02/2021


import string
import os
import sys
import fnmatch
import time
import math
#import MySQLdb
try:
    import MySQLdb
except:
    try:
        import mysql.connector
        MySQLdb =  mysql.connector
    except Exception as e: 
        print ('Error!!', e)
    
##############################
# Begin Configuration
# replace all content inside "" to your local path/server
##############################

# connect to MySQL database server: host IP, account user name, password
hostip_real = "123.123.123.123"
mysql_user = "xxxx"
mysql_password = "yyyyyy"

# setup data directory location to rsync data files. use options either (1) or (2) below
# it is STRONGLY recommended to use option (1)
# (1) if database data directory /jdatabase/data/ is mounted directly on the processing machine:
rsync_server_real = 0 
dbpath_real = "/jdatabase/data/"

# (2) if using rsync through ssh to user@jdatahost:/jdatabase/data/:
# important! make sure user accounts have password-free access (keygen) to the remote host, jdatahost
#rsync_server_real = "jdatahost" 
#dbpath_real = "/jdatabase/data/"

# test database location (optional, may leave "" empty if not used)
hostip_test = "111.111.111.11"   #test mysql server, same user/pw as real server
rsync_server_test = 0 
dbpath_test = "/jdatabase/test/"

# Pipeline code location
exepath = "/software/pipeline/"

# sbatch partition - if "#SBATCH --partition" will be used in your SLURM submission
sbatch_partition = "xxxx"
#sbatch_partition = ""  # if not used

# script for setting up PATH and LD_LIBRARY_PATH
# $IMOD_DIR must be defined and will be called by code
# these software must be in $PATH: $IMOD_DIR/bin, mencoder, ffmpeg, convert, xx/EMAN2/bin
source_script_bash = "/software/pipeline/jpath.shrc"  # if jpath.shrc is modified for users' PATH, this file will be sourced
#source_script_bash = ""  # if all required software already in default PATH, no need to source any setting file

# FISE option for pre-processing: FISE must be installed if you would like to use runfise.sh
# script for setting up PATH & LD_LIBRARY_PATH for running runfise.sh
# source_script_fise = "/software/fise/sourcelist"
source_script_fise = ""  # if not using fise

# Admin will get notified if something seriousely wrong when running the pipeline
admin_email = "xxxx@yyyy.com"

##############################
# End Configuration
##############################

def checkgainref(refdir):
# check gain reference for movie mode or FISE pre-processing. must be .dm4 or CountCDSRef*mrc or CountRef*mrc
    gainref = ''
    for fname in os.listdir(refdir):
        if fname.endswith('.dm4'):
            gainref = fname
            return gainref 
        elif fname.startswith('CountCDSRef') and fname.endswith('.mrc'):
            gainref = fname
            return gainref 
        elif fname.startswith('CountRef') and fname.endswith('.mrc'):
            gainref = fname
            return gainref 
    return gainref 


def logwrite(logfile, line):
    print ('logs:', line)
    if line.endswith("\n") == False:
        line = line + '\n'
    try:
        with open(logfile, "a") as p:
            p.write(line)
            p.flush()
    except Exception as e:
        print (e)
        print ('Error in writing logwrite: ' + logfile)
        return 1
    return 0
        

def logprint(line):
    print (line)


def email_to(useremail, subject, msg, machinename):
    SENDMAIL = "/usr/sbin/sendmail" # sendmail location
    try:
        p = os.popen("%s -t" % SENDMAIL, "w")
        p.write("To: "+useremail+"\n")
        p.write("Subject: "+subject+"\n")
        p.write("\n") # blank line separating headers from body
        p.write("This is an auto message from your Pipeline on "+machinename+".\n\n")
        p.write(msg+"\n")
        p.close()
    except:
        print ('sendmail error for ', subject)
    

def sql_connect(hostip):
    try:
        conn = MySQLdb.connect (
            db = "tomography",
            host = hostip,    
            user = mysql_user,
            passwd = mysql_password
            )
        cursor = conn.cursor()
    except MySQLdb.Error as e:
        print (e)
        print ("Error: can not connect to mysql server. please contact your administrator. Exit.")
        return 1, 1, 1
    #print ("Connected to MySQL DB at ", hostip)
    return 0, conn, cursor


def sql_connect2(hostip):
    try:
        conn = MySQLdb.connect (
            db = "tomography",
            host = hostip,    
            user = mysql_user,
            passwd = mysql_password
            )
        cursor = conn.cursor()
    except MySQLdb.Error as e:
        print (e)
        print ("Error: failed to connect to mysql server. Try one more time.")
        time.sleep(5)
        try:
            conn = MySQLdb.connect (
                db = "tomography",
                host = hostip,    
                user = mysql_user,
                passwd = mysql_password
                )
            cursor = conn.cursor()
        except MySQLdb.Error as e:
            print (e)
            print ("Error: failed to connect to mysql server 2 times. please contact your administrator. Exit.")
            return 1, 1, 1
    #print ("Connected to MySQL DB at ", hostip)
    return 0, conn, cursor



def myexesql(hostip, sql, exe, pr):
    if pr == 1:
        print ("myexesql:", sql)
    if exe == 1:
        status, conn, cursor = sql_connect2(hostip)
        if status != 0:
            return 1, []
        try:
            cursor.execute(sql)
        except Exception as e:
            print ("*** Fetal error.", e)
            return 1, []
        finally:
            # return cursor content as a list
            mycursor = list(cursor)
            conn.close()
        return 0, mycursor
    else:
        return 0, []

            
# connect and close
def myexesql_tuple(hostip, sql, values, exe, pr):
# e.g. cursor.execute("INSERT INTO table VALUES (%s, %s, %s)", (var1, var2, var3))
    values = tuple(values)
    if pr == 1:
        line = "myexesql_tuple: " + sql + ", " + str(values)
        print (" myexesql_tuple:", line)
    if exe == 1:
        status, conn, cursor = sql_connect2(hostip) 
        if status != 0:
            return 1, []
        try:
            cursor.execute(sql, values)
        except Exception as e:
            print ("*** Fetal error.", e)
            return 1, []
        finally:
            mycursor = list(cursor)
            conn.close()
        return 0, mycursor

    else:
        return 0, []


def myexersync(path_from, path_to, user_ssh, server_ssh, mkdir, exe, pr):
    if server_ssh == 0 or server_ssh == "0":
        if mkdir:
            cmd = "mkdir -p " + path_to + "; rsync -av --exclude '*.rec.pixel_*' " + path_from + " " + path_to
        else:
            cmd = "rsync -av --exclude '*.rec.pixel_*' " + path_from + " " + path_to
    else:
        if mkdir:
            cmd = 'rsync -ave "ssh -o \'StrictHostKeyChecking no\'" --rsync-path="mkdir -p ' + path_to + ' && rsync" '  + path_from + ' ' + user_ssh + '@' + server_ssh + ':' + path_to
        else:
            cmd = 'rsync -ave "ssh -o \'StrictHostKeyChecking no\'" ' + path_from + ' ' + user_ssh + '@' + server_ssh + ':' + path_to
        
    if pr == 1:
        logprint(cmd)

    #myexecmd(cmd, exe, pr) - this gives errors due to quotations
    ooss = 1
    if exe == 1:
        try:
            ooss = os.system(cmd)
            if ooss !=0:
                time.sleep(10)
                print ('... trying rsync 2nd time in 10s')
                ooss = os.system(cmd)
                if ooss !=0:
                    time.sleep(30)
                    print ('... trying rsync 3dd time in 30s')
                    ooss = os.system(cmd)
            # always rsync twice 
            ooss = os.system(cmd)
        except Exception as e:
            print (e, '.', cmd)
        finally:
            return ooss
    else:
        return 0
    return ooss


def myexecmd(cmd, exe, pr):
    if pr == 1:
        print (" myexecmd:", cmd)
    if exe == 1:
        return os.system(cmd)
    else:
        return 0

def myexecmd2(cmd, exe, pr):
    if pr == 1:
        print (" myexecmd:", cmd)
    if exe == 1:
        ooss = os.system(cmd)
        if ooss == 0:
            return 0
        else:
            print ("... trying 2nd time in 5s ")
            time.sleep(5)
            ooss = os.system(cmd)
            if ooss == 0:
                return 0
            else:
                print ("... trying 3rd time in 15s ")
                time.sleep(15)
                return os.system(cmd)
    else:
        return 0


#generate keyimg and update mysql
#def gen_keyimg (mrcpath, tiltseriesid, dbpath, exe, pr):
def gen_keyimg (mrcpath, outputpath, keypath, tiltseriesid, exe, pr):
# outputpath = ~/Pipeline_Proc/tiltseriesid/
# keypath = ~/Pipeline_Proc/tiltseriesid/upload/
    logprint("generating keyimg:"+tiltseriesid)
    if exe == 0:
        return 0
    if os.path.exists(mrcpath):
        cmd = 'mkdir -p '+outputpath
        myexecmd(cmd, exe, pr)
        result = os.popen('header -size '+ mrcpath)
        line = result.read()
        dims = line.split()
        try:
            dimx = int(dims[0])
        except:
            dimx = 0
        try:
            dimy = int(dims[1])
        except:
            dimy = 0
        try:
            dimz = int(dims[2])
        except:
            dimz = 0
        print ("dims=", dimx, dimy, dimz)
        if dimx == 0 or dimy == 0 or dimz  == 0:
            logprint("mrc file has 0 in dims:"+mrcpath)
            return 1
        if dimz > dimy:
            if dimx==1024 and dimy==1024:
                logprint("x=y=1024")
            elif dimx==2048 and dimy==2048:
                logprint("x=y=2048")
            else:
                print ('Warning!!! dimZ is larger than dimY: ' + mrcpath + '.')
                #print ('Stop!!! dimZ is larger than dimY: ' + mrcpath + '. Exit.')
                #sys.exit(1)

        ll = int(dimz/2) - 2
        hh = int(dimz/2) + 2
        mrctmp = outputpath+tiltseriesid+'_ave.mrc'
        cmd = 'clip avg -2d -iz '+str(ll)+'-'+str(hh)+' '+mrcpath+' '+mrctmp
        myexecmd(cmd, exe, pr)
        cmd = 'newstack -mode 0 -meansd 150,40 '+mrctmp+' '+mrctmp 
        myexecmd(cmd, exe, pr)
        mrcjpg = outputpath+'keyimg_'+tiltseriesid+'.jpg'
        mrcjpg_s = outputpath+'keyimg_'+tiltseriesid+'_s.jpg'
        cmd = 'mrc2tif -j -q 80 '+mrctmp+' '+mrcjpg
        myexecmd(cmd, exe, pr)
        cmd = 'convert '+mrcjpg+' -resize 150x150 -brightness-contrast -10x50 '+ mrcjpg_s
        myexecmd(cmd, exe, pr)
        if exe == 1:
        #    myexesql(sql, exe)
            os.system('chmod 644 '+mrcjpg)
            os.system('chmod 644 '+mrcjpg_s)
            os.system('mv '+mrcjpg+' '+keypath)
            os.system('mv '+mrcjpg_s+' '+keypath)
            os.system('rm '+mrctmp+'*')
    else:
        logprint("mrc file does not exist:"+mrcpath)
        return 1
    return 0
    
#generate keymov and update mysql
def gen_keymov (mrcpath, outputpath, keypath, tiltseriesid, exe, pr):
# outputpath = ~/Pipeline_Proc/tiltseriesid/
# keypath = ~/Pipeline_Proc/tiltseriesid/upload/
    logprint("generating keymov:"+tiltseriesid)
    if exe == 0:
        return 0
    if os.path.exists(mrcpath):
        cmd = 'mkdir -p '+outputpath
        myexecmd(cmd, exe, pr)
        result = os.popen('header -size '+ mrcpath)
        line = result.read()
        dims = line.split()
        try:
            dimx = int(dims[0])
        except:
            dimx = 0
        try:
            dimy = int(dims[1])
        except:
            dimy = 0
        try:
            dimz = int(dims[2])
        except:
            dimz = 0
        print ("dims=", dimx, dimy, dimz)
        if dimx == 0 or dimy == 0 or dimz  == 0:
            logprint("mrc file has 0 in dims:"+mrcpath)
            return 1
        #dimz = dimz-1 #prevent bad end

        #for range (2,5) means 2,3,4
        pictmp = []
        for i in range(0, dimz):
            if i < 10:
                ii = '000'+str(i)
            elif i < 100:
                ii = '00'+str(i)
            elif i < 1000:
                ii = '0'+str(i)
            ptmp = outputpath+tiltseriesid+'_ave'+ii
            pictmp.append(ptmp)

        cmd = 'clip avg -2d -iz 0-2 '+mrcpath+' '+pictmp[0]+'.mrc'
        myexecmd(cmd, exe, pr)
        cmd = 'clip avg -2d -iz 0-3 '+mrcpath+' '+pictmp[1]+'.mrc'
        myexecmd(cmd, exe, 0)                    
        for i in range(2, dimz-2):   
            ll = i - 2
            hh = i + 2
            cmd = 'clip avg -2d -iz '+str(ll)+'-'+str(hh)+' '+mrcpath+' '+pictmp[i]+'.mrc'
            myexecmd(cmd, exe, 0)
        jfrom = dimz-4
        jto = dimz-1
        cmd = 'clip avg -2d -iz '+str(jfrom)+'-'+str(jto)+' '+mrcpath+' '+pictmp[dimz-2]+'.mrc'
        myexecmd(cmd, exe, 0)
        jfrom = dimz-3
        jto = dimz-1
        cmd = 'clip avg -2d -iz '+str(jfrom)+'-'+str(jto)+' '+mrcpath+' '+pictmp[dimz-1]+'.mrc'
        myexecmd(cmd, exe, 0)                    
        #adjust and shrink each image
        print ("resizing...")
        for i in range(0, dimz):   
            cmd = 'newstack -mode 0 -meansd 150,40 '+pictmp[i]+'.mrc'+' '+pictmp[i]+'.mrc' 
            myexecmd(cmd, exe, 0)
            cmd = 'mrc2tif -j -q 100 '+pictmp[i]+'.mrc'+' '+pictmp[i]+'.jpg'
            myexecmd(cmd, exe, 0)
            cmd = 'convert '+pictmp[i]+'.jpg'+' -resize 512x512 '+pictmp[i]+'.jpg'
            myexecmd(cmd, exe, 0)
            sys.stdout.flush()
            if exe == 1:
                os.system('rm '+pictmp[i]+'.mrc*')
        cmd = 'mencoder -nosound -mf type=jpg:fps=24 -ovc copy -o ' + outputpath+tiltseriesid+'_lossless.avi ' + 'mf://' + outputpath + '\*ave*.jpg'
        myexecmd(cmd, exe, pr)
        movpath = outputpath+'keymov_'+tiltseriesid+'.mp4'
        if os.path.exists(movpath):
            cmd = 'rm ' +  movpath
            myexecmd(cmd, exe, pr)
        cmd = 'ffmpeg -hide_banner -nostats -loglevel panic -i ' + outputpath+tiltseriesid+'_lossless.avi -movflags faststart -nostats -n -vcodec libx264 -pix_fmt yuv420p -vf pad=512:512 -qscale 0 ' + movpath
        myexecmd(cmd, exe, pr)

        if exe == 1:
            os.system('chmod 644 '+movpath)
            os.system('mv '+movpath+' '+keypath)
            print ("keymov made for "+tiltseriesid)
            for i in range(0, dimz):   
                os.system('rm '+pictmp[i]+'.jpg')
            #print ('rm '+keypath+tiltseriesid+'_lossless.avi')
            os.system('rm '+outputpath+tiltseriesid+'_lossless.avi')
    else:
        logprint("mrc file does not exist:"+mrcpath)
        return 1
    return 0


def gen_keyimg_raw (mrcpath, outputpath, keypath, tiltseriesid, exe, pr):
#for raw data only, take the central slices
# outputpath = ~/Pipeline_Proc/tiltseriesid/
# keypath = ~/Pipeline_Proc/tiltseriesid/upload/
    logprint("generating raw keyimg:"+tiltseriesid)
    if exe == 0:
        return 0
    if os.path.exists(mrcpath):
        cmd = 'mkdir -p '+outputpath
        myexecmd(cmd, exe, pr)
        result = os.popen('header -size '+ mrcpath)
        line = result.read()
        dims = line.split()
        try:
            dimx = int(dims[0])
        except:
            dimx = 0
        try:
            dimy = int(dims[1])
        except:
            dimy = 0
        try:
            dimz = int(dims[2])
        except:
            dimz = 0
        print ("dims=", dimx, dimy, dimz)
        if dimx == 0 or dimy == 0 or dimz  == 0:
            logprint("raw mrc file has 0 in dims:"+mrcpath)
            return 1
        ll = int(dimz/2)
        mrctmp = outputpath+tiltseriesid+'_0tilt.mrc'
        cmd = 'newstack -secs '+str(ll)+'-'+str(ll)+' '+mrcpath+' '+mrctmp
        myexecmd(cmd, exe, pr)
        cmd = 'newstack -mode 0 -meansd 150,40 '+mrctmp+' '+mrctmp 
        myexecmd(cmd, exe, pr)
        mrcjpg = outputpath+'keyimg_'+tiltseriesid+'.jpg'
        mrcjpg_s = outputpath+'keyimg_'+tiltseriesid+'_s.jpg'
        cmd = 'mrc2tif -j -q 80 '+mrctmp+' '+mrcjpg
        myexecmd(cmd, exe, pr)
        cmd = 'convert '+mrcjpg+' -resize 150x150 -brightness-contrast -10x15 '+mrcjpg_s
        myexecmd(cmd, exe, pr)
        if exe == 1:
            os.system('chmod 644 '+mrcjpg)
            os.system('chmod 644 '+mrcjpg_s)
            os.system('mv '+mrcjpg+' '+keypath)
            os.system('mv '+mrcjpg_s+' '+keypath)
            os.system('rm '+mrctmp+'*')
    else:
        logprint("raw mrc file does not exist:"+mrcpath)
        return 1
    return 0
