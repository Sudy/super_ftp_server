import sys
import getopt
import logging
import socket
import os
import threading
from interface import Connection
from tools import get_logger
import select
import stat,time


host = "127.0.0.1"
tcp_port = 10030
udp_port = 10040
http_port = 10050

timeout = 60

default_dir = os.path.normpath(os.path.abspath(os.curdir)).replace('\\', '/')



def parse_opts(opts):
	global tcp_port,udp_port,http_port,logger
	
	#create a logger
	logger =  get_logger()
	for arg,param in opts:
		if arg == '-h':
			usage()
			sys.exit(0)
		elif arg == '-u': 
			try:
				udp_port = int(param)
			except Exception as e:
				usage()
				sys.exit(0)
		elif arg == '-p':
			try:
				tcp_port = int(param)
			except Exception as e:
				usage()
				sys.exit(0)		
		elif arg == '-t':
			try:
				http_port = int(param)
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




class FTP_TCP_Connection(Connection):

	def __init__(self, fd):
		super(FTP_TCP_Connection,self).__init__(fd)

	def command_LIST(self,args):

		# self.send_message(client_addr,125, "OK")
		try:
			template = "%s%s%s------- %04u %8s %8s %8lu %s %s\n"
			message = ""
			for filename in os.listdir('.'):
				path =  './' + filename
				if os.path.isfile(path) or os.path.isdir(path): # ignores link or block file
					status = os.stat(path)
					msg = template % (
						'd' if os.path.isdir(path) else '-',
						'r', 'w', 1, '0', '0', 
						status[stat.ST_SIZE], 
						time.strftime("%b %d  %Y", time.localtime(status[stat.ST_MTIME])), 
						filename)
					message += msg
			self.send_message(220,message)
		except Exception as e:
			self.send_message(500,"listdir error")
			logger.error(e)
		# self.send_message 226, "Limit")
		# self.send_message 200,"OK")
		
	def command_SIZE(self,args):
		if len(args) != 1:
			self.send_message(500,"SZIE filename")
			return
		msg = "\n%s size: %s"%(args[0],str(os.path.getsize(args[0])))
		self.send_message(231,msg)
		
	def command_STORE(self,args):
		if len(args) != 1:
			self.send_message(500,"STORE filename")
		with open('test/' + args[0],'w') as fp:
			while True:
				data = self.fd.recv(2048).decode()
				if not data:
					break
				fp.write(data)
				fp.flush()
		self.send_message(200,"%s store finished!"%args[0])

	def command_RETR(self,args):
		if len(args) != 1:
			self.send_message(500,"RETR filename")
			return
		with open(args[0],'r') as fp:
			while  True:
				data = fp.read(2048)
				if not data:
					break
				self.fd.send(data)
		logger.info("%s send finished!"%args[0])
		
	def command_BYE(self,args):
		self.running = False
		self.send_message(200, "OK")
		self.fd.close()

	def start(self):
		try:
			while self.running:
				success,command,args = self.recv()
				print success,command,args
				if not success:
					logger.info("recv no command")
					self.send_message(500,"recv no command")
					continue
				else:
					command = command.upper()
					if command not in self.command_list.keys():
						self.send_message(500,"command not supported yet")
						logger.error("command not supported yet")
						continue
					try:
						logger.info("[%s] executing"%command)
						self.command_list[command](args)
					except Exception as e:
						logger.error(e)
						self.send_message(500,"command execute error")
						logger.error("command execute error")
						continue

		except Exception as e:
			logger.error(e)
			logger.error("in ftp_tcp start")
		finally:
			self.fd.close()

		logger.info("FTP UDP connnection done.")
		return True


	def send_message(self,code,msg):
		self.fd.send("[%s]:%s\n"%(str(code),msg))

	def recv(self):
		try:
			success,command, args = True, '', ''
			data = self.fd.recv(1024)

			if not data:
				success = False
				return success,command,args
			data_split = [item.strip() for item in data.split()]

			command,args = data_split[0],data_split[1:] if len(data_split) > 1 else [] 
		except Exception as e:
			logger.error(e)
			logger.error("in tcp recv")
			success = False
		return success, command, args

		

class FTP_UDP_Connection(Connection):
	def __init__(self,fd):
		super(FTP_UDP_Connection,self).__init__(fd)

	def command_LIST(self,client_addr,args):

		# self.send_message(client_addr,125, "OK")
		try:
			template = "%s%s%s------- %04u %8s %8s %8lu %s %s\n"
			message = ""
			for filename in os.listdir('.'):
				path =  './' + filename
				if os.path.isfile(path) or os.path.isdir(path): # ignores link or block file
					status = os.stat(path)
					msg = template % (
						'd' if os.path.isdir(path) else '-',
						'r', 'w', 1, '0', '0', 
						status[stat.ST_SIZE], 
						time.strftime("%b %d  %Y", time.localtime(status[stat.ST_MTIME])), 
						filename)
					message += msg
			self.send_message(client_addr,220,message)
		except Exception as e:
			self.send_message(client_addr,500,"listdir error")
			logger.error(e)
		# self.send_message(client_addr,226, "Limit")
		# self.send_message(client_addr,200,"OK")
		
	def command_SIZE(self,client_addr,args):
		if len(args) > 1:
			self.send_message(client_addr,500,"SZIE filename")
		msg = "\n%s size: %s"%(args[0],str(os.path.getsize(args[0])))
		self.send_message(client_addr,231,msg)
		
	def command_STORE(self,client_addr,args):
		if len(args) != 1:
			self.send_message(client_addr,500,"STORE filename")
		with open('test/' + args[0],'w') as fp:
			while True:
				data,addr = self.fd.recvfrom(2048)
				if not data:
					break
				fp.write(data)
				fp.flush()
	def command_RETR(self,client_addr,args):
		if len(args) != 1:
			self.send_message(client_addr,500,"RETR filename")
		with open(args[0],'r') as fp:
			while  True:
				data = fp.read(2048)
				if not data:
					break
				self.fd.sendto(data,client_addr)
		#self.send_message(client_addr,200,"%s send finished!"%args[0])
		
	def command_BYE(self,client_addr,args):
		self.running = False
		self.send_message(client_addr, 200, "OK")
	def start(self):
		try:
			while self.running:
				client_addr,success,command,args = self.recv()
				if not success:
					logger.info("recv no command")
					self.send_message(client_addr,500,"recv no command")
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
	def __init__(self, fd):
		threading.Thread.__init__(self)
		self.http = HTTPConnection(fd, remote_ip)
	
	def run(self):
		self.http.start()
		logger.info("Thread done")


class FTP_TCP_Thread(threading.Thread):
	'''FTPConnection Thread Wrapper'''
	def __init__(self, fd):
		threading.Thread.__init__(self)
		self.ftp_tcp = FTP_TCP_Connection(fd)

	def run(self):
		self.ftp_tcp.start()
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
			
			tcp_thread = FTP_TCP_Thread(tcp_client_fd)
			tcp_thread.start()

			#start process thread
		if listen_http_fd in rfds_list:
			http_client_fd,http_client_addr = listen_http_fd.accept()
			http_thread = HTTPThread(http_client_fd,http_client_addr)
			http_thread.start()

	



if __name__ == '__main__': 
	try:
		opts, args = getopt.getopt(sys.argv[1:], 't:u:p:h')
	except getopt.GetoptError:
		usage()
	parse_opts(opts)
	socket.setdefaulttimeout(timeout)
	main_server()