# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.

import sys
sys.path.append('../')
import time
import threading
from CQRobot_ADS1115 import ADS1115
from azure.iot.device import IoTHubDeviceClient, Message, MethodResponse
ADS1115_REG_CONFIG_PGA_6_144V        = 0x00 # 6.144V range = Gain 2/3
ADS1115_REG_CONFIG_PGA_4_096V        = 0x02 # 4.096V range = Gain 1
ADS1115_REG_CONFIG_PGA_2_048V        = 0x04 # 2.048V range = Gain 2 (default)
ADS1115_REG_CONFIG_PGA_1_024V        = 0x06 # 1.024V range = Gain 4
ADS1115_REG_CONFIG_PGA_0_512V        = 0x08 # 0.512V range = Gain 8
ADS1115_REG_CONFIG_PGA_0_256V        = 0x0A # 0.256V range = Gain 16
ads1115 = ADS1115()

# The device connection string to authenticate the device with your IoT hub.
# Using the Azure CLI:
# az iot hub device-identity show-connection-string --hub-name {YourIoTHubName} --device-id MyNodeDevice --output table
CONNECTION_STRING = "HostName=VRIOTRasbHub.azure-devices.net;DeviceId=myPi001;SharedAccessKey=s6JIuphWH8U6fHj2EqkueY8LIkjWMsSP23mzgnSAIb0="
# Define the JSON message to send to IoT Hub.
MSG_TXT = '{{"Voltage": {voltage},"TDS Value": {tdsValue}}}'
INTERVAL = 1
tdsValue=0

def iothub_client_init():
    # Create an IoT Hub client
    client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
    return client

def device_method_listener(device_client):
    global INTERVAL
    while True:
        method_request = device_client.receive_method_request()
        print (
            "\nMethod callback called with:\nmethodName = {method_name}\npayload = {payload}".format(
                method_name=method_request.name,
                payload=method_request.payload
            )
        )
        if method_request.name == "SetTelemetryInterval":
            try:
                INTERVAL = int(method_request.payload)
            except ValueError:
                response_payload = {"Response": "Invalid parameter"}
                response_status = 400
            else:
                response_payload = {"Response": "Executed direct method {}".format(method_request.name)}
                response_status = 200
        else:
            response_payload = {"Response": "Direct method {} not defined".format(method_request.name)}
            response_status = 404

        method_response = MethodResponse(method_request.request_id, response_status, payload=response_payload)
        device_client.send_method_response(method_response)



def iothub_client_telemetry_sample_run():

    try:
        client = iothub_client_init()
        print ( "IoT Hub device sending periodic messages, press Ctrl-C to exit" )

        # Start a thread to listen 
        device_method_thread = threading.Thread(target=device_method_listener, args=(client,))
        device_method_thread.daemon = True
        device_method_thread.start()

        while True:
            #Set the IIC address
            ads1115.setAddr_ADS1115(0x48)
            #Sets the gain and input voltage range.
            ads1115.setGain(ADS1115_REG_CONFIG_PGA_6_144V)
            #Get the Digital Value of Analog of selected channel
            voltage = ads1115.readVoltage(1)
            time.sleep(0.2)
            print(" A1:%dmV "%(voltage['r']))
            #Convert voltage to tds value
            tdsValue = (133.42 * voltage['r'] * voltage['r'] * voltage['r'] - 255.86 * voltage['r'] * voltage['r'] + 857.39 * voltage['r']) * 0.5
            print(" TDS --Value:%dppm "%(tdsValue))
            # Build the message with simulated telemetry values.

            msg_txt_formatted = MSG_TXT.format(voltage=voltage, tdsValue=tdsValue)
            message = Message(msg_txt_formatted)

            # Add a custom application property to the message.
            # An IoT hub can filter on these properties without access to the message body.
            if tdsValue > 100:
              message.custom_properties["tdsAlert"] = "true"
            else:
              message.custom_properties["tdsAlert"] = "false"

            # Send the message.
            print( "Sending message: {}".format(message) )
            client.send_message(message)
            print( "Message sent" )
            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print ( "IoTHubClient stopped" )


if __name__ == '__main__':
    print ( "IoT Hub Quickstart #2 - Tds device" )
    print ( "Press Ctrl-C to exit" )
    iothub_client_telemetry_sample_run()
   
