import Hobot.GPIO as GPIO
import time

LED_PIN = 31      
BUTTON_PIN = 13 

GPIO.setmode(GPIO.BOARD)

GPIO.setup(LED_PIN, GPIO.OUT)

GPIO.setup(BUTTON_PIN, GPIO.IN)

print("start")

try:
    while True:
        button_state = GPIO.input(BUTTON_PIN)

        if button_state == GPIO.HIGH:
            GPIO.output(LED_PIN, GPIO.HIGH)
            print("LED ON")
        else:
            GPIO.output(LED_PIN, GPIO.LOW)
            
        
        time.sleep(0.02)

except KeyboardInterrupt:
    print("broken")

finally:
    print("Clena...")
    GPIO.output(LED_PIN, GPIO.LOW) 
    GPIO.cleanup()
    print("End")