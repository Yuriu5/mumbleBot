#!/usr/bin/env python

import socket
import os
import sys
import platform
import struct

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

for i in messageLookupMessage.keys():
        messageLookupNumber[messageLookupMessage[i]]=i


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
        rcvMess = Mumble_pb2.CryptSetup()



    def packageMessageForSending(self,msgType,stringMessage):
        length=len(stringMessage)
        return struct.pack(headerFormat,msgType,length)+stringMessage

    def readTotally(self, size-len):
        message=""
        while len(message)<size:
            received = self.socket.recv(size-len(message))
            message+=received
        return message

    def readPacket(self):
        meta=self.readTotally(6)
        msgType, length=struct.unpack(headerFormat, meta)
        stringMessage=self.readTotally(length)
        #Type 7
        if msgType==7
            message=self.parseMessage(msgType, stringMessage)
            self.session=message.session

    def parseMessage(self,msgType,stringMessage):
        msgClass=messageLookupNumber[msgType]
        message=msgClass()
        message.ParseFromString(stringMessage)
        return message



def main():

    connection=connexionMumble('localhost', 64738, 'Yuriu', 'Channel1', 'derp')
    connection.connexion()

if __name__ == '__main__':
        main()