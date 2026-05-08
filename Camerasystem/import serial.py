import serial
import time

ser = serial.Serial('/dev/tty.usbmodem4873641', 9600)

while True:
    ser.write(b"V?\n")
    voltage = ser.readline().decode().strip()

    ser.write(b"I?\n")
    current = ser.readline().decode().strip()

    print(voltage, current)
    time.sleep(1)