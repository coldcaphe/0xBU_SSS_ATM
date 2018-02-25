import logging
from interface.psoc import DeviceRemoved, NotProvisioned



class ATM(object):
    """Interface for ATM xmlrpc server

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
        self.REQUEST_NAME                = 0x00
        self.RETURN_NAME                 = 0x01
        self.REQUEST_SERVER_NONCE        = 0x02
        self.RETURN_NONCE                = 0x03
        self.REQUEST_CARD_SIGNATURE      = 0x04
        self.RETURN_CARD_SIGNATURE       = 0x05
        self.REQUEST_HSM_NONCE           = 0x06
        self.RETURN_HSM_NONCE            = 0x07
        self.SEND_TRANSACTION_TO_SERVER  = 0x08
        self.RETURN_RESULT               = 0x09
        self.REQUEST_HSM_UUID            = 0x0A
        self.RETURN_HSM_UUID             = 0x0B
        self.REQUEST_WITHDRAWL           = 0x0C

        self.CHECK_PIN                   = 0x10
        self.CHECK_BALANCE               = 0x11
        self.CHANGE_PIN                  = 0x12
        self.WITHDRAW                    = 0x13
        



    def check_balance(self, pin): #secured
        """Tries to check the balance of the account associated with the
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
                logging.info('Requesting nonce')
                nonce = self.bank.get_nonce(self.REQUEST_SERVER_NONCE,card_id) #encrypted nonce
                encrypted_data = self.card.sign_nonce(self.CHECK_BALANCE,nonce,pin) #signs the random nonce
                response = self.bank.verify_nonce(SEND_TRANSACTION_TO_SERVER,card_id,encrypted_data)

                if response is not None: #checks that it's not None
                    return response # returns bank balance
                
            logging.info('check_balance failed')
            return False

        except DeviceRemoved:
            logging.info('ATM card was removed!')
            return False

        except NotProvisioned:
            logging.info('ATM card has not been provisioned!')
            return False

    def change_pin(self, old_pin, new_pin): #secured
        """Tries to change the PIN of the connected ATM card

        Args:
            old_pin (str): 8 digit PIN currently associated with the connected
                ATM card
            new_pin (str): 8 digit PIN to associate with the connected ATM card

        Returns:
            bool: True on successful PIN change
            bool: False on failure
        """
        
        transaction = self.CHANGE_PIN #set transaction ID
        try:
            card_id = self.card.get_card_id(self.REQUEST_NAME)
            
            # request nonce from server
            if card_id is not None: #checks that it's not none
                logging.info('Requesting nonce')
                nonce = self.bank.get_nonce(self.REQUEST_SERVER_NONCE,card_id) #encrypted nonce
                encrypted_data = self.card.change_pin_sign_nonce(self.CHANGE_PIN,nonce,old_pin,new_pin) #signs the random nonce
                response = self.bank.verify_nonce(self.SEND_TRANSACTION_TO_SERVER,card_id,encrypted_data)
                
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
        """Tries to withdraw money from the account associated with the
        connected ATM card

        Args:
            pin (str): 8 digit PIN currently associated with the connected
                ATM card
            amount (int): number of bills to withdraw

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
                                                        
                nonce = self.bank.get_nonce(self.REQUEST_SERVER_NONCE,card_id) #encrypted nonce
                encrypted_data = self.card.withdraw_sign_nonce(self.WITHDRAW,nonce,pin,hsm_nonce,hsm_id,amount) #signs the random nonce
                response = self.bank.verify_nonce(SEND_TRANSACTION_TO_SERVER,card_id,encrypted_data) #this response will contain the signed nonce from the server
                if response is not None: #hsm
                    hsm_resp = self.hsm.verify_signed_nonce(response)
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
