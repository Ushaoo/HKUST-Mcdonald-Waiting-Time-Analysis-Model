import cv2
import time

cap = cv2.VideoCapture(0)
ret, frame = cap.read()
if ret:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)

    ts = int(time.time())
    cv2.imwrite(f"original_{ts}.jpg", frame)
    cv2.imwrite(f"edges_{ts}.jpg", edges)
    print("Original and edges images saved")
else:
    print("Failed to capture image")

cap.release()
