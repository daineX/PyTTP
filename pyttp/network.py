# -*- coding: utf-8 -*-
from __future__ import print_function
import socket
import multiprocessing
from pyttp.core import *
import datetime, time
import sys

try:
    import Queue
except ImportError:
    import queue as Queue
import threading

import ssl

class HTTPListener(object):
    
    
    def __init__(self, port = None, handler = None, timeout = None):
    
        if port != None:
            self.port = int(port)
        else:
            self.port = 80
            
        self.timeout = timeout
            
        self.handler = handler
        if self.handler:
            self.handlerRegistered = True
        else:
            self.handlerRegistered = False
        
        self.socket = socket.socket()
        
        self.socket.bind(('', self.port))
        
        self.processes = {}
        
    def setHandler(self, handler):
        self.handler = handler
        self.handlerRegistered = True

    def handlerDispatch(self, queue, i, conn, addr, dt):
        self.handler(conn, addr)
        print("%sµs" % ((datetime.datetime.now() - dt).microseconds))
        queue.put(i)
        
    def serve(self):
        self.queue = multiprocessing.Queue()
        count = 0
        while self.handlerRegistered:
            print(count)
            count += 1
            self.socket.listen(1)
            (conn, addr) = self.socket.accept()

            print('Number of processes: ', len(self.processes))
            finished = []
            now = datetime.datetime.now()
            for i in self.processes:
                try:
                    finished.append(self.queue.get_nowait())
                    process, start = self.processes[i]
                    if  not process.is_alive():
                        finished.append(i)
                    if self.timeout:
                         if (now - start).seconds > timeout:
                            finished.append(i)
                    print("Finished process %s" % finished)
                except Exception as e:
                    print(e)
#            self.processes = [p for i, p in enumerate(self.processes[:]) if i not in finished]
            self.processes = dict([(i, p) for i, p in self.processes.items() if i not in finished])
            now = datetime.datetime.now()
#            self.processes.append((multiprocessing.Process(target=self.handlerDispatch, args=(self.queue, len(self.processes), conn, addr, now)), now))
            self.processes[count] = (multiprocessing.Process(target=self.handlerDispatch, args=(self.queue, count, conn, addr, now)), now)
            self.processes[count][0].start()



class ParallelSocketListener(object):

    STATE_LISTEN = "L"
    STATE_RUNNING = "R"
    STATE_DONE = "D"


    def __init__(self, port = None, handler = None, timeout = None, nProcesses = None):
        if port != None:
            self.port = port
        else:
            self.port = 80
        self.handler = handler
        self.timeout = timeout

        if nProcesses:
            self.nProcesses = nProcesses
        else:
            self.nProcesses = 4
        self.processes = []
        self.iQueues = []
        self.theOutputQueue = multiprocessing.Queue()
        self.state = []
        for i in range(self.nProcesses):
            iQueue = multiprocessing.Queue()
            self.processes.append(multiprocessing.Process(target=self.handlerDispatch, args=(iQueue, self.theOutputQueue, i, self.port, self.handler)))
            self.iQueues.append(iQueue)
            self.state.append(self.STATE_DONE)


    def serve(self):
        for i in range(self.nProcesses):
            self.processes[i].start()
        cycle = 0
        served = 0
        lastLocked = -1
        isInStart = False
        startTimes = [0]*self.nProcesses
        areRunning = 0
        while True:
            if not isInStart:
                for npid, iQueue in enumerate(self.iQueues):
                    if self.state[npid] == self.STATE_DONE:
                        iQueue.put("doStart")
                        isInStart = True
                        lastLocked = npid
                        self.state[npid] = self.STATE_LISTEN
                        break
            pid, state = self.theOutputQueue.get()
            if state != "":
                self.state[pid] = state
            if state == self.STATE_RUNNING and pid == lastLocked:
                lastLocked = -1
                isInStart = False
                areRunning += 1
                startTimes[pid] = datetime.datetime.now()
            if state == self.STATE_DONE:
                served += 1                        
                now = datetime.datetime.now()
                timeSpan = (now - startTimes[pid]).microseconds
                areRunning -= 1
                print("Request took %sµs" % timeSpan)

            cycle += 1
            print(cycle, self.state)


    def handlerDispatch(self, inputQueue, outputQueue, pid, port, handler):
        print("Process %s started." % pid)
        while True:
            action = inputQueue.get()
#            print action
            outputQueue.put((pid, self.STATE_LISTEN))
            pSocket = socket.socket()
            pSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            pSocket.bind(('', port))
            pSocket.listen(1)
            (conn, addr) = pSocket.accept()
            pSocket.close()
            outputQueue.put((pid, self.STATE_RUNNING))
            handler(conn, addr)
            outputQueue.put((pid, self.STATE_DONE))


        

class ThreadedSocketListener(object):

    def __init__(self, port = None, handler = None, timeout = None, nThreads = None):
        if port != None:
            self.port = port
        else:
            self.port = 80
        self.handler = handler
        self.timeout = timeout

        if nThreads:
            self.nThreads = nThreads
        else:
            self.nThreads = 4
            
        self.queue = Queue.Queue()

        self.threads = []
        for tid in range(self.nThreads):
            self.threads.append(threading.Thread(target=self.handlerDispatch, args=(tid, self.queue, self.handler)))
        
        import atexit
        atexit.register(self.clearThreads)
            
    def clearThreads(self):
        print("Cleaning up ...\n")
        print("\tThreads ...")
        for tid in range(self.nThreads):    
            self.queue.put((None, None))
        for thread in self.threads:
            thread.join()
        print(" done.")

    def serve(self):
        for tid in range(self.nThreads):
            self.threads[tid].start()
        cycle = 0
        try:        
            listenSocket = socket.socket()
            listenSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            print("Binding to port {} ...".format(self.port))
            while True:
                try:
                    listenSocket.bind(('', self.port))
                    break
                except:
                    continue
            print(" succesful.")
                
                
            listenSocket.listen(5)
            while True:
                conn, addr = listenSocket.accept()
                self.queue.put((conn, addr))
                cycle += 1

        except KeyboardInterrupt:
            self.clearThreads()
            listenSocket.close()
            print("Served %s connections." % cycle)
        except Exception as e:
            print(e)
            self.clearThreads()
            listenSocket.close()


    def handlerDispatch(self, tid, queue, handler):
        
        while True:
            conn, addr = queue.get()
            if not conn:
                return
            handler.ready = True
            handler(conn, addr)



class ThreadedSSLListener(ThreadedSocketListener):
    
    def __init__(self, certFile, keyFile, sslVersion, port = None, handler = None, timeout = None, nThreads = None):
        ThreadedSocketListener.__init__(self, port, handler, timeout, nThreads)
        self.certFile = certFile
        self.keyFile = keyFile
        self.sslVersion = sslVersion
        
    def handlerDispatch(self, tid, queue, handler):
        while True:
            conn, addr = queue.get()
            if not conn:
                return
            wrappedConn = ssl.wrap_socket(conn,
                                server_side=True,
                                certfile = self.certFile,
                                keyfile = self.keyFile,
                                ssl_version=self.sslVersion)
            handler.ready = True
            handler(wrappedConn, addr)
            conn.close()
    

if __name__ == "__main__":

    bigString = "Hello World!"*100000
    def hello_world_app(environ, start_response):
        status = '200 OK' # HTTP Status
        headers = [('Content-type', 'text/plain')] # HTTP Headers
        start_response(status, headers)

        # The returned object is going to be printed
        return [environ['PATH_INFO']]
        
    port = int(sys.argv[1])
    handler = AppHandler(hello_world_app, port)
    
#    http = HTTPListener(port = port, handler = handler)   
#    http = ParallelSocketListener(port = port, handler = handler)
    http = ThreadedSocketListener(port = port, handler = handler)
    try:
        http.serve()
    except KeyboardInterrupt:
        http.clearThreads()
        pass
   
    
    
