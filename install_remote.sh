#!/bin/bash

IP=$1
PW=raspberry

echo "$IP $PW"

sshpass -p "$PW" scp -o StrictHostKeyChecking=no  -r ~/Desktop/testlogger/ pi@$IP:~
sshpass -p "$PW" ssh -o StrictHostKeyChecking=no  pi@$IP "sudo chmod +x /home/pi/testlogger/*"
sshpass -p "$PW" ssh -o StrictHostKeyChecking=no  pi@$IP "cd ~/testlogger ; sudo ./install.sh"
