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
from varint_2 import *

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
headerFormat_data=">BBB"
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
        self.readMusicOn = False
        self.file = open('..\Feather.opus', 'r')
        self.debug = 0


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
        pbMess.username=self.nickname
        pbMess.password=self.password
        messageToSend = self.packageMessageForSending(messageLookupMessage[type(pbMess)], pbMess.SerializeToString())
        self.socket.send(messageToSend)



    def decodePDSInt(self,m,si=0):
        v = ord(m[si])
        if ((v & 0x80) == 0x00):
            return ((v & 0x7F),1)
        elif ((v & 0xC0) == 0x80):
            return ((v & 0x4F) << 8 | ord(m[si+1]),2)
        elif ((v & 0xF0) == 0xF0):
            if ((v & 0xFC) == 0xF0):
                return (ord(m[si+1]) << 24 | ord(m[si+2]) << 16 | ord(m[si+3]) << 8 | ord(m[si+4]),5)
            elif ((v & 0xFC) == 0xF4):
                return (ord(m[si+1]) << 56 | ord(m[si+2]) << 48 | ord(m[si+3]) << 40 | ord(m[si+4]) << 32 | ord(m[si+5]) << 24 | ord(m[si+6]) << 16 | ord(m[si+7]) << 8 | ord(m[si+8]),9)
            elif ((v & 0xFC) == 0xF8):
                result,length=decodePDSInt(m,si+1)
                return(-result,length+1)
            elif ((v & 0xFC) == 0xFC):
                return (-(v & 0x03),1)
            else:
                print time.strftime("%a, %d %b %Y %H:%M:%S +0000"),"Help Help, out of cheese :("
                sys.exit(1)
        elif ((v & 0xF0) == 0xE0):
            return ((v & 0x0F) << 24 | ord(m[si+1]) << 16 | ord(m[si+2]) << 8 | ord(m[si+3]),4)
        elif ((v & 0xE0) == 0xC0):
            return ((v & 0x1F) << 16 | ord(m[si+1]) << 8 | ord(m[si+2]),3)
        else:
            print time.strftime("%a, %d %b %Y %H:%M:%S +0000"),"out of cheese?"
            sys.exit(1)    

        
    def packageMessageForSending(self,msgType,stringMessage):
        length=len(stringMessage)
        print length
        return struct.pack(headerFormat,msgType,length)+stringMessage

    def packageDataForSending(self, stringMessage, sequence, nbFrame):
        total_length=len(stringMessage)
        length=total_length
        session_varint = encode_varint(0)
        sequence_varint =  encode_varint(sequence)
        print 'Debug : '
        print 'Type(sequence) : ' + type(sequence)
        print 'Type(sequence_varint) : ' + type(sequence)
        if nbFrame==7:
            header=0xFF
        else:
            header=0x7F
#        if sequence%7==0:
        return struct.pack(headerFormat_data, 0x0, ord(sequence_varint), header) + stringMessage
#        else:
#            return chr(header) + stringMessage


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
            self.debug=1
            print 'debug'
            #self.playMusic()
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
            if message.message=='!music':
                test = 1
                while True:
                    self.playMusic()
        #Type 1 = Data
        if msgType==1:
            test = stringMessage
            session,sessLen=self.decodePDSInt(stringMessage,1)
            #print stringMessage
            #print sessLen

    def parseMessage(self,msgType,stringMessage):
        msgClass=messageLookupNumber[msgType]
        message=msgClass()
        message.ParseFromString(stringMessage)
        return message

    def playMusic(self):
        data = self.file.read(127)
        sequence = 0
        counter = 0
        message = ''
        while len(data) != 0:
            sequence = (sequence+7)
            message += self.packageDataForSending(data, sequence, counter)
            data = self.file.read(127)
            counter = (counter + 1)%7
            if counter == 0:
                 to_send = self.packageMessageForSending(1, message)
                 self.socket.send(to_send)
                 message=''
        self.file.close()
        self.file = open('..\Feather.opus', 'r')

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

    bot=connexionMumble('localhost', 64738, 'SWAGGY DOGGY', 'Channel1', 'derp')
    pp=bot.plannedPackets
    bot.connexion()
    bot.run()

if __name__ == '__main__':
        main()
