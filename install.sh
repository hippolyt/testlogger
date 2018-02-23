#!/bin/bash
./uninstall.sh
mkdir /opt/testlogger
cp *  /opt/testlogger
chmod +x /opt/testlogger/*
cp testlogger.service /etc/systemd/system/
systemctl enable testlogger.service
sudo -H pip3 install pyudev psutil
