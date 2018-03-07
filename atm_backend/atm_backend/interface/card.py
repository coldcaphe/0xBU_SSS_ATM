from psoc import Psoc
from serial_emulator import CardEmulator
import logging
import struct


class Card(Psoc):
    """
    Interface for communicating with the ATM card

    Args:
        port (str, optional): Serial port connected to an ATM card
            Default is dynamic card acquisition
        verbose (bool, optional): Whether to print debug messages
    """

    def __init__(self, port=None, verbose=False):
        self.port = port
        self.verbose = verbose

    def initialize(self):
        super(Card, self).__init__('CARD', self.port, self.verbose)

    def get_card_id(self):
        """
        Checks the card balance

        Returns:
            str: UUID of ATM card on success
        """
        self._sync(False)
        self._push_msg(struct.pack('b', self.REQUEST_NAME)) 
        response = self.read(size=37)
        return struct.unpack('b36s',response)[1]
    
    def sign_nonce(self,nonce, pin):
        """
        Signs the random nonce, called when customer tries to perform
        an action of the account associated with the connected ATM card

        Args:
            nonce (str): Random nonce
            pin (str): Challenge PIN
            transaction (int): Transaction ID
            
        Returns 
            str: Signed nonce
        """

        self._sync(False)
        self._push_msg(struct.pack('b32s8s', self.REQUEST_CARD_SIGNATURE, nonce, pin)) 
        signed_nonce = self.read(size=65)

        return struct.unpack('b64s',signed_nonce)[1]

    def request_new_public_key(self, new_pin):
        """
        Calculates what the public key would be based on the pin sent

        Args:
            transaction(int): Transaction ID
            new_pin: theoretical new pin
            
        Returns
            str: New Public Key
        """

        self._sync(False)
        self._push_msg(struct.pack('B8s', self.REQUEST_NEW_PK, new_pin))
        public_key = self.read(size=33)
        return struct.unpack('32s',public_key[1:])[0]

    def provision(self, r, rand_key, uuid):
        """
        Attempts to provision a new ATM card

        Args:
            r (str): 32 byte prf key
            rand_key (str): 32 byte prf key for randomness
            uuid (str): New UUID for ATM card

        Returns:
            bool: True if provisioning succeeded, False otherwise
        """

        self._sync(True)
        self._push_msg(struct.pack("1s", chr(self.REQUEST_PROVISION)))
        self._push_msg(struct.pack("32s", r))
        self._push_msg(struct.pack("32s", rand_key))
        self._push_msg(struct.pack("36s", uuid))

        if ord(self.read(1)) != self.ACCEPTED:
            return False

        return True

import string
import random
def random_generator(size=32, chars=string.ascii_uppercase + string.digits):                           
    return ''.join(random.choice(chars) for x in range(size))

class DummyCard(Card):

    """Emulated ATM card for testing

    Arguments:
        verbose (bool, optional): Whether to print debug messages
        provision (bool, optional): Whether to start the ATM card ready
            for provisioning
    """
    def __init__(self, verbose=False, provision=False):
        ser = CardEmulator(verbose=verbose, provision=provision)
        super(DummyCard, self).__init__(ser, verbose)
    
    
    def get_card_id(self,transaction):
        """Checks the card balance

        Returns:
            str: UUID of ATM card on success
        """
        return "CARD_0001"

    
    def sign_nonce(self,transaction, nonce, pin):
        """Signs the random nonce, called when customer tries to perform
        an actoin of the account associated with the connected ATM card

        Args:
            nonce (str): Random nonce
            pin (str): Challenge PIN
            transaction (int): Transaction ID
        Returns 
            str: Signed nonce
        """

        packed = struct.pack('b32s8s',transaction,nonce,pin)
        signed_nonce = struct.pack('b32s',0,random_generator()) 

        return struct.unpack('b32s',signed_nonce)[1]

        """Calculates what the public key would be based on the pin sent

        Args:
            transaction(int): Transaction ID
            new_pin: theoretical new pin
        Returns
            str: New Public Key
        """
    def request_new_public_key(self,transaction,new_pin):
        packed = struct.pack('b8s',transaction,new_pin)
        public_key = struct.pack('b32s',0,random_generator())
        return struct.unpack('b32s',public_key)

    def provision(self, uuid, pin):
        """Attempts to provision a new ATM card

        Args:
            uuid (str): New UUID for ATM card
            pin (str): Initial PIN for ATM card

        Returns:
            bool: True if provisioning succeeded, False otherwise
        """

        self._sync(True)

        msg = self._pull_msg()
        if msg != 'P':
            self._vp('Card alredy provisioned!', logging.error)
            return False
        self._vp('Card sent provisioning message')

        self._push_msg('%s\00' % pin)
        while self._pull_msg() != 'K':
            self._vp('Card hasn\'t accepted PIN', logging.error)
        self._vp('Card accepted PIN')

        self._push_msg('%s\00' % uuid)
        while self._pull_msg() != 'K':
            self._vp('Card hasn\'t accepted uuid', logging.error)
        self._vp('Card accepted uuid')

        self._vp('Provisioning complete')

        return True

