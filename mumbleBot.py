#!/usr/bin/env python

import socket
import os
import sys
import platform
import struct
import thread
import threading
import collections
import time
import select

try:
    import ssl
except:
    warning+="WARNING: This python program requires the python ssl module (available in python 2.6; standalone version may be at found http://pypi.python.org/pypi/ssl/)\n"
try:
    import Mumble_pb2
except:
    warning+="WARNING: Module Mumble_pb2 not found\n"
    warning+="This program requires the Google Protobuffers library (http://code.google.com/apis/protocolbuffers/) to be installed\n"
    warning+="You must run the protobuf compiler \"protoc\" on the Mumble.proto file to generate the Mumble_pb2 file\n"
    warning+="Move the Mumble.proto file from the mumble source code into the same directory as this bot and type \"protoc --python_out=. Mumble.proto\"\n"


headerFormat=">HI"
messageLookupMessage={Mumble_pb2.Version:0,Mumble_pb2.UDPTunnel:1,Mumble_pb2.Authenticate:2,Mumble_pb2.Ping:3,Mumble_pb2.Reject:4,Mumble_pb2.ServerSync:5,
        Mumble_pb2.ChannelRemove:6,Mumble_pb2.ChannelState:7,Mumble_pb2.UserRemove:8,Mumble_pb2.UserState:9,Mumble_pb2.BanList:10,Mumble_pb2.TextMessage:11,Mumble_pb2.PermissionDenied:12,
        Mumble_pb2.ACL:13,Mumble_pb2.QueryUsers:14,Mumble_pb2.CryptSetup:15,Mumble_pb2.ContextActionAdd:16,Mumble_pb2.ContextAction:17,Mumble_pb2.UserList:18,Mumble_pb2.VoiceTarget:19,
        Mumble_pb2.PermissionQuery:20,Mumble_pb2.CodecVersion:21}    
messageLookupNumber={}
threadNumber=0;

for i in messageLookupMessage.keys():
        messageLookupNumber[messageLookupMessage[i]]=i


class timedWatcher(threading.Thread):
    def __init__(self, plannedPackets,socketLock,socket):
        global threadNumber
        threading.Thread.__init__(self)
        self.plannedPackets=plannedPackets
        self.pingTotal=1
        self.isRunning=True
        self.socketLock=socketLock
        self.socket=socket
        i = threadNumber
        threadNumber+=1
        self.threadName="Thread " + str(i)

    def stopRunning(self):
        self.isRunning=False

    def run(self):
        self.nextPing=time.time()-1

        while self.isRunning:
            t=time.time()
            if t>self.nextPing:
                pbMess = Mumble_pb2.Ping()
                pbMess.timestamp=(self.pingTotal*5000000)
                pbMess.good=0
                pbMess.late=0
                pbMess.lost=0
                pbMess.resync=0
                pbMess.udp_packets=0
                pbMess.tcp_packets=self.pingTotal
                pbMess.udp_ping_avg=0
                pbMess.udp_ping_var=0.0
                pbMess.tcp_ping_avg=50
                pbMess.tcp_ping_var=50
                self.pingTotal+=1
                packet=struct.pack(headerFormat,3,pbMess.ByteSize())+pbMess.SerializeToString()
                self.socketLock.acquire()
                while len(packet)>0:
                    sent=self.socket.send(packet)
                    packet = packet[sent:]
                self.socketLock.release()
                self.nextPing=t+5
            if len(self.plannedPackets) > 0:
                if t > self.plannedPackets[0][0]:
                    self.socketLock.acquire()
                    while t > self.plannedPackets[0][0]:
                        event = self.plannedPackets.popleft()
                        packet = event[1]
                        while len(packet)>0:
                            sent=self.socket.send(packet)
                            packet = packet[sent:]
                        if len(self.plannedPackets)==0:
                            break
                    self.socketLock.release()
            sleeptime = 10
            if len(self.plannedPackets) > 0:
                sleeptime = self.plannedPackets[0][0]-t
            altsleeptime=self.nextPing-t
            if altsleeptime < sleeptime:
                sleeptime = altsleeptime
            if sleeptime > 0:
                time.sleep(sleeptime)
        print time.strftime("%a, %d %b %Y %H:%M:%S +0000"),self.threadName,"timed thread going away"




class connexionMumble():
    def __init__(self, host=None, port=None,  nickname=None, channel=None, password=None):
        tcpSock=socket.socket(type=socket.SOCK_STREAM)
        self.socket=ssl.wrap_socket(tcpSock,ssl_version=ssl.PROTOCOL_TLSv1)
        self.host=host
        self.port=port
        self.nickname=nickname
        self.channel=channel
        self.password=password
        self.session=None
        self.timedWatcher = None
        self.cryptKey = None
        self.plannedPackets=collections.deque()
        self.socketLock=thread.allocate_lock()
        self.threadName="main thread"
        self.endBot = False


    def connexion(self):

        self.socket.connect((self.host,self.port))

        ## VERSION ECHANGE ##
        pbMess = Mumble_pb2.Version()
        pbMess.release="1.2.0"
        pbMess.version=66048
        pbMess.os=platform.system()
        pbMess.os_version="YURIUBOTISBACK"
        messageToSend = self.packageMessageForSending(messageLookupMessage[type(pbMess)], pbMess.SerializeToString())        
        self.socket.send(messageToSend)

        ## AUTHENTIFICATION ##
        pbMess = Mumble_pb2.Authenticate()
        pbMess.username="Yuriubotlolz"
        pbMess.password="derp"
        messageToSend = self.packageMessageForSending(messageLookupMessage[type(pbMess)], pbMess.SerializeToString())
        self.socket.send(messageToSend)

        ## CRYPT SETUP ##
        #pbMess = Mumble_pb2.CryptSetup()

        



    def packageMessageForSending(self,msgType,stringMessage):
        length=len(stringMessage)
        return struct.pack(headerFormat,msgType,length)+stringMessage

    def readTotally(self, size):
        message=""
        while len(message)<size:
            received = self.socket.recv(size-len(message))
            message+=received
        return message

    def readPacket(self):
        meta=self.readTotally(6)
        msgType, length=struct.unpack(headerFormat, meta)
        stringMessage=self.readTotally(length)
        #type 15 = CryptSetup
        if msgType==15:
            message=self.parseMessage(msgType,stringMessage)
            self.cryptKey=message.key;
        #Type 5 = ServerSync
        if msgType==5:
            message=self.parseMessage(msgType,stringMessage)
            self.session=message.session
        #Type 7 = ChannelState
        if msgType==7:
            message=self.parseMessage(msgType,stringMessage) 
        #Type 9 = UserState
        if msgType==9:
            message=self.parseMessage(msgType,stringMessage)
        #Type 11 = TextMessage
        if msgType==11:
            message=self.parseMessage(msgType, stringMessage)
            if message.message=='!stop':
                self.endBot=True


    def parseMessage(self,msgType,stringMessage):
        msgClass=messageLookupNumber[msgType]
        message=msgClass()
        message.ParseFromString(stringMessage)
        return message

    def run(self):
        self.timedWatcher = timedWatcher(self.plannedPackets,self.socketLock,self.socket)
        self.timedWatcher.start()
        print time.strftime("%a, %d %b %Y %H:%M:%S +0000"),self.threadName,"started timed watcher",self.timedWatcher.threadName

        sockFD=self.socket.fileno()
        while self.endBot==False:
            pollList,foo,errList=select.select([sockFD],[],[sockFD])
            for item in pollList:
                if item==sockFD:
                    self.readPacket()

        if self.timedWatcher:
            self.timedWatcher.stopRunning()



def main():

    bot=connexionMumble('localhost', 64738, 'Yuriu', 'Channel1', 'derp')
    pp=bot.plannedPackets
    bot.connexion()
    bot.run()

if __name__ == '__main__':
        main()