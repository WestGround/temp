import time

from PyQt5.QtCore import QMutex, QThread, QWaitCondition
from queue import Queue
from GDM8341 import *
from GPIO import *

class AdcController(QThread):
    """
    The controller class uses QThread class as a base, handling commands and the device is done by QThread.
    This avoids being delayed by the main thread's jam.
    
    The logger decorator automatically records exceptions when bugs happen.
    """
    _status = "standby"
    
    def __init__(self, logger=None, parent=None, device=None):  #원래는 device 자리에 adc 들어가있었음
        super().__init__()
        self.logger = logger
        print("ADC controller v0.01")
        self.queue = Queue()
        self.adc = GDM8341()
        self.gpio = GPIO()
        self.loopThread = Loop(self, self.gpio)

        self.loopThread.start()
    
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

# Command : Type of command
# Data : value of command - freq / power

    @logger_decorator          
    def run(self):
        while True:
            # work example: ["Q", "VOLT", [1]]
            work = self.queue.get()
            self._status  = "running"
            # decompose the job
            work_type, command = work[:2]
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
                """
                if command == "VOLT":
                    data = work[2] 
                    result, toall = self.adc.readVoltage("DC"), False
                    
                elif command == "CURR":
                    data = work[2] 
                    result, toall = self.adc.readCurrent("DC"), False
                                        
                elif command == "RESI":
                    data = work[2] 
                    result, toall = self.adc.readResistance(), False
                    
                else:
                    self.toLog("critical", "Unknown command (\"%s\") has been detected." % command)
                """
                if command == "VOLT_ON":
                    # work[2] contains the initial channel number
                    channelNumber = work[2]
                    self.loopThread.switchChannel(channelNumber)
                    self.loopThread.startLoop()
                    # todo - notify to all clients that the ADC is turned on
                elif command == "VOLT_OFF":
                    self.loopThread.stopLoop()
                    # todo - notify to all clients that the ADC is turned off
                elif command == "SWITCH_CHANNEL":
                    # work[2] contains the modified channel number
                    channelNumber = work[2]
                    self.loopThread.switchChannel(channelNumber)
                    # todo - notify to all clients that the ADC channel is changed

            else:
                self.toLog("critical", "Unknown work type (\"%s\") has been detected." % work_type)
                
            msg = ['D', 'ADC', work_type , [result]]  #result value should have a list form
            
            if toall == True:
                self.informClients(msg, self._client_list)
            else:
                self.informClients(msg, client)
                
            self._status = "standby"

    @logger_decorator
    def informClients(self, msg, client):
        if type(client) != list:
            client = [client]
        
        print('To Client :', msg)
        #self.informing_msg = msg
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

class Loop(QThread):
    def __init__(self, controller, gpio):
        super().__init__()
        self.controller = controller
        self.gpio = gpio

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
        self._channelChanged = True
        self._channelNumber = channelNumber

    def run(self):
        while True:
            self._mutex.lock()
            if self._isRunning:
                if self._channelChanged:
                    # todo - call GPIO module to change the output voltage configuration
                    #        self.gpio._some_function(self._channelNumber)
                    time.sleep(1000)
                    self._channelChanged = False
                result = self.adc.readVoltage("DC")
                msg = ['D', 'ADC', 'VOLT', [self._channelNumber, result]]
                # todo - notify the msg to the clients (maybe all clients)
                #        self.controller.informClients(msg, [_some_client_list])
                time.sleep(1000)
            else:
                self._cond.wait(self._mutex)
            self._mutex.unlock()

class DummyClient():
    
    def __init__(self):
        pass
    
    def sendMessage(self, msg):
        print(msg)