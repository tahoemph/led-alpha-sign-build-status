from datetime import datetime, timedelta
import json
import requests
import serial
import time

SYNC = chr(0) * 5
SOH = chr(1)
STX = chr(2)
ETX = chr(3)
EOT = chr(4)
CR = chr(0x0d)
ESC = chr(0x1b)

def _cksum_message(message):
    message_hex = ''.join(c.encode('hex') for c in message)
    checksum = sum([int(message_hex[i:i+2], 16) for i in range(0, len(message_hex), 2)])
    return checksum

def set_enable_ack(dev):
    msg = ''.join((STX, SOH, 'Z00', STX, 'Es1', EOT))
    dev.write(msg)

def set_message(dev, message, file_code='A'):
    msg_body = ''.join((STX, 'A', file_code, message, ETX))
    checksum = _cksum_message(msg_body)
    msg = ''.join((SYNC, SOH, 'Z00', msg_body, '%04X' % checksum, EOT))
    dev.write(msg)

def decode_color(resp):
    if resp.endswith('anime'):
        return "building"
    elif resp == "blue":
        return "built"
    else:
        return "failed"

services = json.load(open('../config.json'))
s = serial.Serial(port="/dev/ttyUSB0", baudrate=9600)
set_message(s, '', file_code='0')  # Turn off priority messages
# set size of file 'A' to 0x100
s.write(''.join((SYNC, SOH, 'Z00', STX, 'E$', 'AAU0100FF00', EOT)))
last_time = datetime.now()
while True:
    # loop over the services collecting status
    status = {}
    for service_name, service_url in services.iteritems():
        resp = requests.get(service_url)
        status[service_name] = decode_color(resp.json()['color'])
    # What we want to do is to display any that are failing if they exist,
    # building if they exist, or if nothing going on then just the date and
    # time.
    if 'failed' in status.values():
        message = CR.join(x + ': ' + 'failed'
            for x in status if status[x] == "failed")
        set_message(s, ESC + '0b' + message)
    elif 'building' in status.values():
        message = CR.join(x + ': ' + 'building'
            for x in status if status[x] == "building")
        set_message(s, ESC + '0b' + message)
    else:
        set_message(s, ESC + '0b' + datetime.now().strftime("%a %b %d %H:%M"))
    time.sleep(60)
