from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
import logging
import time
import json
import argparse
import sys
import serial, serial.tools.list_ports

import lightstripcfg as cfg

clientId = "LightStrip"

arduino = None

# See Ala.h on GitHub for reference
# https://github.com/bportaluri/ALA/blob/master/src/Ala.h


curr_brightness = 50
curr_color = "FFFFFF"
curr_animation = 102
curr_duration = 1000
curr_palette = 0


# Delta callback
def customShadowCallback_Delta(payload, responseStatus, token):
    global curr_brightness
    global curr_color
    global curr_animation
    global curr_duration
    global curr_palette


    print(responseStatus)
    payloadDict = json.loads(payload)
    print("++++ DELTA RECEIVED ++++++++++++++++++++++++++++++++++\n" + \
          json.dumps(payloadDict, indent=4) + "\n" + \
          "++++++++++++++++++++++++++++++++++++++++++++++++++++++\n")
    # retrieve the desired state

    new_brightness = None
    new_color = None
    new_animation = None
    new_duration = None
    new_palette = None
    print(payloadDict)
    if 'brightness' in payloadDict["state"]:
        new_brightness = int(payloadDict["state"]["brightness"])
    if 'color' in payloadDict["state"]:
        new_color = payloadDict["state"]["color"]
    if 'animation' in payloadDict["state"]:
        new_animation = int(payloadDict["state"]["animation"])
    if 'duration' in payloadDict["state"]:
        new_duration = int(payloadDict["state"]["duration"])
    if 'palette' in payloadDict["state"]:
        new_palette = int(payloadDict["state"]["palette"])


    if new_brightness != None:
        print(new_brightness)
        curr_brightness = new_brightness
        sendCmd("B=" + str(new_brightness))

    if new_color != None:
        print(new_color)
        curr_color = new_color
        sendCmd("C=" + new_color)

    if new_animation != None:
        print(new_animation)
        curr_animation = new_animation
        sendCmd("A=" + str(new_animation))

    if new_duration != None:
        print(new_duration)
        curr_duration = new_duration
        sendCmd("D=" + str(new_duration))

    if new_palette != None:
        print(new_palette)
        curr_palette = new_palette
        sendCmd("P=" + str(new_palette))


    #JSONPayload = get_reported_json("reported")
    JSONPayload = get_json(get_curr_status_dict(), None)

    
    # report the current state
    print("++++ Response ++++++++++++++++++++++++++++++++++++++++\n" + \
          JSONPayload + "\n" + \
          "++++++++++++++++++++++++++++++++++++++++++++++++++++++\n")

    deviceShadowHandler.shadowUpdate(JSONPayload, customShadowCallback_Update, 5)


# Update callback
def customShadowCallback_Update(payload, responseStatus, token):
    if responseStatus == "timeout":
        print("Update request " + token + " time out!")
    if responseStatus == "accepted":
        payloadDict = json.loads(payload)
        #print("Update request with token: " + token + " accepted!")
        print("++++ Update ++++++++++++++++++++++++++++++++++++++++++\n" + \
          json.dumps(payloadDict, indent=4) + "\n" + \
          "++++++++++++++++++++++++++++++++++++++++++++++++++++++\n")
    if responseStatus == "rejected":
        print("Update request " + token + " rejected!")


def sendCmd(s):
    arduino.flush();
    s = s+'\n'
    arduino.write(s.encode());
    time.sleep(.1);
    get_resp(arduino);
    #arduino.flush()
    
def get_resp(s):
    #time.sleep(.1);
    while (s.in_waiting > 0):
        print(s.readline().decode(), end="")

# try to detect the USB port where Arduino is connected
def arduino_get_port():
    print("Listing ports")
    port = None
    ports = serial.tools.list_ports.comports()
    for p in ports:
        print(p)
        if "Arduino" in p[1] or "85735313832351908032" in p[2] or "7573530303235191A0F0" in p[2]:
            port = p[0]
            print("Arduino detected on port", port)

    return port


def get_curr_status_dict():
    global curr_brightness
    global curr_color
    global curr_animation
    global curr_duration
    global curr_palette

    state_dict = {}
    state_dict['brightness'] = curr_brightness
    state_dict['color'] = curr_color
    state_dict['animation'] = curr_animation
    state_dict['duration'] = curr_duration
    state_dict['palette'] = curr_palette

    return state_dict
    
def get_json(reported_dict, delta_dict):

    json_obj = {}
    if reported_dict != None:
        json_obj['state'] = {"reported": reported_dict}
    if delta_dict != None:
        json_obj['state'].update({"delta": delta_dict})

    return json.dumps(json_obj, indent=4)

    

if __name__ == "__main__":

    port = None
    
    # use the USB port name if passed
    if len(sys.argv)>1:
        port = sys.argv[1]
        print("Arduino port: " + port)

    # otherwise tries to detect the port
    # this seems to work only on Windows if Arduino USB driver is installed
    while(port==None):
        port = arduino_get_port()
        if port==None:
            print("Arduino not found. Retrying...")
            time.sleep(5);

    #serial.Serial(serial_port).close();
    arduino = serial.Serial(port, 9600, timeout=1)
    time.sleep(.5);

    # Configure logging
    logger = logging.getLogger("AWSIoTPythonSDK.core")
    logger.setLevel(logging.DEBUG)
    streamHandler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)

    # Init AWSIoTMQTTShadowClient
    myAWSIoTMQTTShadowClient = None


    myAWSIoTMQTTShadowClient = AWSIoTMQTTShadowClient(clientId)
    myAWSIoTMQTTShadowClient.configureEndpoint(cfg.AWSIOT, 8883)
    myAWSIoTMQTTShadowClient.configureCredentials(cfg.ROOT_CA, cfg.PRIVATE_KEY, cfg.CERTIFICATE)

    myAWSIoTMQTTShadowClient.configureAutoReconnectBackoffTime(1, 32, 20)
    myAWSIoTMQTTShadowClient.configureConnectDisconnectTimeout(10)  # 10 sec
    myAWSIoTMQTTShadowClient.configureMQTTOperationTimeout(5)  # 5 sec


    myAWSIoTMQTTShadowClient.connect()

    # Create a deviceShadow with persistent subscription
    deviceShadowHandler = myAWSIoTMQTTShadowClient.createShadowHandlerWithName(cfg.DEVICE_NAME, True)

    # Listen on deltas
    deviceShadowHandler.shadowRegisterDeltaCallback(customShadowCallback_Delta)

    time.sleep(2)

    curr_status = get_json(get_curr_status_dict(), None)

    print(">>>> Update ThingShadow sending desired state")
    print("++++++++++++++++++++++++++++++++++++++++++++++++++++++\n" + \
          curr_status + "\n" + \
          "++++++++++++++++++++++++++++++++++++++++++++++++++++++\n")
    deviceShadowHandler.shadowUpdate(curr_status, customShadowCallback_Update, 5)

    # Loop forever
    while True:
        time.sleep(1)
