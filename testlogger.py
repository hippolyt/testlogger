#!/usr/bin/env python3

import time
import csv
import subprocess
from io import StringIO
import numpy as np
import datetime
from pathlib import Path
import re
import sys,os
from os import statvfs
from functools import wraps
from time import time, sleep
import shutil
from glob import glob
from subprocess import check_output, CalledProcessError, STDOUT
import pyudev
import psutil
from random import randrange
import filecmp


def check_if_running():
    """
    Check if Script is already running in another instance
    """
    print("Checking for other instances")
    lock_path = Path("./logger.lock")
    exists = lock_path.is_file()
    now = datetime.datetime.now()

    if exists:
        with open("./logger.lock",'r') as lastlog:
            line = lastlog.readline()
            locktime = datetime.datetime.strptime(line, '%Y-%m-%d %H:%M:%S')
            lock_age = (now - locktime).total_seconds()
            if lock_age < 60:
                print(now.strftime("%Y-%m-%d %H:%M:%S"),"\nFile locked, already running since",lock_age)
                exit()

    with open("./logger.lock",'w') as lastlog:
            lastlog.write(now.strftime("%Y-%m-%d %H:%M:%S"))

def release_lockfile():
    print("Releasing Instance Lockfile")
    lock_path = Path("./logger.lock")
    exists = lock_path.is_file()
    if exists:
        os.remove("logger.lock")


def find_usb_path():
    print("Finding USB path")
    mountpoints=[]
    context = pyudev.Context()
    removable = [device for device in context.list_devices(subsystem='block', DEVTYPE='disk') if device.attributes.asstring('removable') == "1"]
    for device in removable:
        partitions = [device.device_node for device in context.list_devices(subsystem='block', DEVTYPE='partition', parent=device)]
        print("All removable partitions: {}".format(", ".join(partitions)))
        print("Mounted removable partitions:")
        for p in psutil.disk_partitions():
            if p.device in partitions:
                print("  {}: {}".format(p.device, p.mountpoint))
                mountpoints.append(p.mountpoint)

    if len(mountpoints) > 0:
        usb_logs_path = mountpoints[0] + "/"
    else:
        usb_logs_path = ""
    return usb_logs_path   # First removable storage device

def check_diskspace():
    print("Checking remaining disk space")
    f = os.statvfs("/home")
    avb = getattr(f,'f_bavail')
    bs  = getattr(f,'f_bsize')
    free_space_mb = avb * bs / 1e6
    print("free space [MB]", free_space_mb)
    if free_space_mb < 1e3:
        print("Not enough space, deleting writetest directories")
        deletepath = "writetests"
        if os.path.exists(deletepath):
            shutil.rmtree(deletepath)

    f = os.statvfs("/home")
    avb = getattr(f,'f_bavail')
    bs  = getattr(f,'f_bsize')
    free_space_mb = avb * bs / 1e6
    if free_space_mb < 1e3:
        print("Still not enough space, deleting writetest error directories")
        deletepath = "writetests_err"
        if os.path.exists(deletepath):
            shutil.rmtree(deletepath)

def write_for_sec(write_seconds):
     # First create testing directory
    directory = "writetests/"
    if not os.path.exists(directory):
        os.makedirs(directory)
    directory_err = "writetests_err/"
    if not os.path.exists(directory_err):
        os.makedirs(directory_err)

    print("Writing for",write_seconds,"seconds")
    start = time()
    while time() - start < write_seconds:
        filename1 = "permawrite_5M_"+str(randrange(1e6)) + "_1.test"
        filename2 = "permawrite_5M_"+str(randrange(1e6)) + "_2.test"
        content = os.urandom(int(1e7))
        with open(directory+filename1, 'wb') as fout:
            fout.write(content)
        with open(directory+filename2, 'wb') as fout:
            fout.write(content)
        # Compare the two files
        if not filecmp.cmp(directory+filename1,directory+filename2):
            shutil.copyfile(directory+filename1,directory_err+filename1)
            shutil.copyfile(directory+filename2,directory_err+filename2)
            with open(directory_err+"errors.log",'a') as errorlog:
                errorlog.write(datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")+","+filename1+","+filename2+","+"unequal testfiles\n")
    end = time()
    print('Elapsed time: {}'.format(end-start))

def write_speedtest():
    print("Starting Write Speed Test")
    # First create testing directory
    directory = "writetests/"
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Create 1 100MB file
    print("1 file, 100MB")
    filename = "test_100M"
    start = time()
    with open(directory+filename, 'wb') as fout:
        fout.write(os.urandom(int(1e8)))
    end = time()
    bigfiletime = end-start
    print('Elapsed time: {}'.format(end-start))

    # Create 10 100KB files
    print("1000 files, 100KB")
    start = time()
    lap = time()
    for i in range(1000):
        filename = "test_100K_"+str(i)
        with open(directory+filename, 'wb') as fout:
            fout.write(os.urandom(int(1e5)))
        if i % 100 == 0:
            print(i)
            print(time()-lap)
    end = time()
    smallfiletime = end-start
    print('Elapsed time: {}'.format(end-start))

    return [bigfiletime, smallfiletime]

def log_events(usb_logs_path):
    """
    This checks, if eventlogs were written since last boot.
    If not, it checks the 10 most recent events of different types.
    Everything that is not new, is logged.
    """
    print("Logging events and crashes")
    # First create eventlog directory
    directory = usb_logs_path + "events/"
    if not os.path.exists(directory):
        os.makedirs(directory)

    print(directory)
    # Get current time
    now = datetime.datetime.now()
    date_today = now.strftime("%Y-%m-%d")

    # Check time of last log_events
    last_log_event_path = Path(directory+"last_log_events_time.date")
    exists = last_log_event_path.is_file()
    if exists:
        with open(directory+"last_log_events_time.date",'r') as lastlog:
            line = lastlog.readline()
            last_log_events_time = datetime.datetime.strptime(line, '%Y-%m-%d %H:%M')
    else:
            last_log_events_time = datetime.datetime(2017, 1, 1, 1, 1)


    # Store available commands:
    # First name, then command
    commands = [
                 ["last_boot", "who -b"],
                 ["sleep", "sleep 0.1"],
                 ["last_boot_command_3", "last -FRx3 boot reboot shutdown root"],
                 ["last_crash_3", "last | grep crash | head -3"],
                 ["journal_crash_reports_n", "journalctl | grep crash"],
                 ["writetest_errors", "cat writetests_err/errors.log"]
               ]
    commands_array = np.array(commands)


    # Check time of last boot
    out = check_output( "who -b", stderr=STDOUT,shell=True)     # If I enable the shell, I can I can pass a whole string there. Otherwise the elements of the command would be in an array.
    out = str(out, 'utf-8')                     # Convert byte literal to string
    match = re.search('\d{4}-\d{2}-\d{2}\ \d{2}:\d{2}', out) #\ \d{2}\:\d{2}
    boot_time = datetime.datetime.strptime(match.group(), '%Y-%m-%d %H:%M')





    # Go through the commands:
    for row in commands_array:
        name = row[0]
        command = row[1]

        # Command output # TODO: Make this cleaner to notice nonzero return codes
        out = check_output(command+";exit 0",stderr=STDOUT, shell=True)   #This forces a 0 return code, so the program runs through
        out = str(out, 'utf-8')                     # Convert byte literal to string

        filename_ok = False
        new_file = False
        old_file_exists = False
        suffix = 0

        while not filename_ok:
            # Make a new log file for every day
            # Each has an own file  events_$CMD_NAME_$DATE_$SUFFIX
            events_logfile_name  = directory+"events_" + name + "_" + date_today + "_" + str(suffix).zfill(3) + ".log"
            # Check if log file exists
            # Check if existing log file is too large (>10MB)
            # If new file is necessary
            # Create a new log file
            my_file = Path(events_logfile_name)
            exists = my_file.is_file()

            if not exists:
                new_file = True     # Check if new file is necessary
                filename_ok = True
                break

            too_large = my_file.stat().st_size > 1*1e6     # File size limit 1 MB

            if not too_large :
                filename_ok = True
                break

            if exists and too_large:
                suffix = suffix + 1
        events_logfile_name  = directory+"events_" + name + "_" + date_today + "_" + str(suffix).zfill(3) + ".log"
        # Write command to new file
        if new_file:
            with open(events_logfile_name,'a') as myfile:
                myfile.write("# Here we collect the output of command:\n#"+command+"\n")
        # Check for old file
        if new_file and suffix > 0:
                old_events_logfile_name = directory+"events_" + name + "_" + date_today + "_" + str(suffix-1).zfill(3) + ".log"
                old_file_exists = True
        elif not new_file:
            old_events_logfile_name = events_logfile_name
            old_file_exists = True


        out_list = out.splitlines()

        if old_file_exists:
            # Check last 100 lines of oldest logfile and match with cmd output
            # All duplicate lines are removed
            lastlines = subprocess.check_output(['tail', '-100', old_events_logfile_name],stderr=STDOUT)
            lastlines = str(lastlines, 'utf-8').splitlines()

            out_list = [line for line in out_list if line not in lastlines]

        out = "\n".join(out_list)   # Ensure proper \n

        if len(out) > 3:
            out = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")+ "\n" + out
            if not out.endswith("\n"):
                out = out + "\n"

        with open(events_logfile_name,'a') as logfile:
            logfile.write(out)

    # Write a marker with last time function was executed wholly
    with open(directory+"last_log_events_time.date",'w') as lastlog:
            lastlog.write(now.strftime("%Y-%m-%d %H:%M"))



def log_metrics(usb_logs_path):
    """
    This is executed every minute and logs interesting system metrics to a csv file
    """
    print("Logging metrics")
    # First create metrics directory
    directory = usb_logs_path + "metrics/"
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Get metrics from script
    out = check_output(["./print_metrics.sh"],stderr=STDOUT)
    out = str(out, 'utf-8')                     # Convert byte literal to string
    out = out.replace(" ", "")                  # Remove whitespace
    buff = StringIO(out)
    csv_reader = csv.reader(buff)
    metrics_array = np.array(list(csv_reader))

    # Get times from writetests
    bigfiletime, smallfiletime = write_speedtest()

    # Make a new log file for every day
    now = datetime.datetime.now()
    date_today = now.strftime("%Y-%m-%d")
    time_now = now.strftime("%Y-%m-%d_%H:%M:%S")
    metrics_logfile_name = date_today

    # Extract names and values
    names = ["time", "writetest_big", "writetest_small"] + list(metrics_array[:,0])
    values = [time_now, bigfiletime, smallfiletime] + list(metrics_array[:,1])

    # Choose the right logfile for writing
    filename_ok = False
    new_file = False
    suffix = 0
    while not filename_ok:
        metrics_logfile_name  = directory+"metrics_" + date_today + "_" + str(suffix).zfill(3) + ".csv"
        my_file = Path(metrics_logfile_name)    #file = Path() / 'doc.txt'
        exists = my_file.is_file()
        if not exists:
            new_file = True     # Check if new file is necessary
            filename_ok = True
            break

        too_large = my_file.stat().st_size > 1*1e6     # File size limit 1 MB
        if not too_large :
            filename_ok = True
            break

        if exists and too_large:
            suffix = suffix + 1

    metrics_logfile_name  =  directory+"metrics_" + date_today + "_" + str(suffix).zfill(3) + ".csv"

    # Write metrics values to log file
    metrics_logfile = open(metrics_logfile_name,'a')
    csv_writer = csv.writer(metrics_logfile)
    if new_file:                # Write names to header line
        csv_writer.writerow(names)
    csv_writer.writerow(values)


def main_loop():
    """
    This triggers the other functions
    """
    while True :
        usb_logs_path = find_usb_path()
        check_diskspace()
        log_metrics(usb_logs_path)
        log_events(usb_logs_path)
        write_for_sec(60)

check_if_running()
sleep(30)   # Give the system time to boot
main_loop()
release_lockfile()
print("main end")
