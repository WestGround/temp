from PyQt5.QtCore import QThread, QTimer, pyqtSignal
from queue import Queue
from GDM8341 import GDM8341

from GPIO import *

import time

class AdcController(QThread):
    """
    The controller class uses QThread class as a base, handling commands and the device is done by QThread.
    This avoids being delayed by the main thread's jam.
    
    The logger decorator automatically records exceptions when bugs happen.
    """
    sigStartTimer = pyqtSignal()
    sigStopTimer = pyqtSignal()
    _status = "standby"
    
    def __init__(self, logger=None, parent=None, device=None):  #원래는 device 자리에 adc 들어가있었음
        super().__init__()
        print("ADC controller v0.01")
        self.logger = logger
        self.device = device
        self._client_list = []
        self.queue = Queue()
        
        self.gpio = GPIO()
        self.channelNumber = -1

        self.timer = None
        self.sigStartTimer.connect(self.startQTimer)
        self.sigStopTimer.connect(self.stopQTimer)
    
    def logger_decorator(func):
        """
        It writes logs when an exception happens.
        """
        def wrapper(self, *args):
            try:
                func(self, *args)
            except Exception as err:
                if not self.logger == None:
                    self.logger.error("An error ['%s'] occured while handling ['%s']." % (err, func.__name__))
                else:
                    print("An error ['%s'] occured while handling ['%s']." % (err, func.__name__))
        return wrapper
    
    @logger_decorator
    def openDevice(self):
        if self.device == "GDM8341":
            from GDM8341 import GDM8341
            self.adc = GDM8341()
        self.adc.openDevice()
    
    @logger_decorator
    def closeDevice(self):
        self.adc.closeDevice()

    @logger_decorator    
    def toWorkList(self, cmd):
        client = cmd[-1]
        if not client in self._client_list:
            self._client_list.append(client)
            
        self.queue.put(cmd)
        if not self.isRunning():
            self.start()
            print("Thread started")

    def startQTimer(self):
        if self.timer == None:
            self.timer = QTimer()
            self.timer.timeout.connect(self.measureVoltage)
        self.timer.setInterval(1000)
        self.timer.start()

    def stopQTimer(self):
        self.timer.stop()

    def measureVoltage(self):
        result = self.adc.readVoltage('DC')
        msg = ['D', 'ADC', 'VOLT', [self.channelNumber, result]]
        self.informClients(msg, self._client_list)

    def switchChannel(self, channelNumber):
        if self.channelNumber == channelNumber:
            return

        self.channelNumber = channelNumber
        self.gpio.switchRelayBorad(channelNumber)

    @logger_decorator          
    def run(self):
        while True:
            # work example: ["Q", "VOLT", [1]]
            work = self.queue.get()
            self._status  = "running"
            # decompose the job
            work_type, command, data = work[:3]
            client = work[-1]

            if work_type == "C":
                if command == "ON":
                    """
                    When a client is connected, opens the devcie and send voltage data to the client.
                    """
                    print("opening the device")
                    if not self.adc._is_opened:
                        self.openDevice()
                    else:
                        print("The device is already opened")
                        
                    client.toMessageList(["D", "ADC", "HELO", []])
                    
                elif command == "OFF":
                    """
                    When a client is disconnected, terminate the client and close the device if no client left.
                    """
                    if client in self._client_list:
                        self._client_list.remove(client)
                    # When there's no clients connected to the server. close the device.
                    if not len(self._client_list):
                        self.closeDevice()
                        self.toLog("info", "No client is being connected. closing the device.")
                else:
                    self.toLog("critical", "Unknown command (\"%s\") has been detected." % command)

                #work[2] may be used for selecting the channel of ADC                 
            elif work_type == "Q":
                if command == "VOLT_ON":
                    channelNumber = data[0]
                    self.switchChannel(channelNumber)
                    self.sigStartTimer.emit()
                    # do not work - self.startQTimer()
                    msg = ['D', 'ADC', 'ON', [channelNumber]]
                elif command == "VOLT_OFF":
                    msg = ['D', 'ADC', 'OFF', []]
                    self.sigStopTimer.emit()
                    # do not work - self.stopQTimer()
                elif command == "SWITCH_CHANNEL":
                    channelNumber = data[0]
                    self.switchChannel(channelNumber)
                    msg = ['D', 'ADC', 'SWIT', [self.channelNumber]]
                else:
                    self.toLog("critical", "Unknown command (\"%s\") has been detected." % command)
                    continue
                self.informClients(msg, self._client_list)

            else:
                self.toLog("critical", "Unknown work type (\"%s\") has been detected." % work_type)
                continue

            self._status = "standby"

    @logger_decorator
    def informClients(self, msg, client):
        if type(client) != list:
            client = [client]
        
        print('To Client :', msg)
        for clt in client:
            clt.toMessageList(msg)
            
        print("informing Done!")
         
    def toLog(self, log_type, log_content):
        if not self.logger == None:
            if log_type == "debug":
                self.logger.debug(log_content)
            elif log_type == "info":
                self.logger.info(log_content)
            elif log_type == "warning":
                self.logger.warning(log_content)
            elif log_type == "error":
                self.logger.error(log_content)
            else:
                self.logger.critical(log_content)
        else:
            print(log_type, log_content)

"""
class Loop(QThread):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
             
        self._channelNumber = -1
        self._isRunning = False
        self._channelChanged = False
        self._mutex = QMutex()
        self._cond = QWaitCondition()

    def startLoop(self):
        self._isRunning = True
        self._cond.wakeAll()

    def stopLoop(self):
        self._isRunning = False

    def switchChannel(self, channelNumber):
        if channelNumber != self._channelNumber:
            self._channelChanged = True
            self._channelNumber = channelNumber
        
    def run(self):
        while True:
            self._mutex.lock()
            if self._isRunning:
                if self._channelChanged:
                    # todo - call GPIO module to change the output voltage configuration
                    #        self.gpio._some_function(self._channelNumber)
                    time.sleep(1)
                    self._channelChanged = False
                result = self.controller.adc.readVoltage("DC")
                msg = ['D', 'ADC', 'VOLT', [self._channelNumber, result]]
                self.controller.informClients(msg, [_client_list])   #notify the msg to the clients (maybe all clients)
                time.sleep(1)  
            else:
                self._cond.wait(self._mutex)
            self._mutex.unlock()
"""

class DummyClient():
    
    def __init__(self):
        pass
    
    def sendMessage(self, msg):
        print(msg)