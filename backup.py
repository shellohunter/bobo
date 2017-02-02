#!/usr/local/bin/python3
# -*- coding: <utf-8> -*-

import os
import sys
import binascii
import datetime

class EncFile(object):
	def __init__(self):
		self.fp = None
		self.c1 = b'0123456789abcdefABCDEF'
		self.c2 = b'jCl+o.#,!s?u-Awcne*vzi'
		self.c3 = [] # leftover
		leftovers = ["\r","\n"," ","\t"]
		for each in leftovers:
			tmp = binascii.b2a_hex(each.encode("ascii"))
			a = tmp[0]
			b = tmp[1]
			i = self.c1.find(int(a))
			j = self.c1.find(int(b))
			c = bytes([self.c2[i], self.c2[j]])
			c = str(c)[1:].strip("'")
			self.c3.append((each, c))

	def encode(self, bindata):
		bin1 = binascii.b2a_hex(bindata)
		trans = bytes.maketrans(self.c1, self.c2)
		bin2 = bin1.translate(trans)
		enctext = str(bin2)[1:].strip("'")
		for each in self.c3:
			enctext = enctext.replace(each[1], each[0])
		return enctext.encode("ascii")

	def decode(self, enctext):
		txt1 = enctext
		for each in self.c3:
			txt1 = txt1.replace(each[0], each[1])
		bin1 = txt1.encode("ascii")
		trans = bytes.maketrans(self.c2, self.c1)
		bin2 = bin1.translate(trans)
		decdata = binascii.a2b_hex(bin2)
		return decdata

	def open(self, path, mode = "rb"):
		if None == mode.find("b"):
			mode = mode + "b"
		self.fp = open(path, mode)

	def write(self, data):
		data_enc = self.encode(data)
		return self.fp.write(data_enc)

	def read(self):
		data_enc = self.fp.read()
		data = self.decode(data_enc.decode("ascii"))
		return data

	def close(self):
		self.fp.close()



def backup():

	def iterbrowse(path):
		for home, dirs, files in os.walk(path):
			for filename in files:
				yield os.path.join(home, filename)
	ret = os.system("tar cJvf blog.tar.xz .db.py")
	if ret != 0:
		print("ret %d. something is wrong!"%ret)

	enc = EncFile()
	enc.open("blog.tar.xz.enc", "wb")
	with open("blog.tar.xz", "rb") as fp:
		enc.write(fp.read())
	enc.close()

	os.system("git clone --depth 1 https://github.com/shellohunter/backup;"
		+"cp blog.tar.xz.enc backup/ ;"
		+"cd backup ;"
		+"git add blog.tar.xz.enc;"
		+"git commit -m \""+str(datetime.datetime.utcnow()).split(".")[0]+"\";"
		+"git push origin master;"
		+"cd - ;"
		+"rm -rf blog.tar.* ;"
		+"rm -rf backup;")

def restore():
	os.system("rm -rf backup")
	os.system("git clone --depth 1 https://github.com/shellohunter/backup")
	os.system("mv backup/blog.tar.xz.enc .")

	enc = EncFile()
	enc.open("blog.tar.xz.enc", "rb")
	with open("blog.tar.xz", "wb") as fp:
		fp.write(enc.read())
	enc.close()

	os.system("cp .db.py .db.bak.py")
	ret = os.system("tar xJvf blog.tar.xz")
	os.system("rm -rf blog.tar.*")
	os.system("rm -rf backup")


if __name__ == "__main__":
	print(sys.argv)
	if len(sys.argv) < 2:
		print("python3 backup.py <backup|restore>")
		sys.exit(-1)
	if sys.argv[1] == "backup":
		backup()
	else:
		restore()


