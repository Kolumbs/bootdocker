'''Module provides quick solution for auto-deploying docker from git.

Wish: 
    -> have argument handler, when running from terminal: python3 bootdocker.py
    -> test against older versions than 3.7, as older not supported
        Subprocess:
        Changed in version 3.7: Added the text parameter, as a more understandable alias of universal_newlines. Added the capture_output parameter

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




class Util():

    def __init__(self,log_file):
        self.log_message = ''
        self.file = log_file

    def log(self,msg,post=False,buf_clear=True):
        if not self.log_message:
            self.log_message += msg + '\n'
        elif post:
            self.log_message += ' '*4 + str(msg)
        else:
            self.log_message += ' '*4 + str(msg) + '\n'
        if post: 
            logging.info(self.log_message)
            if buf_clear: self.log_message = ''

    def error_trace(self,exc,error):
        '''Adds stack trace and returns it.'''
        stack = traceback.format_exception(exc,error,error.__traceback__)
        for item in stack:
            self.log(item)

    def get_log(self,lines=1000):
        '''Opens log file rewrites from bottom to top all content.
        Returns string'''
        logs = []
        l = ''
        with open(self.file) as f:
            in_lines = f.readlines()
        while in_lines and lines:
            new_line = in_lines.pop()
            if new_line[:2] == '  ':
                l = new_line + l
            elif new_line[:2] == '\n':
                continue
            elif l:
                logs.append(new_line + l)
                l = ''
            else:
                logs.append(new_line)
            lines -=1
        for line in logs:
            l += line
        logs = '<pre>' + l + '</pre>'
        return logs

class Docker(Util):
    '''
    Manages docker images by building them, starting and running. 
    
    Starts docker and returns STARTED, if docker fails at any time issues FAILED
    >>> url = 'git@github.com:Kolumbs/bootdocker.git#main:test'
    >>> Docker('bot','demo',url,'/tmp/bootdocker').start()
    '''


    def __init__(self,repo,tag,git_url,log_file):
        self.repo = repo
        self.tag = tag
        self.url = git_url
        Util.__init__(self,log_file) 

    def run(self,program,log=True,blocking=True):
        '''Runs program and returns completed process.
        program - string of shell command
        log - set to True if Stdout must be logged not returned
        blocking - set to False to not wait for return'''
        self.log('Calling shell: ' + program)
        logs = []
        proc = subprocess.Popen(program,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        proc.poll()
        if blocking: proc.wait()
        if log: logs += proc.stdout.readlines()
        if proc.returncode != 0 and proc.returncode != None: logs += proc.stderr.readlines()
        for log in logs:
            log = log.strip(b'\n')
            if log: self.log(log.decode())
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
        self.log('STARTED')
        cmd = 'docker build --tag %s:%s %s' % (self.repo,self.tag,self.url)
        self.run(cmd)
        self.log('BUILT')
        self.cons('stop')
        self.run('docker container prune -f')
        proc = self.run('docker run %s:%s' % (self.repo,self.tag),blocking=False)
        self.log('STARTED RUN...',post=True,buf_clear=False)
        while proc.returncode == None:
            time.sleep(2)
            proc.poll()
            if not proc.returncode == None or not proc.returncode == 0:
                self.log('Program ends with error code: ' + str(proc.returncode))
                for line in proc.stderr.readlines():
                    self.log(line.decode())
            else:
                self.log('Program has finished succesfully with code: ' + str(proc.returncode))
            time.sleep(20)
            proc
        self.log('END',post=True)



class DockerServer(socketserver.StreamRequestHandler,Util):


    def handle(self):
        Util.__init__(self,args.file) 
        self.data = self.rfile.readline().decode()
        self.data = self.data.strip('\r\n')
        self.data = self.data.split(' ')
        if self.data:
            self.dispatcher()
        self.log('Client disconnected: ' + str(self.client_address),post=True)

    def dispatcher(self):
        services = {'SSH': self.data[0], 'POST': self.data[0], 'GET': self.data[0]}
        s = [key for key in services if key == services[key]]
        if s:
            self.log('Client with IP: ' + str(self.client_address))
            self.log('Sending: ' + str(self.data))
            self.log('Dispatching service: ' + s[0])
            try:
                eval('self.' + s[0].lower() + '()')
            except Exception as err:
                self.error_trace(Exception,err)
        else:
            self.log('No matching service found')

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

    def git(self,params):
        self.log('Http headers: ' + str(self.httphead.keys()))
        self.log('Http values: ' + str(self.httphead.values()))
        self.payload = self.payload.decode()
        self.log('Data(decoded): ' + self.payload)
        git_url = self.extract(self.payload,'git_url')
        git_branch = self.extract(self.payload,'ref')
        if git_url and git_branch:
            git_branch = git_branch.split('/')
            url = git_url + '#' + git_branch[2]
            if 'folder' in p:
                url += ':' + p['folder']
            self.log('Docker launch with: ' + url)
            self.send_response(msg='Git handler posted\n')
            self.log('Docker starts')
            docker = Docker(p['repo'],p['tag'],url,args.file)
            _thread.start_new_thread(docker.start,())
            self.log('Docker started as thread')
        else:
            msg = 'POST requests with /git requires payload to contain:\n'
            msg += '    git_url - git://github.com/{yourRepoPath... \n'
            msg += '    ref - branch location in commit ref/heads/{branch}\n'
            self.send_response(status='400 Bad Request',msg=msg)

    def extract(self,content,key):
        '''Safely extracts content assuming json file'''
        if key in content:
            a = content.find(key)
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
        request = request.split('?')
        try:
            assert request[0] == '/git'
            params = request[1].split('&')
            p = {}
            for param in params:
                param = param.split('=')
                p[param[0]] = param[1]
            assert 'tag' in p.keys() and 'repo' in p.keys()
            self.git(p)
        except:
            msg = 'POST requests for git contain:\n'
            msg += '    repo - name of docker repo to use\n'
            msg += '    tag - tag of docker image\n'
            msg += '    folder[Optional] - if dockerfile is located outside git root folder\n'
            msg += 'Syntax:\n'
            msg += '/git?repo=foo&tag=sometag&folder=subfoldername\n'
            self.log(msg)
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
            self.log('Sending log request')
            logs = self.get_log()
            self.send_response(msg=logs,title='Bot logs')
        else:
            self.send_response()


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
        _log = Util(args.file)
        with ThreadedTCPServer(myPort, DockerServer) as server:
            logging.info('Server started listening on port: ' + str(myPort))
            server.serve_forever()
    except PermissionError as perm:
        print('Application stack trace:')
        _log.error_trace(Exception,perm)
        print(_log.log_message)
        print('Permission error: please run with elevated privileges')
    except OSError as err:
        print('Application stack trace:')
        _log.error_trace(Exception,perm)
        print(_log.log_message)
        print('err string value: ' + str(err))
        if 'Errno 98' in str(err):
            print('Wait for socket to free up and try to start again')
    except Exception as err:
        _log.error_trace(Exception,perm)
        print(_log.log_message)
