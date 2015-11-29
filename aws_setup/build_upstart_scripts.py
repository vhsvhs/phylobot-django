#
# This script writes all the PhyloBot environment variables into the
# upstart configuration scripts.
# You are not intended to directly execute this script!
# It is currently called within the setup script setup_phylobot_server_on_aws.sh
#

import os, re, sys

configpath_erg = sys.argv[1]
configpath_final = sys.argv[2]
bashscriptpath = "/home/ubuntu/.phylobot"

export_lines = []
fin = open(bashscriptpath, "r")

for line in fin.xreadlines():
    if line.startswith("export"):
        newline = re.sub("export ", "env ", line)
        export_lines.append( newline )
fin.close()

fin = open(configpath_erg, "r")
fout = open(configpath_final, "w")
for line in fin.xreadlines():
    if False == line.startswith("#ENV"):
        fout.write(line)
        continue
    for l in export_lines:
        fout.write(l)
fout.close()
fin.close()