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


class Docker():
    '''
    Manages docker images by building them, starting and running. 
    
    Starts docker and returns STARTED, if docker fails at any time issues FAILED
    >>> url = 'git@github.com:Kolumbs/bootdocker.git#master:test'
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


if __name__ == '__main__':
    logging.basicConfig(filename='test.log', level=logging.DEBUG)
    import doctest
    doctest.testmod()
