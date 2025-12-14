import cv2

# Try changing the index to 1 or 2 if 0 does not work
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Cannot open camera")
    exit()

ret, frame = cap.read()
if not ret or frame is None:
    print("Failed to capture image")
else:
    cv2.imwrite("test4.jpg", frame)
    print("Image saved as test.jpg")

cap.release()
