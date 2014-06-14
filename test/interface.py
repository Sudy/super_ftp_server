class Connection(object):

	def __init__(self,fd):
		self.running = True
		self.fd = fd 
		self.command_list = {"LIST":self.command_LIST,
					 "SIZE":self.command_SIZE,
					 "STORE":self.command_STORE,
					 "RETR":self.command_RETR,
					 "BYE":self.command_BYE
			}

	def command_LIST(self):
		pass
	def command_SIZE(self):
		pass
	def command_BYE(self):
		pass
	def command_STORE(self):
		pass
	def command_RETR(self):
		pass
	def sendmessage(self):
		pass
	def recv(self):
		pass
	def start(self):
		pass


class Client(object):
	def __init__(self):
		super(Client, self).__init__()
		self.command_list = {"STORE":self.handle_STORE,"RETR":self.handle_RETR}
	def start(self):
		pass
	def recv(self):
		pass
	def parse_command(self,input_line):
		if input_line:
			input_line = [item.strip() for item in input_line.split()]
			cmd,args = input_line[0],input_line[1:] if len(input_line) > 1 else []
			return cmd,args
	def handle_STORE(self):
		pass
	def handle_RETR(self):
		pass
		