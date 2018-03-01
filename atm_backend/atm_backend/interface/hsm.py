from psoc import Psoc
import struct
from serial_emulator import HSMEmulator
import logging
import time

class HSM(Psoc):
    """
    Interface for communicating with the HSM

    Args:
        port (str, optional): Serial port connected to HSM
        verbose (bool, optional): Whether to print debug messages

    Note:
        Calls to get_uuid and withdraw must be alternated to remain in sync
        with the HSM
    """

    def __init__(self, port=None, verbose=False, dummy=False):
        self.port = port
        self.verbose = verbose
        self.dummy = dummy
        
    def initialize(self):
        super(HSM, self).__init__('HSM', self.port, self.verbose)
        self._vp('Please connect HSM to continue.')
        while not self.connected and not self.dummy:
            time.sleep(2)
        self._vp('Initialized')
        self.RETURN_WITHDRAWAL      = 0x09
        self.RETURN_BALANCE         = 0x0B
        self.ACCEPTED               = 0x20
        self.REJECTED               = 0x21


    

    def get_nonce(self,transaction):   
        '''
        Has the hsm generate a random nonce and store it in the cash.
        Server needs to sign this nonce to proove that it is a valid request

        Args:
            transaction(int): The transaction type. Lets the hsm know what is happening

        Returns:
            str: Randomly generated nonce that is encrypted with a shared secret key that corosponds to 
            the hsm_id
        '''
        self._sync(True)
        self._push_msg(struct.pack('b',transaction))
        resp = self.read(size=33) #read 33 bytes
        return struct.unpack('b32s',resp)[1]
        

    def get_uuid(self,transaction):
        """
        Retrieves the UUID from the HSM
        
        Args:
            transaction(int): The transaction type. Lets the hsm know what is happening

        Returns:
            str: UUID of HSM
        """
        self._sync(True)
        self._push_msg(struct.pack('b',transaction))
        resp = self.read(size=33) #read 33 bytes
        uuid = struct.unpack('b32s',resp)[1]
        return uuid

    def send_action(self,transaction,encrypted_data):
        '''
        Verifies the nonce was correctly signed and completes the transactions request

        Args:
            transaction(int): The transaction type. Lets the hsm know what is happening
            encrypted_data(str): contains the data that the hsm will use for its transaction
     
        Returns:
            var: Can either be an array of bills or a balance.
        '''
        self._push_msg(struct.pack('b',transaction)+encrypted_data)
        resp = self.read(size=1)
        responseAction = struct.unpack('b',resp)
        
        if responseAction == self.RETURN_BALANCE: #handles case depending on byte
            resp = self.read(size=1) #determine if request was bad and should keep reading
            acceptByte =struct.unpack('b',resp)
            
            if acceptByte==self.ACCEPTED:
                resp = self.read(size=4)
                balance = struct.unpack('i',resp)
                return balance #reveals acount balance to atm
            elif acceptByte==self.REJECTED:
                raise Exception('HSM Rejected request')
            else:
                raise ValueError('Unexpected Byte read from hsm (expected ACCEPT or REJECT byte) got: ' + str(acceptByte))
                
        elif responseAction == self.RETURN_WITHDRAWAL:
            resp = self.read(size=4)
            numBills = struct.unpack('i',resp) #number of bills to pull
            bills = [] #array of bills
            
            for i in range(numBills):
                resp = self.read(size=16)
                bill = struct.unpack('16s',resp) #loads the 16 byte bill
                bills.append(bill)
            return bills
        
        else:
            raise ValueError('Unexpected Byte read from hsm (expected Withdrawal or Check Balance byte ) got: ' + str(responseAction))


    def provision(self, hsm_key, rand_key, uuid, bills):
        """
        Attempts to provision HSM

        Args:
            uuid (str): UUID for HSM
            bills (list of str): List of bills to store in HSM

        Returns:
            bool: True if HSM provisioned, False otherwise
        """
        self._sync(True)

        msg = self._pull_msg()
        if msg != 'P':
            self._vp('HSM already provisioned!', logging.error)
            return False
        self._vp('HSM sent provisioning message')

        ########################

        self._push_msg(struct.pack("32s", hsm_key))
        while self._pull_msg() != 'K':
            self._vp('Card hasn\'t accepted hsm_key', logging.error)
        self._vp('Card accepted hsm_key')

        self._push_msg(struct.pack("32s", rand_key))
        while self._pull_msg() != 'K':
            self._vp('Card hasn\'t accepted rand_key', logging.error)
        self._vp('Card accepted rand_key')

        self._push_msg(struct.pack("32s", uuid))
        while self._pull_msg() != 'K':
            self._vp('Card hasn\'t accepted uuid', logging.error)
        self._vp('Card accepted uuid')

        for bill in bills:
            msg = bill.strip()
            self._vp('Sending bill \'%s\'' % msg.encode('hex'))
            self._push_msg(msg)

            while self._pull_msg() != 'K':
                self._vp('HSM hasn\'t accepted bill', logging.error)
            self._vp('HSM accepted bill')

        self._vp('All bills sent! Provisioning complete!')

        return True


import string
import random
class DummyHSM(HSM):
    def random_generator(size=32, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for x in range(size))

    """Emulated HSM for testing

    Arguments:
        verbose (bool, optional): Whether to print debug messages
        provision (bool, optional): Whether to start the HSM ready
            for provisioning
    """
    def __init__(self, verbose=False, provision=False):
        ser = HSMEmulator(verbose=verbose, provision=provision)
        super(DummyHSM, self).__init__(port=ser, verbose=verbose, dummy=True)
 
    '''Has the hsm generate a random nonce and store it in the cash.
    Server needs to sign this nonce to proove that it is a valid request

    Args:
    transaction(int): The transaction type. Lets the hsm know what is happening

    Returns:
    a randomly generated nonce that is encrypted with a shared secret key that corosponds to 
    the hsm_id

    '''
    def get_nonce(self,transaction):
        packed = struct.pack('b',transaction)
        resp = struct.pack('b32s',1,random_generator()) #read 33 bytes
        return struct.unpack('b32s',resp)[1]
        

    def get_uuid(self,transaction):
        """Retrieves the UUID from the HSM
        Args:
            transaction(int): The transaction type. Lets the hsm know what is happening

        Returns:
            str: UUID of HSM
        """
        packed = struct.pack('b',transaction)
        resp = struct.pack('b32s',1,random_generator()) #read 33 bytes
        uuid = struct.unpack('b32s',resp)[1]
        return uuid

    '''
    Verifies the nonce was correctly signed and completes the transactions request

    Args:
        transaction(int): The transaction type. Lets the hsm know what is happening
        encrypted_data(str): contains the data that the hsm will use for its transaction
    Returns:
        var: Can either be an array of bills or a balance.
    '''
    def send_action(self,transaction,encrypted_data):
        packed = (struct.pack('b',transaction)+encrypted_data)
        responseAction = self.RETURN_BALANCE if transaction == 0x0A else self.RETURN_WITHDRAWAL
        if responseAction == self.RETURN_BALANCE: #handles case depending on byte
            acceptByte = self.ACCEPTED
            if acceptByte==self.ACCEPTED:
                balance = 5000 
                return balance #reveals acount balance to atm
            elif acceptByte==self.REJECTED:
                raise Exception('HSM Rejected request')
            else:
                raise ValueError('Unexpected Byte read from hsm (expected ACCEPT or REJECT byte) got: ' + str(acceptByte))
        elif responseAction == self.RETURN_WITHDRAWAL:
            numBills = 3 #number of bills to pull
            bills = ['chets $$$$$$ bill 1', 'chets $$$$$$$ 2', 'chesttess $$$$$$$3' ] #array of bills
            return bills
        else:
            raise ValueError('Unexpected Byte read from hsm (expected Withdrawal or Check Balance byte ) got: ' + str(responseAction))


    def provision(self, uuid, bills):
        """Attempts to provision HSM

        Args:
            uuid (str): UUID for HSM
            bills (list of str): List of bills to store in HSM

        Returns:
            bool: True if HSM provisioned, False otherwise
        """

        msg = self._pull_msg()
        if msg != 'P':
            self._vp('HSM already provisioned!', logging.error)
            return False
        self._vp('HSM sent provisioning message')

        self._push_msg('%s\00' % uuid)
        while self._pull_msg() != 'K':
            self._vp('HSM hasn\'t accepted UUID \'%s\'' % uuid, logging.error)
        self._vp('HSM accepted UUID \'%s\'' % uuid)

        self._push_msg(struct.pack('B', len(bills)))
        while self._pull_msg() != 'K':
            self._vp('HSM hasn\'t accepted number of bills', logging.error)
        self._vp('HSM accepted number of bills')

        for bill in bills:
            msg = bill.strip()
            self._vp('Sending bill \'%s\'' % msg.encode('hex'))
            self._push_msg(msg)

            while self._pull_msg() != 'K':
                self._vp('HSM hasn\'t accepted bill', logging.error)
            self._vp('HSM accepted bill')

        self._vp('All bills sent! Provisioning complete!')

        return True


