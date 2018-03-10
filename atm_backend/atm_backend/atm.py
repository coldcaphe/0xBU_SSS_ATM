import logging
import xmlrpclib
from interface.psoc import DeviceRemoved, NotProvisioned

class ATM(object):
    """
    Interface for ATM xmlrpc server

    Args:
        bank (Bank or BankEmulator): Interface to bank
        hsm (HSM or HSMEmulator): Interface to HSM
        card (Card or CardEmulator): Interface to ATM card
    """
    
    def __init__(self, bank, hsm, card):
        self.bank = bank
        self.hsm = hsm
        self.card = card

        #enum values for transaction opcodes
        self.CHECK_BALANCE               = 0x11
        self.REQUEST_WITHDRAWAL         = 0x08
        self.REQUEST_BALANCE            = 0x0A
        self.WITHDRAW                    = 0x13


    def hello(self):
        logging.info("Got hello request")
        return "hello"


    def check_balance(self, pin): #secured
        """
        Tries to check the balance of the account associated with the
        connected ATM card

        Args:
            pin (str): 8 digit PIN associated with the connected ATM card

        Returns:
            str: Balance on success
            bool: False on failure
        """

        if not self.hsm.inserted():
            logging.info('No hsm inserted')
            return False

        if not self.card.inserted():
            logging.info('No card inserted')
            return False

        try:
            card_id = self.card.get_card_id()

            if card_id is None:
                logging.info('check_balance: didnt get card id')
                return False

            # request nonce from server
            hsm_id = self.hsm.get_uuid()
            if hsm_id is None:
                logging.info('check_balance: didnt get hsm id')
                return False

            hsm_nonce = self.hsm.get_nonce() 
            if hsm_nonce is None:
                logging.info('check_balance: didnt get hsm nonce')
                return False

            nonce = self.bank.get_nonce(card_id)
            if nonce is None:
                logging.info("check_balance: didn't get nonce :(")
                return False

            signature = self.card.sign_nonce(nonce, pin)
            if signature is None:
                logging.info("check_balance: didn't get signature :(")
                return False

            encrypted_balance = self.bank.check_balance(card_id, nonce, signature, hsm_id, hsm_nonce)
            if encrypted_balance is None:
                logging.info("check_balance: didn't get encrypted balance")
                return False

            hsm_resp = self.hsm.handle_balance_check(encrypted_balance)
            if hsm_resp is None:
                logging.info("check_balance: didn't get hsm response")
                return False

            return hsm_resp # returns bank balance

        except DeviceRemoved:
            logging.info('ATM card was removed!')
            return False

        except NotProvisioned:
            logging.info('ATM card has not been provisioned!')
            return False

    def change_pin(self, old_pin, new_pin): #secured
        """
        Tries to change the PIN of the connected ATM card

        Args:
            old_pin (str): 8 digit PIN currently associated with the connected
                ATM card
            new_pin (str): 8 digit PIN to associate with the connected ATM card

        Returns:
            bool: True on successful PIN change
            bool: False on failure
        """
        if not self.card.inserted():
            logging.info('No card inserted')
            return False

        try:
            card_id = self.card.get_card_id()
            if card_id is None:
                logging.info("change_pin: didn't get card_id")
                return False

            nonce = self.bank.get_nonce(card_id) 
            if nonce is None:
                logging.info("change_pin: didn't get nonce :(")
                return False

            new_pk = self.card.request_new_public_key(new_pin)
            if new_pk is None:
                logging.info("change_pin: didn't get new pk")
                return False

            signature = self.card.sign_nonce(nonce, old_pin)
            if signature is None:
                logging.info("change_pin: didn't get signature")
                return False

            response = self.bank.change_pin(card_id, nonce, signature, new_pk)
            if response is None:
                logging.info("change_pin: didn't get ok response")
                return False

            return response == "OKAY"

        except DeviceRemoved:
            logging.info('ATM card was removed!')
            return False

        except NotProvisioned:
            logging.info('ATM card has not been provisioned!')
            return False

    def withdraw(self, pin, amount):
        """
        Tries to withdraw money from the account associated with the
        connected ATM card

        Args:
            pin (str): 8 digit PIN currently associated with the connected
                ATM card
            amount (int): Number of bills to withdraw

        Returns:
            list of str: Withdrawn bills on success
            bool: False on failure
        """

        if not self.hsm.inserted():
            logging.info('No hsm inserted')
            return False

        if not self.card.inserted():
            logging.info('No card inserted')
            return False

        if not isinstance(amount, int):
            logging.info('withdraw: amount must be int')
            return False

        try:
            card_id = self.card.get_card_id()
            if card_id is None:
                logging.info("withdraw: didn't get card_id")
                return False
        
            hsm_id = self.hsm.get_uuid()
            if hsm_id is None:
                logging.info("withdraw: didn't get hsm_id")
                return False

            hsm_nonce = self.hsm.get_nonce()
            if hsm_nonce is None:
                logging.info("withdraw: didn't get hsm nonce")
                return False

            #get server nonce and sign it                                                        
            nonce = self.bank.get_nonce(card_id)
            if nonce is None:
                logging.info("withdraw: didn't get nonce")
                return False

            signature = self.card.sign_nonce(nonce,pin) 
            if signature is None:
                logging.info("withdraw: didn't get signature")
                return False

            #this response will contain an encrypted withdrawal request from the server to the hsm
            ciphertext = self.bank.withdraw(card_id, nonce, signature, hsm_id, hsm_nonce, amount)
            if ciphertext is None:
                logging.info("withdraw: didn't get ciphertext")
                return False

            hsm_resp = self.hsm.handle_withdrawal(ciphertext)
            if hsm_resp is None:
                logging.info("withdraw: didn't get hsm response")
                return False

            return hsm_resp #returns if nonce + encrypted request was verified by the HSM          

        except NotProvisioned:
            logging.info('ATM card has not been provisioned!')
            return False
        except ValueError:
            logging.info('amount must be an int')
            return False
        except DeviceRemoved:
            logging.info('ATM card was removed!')
            return False
        except NotProvisioned:
            logging.info('ATM card has not been provisioned!')
            return False
