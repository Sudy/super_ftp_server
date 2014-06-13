import sys
import getopt
import logging
import socket
import os
import threading
from interface import Command,Connection
import select


host = "127.0.0.1"
tcp_port = 10030
udp_port = 10040
http_port = 10050
max_conn = 10

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



class TCP_Command(Command):
	def __init__(self, arg):
		super(TCP_Command, self).__init__()
		self.arg = arg

class UDP_Command(Command):
	"""docstring for UDP_Command"""
	def __init__(self, arg):
		super(UDP_Command, self).__init__()
		self.arg = arg
		


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
			logger.info(os.curdir)
			contlist = list()
			for files in os.listdir("."):
				contlist.append('<a href="%s">%s</a><br>'%(files,files))
			main_content = context.format(default_dir="ftpdir",main_content = "\n".join(contlist))
			
			response = "%s %d\n\n%s\n\n" % (header, len(main_content), main_content)
			return response

	def start(self):
		data = self.fd.recv(1024).decode()
		if not data:
			return
		self.fd.send(self.HttpResponse(self.httpheader, './ftpdir/index.html').encode() )
		self.fd.close()



class FTP_UDP_Connection(Connection):
	def __init__(self,fd):
		super(FTP_UDP_Connection,self).__init__()
		self.fd = fd
		self.client_addr = None
		self.running = True

		self.command_list = {"LIST":self.command_LIST,
							 "SIZE":self.command_SIZE,
							 "STORE":self.command_STORE,
							 "RETR":self.command_RETR,
							 "BYE":self.command_BYE
		}

	def command_LIST(self,client_addr,args):
		self.send_message(client_addr,200,"OK")
		
	def command_SIZE(self):
		pass
	def command_STORE(self):
		pass
	def command_RETR(self):
		pass
	def command_BYE(self):
		pass
	def start(self):
		try:
			while self.running:
				client_addr,success,command,args = self.recv()
				if not success:
					logger.info("recv no command")
					self.send_message(500,"recv no command",client_addr)
					continue
				else:
					command = command.upper()
					if command not in self.command_list.keys():
						self.send_message(client_addr,500,"command not supported yet")
						logger.error("command not supported yet")
						continue
					try:
						logger.info("[%s] executing"%command)
						self.command_list[command](client_addr,args)
					except Exception as e:
						logger.error(e)
						self.send_message(client_addr,500,"command execute error")
						logger.error("command execute error")
						continue
		except Exception as e:
			logger.error(e)
			logger.error("in ftp_udp start")
		finally:
			self.fd.close()

		logger.info("FTP UDP connnection done.")
		return True

			

	def stop(self):
		self.running = False
	def say_hello(self):
		pass
		#self.send_message()

	def send_message(self,client_addr,code,msg):
		self.fd.sendto("[%s]:%s\n"%(str(code),msg),client_addr)

	def recv(self):
		try:
			client_addr,success,command, args = '',True, '', ''
			data,client_addr = self.fd.recvfrom(1024)

			if not data:
				success = False
				return client_addr,success,command,args
			data_split = [item.strip() for item in data.split()]

			command,args = data_split[0].strip(),data_split[1:] if len(data_split) > 1 else [] 
		except Exception as e:
			logger.error(e)
			logger.error("in recv")
			success = False
		return client_addr,success, command, args

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
		self.ftp = FTP_TCP_Connection(fd, remote_ip)

	def run(self):
		self.ftp.start()
		logger.info("Thread done")

class FTP_UDP_Thread(threading.Thread):
	'''FTPConnection Thread Wrapper'''
	def __init__(self, fd):
		threading.Thread.__init__(self)
		self.ftp_udp = FTP_UDP_Connection(fd)

	def run(self):
		self.ftp_udp.start()
		logger.info("FTP UDP Thread done")
	



def main_server():
	#create socket for http connections 
	listen_http_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	#set http socket opts
	listen_http_fd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	#bind address and port
	listen_http_fd.bind((host, http_port))
	#listen allow maxmium 10 connections 
	listen_http_fd.listen(10)

	#create TCP connections
	listen_tcp_fd = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	listen_tcp_fd.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
	listen_tcp_fd.bind((host,tcp_port))
	listen_tcp_fd.listen(10)

	#create udp connections
	listen_udp_fd = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
	listen_udp_fd.bind((host,udp_port))
	ftp_udp_thread = FTP_UDP_Thread(listen_udp_fd)
	ftp_udp_thread.start()

	read_fds = [listen_http_fd,listen_tcp_fd]

	while True:
		rfds_list,wfds_list,xfds_list = select.select(read_fds,[],[])
		if listen_tcp_fd in rfds_list:
			tcp_client_fd,tcp_client_addr = listen_tcp_fd.accept()

			#start process thread
		if listen_http_fd in rfds_list:
			http_client_fd,http_client_addr = listen_http_fd.accept()


	



if __name__ == '__main__': 
	try:
		opts, args = getopt.getopt(sys.argv[1:], 't:u:p:h')
	except getopt.GetoptError:
		usage()
	parse_opts(opts)
	socket.setdefaulttimeout(timeout)
	main_server()