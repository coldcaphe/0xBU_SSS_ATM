"""Backend of ATM interface for xmlrpc"""

import logging
import sys
import socket
import xmlrpclib
import base64
import random 
import string

class Bank:
    """
    Interface for communicating with the bank
    
    Args:
        address (str): IP address of bank
        port (int): Port to connect to
    """
    
    def __init__(self, address='127.0.0.1', port=1337):
        try:
            self.bank_rpc = xmlrpclib.ServerProxy('http://' + address + ':' + str(port))
        except socket.error:
            logging.error('Error connecting to bank server')
            sys.exit(1)
        logging.info('Connected to Bank at %s:%s' % (address, str(port)))
    
    def get_nonce(self,card_id):
        '''
        Asks the bank server to generate a random nonce so that the card can proove itself
        
        Args:
            card_id(int): The id on the card. will be used to help the bank find the shared secret to decrypt.
        
        Returns:
            str: Randomly generated nonce
        '''
        nonce = self.bank_rpc.get_nonce(card_id)
        return nonce
    

    def check_balance(self,card_id,signed_nonce,hsm_nonce,hsm_id):
        '''
        Verifies that a nonce has been properly signed. 
        
        Args:
            card_id(int): The id on the card. will be used to help the bank find the shared secret to decrypt.
            signed_nonce(str): Proof the message came from the card with the pin
            hsm_nonce: Nonce the server needs to sign for the hsm to decrypt the message the server signs
            hsm_id: ID of the hsm
        
        Returns:
            str: Response will be an encrypted message containing the account balance 
        '''
        encoded_signed_nonce = xmlrpclib.Binary(signed_nonce)
        encoded_hsm_nonce = xmlrpclib.Binary(hsm_id)
        res = self.bank_rpc.check_balance(card_id,encoded_signed_nonce,encoded_hsm_nonce,hsm_id) #signed_nonce,transaction,extra_data
        return res
    
    def change_pin(self,card_id,signed_nonce,new_pk):
        '''
        Changes the public key the server is using
    
        Args:
            card_id(int): The id on the card. will be used to help the bank find the shared secret to decrypt.
            signed_nonce(str): Proof the message came from the card with the pin
            new_pk(str): The new private key the server should use
        Returns:
            str: Response will be either an accept or reject message 
        '''
        encoded_signed_nonce = xmlrpclib.Binary(signed_nonce)
        res = self.bank_rpc.change_pin(card_id,encoded_signed_nonce,new_pk) 
        return res

    def withdraw(self,card_id,signed_nonce,hsm_nonce,hsm_id,amount):
        '''
        Requests server to aproove a withdraw request. 
        Args:
            card_id(int): The id on the card.
            signed_nonce(str): Proof the message came from the card with the pin
            hsm_nonce: Nonce the server needs to sign for the hsm to decrypt the message the server signs
            hsm_id: ID of the hsm
            amount: Amount of money requested
        Returns:
            str: Response will be an encrypted message containing the acount balance 
        '''
        encoded_signed_nonce = xmlrpclib.Binary(signed_nonce)
        encoded_hsm_nonce = xmlrpclib.Binary(hsm_nonce)
        res = self.bank_rpc.withdraw(card_id,encoded_signed_nonce,encoded_hsm_nonce,hsm_id,amount) 
        return res

    def set_first_pk(self,card_id,pk):
        '''
        Requests server to set a card's first pk (for provisioning)
        Args:
            card_id (int): The card id to set the pin for
            pk (str): The pk to set

        Returns:
            bool: True on success, False otherwise
        '''
        return self.bank_rpc.set_first_pk(card_id, pk) 

class DummyBank:
    """Emulated bank for testing"""

    def __init__(self):
        pass

    def random_generator(self,size=32,chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for c in range(size))

    def get_nonce(self,card_id):
        '''
        Asks the bank server to generate a random nonce so that the card can proove itself
        
        Args:
            card_id(int): The id on the card. will be used to help the bank find the shared secret to decrypt.
        
        Returns:
            str: Randomly generated nonce
        '''
        #nonce = self.bank_rpc.get_nonce(card_id)
        #return nonce
        return self.random_generator()
    
    def check_balance(self,card_id,signed_nonce,hsm_nonce,hsm_id):
        '''
        Verifies that a nonce has been properly signed. 
        
        Args:
            card_id(int): The id on the card. will be used to help the bank find the shared secret to decrypt.
            signed_nonce(str): Proof the message came from the card with the pin
            hsm_nonce: Nonce the server needs to sign for the hsm to decrypt the message the server signs
            hsm_id: ID of the hsm
        
        Returns:
            str: Response will be an encrypted message containing the account balance 
        '''
        encoded_signed_nonce = xmlrpclib.Binary(signed_nonce)
        encoded_hsm_nonce = xmlrpclib.Binary(hsm_id)
        return ''.join(random.choice(string.digits) for c in range(4))
        #res = self.bank_rpc.check_balance(card_id,encoded_signed_nonce,encoded_hsm_nonce,hsm_id) #signed_nonce,transaction,extra_data
        #return res
    
    def change_pin(self,card_id,signed_nonce,new_pk):        
        '''
        Changes the public key the server is using
    
        Args:
            card_id(int): The id on the card. will be used to help the bank find the shared secret to decrypt.
            signed_nonce(str): Proof the message came from the card with the pin
            new_pk(str): The new private key the server should use
            
        Returns:
            str: Response will be either an accept or reject message 
        '''
        encoded_signed_nonce = xmlrpclib.Binary(signed_nonce)
        return ('Accept')
        #res = self.bank_rpc.change_pin(card_id,encoded_signed_nonce,new_pk) 
        #return res


    def withdraw(self,card_id,signed_nonce,hsm_nonce,hsm_id,amount):
        '''
        Requests server to aproove a withdraw request. 
        
        Args:
            card_id(int): The id on the card.
            signed_nonce(str): Proof the message came from the card with the pin
            hsm_nonce: Nonce the server needs to sign for the hsm to decrypt the message the server signs
            hsm_id: ID of the hsm
            amount: Amount of money requested
        
        Returns:
            str: Response will be an encrypted message containing the acount balance 
        '''
        encoded_signed_nonce = xmlrpclib.Binary(signed_nonce)
        encoded_hsm_nonce = xmlrpclib.Binary(hsm_nonce)
        return ''.join(random.choice(string.digits) for c in range(4))
        #res = self.bank_rpc.withdraw(card_id,encoded_signed_nonce,encoded_hsm_nonce,hsm_id,amount) 
        #return res
