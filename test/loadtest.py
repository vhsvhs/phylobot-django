#
# Pings an IP running phylobot with a lot of requests.
#
import time, urllib2
import threading
from threading import Thread

URLS = ["http://54.183.185.164/582058403/trees", "http://www.phylobot.com/582058403/trees"]

def testthread(url, threadnum):
    start = time.time()
    response = urllib2.urlopen(url)
    html = response.read()
    stop = time.time()
    print url, threadnum, stop-start

for url in URLS:
    for ii in range(0,10):
        print ii
        #response = urllib2.urlopen(url)
        #html = response.read()
        worker = Thread(target=testthread, args=(url, ii,) )
        worker.start()

for worker in threading.enumerate():
    worker.join()

#time.sleep(10)

