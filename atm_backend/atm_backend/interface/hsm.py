from psoc import Psoc
import struct
from serial_emulator import HSMEmulator
import logging
import time

class HSM(Psoc):
    """Interface for communicating with the HSM

    Args:
        port (str, optional): Serial port connected to HSM
        verbose (bool, optional): Whether to print debug messages

    Note:
        Calls to get_uuid and withdraw must be alternated to remain in sync
        with the HSM
    """

    def __init__(self, port=None, verbose=False, dummy=False):
        super(HSM, self).__init__('HSM', port, verbose)
        self._vp('Please connect HSM to continue.')
        while not self.connected and not dummy:
            time.sleep(2)
        self._vp('Initialized')

    def _authenticate(self, uuid):
        """Requests authentication from the HSM

        Args:
            uuid (str): Challenge UUID of HSM

        Returns:
            bool: True if HSM verified authentication, False otherwise
        """
        self._vp('Sending UUID %s' % uuid)
        self._push_msg('%s\00' % uuid)

        resp = self._pull_msg()
        self._vp('Received response %s from HSM' % resp)

        return resp == 'K'
    
    '''Has the hsm generate a random nonce and store it in the cash.
    Server needs to sign this nonce to proove that it is a valid request

    Args:
    transaction(int): The transaction type. Lets the hsm know what is happening

    Returns:
    a randomly generated nonce that is encrypted with a shared secret key that corosponds to 
    the hsm_id

    '''
    def get_nonce(self,transaction):
        self._sync(True)
        self._push_msg(struct.pack('b',transaction))
        resp = self._pull_msg()

        return struct.unpack('b32s',resp)[1]
        

    def get_uuid(self,transaction):
        """Retrieves the UUID from the HSM
        Args:
            transaction(int): The transaction type. Lets the hsm know what is happening

        Returns:
            str: UUID of HSM
        """
        self._sync(True)
        self._push_msg(struct.pack('b',transaction))
        uuid = struct.unpack('b32s',self._pull_msg())[1]
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
        self._push_msg(signed_nonce_and_amount)
        resp = self._pull_msg()
        return resp

    def provision(self, uuid, bills):
        """Attempts to provision HSM

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


class DummyHSM(HSM):
    """Emulated HSM for testing

    Arguments:
        verbose (bool, optional): Whether to print debug messages
        provision (bool, optional): Whether to start the HSM ready
            for provisioning
    """
    def __init__(self, verbose=False, provision=False):
        ser = HSMEmulator(verbose=verbose, provision=provision)
        super(DummyHSM, self).__init__(port=ser, verbose=verbose, dummy=True)
