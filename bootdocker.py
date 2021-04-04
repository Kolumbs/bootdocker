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
    STARTED
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
        cmd = 'docker build --tag %s:%s %s' % (self.repo,self.tag,self.url)
        self.run(cmd)
        self.cons('stop')
        self.run('docker container prune -f')
        proc = self.run('docker run %s:%s' % (self.repo,self.tag),blocking=False)
        print('STARTED')
        while proc.returncode == None:
            proc.poll()
            time.sleep(20)
        print('FAIL')

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


class DockerServer(socketserver.StreamRequestHandler):
    
    
    def handle(self):
        logging.info('Client connected: ' + str(self.client_address))
        self.data = self.rfile.readline().decode()
        self.data = self.data.strip('\r\n')
        if self.data:
            logging.info('Client sending: ' + str(self.data))
            self.dispatcher()
        logging.info('Client disconnected: ' + str(self.client_address))

    def dispatcher(self):
        data = self.data.split(' ')
        logging.info(data)
        services = {'SSH': data[0], 'POST': data[0], 'GET': data[0]}
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

    def parse_http(self):
        self.httphead = http.client.parse_headers(self.rfile)
        logging.info(self.httphead.keys())
        logging.info(self.httphead.values())
            
    def post(self):
        try:
            self.parse_http()
            c = int(self.httphead.get('Content-Length'))
            self.payload = self.rfile.read(c)
            sendback = b'HTTP/1.1 200 OK\r\n'
            sendback += 'Content-Type: text/html\r\n'.encode()
            sendback += b'\r\n'
            sendback += ('<html><body><pre>%s</pre></html>\r\n').encode()
            self.request.send(sendback)
            logging.info('Sent everything')
            bootdocker.start()
            logging.info('Docker lanched')
        except Exception as err:
            logging.info('error needs traceback implementation')
            logging.info(error_trace(Exception,err))
            logging.info('traceback implemented')
            raise

    def get(self):
        data = self.rfile.readline()
        while data:
            logging.info(data)
            msg = data
            data = self.rfile.readline()
            msg += data
            if data == b'\r\n':
                logging.info('Sending back:')
                sendback = b'HTTP/1.1 200 OK\r\n'
                sendback += 'Content-Type: text/html\r\n'.encode()
                sendback += b'\r\n'
                sendback += ('<html><body><pre>%s</pre></html>\r\n' % msg).encode()
                self.request.sendall(sendback)
                logging.info(sendback)
                break


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


if __name__ == '__main__':
    print('Loading system . . .')
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
