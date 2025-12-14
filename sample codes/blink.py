import Hobot.GPIO as GPIO
import time

LED_PIN = 31

GPIO.setmode(GPIO.BOARD)

GPIO.setup(LED_PIN, GPIO.OUT)

print(f"Start")

try:
    while True:
        print("LED ON")
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(1)

        print("LED OFF")
        GPIO.output(LED_PIN, GPIO.LOW)
        time.sleep(1)

except KeyboardInterrupt:
    print("Broken")

finally:
    print("Cleanning...")
    GPIO.cleanup()
    print("Done")