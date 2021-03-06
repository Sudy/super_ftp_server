import socket
import os
from tools import get_logger
import getopt
import sys
from interface import Client
import time

host = "127.0.0.1"
tcp_port = 10030
udp_port = 10040
timeout = 60
global_options = {'run_mode':'tcp_mode'}



class TCPClient(Client):
	"""docstring for TCPClient"""
	def __init__(self):
		super(TCPClient, self).__init__()
		self.tcp_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		try:
			self.tcp_socket.connect((host,tcp_port))
		except Exception as e:
			print "here!"
			logger.error(e)
			return

		self.running = True


	def start(self):
		while self.running:
			message = raw_input('>')
			if not message:
				break

			cmd,args = self.parse_command(message)
			if cmd.upper() in ["RETR","STORE"]:
				try:
					self.tcp_socket.send(message)
					self.command_list[cmd.upper()](args)
				except Exception as e:
					logger.error(e)
					logger.error("executing %s error"%cmd)

			else:
				try:
					self.tcp_socket.send(message)
				except Exception as e:
					logger.error(e)
					self.running = False
				
				try:
					data = self.tcp_socket.recv(2048)
					if not data:
						self.tcp_socket.close()
						logger.info("tcp recvd no data,closing")
					print data
				except Exception as e:
					logger.error(e)

	def handle_STORE(self,args):
		if len(args) != 1:
			logger.error("store filename")
			return
		with open(args[0],'r') as fp:
			while True:
				data = fp.read(2048)
				if not data:
					self.tcp_socket.send("EOF")
					break
				self.tcp_socket.send(data)
				time.sleep(0.1)
		logger.info("send file %s succeed"%args[0])

	def handle_RETR(self,args):
		if len(args) != 1:
			logger.error("store filename")
			return
		with open("test/" + args[0],'w') as fp:
			while True:
				data = self.tcp_socket.recv(2048).decode()
				if len(data) <= 0:
					break
				fp.write(data)
				fp.flush()
			logger.info("recv file %s finished!"%args[0])

class UDPClient(Client):
	def __init__(self):
		super(UDPClient, self).__init__()
		self.udp_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.running = True
		
	def start(self):
		while self.running:
			message = raw_input('>')
			if not message:
				break

			cmd,args = self.parse_command(message)
			if cmd.upper() in ["RETR","STORE"]:
				try:
					self.udp_socket.sendto(message,(host,udp_port))
					self.command_list[cmd.upper()](args)
				except:
					logger.error("executing %s error"%cmd)

			else:
				try:
					self.udp_socket.sendto(message,(host,udp_port))
				except Exception as e:
					logger.error(e)
					self.running = False
				
				try:
					data,addr = self.udp_socket.recvfrom(2048)
					if not data:
						self.udp_socket.close()
						logger.info("udp recvd no data,closing")
					print data
				except Exception as e:
					logger.error(e)


	def recv(self):
		data_buf = ""
		while True:
			message,addr = self.udp_socket.recvfrom(2048)
			logger.info("recv from %s:%s"%addr)
			if not message:
				break
			data_buf += message
		return data_buf,addr

	def handle_STORE(self,args):
		if len(args) != 1:
			logger.error("store filename")
			return
		with open(args[0],'r') as fp:
			while True:
				data = fp.read(2048)
				if not data:
					break
				self.udp_socket.sendto(data,(host,udp_port))
		logger.info("send file %s succeed"%args[0])

	def handle_RETR(self,args):
		if len(args) != 1:
			logger.error("store filename")
			return
		with open('test/' + args[0],'w') as fp:
			while True:
				data,addr = self.udp_socket.recvfrom(2048)
				if not data:
					break
				fp.write(data)
				fp.flush()
				time.sleep(0.1)

						
def main_client():
	client = None
	if global_options["run_mode"] == 'tcp_mode':
		client = TCPClient()
	elif global_options["run_mode"] == 'udp_mode':
		client = UDPClient()
	if client:
		client.start()

def usage():
	print ('''usage: %s [-r remote_addr] [-h] [-u udp_port] [-t tcp_port]
	-r remote addr
	-h help
	-u udp_port
	-t tcp_port
''' )% os.path.basename(sys.argv[0])

def parse_opts(opts):
	global tcp_port,udp_port,host,logger,global_options
	#create a logger
	logger =  get_logger()
	for arg,param in opts:
		if arg == '-h':
			usage()
			sys.exit(0)
		elif arg == '-u': 
			try:
				udp_port = int(param)
				global_options["run_mode"] = "udp_mode"
			except Exception as e:
				usage()
				sys.exit(0)
		elif arg == '-t':
			try:
				tcp_port = int(param)
				global_options["run_mode"] = "tcp_mode"
			except Exception as e:
				usage()
				sys.exit(0)
		elif arg == '-r':
			try:
				host = param.strip()
			except Exception as e:
				usage()
				sys.exit(0)

if __name__ == '__main__': 
	try:
		opts, args = getopt.getopt(sys.argv[1:], 't:u:r:h')
	except getopt.GetoptError:
		usage()
		sys.exit(2)

	parse_opts(opts)

	socket.setdefaulttimeout(timeout)
	main_client()
	