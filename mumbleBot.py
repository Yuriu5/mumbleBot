#!/usr/bin/env python

import socket
import os
import sys

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



messageLookupMessage={Mumble_pb2.Version:0,Mumble_pb2.UDPTunnel:1,Mumble_pb2.Authenticate:2,Mumble_pb2.Ping:3,Mumble_pb2.Reject:4,Mumble_pb2.ServerSync:5,
        Mumble_pb2.ChannelRemove:6,Mumble_pb2.ChannelState:7,Mumble_pb2.UserRemove:8,Mumble_pb2.UserState:9,Mumble_pb2.BanList:10,Mumble_pb2.TextMessage:11,Mumble_pb2.PermissionDenied:12,
        Mumble_pb2.ACL:13,Mumble_pb2.QueryUsers:14,Mumble_pb2.CryptSetup:15,Mumble_pb2.ContextActionAdd:16,Mumble_pb2.ContextAction:17,Mumble_pb2.UserList:18,Mumble_pb2.VoiceTarget:19,
        Mumble_pb2.PermissionQuery:20,Mumble_pb2.CodecVersion:21}    



s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

ssl_sock = ssl.wrap_socket(s, ca_certs="./", cert_reqs=ssl.CERT_REQUIRED)
ssl_sock.connect("localhost", 64738)

ssl_sock.close()
