#include <Python.h>
#include <stdio.h>
#include "../libhydrogen/hydrogen.h"
#include <string.h>

static PyObject* crypto_secretbox_encrypt(PyObject* self, PyObject* args){
	char* m;
	size_t mlen;
	uint64_t msg_id;
	char *ctx;
	size_t ctx_len;
	const uint8_t *key; //this shouldn't matter its secret
	size_t key_len;
	PyArg_ParseTuple(args, "s#Ks#s#", &m, &mlen, &msg_id, &ctx, &ctx_len, &key, &key_len); //only s# accepts null bytes, need to random pointers to store lengths
	//printf("Parsed \n");
	//printf("MSG: %s, MSG_ID: %" PRIu64 ", CTX: %s\n", m, msg_id, ctx);
	/* idk why it parses the message length correctly but not the context length or key length, whatever, ignore those variables
	if(ctx_len != hydro_secretbox_CONTEXTBYTES){
		PyErr_Format(PyExc_ValueError, "Context not of correct size: Received %lu bytes", ctx_len);
		return NULL;
	}

	if(key_len != hydro_secretbox_KEYBYTES){
		PyErr_Format(PyExc_ValueError, "Key not of correct size: Received %lu bytes", key_len);
		return NULL;
	}
	*/

	//be careful adding print debug statements, i randomly get segfaults/get unintended functionality


	uint8_t c[hydro_secretbox_HEADERBYTES + mlen];
	hydro_secretbox_encrypt(c, m, mlen, msg_id, ctx, key);

	//dont comment this out it segfaults
	for (int i = 0; i < hydro_secretbox_HEADERBYTES + mlen; i++){
		//printf("%02x", c[i]);
	}
	//printf("\n");


	PyObject *ret = Py_BuildValue("s#", c); //s# incase it has null bytes?
	return ret;
}
static PyObject* crypto_secretbox_decrypt(PyObject* self, PyObject* args){
	uint8_t* c;
	size_t clen;
	uint64_t msg_id;
	char* ctx;
	size_t ctx_len;
	uint8_t *key;
	size_t key_len;
	PyArg_ParseTuple(args, "s#Ks#s#", &c, &clen, &msg_id, &ctx, &ctx_len, &key, &key_len);

	char m[clen - hydro_secretbox_HEADERBYTES];
	if (hydro_secretbox_decrypt(m, c, clen, msg_id, ctx, key) != 0){ //when returning to python, two bytes get appended, idk why but remove those end bytes, leaving this comment here but it doesn't happen anymore for some reason
		PyErr_Format(PyExc_ValueError, "Message forged: %s, did not decrypt successfully?\n", m);
		return NULL;
	}
	//don't comment this out, it segfaults, idk why
	for (int x = 0; x < clen - hydro_secretbox_HEADERBYTES; x++){
		//printf("%c", m[x]);
	}
	PyObject *ret = Py_BuildValue("s#", m);
	return ret;
}

static char module_docstring[] = "This module provides an interface for several libhydrogen functions";
static char secretbox_encrypt_docstring[] = "Encrypts a message of length mlen, using a context and secret key, with message counter msg_id";
static char secretbox_decrypt_docstring[] = "Decrypts ciphertext, using the message id, context, and secret key";
static PyMethodDef module_methods[] = {
	{"secretbox_encrypt", crypto_secretbox_encrypt, METH_VARARGS, secretbox_encrypt_docstring},
	{"secretbox_decrypt", crypto_secretbox_decrypt, METH_VARARGS, secretbox_decrypt_docstring}
};

PyMODINIT_FUNC initcrypto(void){
	PyObject *m = Py_InitModule3("crypto", module_methods, module_docstring);
	if (m == NULL)
		return;
	//printf("Init\n");

}
