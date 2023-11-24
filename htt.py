#!/usr/bin/env python3
import socketserver
import http.server
import socket
import sys
import time
import urllib
import urllib.request
import json
import hashlib

serverqueryarchive={}
timecounts=10

class Handler(http.server.BaseHTTPRequestHandler):
    '''   use our own handlers functions '''

    def sendtextinfo(self, code, text):
        self.send_response(code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        if type(text)==type([]):
            for lines in text:
                self.wfile.write((str(lines)+"\n").encode())
        else:
            self.wfile.write((str(text)+"\n").encode())

    def do_GET(self):
        '''   handle get   '''
        tnow = time.time()
        gnow = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(tnow)) #Formatted UTC time
        parsed_data = urllib.parse.urlparse(self.path)
        path=parsed_data.geturl().lower()
        if path == "/time":
            message = "Server Time: "+str(gnow)
        elif path == "/history":
            archivetext=json.dumps(serverqueryarchive,indent=" ")
            message = f"<pre>{archivetext}</pre>"
        else : message="This is HTTP Timing Tool"
        self.sendtextinfo(200,message)

    def do_POST(self):
        '''   handle post like rest API   '''
        try: #try getting the bytestream of the request
            content_length = int(self.headers['Content-Length'])
        except Exception as err:
            print("malformed headers")
            self.sendtextinfo(200,str(err))
            return

        if content_length > 0:
            rawrequest = self.rfile.read(content_length).decode('utf-8')
            print("Received POST: {}".format(rawrequest))
            try:
                jrequest = json.loads(rawrequest)
            except BaseException as anError:
                self.sendtextinfo(200,"Error in JSON: {}".format(str(anError)))
                return
        if "CMD" in jrequest:
            if jrequest["CMD"]=="TimeTool":
                clientip,clientport=self.client_address
                if jrequest["Stage"]=="0":
                    svrtime=time.time()
                    sresponse={
                        "ClientIPatServer":str(clientip),
                        "ServerTime":str(svrtime)
                    }
                    self.sendtextinfo(200,json.dumps(sresponse))
                    return
            if jrequest["CMD"]=="Archive":
                clientip,clientport=self.client_address
                serverqueryarchive[jrequest["Client"]]=jrequest
                svrtime=time.time()
                sresponse={
                    "ClientIPatServer":str(clientip),
                    "ServerTime":str(svrtime)
                }
                self.sendtextinfo(200,json.dumps(sresponse))
                return
                    
                    
        print(jrequest)
        self.sendtextinfo(200,"No operation for your request: {}".format(rawrequest))
        return

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    '''    Basic threaded server class    '''
    http.server.HTTPServer.request_queue_size = 128


def client_setup():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print("Client is {} at {}".format(hostname,local_ip))
    codestring="{}-{}".format(hostname,local_ip)
    #clientkeyname=hashlib.md5(codestring.encode("utf-8")).hexdigest()
    clientkeyname=codestring
    print("Client unique name is  {}".format(clientkeyname))
    return clientkeyname

def AddTime(tkey,obj,tval):
    #does not need to return, dict passes by reference!
    idx=int(obj.get("Stage"))
    if idx>=timecounts:
        obj[tkey]=obj[tkey].pop(0) #drop first in list
        obj[tkey].append(tval)
    else:
        obj[tkey][idx]=tval
    return


def TimeMeasurement(service,tdata):
    encoded_data = json.dumps(tdata).encode('utf-8')
    with urllib.request.urlopen(service, data=encoded_data) as response:
        if response.getcode()==200:
            responsedata=response.read().decode('utf-8')
            jresponsedata=json.loads(responsedata)
            AddTime("ServerRspSentTimes",tdata,jresponsedata["ServerTime"])
            AddTime("ClientRspResvTimes",tdata,time.time())

def ServerArchiveUpdate(service,tdata):
    tdata["CMD"]="Archive"
    encoded_data = json.dumps(tdata).encode('utf-8')
    with urllib.request.urlopen(service, data=encoded_data) as response:
        if response.getcode()==200:
            responsedata=response.read().decode('utf-8')
            jresponsedata=json.loads(responsedata)


def client_requests(clnt,port):
    clientkeyname=client_setup()
    service = "http://"+clnt+":"+port
    tdata = {
        "CMD":"TimeTool",
        "Client": clientkeyname,
        "ClientReqSentTimes": [0]*timecounts,
        "ServerRspSentTimes": [0]*timecounts,
        "ClientRspResvTimes": [0]*timecounts,
        "Stage": "0"
        }
    AddTime("ClientReqSentTimes",tdata,time.time())
    TimeMeasurement(service,tdata)
    ServerArchiveUpdate(service,tdata)
    print(json.dumps(tdata,indent="  "))

       

if __name__=="__main__":
    args=sys.argv
    port=None
    clnt=None
    if "-p" in args: port=args[args.index("-p")+1]
    if "-c" in args: clnt=args[args.index("-c")+1] #client of ...
        
    helptext = f"Usage:\nserver -> {args[0]} -p [port]\nclient -> {args[0]} -p [port] -c [serverip]\n"
    if (port==None):
        print(helptext)
        sys.exit(0)

    if (clnt==None): # if not a client
        port=int(port)
        HTSERVER = ThreadedHTTPServer(('', port), Handler)
        try:
            while 1:
                sys.stdout.flush()
                HTSERVER.handle_request()
        except KeyboardInterrupt:
            print("Server Stopped")
    else: # else run in client mode
        client_requests(clnt,port)
        
