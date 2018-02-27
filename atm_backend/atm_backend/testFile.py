from interface import hsm,bank,card
import atm
myHSM = hsm.DummyHSM()
myBank = bank.DummyBank()
myCard = card.DummyCard()
myATM = atm.ATM(myBank,myHSM,myCard)
