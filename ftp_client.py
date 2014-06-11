#encoding=utf-8

import ftplib
import os, socket

HOST = "127.0.0.1"
DIRN = "test/"
FILE = "index.html"
 

def main():
	f = ftplib.FTP()
	try:
		f.connect(host = HOST, port = 50030, timeout = 999)
	except (socket.error, socket.gaierror) as e:
		print("Error: %s" % e)
		return
	print("Connected to host '%s'" % HOST)
	
	try:
		f.login()
	except ftplib.error_perm:
		print("Error: cannot login by anonymously")
		f.quit()
		return
	print("Logged in as 'anonymous'")
	
	try:
		f.cwd(DIRN)
	except ftplib.error_perm:
		print("Error: cannot CD to %s" % DIRN)
		f.quit()
		return
	print("Changed to folder %s" % DIRN)

	try:
		flist = f.nlst('.')
	except ftplib.error_perm:
		print("Error: cannot LIST FILES")
		f.quit()
		return
	print("File list is as follows: \n %s" % flist)
	
	try:
		f.retrbinary("RETR %s" % FILE, open(FILE, "wb").write)
	except ftplib.error_perm:
		print("Error: cannot read file '%s'" % FILE)
		os.unlink(FILE)
	else:
		print("Downloaded '%s' to CWD" % FILE)
		f.quit()
		return
	
if __name__ == "__main__":
	main()
