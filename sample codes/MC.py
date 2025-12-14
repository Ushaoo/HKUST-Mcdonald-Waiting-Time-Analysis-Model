import cv2
import numpy as np
from ultralytics import YOLO
from collections import deque
from datetime import datetime
import os

os.environ['QT_QPA_PLATFORM'] = 'offscreen'

class CrowdDensityMonitor:
    def __init__(self, model_name='yolov8n.pt', camera_id=0):
        """Initialize YOLO model and camera"""
        self.model = YOLO(model_name)
        self.cap = cv2.VideoCapture(camera_id)
        self.density_history = deque(maxlen=100)
        
    def detect_people(self, frame):
        """Detect people in frame using YOLO"""
        results = self.model(frame, classes=0)  # class 0 = person
        detections = results[0].boxes
        return detections
    
    def calculate_density(self, detections, frame_shape):
        """Calculate crowd density"""
        person_count = len(detections)
        frame_area = frame_shape[0] * frame_shape[1]
        density = person_count / (frame_area / 10000)  # persons per 10000 pixels
        self.density_history.append(person_count)
        return person_count, density
    
    def draw_info(self, frame, person_count, density):
        """Draw detection info on frame"""
        cv2.putText(frame, f'People Count: {person_count}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f'Density: {density:.2f}', (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        return frame
    
    def run(self):
        """Main loop for real-time detection"""
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            detections = self.detect_people(frame)
            person_count, density = self.calculate_density(detections, frame.shape)
            
            frame = self.draw_info(frame, person_count, density)
            
            # cv2.imshow('Crowd Density Monitor', frame)  # Disabled for headless mode
            print(f'People Count: {person_count}, Density: {density:.2f}')
            
            # Uncomment below for interactive mode with display
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break
        
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    monitor = CrowdDensityMonitor()
    monitor.run()