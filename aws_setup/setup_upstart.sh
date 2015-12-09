#
# Launch the Job Daemon, using upstart
# (errors will be written to the log @ /var/log/upstart/jobdaemon.log)
#
cd $PHYLOBOT_REPO
sudo chmod 755 phylobot/job_daemon.py
# Manually write all PhyloBot environment variables into the upstart config:
sudo python aws_setup/build_upstart_scripts.py aws_setup/jobdaemon.conf /etc/init/jobdaemon.conf
sudo chmod 755 /etc/init/jobdaemon.conf
init-checkconf /etc/init/jobdaemon.conf
sudo initctl reload-configuration
sudo start jobdaemon

#
# Launch the Backup Daemon, using upstart
# (errors will be written to the log @ /var/log/upstart/phylobotbackupdaemon.log)
#
cd $PHYLOBOT_REPO
sudo chmod 755 phylobot/backup_daemon.py
# Manually write all PhyloBot environment variables into the upstart config:
sudo python aws_setup/build_upstart_scripts.py aws_setup/backupdaemon.conf /etc/init/phylobotbackupdaemon.conf
sudo chmod 755 /etc/init/phylobotbackupdaemon.conf
init-checkconf /etc/init/phylobotbackupdaemon.conf
sudo initctl reload-configuration
sudo start phylobotbackupdaemon

#
# Launch Gunicorn, using upstart
# (errors will be written to the log @ /var/log/upstart/gunicorn.log)
#
cd $PHYLOBOT_REPO
# Manually write all PhyloBot environment variables into the upstart config:
sudo python aws_setup/build_upstart_scripts.py aws_setup/gunicorn.conf /etc/init/gunicorn.conf
sudo chmod 755 /etc/init/gunicorn.conf
init-checkconf /etc/init/gunicorn.conf
sudo initctl reload-configuration
sudo start gunicorn