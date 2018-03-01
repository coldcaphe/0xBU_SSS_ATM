import crypto
from binascii import hexlify, unhexlify

#sanity check that key is 32 bytes/context is 8 bytes in python if ncessary since it doesnt' work with how the arguments get parsed in C for some reason.
c1 = crypto.secretbox_encrypt("1" + "0"*32 + "1123" , 0, "\x00"*8, '\x00'*32);
print len(c1)
print c1

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

sig = "3a77616ed36fdedbe63e26b9d366a5264b9c61022e8f65ddd6bf4d33ecd87f21e4799ee520f49dc140720b914ec25eafb0fb9e3da1a4327bdd9ad2954feb870b"
sig = unhexlify(sig)
m = "\x00essage"
ctx = "\x00"*8
pk = "b14ed7aa48d41efc873dcddb33c97a0d5f059b0592597b64278d6b305b889351"
pk = unhexlify(pk)
print(len(pk))

crypto.sign_verify(sig, m1, ctx, pk)
