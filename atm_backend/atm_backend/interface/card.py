from psoc import Psoc
from serial_emulator import CardEmulator
import logging


class Card(Psoc):
    """Interface for communicating with the ATM card

    Args:
        port (str, optional): Serial port connected to an ATM card
            Default is dynamic card acquisition
        verbose (bool, optional): Whether to print debug messages
    """
    def __init__(self, port=None, verbose=False):
        super(Card, self).__init__('CARD', port, verbose)
        self.CHECK_BAL = 1
        self.WITHDRAW = 2
        self.CHANGE_PIN = 3
        self.SIGN_NONCE = 4

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

        if not self._authenticate(old_pin):
            return False

        self._send_op(self.CHANGE_PIN)

        self._vp('Sending PIN %s' % new_pin)
        self._push_msg(new_pin)

        resp = self._pull_msg()
        self._vp('Card sent response %s' % resp)
        return resp == 'SUCCESS'

    def getCardID(self):
        """checks the card balance

        Returns:
            str: UUID of ATM card on success
        """
        self._sync(False) #not sure if this should be true

        return self._get_uuid()
    
    def change_pin_sign_nonce(self, nonce, old_pin, new_pin, transaction):
        """signs the random nonce

        Args:
            nonce (str): random nonce
            old_pin (str): Challenge PIN
            new_pin (str)
            transaction (int): transaction ID

        Returns 
            str: signed Nonce
        """
        
        self._sync(False) #not sure if this should be true
        self._send_op(self.SIGN_NONCE) 
        self._push_msg(str(transaction) + new_pin + old_pin + nonce + '\00') 
        signedNonce = self._pull_msg()

        return signedNonce

    def withdraw_sign_nonce(self, nonce, pin, hsm_nonce, hsm_id, amount, transaction):
        """signs the random nonce

        Args:
            nonce (str): random nonce
            old_pin (str): Challenge PIN
            hsm_id (str)
            transaction (int): transaction ID

        Returns 
            str: signed Nonce
        """
        
        self._sync(False) #not sure if this should be true
        self._send_op(self.SIGN_NONCE) 
        self._push_msg(str(transaction) + amount + pin + hsm_id + hsm_nonce + nonce + '\00') 
        signedNonce = self._pull_msg()

        return signedNonce
    
    def sign_nonce(self, nonce, pin, transaction):
        """signs the random nonce

        Args:
            nonce (str): random nonce
            pin (str): Challenge PIN
            transaction (int): transaction ID
        Returns 
            str: signed Nonce
        """
        self._sync(False) #not sure if this should be true
        self._send_op(self.SIGN_NONCE) 
        self._push_msg(str(transaction) + pin + nonce + '\00') 
        signedNonce = self._pull_msg()

        return signedNonce



    def withdraw(self, pin):
        """Requests to withdraw from ATM

        Args:
            pin (str): Challenge PIN

        Returns:
            str: UUID of ATM card on success
            bool: False if PIN didn't match
        """
        self._sync(False)

        if not self._authenticate(pin):
            return False

        self._send_op(self.WITHDRAW)

        return self._get_uuid()

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
