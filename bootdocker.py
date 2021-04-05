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
            proc
        print('END')



class DockerServer(socketserver.StreamRequestHandler,Docker):


    def handle(self):
        self.data = self.rfile.readline().decode()
        self.data = self.data.strip('\r\n')
        self.data = self.data.split(' ')
        if self.data:
            self.dispatcher()
        self.msg += '\n    Client disconnected: ' + str(self.client_address)
        logging.info(self.msg)

    def dispatcher(self):
        services = {'SSH': self.data[0], 'POST': self.data[0], 'GET': self.data[0]}
        s = [key for key in services if key == services[key]]
        if s:
            self.msg = 'Client with IP: ' + str(self.client_address[0])
            self.msg += '\n    Sending: ' + str(self.data)
            self.msg += '\n    Dispatching service: ' + s[0]
            try:
                eval('self.' + s[0].lower() + '()')
            except Exception as err:
                logging.info(error_trace(Exception,err))
                raise
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
        self.msg += '\n    Http request: ' + str(self.data)
        self.msg += '\n    Http headers: ' + str(self.httphead.keys())
        self.msg += '\n    Http values: ' + str(self.httphead.values())
        self.payload = self.payload.decode()
        self.msg += '\n    Data(decoded): ' + self.payload
        url = 'git_url'
        value = self.extract(self.payload,url)
        if value:
            url = value + '#main'
            self.msg += '\n    Docker lanched with: ' + url
            self.send_response(msg='Git handler posted\n')
            logging.info('Docker starts')
            resp = Docker(repo,tag,url).start()
            logging.info('Response from Docker object' + str(resp))
            logging.info('Docker ends')
        else:
            msg = 'POST requests with /git-bot:{botnam} requires payload to contain:\n'
            msg += '    git_url\n'
            self.send_response(status='400 Bad Request',msg=msg)

    def extract(self,content,key):
        '''Safely extracts content assuming json file'''
        if key in content:
            a = content.find(url)
            a -= 1
            value = content[a:]
            a = value.find(',')
            value = value[:a]
            a = value.find(':')
            value = value[a+1:]
            value = value.strip('"') 
            return value
        else:
            return False

    def post(self):
        self.httphead = http.client.parse_headers(self.rfile)
        c = int(self.httphead.get('Content-Length'))
        if c: self.payload = self.rfile.read(c)
        request = self.data[1]
        request = request.split(':')
        self.msg += '\n    Request: ' + str(request)
        if request[0] == '/git-bot' and len(request) > 1: 
            self.git('bots',request[1])
        else:
            msg = 'POST requests must contain:\n'
            msg += '    /git-bot:{botname}\n'
            msg += '    where botname is the name you give in docker run\n'
            self.msg += msg
            self.send_response(status='400 Bad Request',msg=msg)

    def send_response(self,status='200 OK',msg=False,title=False):
        if not title:
            title = 'Bot reply'
        if not msg:
            msg = self.boil_html('This is an autobot API service',title=title)
        else:
            msg = self.boil_html(msg,title=title)
        l = len(msg)
        msg = msg.encode()
        sendback = ('HTTP/1.1 %s\r\n' % status).encode()
        sendback += 'Content-Type: text/html\r\n'.encode()
        sendback += ('Content-Length: %s\r\n' % l).encode()
        sendback += b'\r\n'
        sendback += msg 
        self.request.sendall(sendback)

    def get(self):
        logs = self.data[1].split('?')
        if logs[0] == '/logs':
            self.msg += '\n    Sending log request'
            logs = self.get_log()
            self.send_response(msg=logs,title='Bot logs')
        else:
            self.send_response()

    def get_log(self,lines=1000):
        '''Opens log file rewrites from bottom to top all content.
        Returns string'''
        logs = []
        l = ''
        with open(args.file) as f:
            for line in f:
                if line[:2] == '  ':
                    l = logs.pop()
                    l += line
                    line = l
                logs.append(line)
        tmp = []
        while logs and lines:
            line = logs.pop()
            tmp.append(line)
            lines -= 1
        logs = ''
        for line in tmp:
            logs += line
        logs = '<pre>' + logs + '</pre>'
        return logs

    def boil_html(self,msg,title='Blank document'):
        '''Prepares a string of valid html document'''
        html = '<!DOCTYPE html>'
        html += '<html>'
        html += '<head>'
        html += '<meta charset="utf-8"/>'
        html += '<title>%s</title>' % title
        html += '</head>'
        html += '<body>'
        html += str(msg)
        html += '</body>'
        html += '</html>'
        return html

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
        print('Using default log storage path: ' + str(args.file))
    if not args.port:
        args.port = 2000
        print('Using default port to listen to on localhost: ' + str(args.port))
    #Logging to file
    tmp = logging.getLogger('bootdocker')
    tmp.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(args.file, maxBytes=40000,backupCount=1)
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
