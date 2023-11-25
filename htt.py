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
                if jrequest["Step"]=="0":
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
    obj["Timing"][tkey].append(tval)    
    if len(obj["Timing"][tkey])>timecounts:
        obj["Timing"][tkey].pop(0) #drop first in list
    return


def TimeMeasurement(service,xtdata):
    tdata={}
    #dont sent everything, just enough to get server time
    for keys in ["CMD","Step","Client"]:
        tdata[keys]=xtdata[keys]    
    encoded_data = json.dumps(tdata).encode('utf-8')
    with urllib.request.urlopen(service, data=encoded_data) as response:
        if response.getcode()==200:
            clientRestResvTime=time.time()
            responsedata=response.read().decode('utf-8')
            jresponsedata=json.loads(responsedata)
            svrtime=jresponsedata["ServerTime"]
            idx=min(int(xtdata["Step"]),timecounts-1)
            AddTime("ClientRspResvTimes",xtdata,clientRestResvTime)
            AddTime("ServerRspSentTimes",xtdata,svrtime)
            print(json.dumps(xtdata,indent=" "))
            AddTime("ServerTimeOffset",xtdata,float(svrtime)-float(xtdata["Timing"]["ServerTimeEstimate"][idx]))
            AddTime("NetworkLatency",xtdata,float(clientRestResvTime)-float(xtdata["Timing"]["ClientReqSentTimes"][idx]))
            xtdata["Step"]=str(int(xtdata["Step"])+1)

def ServerArchiveUpdate(service,tdata):
    tdata["CMD"]="Archive"
    encoded_data = json.dumps(tdata).encode('utf-8')
    with urllib.request.urlopen(service, data=encoded_data) as response:
        if response.getcode()==200:
            responsedata=response.read().decode('utf-8')
            jresponsedata=json.loads(responsedata)

def calcoffset(tdata):
    track=[]
    idx=1
    for vals in tdata["Timing"]["ServerTimeEstimate"]:
        tguess=float(tdata["Timing"]["ServerTimeEstimate"][-idx])
        tactual=float(tdata["Timing"]["ServerRspSentTimes"][-idx])
        toffset=float(tdata["Timing"]["EstimatedOffset"][-idx])
        nextoffset=toffset+(tactual-tguess)
        track.append(nextoffset)
        idx=idx+1
    #track has last data first.
    weight=timecounts+1
    runningsum=0
    runningweight=0
    for offsets in track:
        runningsum+=offsets*weight
        runningweight+=weight
        weight-=1
    weightedoffset=runningsum/runningweight
    return weightedoffset


def client_requests(clnt,port):
    clientkeyname=client_setup()
    service = "http://"+clnt+":"+port
    tdata = {
        "CMD":"TimeTool",
        "Client": clientkeyname,
        "Timing" :{
            "ClientReqSentTimes": [], #Client's local time at the point of sending
            "ServerTimeEstimate": [], #Client's estimate of server time. Initial matches client
            "EstimatedOffset": [], #Client's estimate of server time. Initial matches client
            "ServerRspSentTimes": [], #Time server responds with
            "ServerTimeOffset": [],   #Calculated offset of estimate vs server's time
            "ClientRspResvTimes": [], #Time the client gets the server's response
            "NetworkLatency": [],     #time from client sending req and getting resp
        },
        "Step": "0"
        }
    Step=0
    while True:
        now=time.time()
        AddTime("ClientReqSentTimes",tdata,now)
        if Step>0:
            eoffset=calcoffset(tdata)
            AddTime("ServerTimeEstimate",tdata,now+eoffset)
            AddTime("EstimatedOffset",tdata,eoffset)
        else:
            AddTime("ServerTimeEstimate",tdata,now)
            AddTime("EstimatedOffset",tdata,0)

        TimeMeasurement(service,tdata)
        ServerArchiveUpdate(service,tdata)
        
        print(json.dumps(tdata,indent="  "))
        print("---------------")
        time.sleep(0.5)
        Step+=1

       

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
        
