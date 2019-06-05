import serial
import serial.tools
import serial.tools.list_ports
import time

#DEFINE
MEGA_SN = "7573530303235191A0F0"
UNO_SN = "85735313832351908032"
MEGA = 'MEGA'

class arduino(object):

    def __init__(self,SN,model = MEGA):
        self.ModelType = model
        self.SN = SN
        self.port = None

    """
    Returns: The port the arduino is routed to
    """
    def arduino_get_port(self):
        print("Listing ports")
        port=None
        ports=serial.tools.list_ports.comports()
        for p in ports:
            print(p)
            if "Arduino" in p[1] or self.SN in p[2]:
                port=p[0]
                print("Arduino detected on port",port)
        return port

    def connect(self):
        while (self.port==None):
            self.port=self.arduino_get_port()
            if self.port==None:
                print("Arduino not found. Retrying...")
                time.sleep(5)
                #serial.Serial(serial_port).close()
        self.port = serial.Serial(self.port,9600,timeout=1)

    def sendCmd(self,s):
        out=''
        self.port.flush()
        self.port.flushInput()
        self.port.flushOutput()
        s=s+'\n'
        self.port.write(s.encode(encoding='utf-8'))
        while self.port.in_waiting>0:
            resp = self.port.read()

    def disconnect(self):
        self.port.close()