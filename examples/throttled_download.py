from urllib import urlretrieve
import time
import sys

class ThrottledDownloader (object):

    def __init__(self, maxDownloadRate):
        self.maxDownloadRate = maxDownloadRate
        self.lastBlockTime = 0
        self.startTime = 0
        self.downloadRate = 0
        self.averageDownloadRate = 0
        self.timeLeft = 0
        self.displayHook = None

    def setMaxDownloadRate(self, maxDownloadRate):
        self.maxDownloadRate = maxDownloadRate

    def setDisplayHook(self, func):
        self.displayHook = func

    def hook(self, blocks, blockSize, totalSize):
        now = time.time()
        timeElapsed = now - self.lastBlockTime
        transferedBytes = blocks * blockSize
        lastDownloadRate = float(blockSize) / float(timeElapsed)
        if self.maxDownloadRate and lastDownloadRate > self.maxDownloadRate:
            minTime = float(blockSize) / float(self.maxDownloadRate)
            waitTime = minTime - timeElapsed
            time.sleep(waitTime)
        actualNow = time.time()
        actualDownloadRate = float(blockSize) / float(actualNow - self.lastBlockTime)
        averageDownloadRate = float(transferedBytes) / float(actualNow - self.startTime)
        if averageDownloadRate > 0:
            self.timeLeft = (totalSize - transferedBytes) / averageDownloadRate
        else:
            self.timeLeft = 0
        self.downloadRate = actualDownloadRate
        self.averageDownloadRate = averageDownloadRate
        self.lastBlockTime = actualNow
        if self.displayHook:
            self.displayHook(self.timeLeft, self.averageDownloadRate, self.downloadRate, totalSize, transferedBytes)
    
    def download(self, url, filename = None):
        self.startTime = time.time()
        self.lastBlockTime = time.time()
        (filename, headers) = urlretrieve(url, filename, reporthook=self.hook)
        return filename

if __name__ == "__main__":
    url = sys.argv[1]
    throttle = ThrottledDownloader(1024*50)
    filename = throttle.download(url)
    print "Filename:", filename
