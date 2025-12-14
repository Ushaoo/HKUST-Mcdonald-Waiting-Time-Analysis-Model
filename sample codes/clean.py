import Hobot.GPIO as GPIO

try:
    GPIO.setmode(GPIO.BOARD)
    GPIO.cleanup()
    print("GPIO is cleanned successfully.")
except Exception as e:
    print(f"Error Message: {e}")
    exit()