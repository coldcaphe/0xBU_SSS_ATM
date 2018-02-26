"""Backend of ATM interface for xmlrpc"""

import logging
import sys
import socket
import xmlrpclib


class Bank:
    """Interface for communicating with the bank
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
    
    
    '''Asks the bank server to generate a random nonce so that the card can proove itself
    Args:
        card_id(int): The id on the card. will be used to help the bank find the shared secret to decrypt.
    Returns:
        Randomly generated nonce
    '''
    def get_nonce(self,card_id):
        nonce = self.bank_rpc.get_nonce(card_id)
        return nonce
    
    '''Verifyies that a nonce has been properly signed. 
    Args:
        card_id(int): The id on the card. will be used to help the bank find the shared secret to decrypt.
        signed_nonce(str): Proof the message came from the card with the pin
        hsm_nonce: a nonce the server needs to sign for the hsm to decrypt the message the server signs
        hsm_id: the id of the hsm
        Returns:
        the response, will be an encrypted message containing the acount balance 
    '''
    def check_balance(self,card_id,signed_nonce,hsm_nonce,hsm_id):
        res = self.bank_rpc.verify_nonce(card_id,signed_nonce,hsm_nonce,hsm_id) #signed_nonce,transaction,extra_data
        return res
    
    '''Changes the public key the server is using
    Args:
        card_id(int): The id on the card. will be used to help the bank find the shared secret to decrypt.
        signed_nonce(str): Proof the message came from the card with the pin
        new_pk(str): the new private key the server should use
    Returns:
    the response, will be either an accept or reject message 
    '''
    def change_pin(self,card_id,signed_nonce,new_pk):
        res = self.bank_rpc.verify_nonce(card_id,signed_nonce,hsm_nonce,hsm_id) 
        return res

    '''Requests server to aproove a withdraw request. 
    Args:
        card_id(int): The id on the card. will be used to help the bank find the shared secret to decrypt.
        signed_nonce(str): Proof the message came from the card with the pin
        hsm_nonce: a nonce the server needs to sign for the hsm to decrypt the message the server signs
        hsm_id: the id of the hsm
        amount: the amount of money requested
        Returns:
        the response, will be an encrypted message containing the acount balance 
    '''
    def withdraw(self,card_id,signed_nonce,hsm_nonce,hsm_id,amount):
        res = self.bank_rpc.verify_nonce(card_id,signed_nonce,hsm_nonce,hsm_id,amount) 
        return res

class DummyBank:
    """Emulated bank for testing"""

    def __init__(self):
        pass

    def withdraw(self, hsm_id, card_id, amount):
        """Authorizes a requested withdrawal
        Args:
            hsm_id (str): UUID of HSM
            card_id (doesn't matter): Isn't used
            amount: (doesn't matter): Isn't used
        Returns:
            str: hsm_id
        """
        return hsm_id

    def check_balance(self, card_id):
        """Authorizes a requested balance check
        Args:
            card_id (doesn't matter): Isn't used
        Returns:
            int: Balance of 2018
        """
        return 2018
