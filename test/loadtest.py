#
# Pings an IP running phylobot with a lot of requests.
#
import time, urllib2
import threading
from threading import Thread
import math

URLS = ["http://54.183.185.164/582058403/trees", "http://www.phylobot.com/582058403/trees"]
NTHREADS = 30

url_times = {}
for url in URLS:
    url_times[url] = []

def mean(values):
    """Returns the mean, or None if there are 0 values."""
    if values.__len__() == 0:
        return None
    sum = 0.0
    for v in values:
        sum += float(v)
    return sum / float(values.__len__())

def sd(values):
    m = mean(values)
    if m == None:
        return None
    sumofsquares = 0.0
    for v in values:
        sumofsquares += (v - m)**2
    return math.sqrt( sumofsquares / float(values.__len__()) )

def testthread(url, threadnum):
    start = time.time()
    response = urllib2.urlopen(url)
    html = response.read()
    stop = time.time()
    time_delta = (stop-start)
    #print url, threadnum, time_delta
    url_times[url].append( time_delta )

for url in URLS:
    for ii in range(0,NTHREADS):
        worker = Thread(target=testthread, args=(url, ii,) )
        worker.start()

    for worker in threading.enumerate():
        try:
            worker.join()
        except RuntimeError:
            pass
    
for url in URLS:
    print url, mean(url_times[url]), sd(url_times[url])
    
#time.sleep(10)

