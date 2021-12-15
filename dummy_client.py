import os, sys

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from ADC_Controller_qtimer import *

class dummyClient(QObject):
    def __init__(self):
        super().__init__()
        self.user_name = "test"

    def toMessageList(self, message):
        print(">>> ", message)

class dummy(QMainWindow):
    def __init__(self):
        super().__init__()

    def executeController(self):
        controller = AdcController(device="GDM8341")
        controller.openDevice()
        client = dummyClient()
        print("1 : C / ON / [] / client")
        print("2 : C / OFF / [] / client")
        print("3 : Q / VOLT_ON / [channel_number] / client")
        print("4 : Q / VOLT_OFF / [] / client")
        print("5 : Q / SWITCH_CHANNEL / [channel_number] / client")
        while(True):
            try:
                flag = int(input())
            except:
                print("wrong format")
                continue
            
            if flag == 1:
                message = ['C', 'ON', [], client]
            elif flag == 2:
                message = ['C', 'OFF', [], client]
            elif flag == 3:
                try:
                    channel_number = int(input("initial channel : "))
                except:
                    print("channel number - enter 1~4")
                    continue
                if channel_number<1 or channel_number>4:
                    print("channel number - enter 1~4")
                    continue
                message = ['Q', 'VOLT_ON', [channel_number], client]
            elif flag == 4:
                message = ['Q', 'VOLT_OFF', [], client]
            elif flag == 5:
                try:
                    channel_number = int(input("change channel to : "))
                except:
                    print("channel number - enter 1~4")
                    continue
                if channel_number<1 or channel_number>4:
                    print("channel number - enter 1~4")
                    continue
                message = ['Q', 'SWITCH_CHANNEL', [channel_number], client]
            elif flag == -1:
                break
            else:
                print("enter 1~5 or -1")
                continue
            controller.toWorkList(message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dum = dummy()
    dum.show()
    dum.executeController()
    sys.exit(app.exec_())
