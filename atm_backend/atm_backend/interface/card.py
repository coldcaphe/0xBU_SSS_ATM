from psoc import Psoc
from serial_emulator import CardEmulator
import logging
import struct


class Card(Psoc):
    """Interface for communicating with the ATM card

    Args:
        port (str, optional): Serial port connected to an ATM card
            Default is dynamic card acquisition
        verbose (bool, optional): Whether to print debug messages
    """

    def __init__(self, port=None, verbose=False):
        super(Card, self).__init__('CARD', port, verbose)

    def _authenticate(self, pin):
        """Requests authentication from the ATM card

        Args:
            pin (str): Challenge PIN

        Returns:
            bool: True if ATM card verified authentication, False otherwise
        """

        self._vp('Sending pin %s' % pin)
        self._push_msg(pin)

        resp = self._pull_msg()
        self._vp('Card response was %s' % resp)
        return resp == 'OK'

    def _get_uuid(self):
        """Retrieves the UUID from the ATM card

        Returns:
            str: UUID of ATM card
        """

        uuid = self._pull_msg()
        self._vp('Card sent UUID %s' % uuid)
        return uuid

    def _send_op(self, op):
        """Sends requested operation to ATM card

        Args:
            op (int): Operation to send from [self.CHECK_BAL, self.WITHDRAW,
                self.CHANGE_PIN]
        """

        self._vp('Sending op %d' % op)
        self._push_msg(str(op))

        while self._pull_msg() != 'K':
            self._vp('Card hasn\'t received op', logging.error)
        self._vp('Card received op')

    def change_pin(self, old_pin, new_pin):
        """Requests for a pin to be changed

        Args:
            old_pin (str): Challenge PIN
            new_pin (str): New PIN to change to

        Returns:
            bool: True if PIN was changed, False otherwise
        """

        self._sync(False)

        if not self._authenticate(old_pin): #if old pin entered was not correct
            return False

        self._send_op(self.CHANGE_PIN)

        self._vp('Sending PIN %s' % new_pin)
        self._push_msg(new_pin)

        resp = self._pull_msg()
        self._vp('Card sent response %s' % resp)
        return resp == 'SUCCESS'

    def get_card_id(self,transaction):
        """Checks the card balance

        Returns:
            str: UUID of ATM card on success
        """

        self._sync(True)
        self._push_msg(struct.pack('b',transaction)) 
        response = self.read(s=1025)#reads 1025 bytes
        return struct.unpack('b1024s',response)[1]
    
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

        self._sync(True)
        self._push_msg(struct.pack('b32s8s',transaction,nonce,pin)) 
        signed_nonce = self.read(s=33)

        return struct.unpack('b32s',signed_nonce)[1]

        """Calculates what the public key would be based on the pin sent

        Args:
            transaction(int): Transaction ID
            new_pin: theoretical new pin
        Returns
            str: New Public Key
        """
    def request_new_public_key(self,transaction,new_pin):
        self._sync(True)
        self._push(struct.pack('b8s',transaction,new_pin))
        public_key = self.read(s=33)
        return struct.unpack('b32s',public_key)

    def provision(self, r, uuid):
        """Attempts to provision a new ATM card

        Args:
            r (str): 32 byte prf key
            uuid (str): New UUID for ATM card

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


