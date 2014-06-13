	import socket
import sys
import struct
import os
import threading
import getopt
import select
import logging
import logging.handlers
import time
import stat

host = '127.0.0.1'
ftp_port = 50030
http_port = 50040
max_conn = 10
timeout = 60
default_home_dir = os.path.normpath(os.path.abspath(os.curdir)).replace('\\', '/')
logfile = default_home_dir + 'ftp.py.log'

runas_user = 'www-data'
global_options = {'run_mode':'thread'}

# current working directory
account_info = {
	'anonymous':{'pass':'', 'home_dir':default_home_dir, 'runas_user':runas_user},
	} 

def runas(username):
	if os.name != 'posix': return
	uid = get_uid(username)
	os.setgid(uid)
	os.setuid(uid)
class HTTPConnection:
	def __init__(self, fd, remote_ip):
		self.fd = fd
		self.httpheader = '''HTTP/1.1 200 OK
Context-Type: text/html
Server: Python-Http
Context-Length: '''

	def HttpResponse(self, header, whtml):
		f = open(whtml)
		contxtlist = f.readlines()
		context = ''.join(contxtlist)
		context = context.format(file_list="hello world")
		response = "%s %d\n\n%s\n\n" % (header, len(context), context)
		return response

	def start(self):
		data = self.fd.recv(1024).decode()
		if not data:
			return
		print (self.fd, data)
		self.fd.send(self.HttpResponse(self.httpheader, 'index.html').encode() )
		self.fd.close()
	
class FTPConnection:
	'''You can add handle func by startswith handle_ prefix.
	When the connection receives CWD command, it'll use handle_CWD to handle it.
	'''
	def __init__(self, fd, remote_ip):
		self.fd = fd
		self.data_fd = 0
		self.options = {'pasv': False, 'utf8': True}
		self.data_host = ''
		self.data_port = 0
		self.localhost = fd.getsockname()[0]
		self.home_dir = default_home_dir
		self.curr_dir = '/test'
		self.running = True
		self.handler = dict(
			[(method[7:], getattr(self, method))			 for method in dir(self)			 if method.startswith("handle_") and callable(getattr(self, method))])

	def start(self): 
		try:
			self.say_welcome()
			while self.running:
				success, command, arg = self.recv()
				command = command.upper()
				logger.info('[ ' + command + ' ] ' + arg)
				#logger.error('HERE!!!')
				if not success: 
					self.send_msg(500, "Failed")
					continue
				if command not in self.handler.keys():
					self.send_msg(500, "Command Not Found")
					continue
				try:
					logger.error(command)
					self.handler[command](arg)
				except OSError as e:
					#logger.error (sys.exc_info()[2].tb_frame.f_back.f_lineno)
					logger.error(e)
					logger.error("in start")
					self.send_msg(500, 'Permission denied')
				#logger.error('TTTT!!!')
			self.say_bye()
		except Exception as e:
			self.running = False
			#logger.error (sys.exc_info()[2].tb_frame.f_back.f_lineno)
			logger.error(e)
			logger.error("in start")
		finally:
			self.fd.close()

		logger.info("FTP connnection done.")

		return True

	def send_msg(self, code, msg):
		message = str(code) + ' ' + msg + '\r\n'
		self.fd.send(message.encode())

	def recv(self):
		'''returns 3 tuples, success, command, arg'''
		try:
			success, buf, command, arg = True, '', '', ''
			while True:
				data = self.fd.recv(4096).decode()
				if not data:
					self.running = False
					success = False
					break
				buf += data
				if buf[-2:] == '\r\n': break
			split = buf.find(' ')
			command, arg = (buf[:split], buf[split + 1:].strip()) if split != -1 else (buf.strip(), '')
		except Exception as e:
			logger.error(e)
			logger.error("in recv")
			self.running = False
			success = False

		return success, command, arg


	def say_welcome(self):
		self.send_msg(220, "Welcome to my FTP")

	def say_bye(self):
		self.handle_BYE('')

	def data_connect(self):
		'''establish data connection'''
		if self.data_fd == 0:
			self.send_msg(500, "no data connection")
			return False
		elif self.options['pasv']:
			fd, addr = self.data_fd.accept()
			self.data_fd.close()
			self.data_fd = fd
		else:
			try:
				self.data_fd.connect((self.data_host, self.data_port))
			except:
				self.send_msg(500, "failed to connect")
				return False
		return True

	def close_data_fd(self):
		self.data_fd.close()
		self.data_fd = 0

	def parse_path(self, path):
		if path == '': path = '.'
		if path[0] != '/': path = self.curr_dir + '/' + path
		logger.info('parse_path ' + path)
		split_path = os.path.normpath(path).replace('\\', '/').split('/')
		remote = '' 
		local = self.home_dir
		for item in split_path:
			if item.startswith('..') or item == '': continue # ignore parent directory
			remote += '/' + item
			local += '/' + item
		if remote == '': remote = '/'
		logger.info(split_path)
		logger.info('remote: %s  local: %s' % (remote, local))
		return remote, local

	# Command Handlers
	def handle_USER(self, arg):
		if arg in account_info:
			self.username = arg
			if self.username == 'anonymous':
				self.send_msg(230, 'OK')
			else:
				self.send_msg(331, "Need password")
		else:
			self.send_msg(500, "Invalid User")
			self.running = False
	def handle_PASS(self, arg):
		if arg == account_info[self.username]['pass']: 
			self.home_dir = account_info[self.username]['home_dir']
			if 'runas_user' in account_info[self.username].keys():
				user = account_info[self.username]['runas_user']
			else:
				user = 'www-data'
			runas(user) 
			if os.path.isdir(self.home_dir):
				self.send_msg(230, "OK")
				return
		self.send_msg(530, "Password is not corrected")
		self.running = False
	def handle_QUIT(self, arg):
		self.handle_BYE(arg)
	def handle_BYE(self, arg):
		self.running = False
		self.send_msg(200, "OK")
	def handle_CDUP(self, arg):
		self.handle_CWD('..')
	def handle_XPWD(self, arg):
		self.handle_PWD(arg)
	def handle_PWD(self, arg):
		remote, local = self.parse_path(self.curr_dir)
		self.send_msg(257, '"' + remote + '"')
	def handle_CWD(self, arg):
		remote, local = self.parse_path(arg)
		try:
			os.listdir(local)
			self.curr_dir = remote
			self.send_msg(250, "OK")
		except Exception as e:
			logger.error(e)
			logger.error("in cwd")
			self.send_msg(500, "Change directory failed!")
	def handle_SIZE(self, arg):
		remote, local = self.parse_path(self.curr_dir)
		self.send_msg(231, str(os.path.getsize(local)))
	def handle_SYST(self, arg):
		self.send_msg(215, "UNIX")
	def handle_STOR(self, arg):
		remote, local = self.parse_path(arg)
		if not self.data_connect(): return
		self.send_msg(125, "OK")
		f = open(local, 'wb')
		while True:
			data = self.data_fd.recv(8192).decode()
			if len(data) == 0: break
			f.write(data)
		f.close()
		self.close_data_fd()
		self.send_msg(226, "OK")
	def handle_RETR(self, arg):
		remote, local = self.parse_path(arg)
		if not self.data_connect(): return
		self.send_msg(125, "OK")
		f = open(local, 'rb')
		while True:
			data = f.read(8192)
			if len(data) == 0: break
			self.data_fd.send(data)
		f.close()
		self.close_data_fd()
		self.send_msg(226, "OK")
	def handle_TYPE(self, arg):
		self.send_msg(220, "OK")
	def handle_RNFR(self, arg):
		remote, local = self.parse_path(arg)
		self.rename_tmp_path = local
		self.send_msg(350, 'rename from ' + remote)
	def handle_RNTO(self, arg):
		remote, local = self.parse_path(arg)
		os.rename(self.rename_tmp_path, local)
		self.send_msg(250, 'rename to ' + remote)
	def handle_NLST(self, arg):
		if not self.data_connect(): return
		self.send_msg(125, "OK")
		remote, local = self.parse_path(self.curr_dir)
		for filename in os.listdir(local):
			self.data_fd.send( (filename + '\r\n').encode() )
		self.send_msg(226, "Limit")
		self.close_data_fd()
	def handle_XMKD(self, arg):
		self.handle_MKD(arg)
	def handle_MKD(self, arg):
		remote, local = self.parse_path(arg)
		if os.path.exists(local):
			self.send_msg(500, "Folder is already existed")
			return
		os.mkdir(local)
		self.send_msg(257, "OK")
	def handle_XRMD(self, arg):
		self.handle_RMD(arg)
	def handle_RMD(self, arg):
		remote, local = self.parse_path(arg)
		if not os.path.exists(local):
			self.send_msg(500, "Folder is not existed")
			return
		os.rmdir(local)
		self.send_msg(250, "OK")
	def handle_LIST(self, arg):
		if not self.data_connect(): return 
		self.send_msg(125, "OK")
		template = "%s%s%s------- %04u %8s %8s %8lu %s %s\r\n"
		remote, local = self.parse_path(self.curr_dir)
		for filename in os.listdir(local):
			path = local + '/' + filename
			if os.path.isfile(path) or os.path.isdir(path): # ignores link or block file
				status = os.stat(path)
				msg = template % (
					'd' if os.path.isdir(path) else '-',
					'r', 'w', 1, '0', '0', 
					status[stat.ST_SIZE], 
					time.strftime("%b %d  %Y", time.localtime(status[stat.ST_MTIME])), 
					filename)
				logger.error(msg)
				self.data_fd.send(msg.encode() )
		self.send_msg(226, "Limit")
		self.close_data_fd()
	def handle_PASV(self, arg):
		self.options['pasv'] = True
		try:
			self.data_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.data_fd.bind((self.localhost, 0))
			self.data_fd.listen(1)
			ip, port = self.data_fd.getsockname()
			self.send_msg(227, 'Enter Passive Mode (%s,%u,%u).' %
					(','.join(ip.split('.')), (port >> 8 & 0xff), (port & 0xff)))
		except Exception as e:
			logger.error(e)
			logger.error("in pasv")
			self.send_msg(500, 'passive mode failed')
	def handle_PORT(self, arg):
		try:
			if self.data_fd:
				self.data_fd.close()
			t = arg.split(',')
			self.data_host = '.'.join(t[:4])
			self.data_port = int(t[4]) * 256 + int(t[5])
			self.data_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		except:
			self.send_msg(500, "PORT failed")
		self.send_msg(200, "OK")
	def handle_DELE(self, arg):
		remote, local = self.parse_path(arg)
		if not os.path.exists(local):
			self.send_msg(450, "File not exist")
			return
		os.remove(local)
		self.send_msg(250, 'File deleted')
	def handle_OPTS(self, arg):
		if arg.upper() == "UTF8 ON":
			self.options['utf8'] = True
			self.send_msg(200, "OK")
		elif arg.upper() == "UTF8 OFF":
			self.options['utf8'] = False
			self.send_msg(200, "OK")
		else:
			self.send_msg(500, "Invalid argument")
			


class HTTPThread(threading.Thread):
	def __init__(self, fd, remote_ip):
		threading.Thread.__init__(self)
		self.http = HTTPConnection(fd, remote_ip)
	
	def run(self):
		self.http.start()
		logger.info("Thread done")
class FTPThread(threading.Thread):
	'''FTPConnection Thread Wrapper'''
	def __init__(self, fd, remote_ip):
		threading.Thread.__init__(self)
		self.ftp = FTPConnection(fd, remote_ip)

	def run(self):
		self.ftp.start()
		logger.info("Thread done")

class FTPThreadServer:
	'''FTP Server which is using thread'''
	def main_server(self):
		listen_ftp_fd = socket.socket()
		listen_ftp_fd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		#print ('XXX', host, ftp_port)
		listen_ftp_fd.bind((host, ftp_port))
		listen_ftp_fd.listen(512)
		
		listen_http_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		listen_http_fd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		listen_http_fd.bind((host, http_port))
		listen_http_fd.listen(512)
		self.read_fds = [listen_ftp_fd, listen_http_fd]
		while True:
			rlist, wlist, xlist = select.select(self.read_fds, [], [])
			logger.info('new server')
			#request ftp
			if (listen_ftp_fd in rlist):
				client_fd, client_addr = listen_ftp_fd.accept()
				if len(self.read_fds) > max_conn:
					logger.error('reject client: ' + str(client_addr))
					client_fd.close()
					continue
				#logger.error(client_fd, client_addr)
				handler = FTPThread(client_fd, client_addr)
				handler.start()
			if (listen_http_fd in rlist):
				client_fd, client_addr = listen_http_fd.accept()
				if (len (self.read_fds) > max_conn):
					logger.error('reject client:' + str(client_addr) )
					client_fd.close()
					continue
				#logger.error(client_fd, client_addr)
				handler = HTTPThread(client_fd, client_addr)
				handler.start()
			for read_fd in rlist:
				if read_fd in [listen_ftp_fd,listen_http_fd]:
					continue
				#this may not happen
				data = os.read(read_fd, 32)
				self.read_fds.remove(read_fd)
				os.close(read_fd)


# class FTPForkServer:
# 	'''FTP Fork Server, use process per user'''
# 	def child_main(self, client_fd, client_addr, write_end):
# 		'''never return'''
# 		for fd in self.read_fds:
# 			os.close(fd)
# 		self.read_fds = []

# 		try:
# 			handler = FTPConnection(client_fd, client_addr)
# 			handler.start()
# 		except Exception as e:
# 			logger.error(e)
# 			logger.error("in child_main")

# 		os.write(write_end, str(write_end))

# 		sys.exit()

# 	def main_server(self):
# 		#
# 		listen_ftp_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# 		listen_ftp_fd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# 		#print (host, ftp_port)
# 		listen_ftp_fd.bind((host, ftp_port))
# 		listen_ftp_fd.listen(512)
		
# 		listen_http_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# 		listen_http_fd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# 		listen_http_fd.bind(host, http_port)
# 		listen_http_fd.listen(512)

# 		self.read_fds = [listen_ftp_fd, listen_http_fd]
# 		while True:
# 			rlist, wlist, xlist = select.select(self.read_fds, [], [])

# 			#print (listen_ftp_fd,rlist)
# 			if listen_ftp_fd in rlist:
# 				client_fd, client_addr = listen_ftp_fd.accept()
# 				if len(self.read_fds) > max_conn:
# 					logger.error('reject client: ' + str(client_addr))
# 					client_fd.close()
# 					continue
# 				try:
# 					logger.info('new client: ' + str(client_addr))
# 					read_end, write_end = os.pipe()
# 					self.read_fds.append(read_end)
# 					fork_result = os.fork()
# 					if fork_result == 0: # child process
# 						listen_ftp_fd.close()
# 						self.read_fds.remove(listen_ftp_fd)
# 						self.child_main(client_fd, client_addr, write_end) # never return
# 					else:
# 						os.close(write_end)
# 				except Exception as e:
# 					logger.error(e)
# 					logger.error('Fork failed')
					
# 			for read_fd in rlist:
# 				if read_fd == listen_ftp_fd: continue
# 				data = os.read(read_fd, 32)
# 				self.read_fds.remove(read_fd)
# 				os.close(read_fd)

						

def get_uid(username = 'www-data'):
	'''get uid by username, I don't know whether there's a
	function can get it, so I wrote this function.'''
	pwd = open('/etc/passwd', 'r')
	pat = re.compile(username + ':.*?:(.*?):.*?')
	for line in pwd.readlines():
		try:
			uid = pat.search(line).group(1)
		except: continue
		return int(uid)

def get_logger(handler = logging.StreamHandler()):
	logger = logging.getLogger()
	formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
	handler.setFormatter(formatter)
	logger.addHandler(handler)
	logger.setLevel(logging.NOTSET)
	return logger

def daemonize(stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
	'''becomes a daemon'''
	try:
		pid = os.fork()
		if pid > 0: sys.exit(0)
	except OSError as e:
		sys.stderr.write("fork #1 failed\n")
		sys.exit(1)

	os.umask(0)
	os.setsid()

	try:
		pid = os.fork()
		if pid > 0: sys.exit(0)
	except OSError as e:
		sys.stderr.write("fork #2 failed\n")
		sys.exit(1)

	for f in sys.stdout, sys.stderr: f.flush()
	si = file(stdin, 'r')
	so = file(stdout, 'a+')
	se = file(stderr, 'a+', 0)
	os.dup2(si.fileno(), sys.stdin.fileno())  # 0
	os.dup2(so.fileno(), sys.stdout.fileno()) # 1
	os.dup2(se.fileno(), sys.stderr.fileno()) # 2

def main_server():
	global global_options
	if global_options['run_mode'] == 'fork':
		signal.signal(signal.SIGCHLD, signal.SIG_IGN)
		server = FTPForkServer()
	else:
		server = FTPThreadServer()
		
	server.main_server()

def usage():
	print ('''usage: %s [-d] [-h] [-p ftp_port] [-q http_port] [-t]
	-d become a daemon
	-h help
	-p listen ftp port(>1023)
	-q listen http port(>1023)
	-t thread mode, fork model by default

''' )% os.path.basename(sys.argv[0])

def param_handler(opts):
	global ftp_port, http_port, logger, global_options
	be_daemon = False
	logger = get_logger()
	for o, a in opts:
		if o == '-h':
			usage()
			sys.exit(0)
		elif o == '-d':
			if not os.name == 'posix':
				print ('Only support the os with posix specifications.')
				sys.exit(-1)
			be_daemon = True
		elif o == '-p':
			try: ftp_port = int(a)
			except Exception as e:
				usage()
				sys.exit(0)
		elif o == '-q':
			try: http_port = int(a)
			except Exception as e:
				usage()
				sys.exit(0)
		elif o == '-t':
			global_options['run_mode'] = 'thread'

	if os.name != 'posix' and global_options['run_mode'] == 'fork':
		print ("You can NOT run fork mode in a non posix os, please use -t options to run in thread mode")
		sys.exit(-1)
	if be_daemon: daemonize()

if __name__ == '__main__': 
	try:
		opts, args = getopt.getopt(sys.argv[1:], 'hdp:q:t')
	except getopt.GetoptError:
		usage()
		sys.exit(2)

	param_handler(opts)

	socket.setdefaulttimeout(timeout)

	main_server()

