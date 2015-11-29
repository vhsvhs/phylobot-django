import os, re, sys

configpath_erg = sys.argv[1]
configpath_final = sys.argv[2]
bashscriptpath = "/home/ubuntu/.phylobot"

export_lines = []
fin = open(bashscriptpath, "r")

for line in fin.xreadlines():
    if False == line.startswith("export"):
        fout.write(line)
        continue
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