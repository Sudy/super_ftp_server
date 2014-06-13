import socket

addr = ("127.0.0.1",10040)
udp_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
while True:
	data = raw_input('>')
	if not data:
		break
	udp_socket.sendto(data,addr)
	data,server_addr = udp_socket.recvfrom(1024)
	print data	
	