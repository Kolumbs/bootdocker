'''Module provides quick solution for auto-deploying docker from git.

Wish: 
    -> have argument handler, when running from terminal: python3 bootdocker.py
    -> test against older versions than 3.7, as older not supported
        Subprocess:
        Changed in version 3.7: Added the text parameter, as a more understandable alias of universal_newlines. Added the capture_output parameter


Simple usage:
'''

import subprocess
import time
import platform
import socketserver
import socket
import http.client
import traceback
import logging
import logging.handlers
import _thread


def error_trace(exc,error):
    '''Adds stack trace and returns it.'''
    stack = traceback.format_exception(exc,error,error.__traceback__)
    msg = ''
    for item in stack:
        msg += item
    return msg


class Docker():
    '''
    Manages docker images by building them, starting and running. 
    
    Starts docker and returns STARTED, if docker fails at any time issues FAILED
    >>> url = 'git@github.com:Kolumbs/bootdocker.git#main:test'
    >>> Docker('bot','demo',url).start()
    <STARTED>
    '''


    def __init__(self,repo,tag,git_url):
        self.repo = repo
        self.tag = tag
        self.url = git_url

    def run(self,program,log=True,blocking=True):
        '''Runs program and returns completed process.
        program - string of shell command
        log - set to True if Stdout must be logged not returned
        blocking - set to False to not wait for return'''
        logging.info('Calling shell: ' + program)
        logs = []
        #Implements workaround for Python 3.7 and below
        py_ver = platform.python_version()
        if py_ver[0] == '3':
            nums = py_ver.split('.')
            nums = int(nums[1])
            logging.info(nums)
            logging.info(nums >= 8)
            logging.info(nums <= 8)
        else:
            logging.info(py_ver)
        proc = subprocess.Popen(program,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        proc.poll()
        if blocking: proc.wait()
        if log: logs += proc.stdout.readlines()
        if proc.returncode != 0 and proc.returncode != None: logs += proc.stderr.readlines()
        for log in logs:
            log = log.strip(b'\n')
            if log: logging.info(log)
        return proc

    def cons(self,job):
        '''Defines what to do with existing containers by job.
        stop - stop all containers and wait while confirmed 
        wait - wait for all containers to finish
        '''
        containers = self.run('docker container ls -aq',log=False)
        for con in containers.stdout.readlines():
            con = con.strip(b'\n')
            if job == 'stop': self.run('docker container stop %s' % con)
            self.run('docker container wait %s' % con,log=False)

    def start(self):
        print('STARTED')
        cmd = 'docker build --tag %s:%s %s' % (self.repo,self.tag,self.url)
        self.run(cmd)
        print('BUILT')
        self.cons('stop')
        self.run('docker container prune -f')
        proc = self.run('docker run %s:%s' % (self.repo,self.tag),blocking=False)
        print('STARTED RUN')
        while proc.returncode == None:
            time.sleep(2)
            proc.poll()
            if not proc.returncode == None or not proc.returncode == 0:
                print('Program ends with error code: ' + str(proc.returncode))
                for line in proc.stderr.readlines():
                    print(line.decode())
            else:
                print('Program has finished succesfully with code: ' + str(proc.returncode))
            time.sleep(20)
        print('END')

    def writer(self,sec='No'):
        '''Opens a file-like object and rewrites from bottom to top all content
        sec - provide a value to loop forever with this interval'''
        while True:
            new_file = []
            with open(args.fileIn) as data:
                for line in data:
                    new_file.append(line)
            with open(args.fileOut,mode='w') as data:
                while new_file:
                    line = new_file.pop()
                    data.write(line)
            if sec == 'No': break
            time.sleep(sec)


class DockerServer(socketserver.StreamRequestHandler,Docker):


    def handle(self):
        logging.info('Client connected: ' + str(self.client_address))
        self.data = self.rfile.readline().decode()
        self.data = self.data.strip('\r\n')
        self.data = self.data.split(' ')
        if self.data:
            logging.info('Client sending: ' + str(self.data))
            self.dispatcher()
        logging.info('Client disconnected: ' + str(self.client_address))

    def dispatcher(self):
        services = {'SSH': self.data[0], 'POST': self.data[0], 'GET': self.data[0]}
        s = [key for key in services if key == services[key]]
        logging.info('Services found: ' + str(s))
        if s:
            logging.info('Dispatching service: ' + s[0])
            eval('self.' + s[0].lower() + '()')
        else:
            logging.info('No matching service found')

    def ssh(self):
        myPort = ('localhost', 22002)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(myPort)
            s.sendall(self.data)
            sfile = s.makefile()
            data = sfile.readline()
            if data:
                logging.info('Received back from ssh service: ' + str(data))
                self.request.sendall(data)
                while True:
                    data = self.rfile.readline()
                    if not data: break
                    logging.info('Receiving from ssh client:\n ' + str(data))
                    s.sendall(data)
                    data = sfile.readline()
                    if not data: break
                    logging.info('Receiving from ssh service:\n ' + str(data))
                    self.request.sendall(data)

    def git(self,repo,tag):
        logging.info('Read json from git webhook')
        logging.info('Http request: ' + str(self.data))
        logging.info('Http headers: ' + str(self.httphead.keys()))
        logging.info('Http values: ' + str(self.httphead.values()))
        logging.info('Data sent: ' + str(self.payload))
        self.payload = self.payload.decode()
        logging.info('Data decoded: ' + self.payload)
        url = 'git_url'
        logging.info('git_url test: ' + str(url in self.payload))
        if url in self.payload:
            a = self.payload.find(url)
            a -= 1
            url = self.payload[a:]
            a = url.find(',')
            url = url[:a]
            logging.info('Url stage 1: ' + url)
            a = url.find(':')
            url = url[a+1:]
            logging.info('Url stage 2: ' + url)
            url = url.strip('"') + '#main'
            logging.info('Docker lanched with: ' + url)
            Docker(repo,tag,url).start()
            logging.info('Docker ends')

    def post(self):
        try:
            self.httphead = http.client.parse_headers(self.rfile)
            c = int(self.httphead.get('Content-Length'))
            self.payload = self.rfile.read(c)
            self._testdata()
            request = self.data[1]
            request = request.split(':')
            logging.info('Request: ' + str(request))
            if request[0] == '/git-bot': 
                self.send_response(msg='Git handler posted\n')
                self.git('bots',request[1])
            else:
                self.send_response()

        except Exception as err:
            logging.info('error needs traceback implementation')
            logging.info(error_trace(Exception,err))
            logging.info('traceback implemented')
            raise

    def send_response(self,status='200 OK',msg=False):
        if not msg:
            msg = '<html><body><pre>This is an autobot API service</pre></html>\r\n'
        l = len(msg)
        msg = msg.encode()
        sendback = ('HTTP/1.1 %s\r\n' % status).encode()
        sendback += 'Content-Type: text/html\r\n'.encode()
        sendback += ('Content-Length: %s\r\n' % l).encode()
        sendback += b'\r\n'
        sendback += msg 
        self.request.sendall(sendback)
        logging.info(sendback)


    def get(self):
        data = self.rfile.readline()
        while data:
            logging.info(data)
            msg = data
            data = self.rfile.readline()
            msg += data
            if data == b'\r\n':
                logging.info('Sending back:')
                self.send_response()
                break

    def _testdata(self):
         logging.info('-'*40 + '\n' + 'Log full received message:')
         logging.info('Http request: ' + str(self.data))
         logging.info('Http headers: ' + str(self.httphead.keys()))
         logging.info('Http values: ' + str(self.httphead.values()))
         logging.info('Data sent: ' + str(self.payload))

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


if __name__ == '__main__':
    print('Loading system ...')
    import argparse

    #Arguments for the software
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, help="log file to read and write")
    parser.add_argument('--port', type=int, help="file to write upside down")
    parser.add_argument('--test', help="perform system test",action="store_true")
    args = parser.parse_args()
    if not args.file:
        args.file = '/tmp/bootdocker'
    if not args.port:
        args.port = 2000
    #Logging to file
    tmp = logging.getLogger('bootdocker')
    tmp.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(args.file, maxBytes=2000)
    fmt = '%(asctime)s %(message)s'
    dt = '%m/%d/%Y %H:%M:%S'
    format = logging.Formatter(fmt,dt)
    handler.setFormatter(format)
    tmp.addHandler(handler)
    logging = tmp
    tmp = None
    if args.test:
        import sys
        import doctest
        doctest.testmod()
        sys.exit()
    myPort = ('', args.port)
    print('Real-time logs are to be found in: ' + args.file)
    try:
        with ThreadedTCPServer(myPort, DockerServer) as server:
            logging.info('Server started listening on port: ' + str(myPort))
            server.serve_forever()
    except PermissionError as perm:
        print('Application stack trace:')
        print(error_trace(Exception,perm))
        print('Permission error: please run with elevated privileges')
    except Exception as err:
        print(error_trace(Exception,err))
