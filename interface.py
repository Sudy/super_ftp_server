class Command:
	def __init__(self):
		pass
	def parse_command(self):
		pass
	def command_LIST(self):
		pass
	def command_BYE(self):
		pass
	def command_RETR(self):
		pass
	def command_STORE(self):
		pass
	def command_SIZE(self):
		pass
	def say_welcome(self):
		pass


class Connection(object):

	def __init__(self):
		pass
	def start(self):
		pass
	def recv(self):
		pass
	def send_msg(self):
		pass

class Client(object):
	def __init__(self):
		super(Client, self).__init__()
	
	def start(self):
		pass
	def recv(self):
		pass
	def parse_command(self,input_line):
		if input_line:
			input_line = input_line.split()
			input_line = [item.strip() for item in input_line]
			cmd,args = (input_line[0],input_line[1:] if len(input_line) > 1 else [])
			return cmd,args
		