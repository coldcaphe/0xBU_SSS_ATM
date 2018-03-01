import logging
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
        #transaction IDs
        #enum values for message types
        self.REQUEST_NAME                = 0x00
        self.RETURN_NAME                 = 0x01
        self.REQUEST_CARD_SIGNATURE      = 0x02
        self.RETURN_CARD_SIGNATURE       = 0x03
        self.REQUEST_HSM_NONCE           = 0x04
        self.RETURN_HSM_NONCE            = 0x05
        self.REQUEST_HSM_UUID            = 0x06
        self.RETURN_HSM_UUID             = 0x07
        self.REQUEST_WITHDRAWAL          = 0x08
        self.RETURN_WITHDRAWAL           = 0x09
        self.REQUEST_BALANCE             = 0x0A
        self.RETURN_BALANCE              = 0x0B
        self.REQUEST_NEW_PK              = 0x0C
        self.RETURN_NEW_PK               = 0x0D

        #enum values for transaction opcodes
        self.CHECK_BALANCE               = 0x11
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
            card_id = self.card.get_card_id(self.REQUEST_NAME)


            # request nonce from server
            if card_id is not None: #checks that it's not none
                hsm_id = self.hsm.get_uuid(self.REQUEST_HSM_UUID)
                hsm_nonce = self.hsm.get_nonce(self.REQUEST_HSM_NONCE) 
                nonce = self.bank.get_nonce(card_id) 
                signed_nonce = self.card.sign_nonce(self.REQUEST_CARD_SIGNATURE,nonce,pin) #signs the random nonce
                response = self.bank.check_balance(card_id,signed_nonce,hsm_nonce,hsm_id) #this response will contain the signed nonce from the server

                if response is not None: #checks that it's not None
                    hsm_resp = self.hsm.send_action(self.REQUEST_BALANCE,response)
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
        try:
            card_id = self.card.get_card_id(self.REQUEST_NAME)
            
            # request nonce from server
            if card_id is not None: #checks that it's not none
                logging.info('Requesting nonce')
                nonce = self.bank.get_nonce(card_id) #encrypted nonce
                signed_nonce = self.card.sign_nonce(self.REQUEST_CARD_SIGNATURE,nonce,old_pin) #signs the random nonce
                new_pk = self.card.request_new_public_key(self.REQUEST_NEW_PK,new_pin)
                response = self.bank.change_pin(card_id,signed_nonce,new_pk)
                
                if response is not None:
                    return response #returns if nonce is verified and pin change is successful 
                
        except DeviceRemoved:
            logging.info('ATM card was removed!')
            return False 
        
        if not self.card.inserted():
            logging.info('No card inserted')
            return False
        try:
            logging.info('change_pin: Sending PIN change request to card')
            if self.card.change_pin(old_pin, new_pin):
                return True
            logging.info('change_pin failed')
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
            card_id = self.card.get_card_id(self.REQUEST_NAME)
            
            # request nonce from server
            if card_id is not None: #checks that it's not none
                logging.info('Requesting nonce')
                hsm_id = self.hsm.get_uuid(self.REQUEST_HSM_UUID)
                hsm_nonce = self.hsm.get_nonce(self.REQUEST_HSM_NONCE) #encrypted nonce
                                                        
                nonce = self.bank.get_nonce(card_id) #encrypted nonce
                signed_nonce = self.card.sign_nonce(self.REQUEST_CARD_SIGNATURE,nonce,pin) #signs the random nonce
                response = self.bank.withdraw(card_id,signed_nonce,hsm_nonce,hsm_id,amount) #this response will contain the signed nonce from the server
                if response is not None: #hsm
                    hsm_resp = self.hsm.send_action(self.REQUEST_WITHDRAWAL,response)
                    if hsm_resp is not None:
                        return hsm_resp #returns if nonce was verified by the HSM                    
                
        except DeviceRemoved:
            logging.info('ATM card was removed!')
            return False 
        
        if not self.card.inserted():
            logging.info('No card inserted')
            return False
        try:
            logging.info('change_pin: Sending PIN change request to card')
            if self.card.change_pin(old_pin, new_pin):
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
