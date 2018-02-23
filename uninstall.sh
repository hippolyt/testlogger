#!/bin/bash
rm -rf /opt/testlogger
systemctl disable testlogger.service
rm /etc/systemd/system/testlogger.service
