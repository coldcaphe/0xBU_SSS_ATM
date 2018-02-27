import crypto
from binascii import hexlify

#sanity check that key is 32 bytes/context is 8 bytes in python if ncessary since it doesnt' work with how the arguments get parsed in C for some reason.


c1 = crypto.secretbox_encrypt("message1", 0, "\x00"*8, '\x00'*32);
print(hexlify(c1))

c2 = crypto.secretbox_encrypt("\x00essage2", 0, "\x00"*8, '\x00'*32);
print(hexlify(c2))

#libhydrogen reseeds with the same randomness each time the it gets reinitialized, might be possible to predict the state, idk not thinking too much about it rn.
#print(len(c1))

m1 = crypto.secretbox_decrypt(c1, 0, "\x00"*8, '\x00'*32)
print(m1)
print(len(m1))

m2 = crypto.secretbox_decrypt(c2, 0, "\x00"*8, '\x00'*32)
print(m2)
print(hexlify(m2))
