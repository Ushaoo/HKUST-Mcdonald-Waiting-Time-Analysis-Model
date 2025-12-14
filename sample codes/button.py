import Hobot.GPIO as GPIO
import time

BUTTON_PIN = 13

GPIO.setmode(GPIO.BOARD)

GPIO.setup(BUTTON_PIN, GPIO.IN)

print(f"start")

try:
    while True:
        button_state = GPIO.input(BUTTON_PIN)

        if button_state == GPIO.HIGH:
            print("Pressed! (Button Pressed)")
        else:
            print("No movement (Button Not Pressed)")

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\Broken")

finally:
    print("Clean...")
    GPIO.cleanup()
    print("DOne")