#!/bin/bash

# Information that is collected any minute:
# $TEMP=$(vcgencmd measure_temp  | sed "s/.*temp=\(.*\)'C.*/\1/")	# Current temperature
# echo temp_celsius, $TEMP

# CPU load average percentage last 1 minute. For 5 or 15 minutes change the chosen awk column (i.e. $(NF-1) od $(NF))
LOAD=$(w | head -n 1 | awk -F' ' '{ print $(NF-2) }' | sed 's/[,.]//g')
LOAD=$((10#$LOAD))
NCORES=4
echo cpu_usage_perc, $(( ( $LOAD + $NCORES/2 ) / $NCORES ))

# Storage
echo disk_space_used_mb, $(df -m | awk '{ print $3}' | sort -rn | head -n 1)
echo disk_space_available_mb, $(df -m | awk '{ print $4}' | sort -rn | head -n 1)
echo disk_space_max_mb, $(df -m | awk '{ print $2}' | sort -rn | head -n 1)

# Ram Info
#cat /proc/meminfo | grep MemTotal
#cat /proc/meminfo | grep MemFree
echo ram_used_mb, $(free -tm | grep Mem | awk '{print $3}')
echo ram_free_mb, $(free -tm | grep Mem | awk '{print $4}')
echo ram_max_mb, $(free -tm | grep Mem | awk '{print $2}')
