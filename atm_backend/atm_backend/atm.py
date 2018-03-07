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

        if not self.card.inserted():
            logging.info('No card inserted')
            return False

        try:
            logging.info('check_balance: Requesting card_id using inputted pin')
            card_id = self.card.get_card_id()

            # request nonce from server
            if card_id is not None:
                hsm_id = self.hsm.get_uuid()
                hsm_nonce = self.hsm.get_nonce() 

                nonce = self.bank.get_nonce(card_id) 
                if nonce is None:
                    print "check_balance: didn't get nonce :("

                signature = self.card.sign_nonce(nonce, pin)
                response = str(self.bank.check_balance(card_id, nonce, signature, hsm_id, hsm_nonce))

                if "ERROR" == response[:len("ERROR")]:
                    return False

                hsm_resp = self.hsm.handle_balance_check(response)

                if hsm_resp is not None:
                    return hsm_resp # returns bank balance
                return response

            logging.info('check_balance failed')
            return False

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
            logging.info('check_balance: Requesting card_id using inputted pin')
            card_id = self.card.get_card_id()

            # request nonce from server
            if card_id is not None:

                nonce = self.bank.get_nonce(card_id) 
                if nonce is None:
                    print "check_balance: didn't get nonce :("

                new_pk = self.card.request_new_public_key(new_pin)
                signature = self.card.sign_nonce(nonce, old_pin)
                response = str(self.bank.change_pin(card_id, nonce, signature, new_pk))

                if "ERROR" == response[:len("ERROR")]:
                    return False

                return response == "OKAY"

            logging.info('check_balance failed')
            return False

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
            logging.info('No card inserted')
            return False

        if not isinstance(amount, int):
            logging.info('withdraw: amount must be int')
            return False

        try:
            card_id = self.card.get_card_id()
            
            if card_id is not None: #checks that it's not none
                logging.info('Requesting nonce')
                hsm_id = self.hsm.get_uuid()
                hsm_nonce = self.hsm.get_nonce()

                #get server nonce and sign it                                                        
                nonce = self.bank.get_nonce(card_id)
                signed_nonce = self.card.sign_nonce(nonce,pin) 

                #this response will contain the signed nonce from the server
                response = str(self.bank.withdraw(card_id, nonce, signed_nonce, hsm_id, hsm_nonce, amount))

                if "ERROR" == response[:len("ERROR")]:
                    return False 

                hsm_resp = self.hsm.handle_withdrawal(response)
                if hsm_resp is not None:
                    return hsm_resp #returns if nonce was verified by the HSM          

                return False          
                
        except DeviceRemoved:
            logging.info('ATM card was removed!')
            return False 
        
        if not self.card.inserted():
            logging.info('No card inserted')
            return False
        try:
            logging.info('change_pin: Sending PIN change request to card')
            if self.card.change_pin(pin, new_pin):
                return True
            logging.info('change_pin failed')
            return False

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
