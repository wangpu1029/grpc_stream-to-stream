import time

import queue as lib_queue
import threading

from concurrent import futures

import grpc
import testrpc_pb2 as pb2
import testrpc_pb2_grpc as pb2_grpc
import pickle

class Buffer(object):
    """A bounded buffer which prefers newer items. We assume only one producer and one consumer."""

    def __init__(self, maxsize):
        self.buf = lib_queue.Queue(maxsize=maxsize)
        self.maxsize = maxsize

    def get(self, *args, **kwargs):
        return self.buf.get(*args, **kwargs)

    def put(self, item):
        while True:
            try:
                self.buf.put(item, timeout=0.05)
                break
            except lib_queue.Full:            
                dropped = self.buf.get()
                print('Dropped', dropped)
                
    def qsize(self):
        return self.buf.qsize()
		
class Listener(threading.Thread):

    def __init__(self, request_iter, buffer, remote_off):
        super(Listener, self).__init__()
        self.request_iter = request_iter
        self.buffer = buffer
        self.remote_off = remote_off

    def run(self):
        print("starting listening!!!!!!!!!!")
        for r in self.request_iter:
            req = pickle.loads(r.msg)
            print("got:", req)
            self.buffer.put(req)
        self.remote_off.put(True)

class Worker(threading.Thread):
    
    def __init__(self, buffer, results, remote_off, local_off):
        super(Worker, self).__init__()
        self.buffer = buffer
        self.results = results
        self.remote_off = remote_off
        self.local_off = local_off
        
    def run(self):
        print("start working!!!!!!!")
        while True:
            try:
                r = self.buffer.get(timeout=0.1)
                time.sleep(2)  # emulate processing
                self.results.put((r))
            except lib_queue.Empty:            
                try:
                    self.remote_off.get(block=False)
                    self.local_off.put(True)
                    break
                except lib_queue.Empty:
                    pass

# class Servie(Thread):
    
#     def __init__(self, flag, request_iter):
#         super(Servie, self).__init__()
#         self.flag = flag
#         self.request_iter = request_iter

#     def run(self):
#         print("start serving!!!!!!!!!!!!!", flush=True)
#         buffer = Buffer(3)
#         results = lib_queue.Queue()
#         remote_off = lib_queue.Queue()
#         local_off = lib_queue.Queue()
        
#         threads = []
#         threads.append(Listener(self.request_iter, buffer, remote_off))
#         threads.append(Worker(buffer, results, remote_off, local_off))
#         for t in threads:
#             t.start()
#         for t in threads:
#             t.join()
#         print("one client is done!!!!!!!!!!")
#         self.flag = True

class TestRPCServicer(pb2_grpc.TestRPCServicer):

    def __init__(self):
        pass

    def OneToOne(self, request, context):
        return pb2.Reply(msg=request.msg)

    def OneToStream(self, request, context):
        for i in range(len(request.msg)):
            yield pb2.Reply(msg=request.msg[i:i+1])

    def StreamToOne(self, request_iter, context):
        all_bytes = []
        for r in request_iter:
            all_bytes.append(r.msg)
        return pb2.Reply(msg=b''.join(all_bytes))

    def StreamToStream(self, request_iter, context):
        buffer = Buffer(3)
        results = lib_queue.Queue()
        remote_off = lib_queue.Queue()
        local_off = lib_queue.Queue()
        try:
            threads = []
            threads.append(Listener(request_iter, buffer, remote_off))
            threads.append(Worker(buffer, results, remote_off, local_off))
            for t in threads:
                t.start()
        except:
            print("error when starting a thread")
        while True:
            try:
                msg = results.get(timeout=0.1)
                yield pb2.Reply(msg=pickle.dumps(msg))
            except lib_queue.Empty:
                if local_off.qsize():
                    break
           
        print("Smoothly stopped.")

try:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    pb2_grpc.add_TestRPCServicer_to_server(TestRPCServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()
except KeyboardInterrupt:
    pass		
