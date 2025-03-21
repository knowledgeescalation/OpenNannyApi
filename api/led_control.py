import RPi.GPIO as GPIO

# Set the GPIO mode to BCM (Broadcom) or BOARD (physical pin numbers)
GPIO.setmode(GPIO.BCM)

# Set up pin 6 as an output

GPIO.setup(6, GPIO.OUT)
GPIO.setup(26, GPIO.OUT)


def right_on():
    GPIO.output(6, GPIO.HIGH)

def right_off():
    GPIO.output(6, GPIO.LOW)

def left_on():
    GPIO.output(26, GPIO.HIGH)

def left_off():
    GPIO.output(26, GPIO.LOW)

left_off()
right_off()
