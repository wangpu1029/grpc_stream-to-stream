import time

import grpc
import testrpc_pb2 as pb2
import testrpc_pb2_grpc as pb2_grpc

def make_OneToOne_call(stub):
    stub = pb2_grpc.TestRPCStub(channel)
    print(stub.OneToOne(pb2.Request(msg='Hello')))

def make_OneToStream_call(stub):
    for reply in stub.OneToStream(pb2.Request(msg='Hello')):
        print(reply)

def make_StreamToOne_call(stub):
    msg = 'Hello'
    splits = [ pb2.Request(msg=msg[i:i+1]) for i in range(len(msg)) ]
    print(stub.StreamToOne(iter(splits)))

def make_StreamToStream_call(stub, interval):
    def req_generator(msg):
        for i in range(len(msg)):
            yield pb2.Request(msg=msg[i:i+1])
            time.sleep(interval)
            
    msg = 'abcdefghijklmnopq'
    for reply in stub.StreamToStream(req_generator(msg)):
        print(reply.msg)
		
with grpc.insecure_channel('localhost:50051') as channel:
    stub = pb2_grpc.TestRPCStub(channel)
    make_OneToOne_call(stub)
    make_OneToStream_call(stub)
    make_StreamToOne_call(stub)
	
with grpc.insecure_channel('localhost:50051') as channel:
    stub = pb2_grpc.TestRPCStub(channel)
    make_StreamToStream_call(stub, 0.01)
