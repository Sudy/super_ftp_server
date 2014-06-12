import sys
import getopt
import logging
import socket
import os
import threading


host = "127.0.0.1"
tcp_port = 10030
udp_port = 10040
http_port = 10050

timeout = 60

default_dir = os.path.normpath(os.path.abspath(os.curdir)).replace('\\', '/')



def main():
	pass

def get_logger(handler = logging.StreamHandler()):
	logger = logging.getLogger()
	formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
	handler.setFormatter(formatter)
	logger.addHandler(handler)
	logger.setLevel(logging.NOTSET)
	return logger

def parse_opts(opts):
	global tcp_port,udp_port,http_port,logger
	
	#create a logger
	logger =  get_logger()
	for arg,parm in opts:
		if arg == '-h':
			usage()
			sys.exit(0)
		elif arg == '-u': 
			try:
				udp_port = int(arg)
			except Exception as e:
				usage()
				sys.exit(0)
		elif arg == '-p':
			try:
				tcp_port = int(arg)
			except Exception as e:
				usage()
				sys.exit(0)		
		elif arg == '-t':
			try:
				http_port = int(arg)
			except Exception as e:
				usage()
				sys.exit(0)	
		
def usage():
	print ''' %s [-t tcp_port] [-u udp_port][-p http_port] [-h]
	-t listening tcp port
	-u listening udp port 
	-p listening http port
	-h help
	''' % sys.argv[0]


class HTTPConnection:
	def __init__(self, fd, remote_ip):
		self.fd = fd
		self.httpheader = '''HTTP/1.1 200 OK
		Context-Type: text/html
		Server: FTP-Http
		Context-Length: '''

	def HttpResponse(self, header, whtml):
		with open(whtml) as fp:
			#read html file
			contxtlist = fp.readlines()
			context = ''.join(contxtlist)
			#construct file list
			logger.info(os.curdir())
			contlist = list()
			for files in os.listdir():
				contlist.append('<a href="./ftpdir/%s">%s</a><br>'%(files,files))
			main_content = context.format(default_dir="ftpdir",main_content = "\n".join(contlist))
			
			response = "%s %d\n\n%s\n\n" % (header, len(context), context)
			return response

	def start(self):
		data = self.fd.recv(1024).decode()
		if not data:
			return
		self.fd.send(self.HttpResponse(self.httpheader, './ftpdir/index.html').encode() )
		self.fd.close()


class HTTPThread(threading.Thread):
	def __init__(self, fd, remote_ip):
		threading.Thread.__init__(self)
		self.http = HTTPConnection(fd, remote_ip)
	
	def run(self):
		self.http.start()
		logger.info("Thread done")


class FTP_TCP_Thread(threading.Thread):
	'''FTPConnection Thread Wrapper'''
	def __init__(self, fd, remote_ip):
		threading.Thread.__init__(self)
		self.ftp = FTPConnection(fd, remote_ip)

	def run(self):
		self.ftp.start()
		logger.info("Thread done")

class FTP_UDP_Thread(threading.Thread):
	'''FTPConnection Thread Wrapper'''
	def __init__(self, fd, remote_ip):
		threading.Thread.__init__(self)
		self.ftp = FTPConnection(fd, remote_ip)

	def run(self):
		self.ftp.start()
		logger.info("Thread done")
	



def main_server():
	listen_http_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	listen_http_fd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	listen_http_fd.bind((host, http_port))
	listen_http_fd.listen(512)

	while True:
		client_fd, client_addr = listen_http_fd.accept()
		#logger.error(client_fd, client_addr)
		handler = HTTPThread(client_fd, client_addr)
		handler.start()


if __name__ == '__main__': 
	try:
		opts, args = getopt.getopt(sys.argv[1:], 't:u:p:h')
	except getopt.GetoptError:
		usage()
	parse_opts(opts)
	socket.setdefaulttimeout(timeout)
	main_server()