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
        self.CHECK_BAL = 1
        self.WITHDRAW = 2
        self.CHANGE_PIN = 3
        self.SIGN_NONCE = 4


    def check_balance(self, pin):#secured
        """Tries to check the balance of the account associated with the
        connected ATM card

        Args:
            pin (str): 8 digit PIN associated with the connected ATM card

        Returns:
            str: Balance on success
            bool: False on failure
        """
        transaction = self.CHECK_BAL
        if not self.card.inserted():
            logging.info('No card inserted')
            return False

        try:
            logging.info('check_balance: Requesting card_id using inputted pin')
            card_id = self.card.getCardID()

            # request nonce from server
            if card_id is not None: #checks that its not none
                logging.info('Requesting nonce')
                nonce = self.bank.get_nonce(card_id) #this nonce is encyrpted
                #nonce = encrypt(nonce)
                encrypted_data = self.card.sign_nonce(nonce,pin,transaction) # signed nonce, transaction
                
                response = self.bank.verify_nonce(card_id,encrypted_data)
                if response is not None:
                    return response #returns bank balance
                
            logging.info('check_balance failed')
            return False
        except DeviceRemoved:
            logging.info('ATM card was removed!')
            return False
        except NotProvisioned:
            logging.info('ATM card has not been provisioned!')
            return False

    def change_pin(self, old_pin, new_pin):
        """Tries to change the PIN of the connected ATM card

        Args:
            old_pin (str): 8 digit PIN currently associated with the connected
                ATM card
            new_pin (str): 8 digit PIN to associate with the connected ATM card

        Returns:
            bool: True on successful PIN change
            bool: False on failure
        """
        
        transaction = self.CHANGE_PIN
        try:
            card_id = self.card.getCardId()
            
            # request nonce from server
            if card_id is not None: #checks that its not none
                logging.info('Requesting nonce')
                nonce = self.bank.get_nonce(card_id) #this nonce is encyrpted
                #nonce = encrypt(nonce)
                encrypted_data = self.card.change_pin_sign_nonce(nonce,old_pin,new_pin,transaction) # signed nonce,transaction,extra_data
                response = self.bank.verify_nonce(card_id,encrypted_data)
                
                if response is not None:
                    return response #returns bank balance
                
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
        
        transaction = self.WITHDRAW

        if not self.hsm.inserted():
            logging.info('No card inserted')
            return False

        if not isinstance(amount, int):
            logging.info('withdraw: amount must be int')
            return False

        try:
            card_id = self.card.getCardId()
            
            # request nonce from server
            if card_id is not None: #checks that its not none
                logging.info('Requesting nonce')
                hsm_id = self.hsm.get_uuid()
                                                        
                nonce = self.bank.get_nonce(card_id) #this nonce is encyrpted
                #nonce = encrypt(nonce)
                encrypted_data = self.card.withdraw_sign_nonce(nonce,pin,hsm_id,transaction) # signed nonce,transaction,extra_data
                response = self.bank.verify_nonce(card_id,encrypted_data)
                if response is not None:
                    ##return response #returns bank balance
                    hsm_encrypted_data = self.hsm.get_nonce(response)
                    server_encrypted_data = self.bank.hsm_sign_nonce(hsm_id,hsm_encrypted_data)
                    hsm_resp = self.hsm.verify_signed_nonce(server_encrypted_data)
                    if hsm_resp is not None:
                        return hsm_resp
                    
                
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
