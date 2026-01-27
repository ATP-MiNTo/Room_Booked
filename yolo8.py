import cv2
from ultralytics import YOLO
import time
import os
import pandas as pd
import random

# โหลดโมเดล
model = YOLO("yolov8n.pt")

# เปิดกล้อง
cap = cv2.VideoCapture(1)

# ตั้งค่าขนาดกล้อง (Full HD - maximum quality)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

# โฟลเดอร์เก็บ ROI
roi_dir = "roi_images"
os.makedirs(roi_dir, exist_ok=True)

# เก็บข้อมูล tracked persons: {person_id: {"name": str, "last_save": timestamp, "folder": path}}
tracked_persons = {}
person_id_counter = 0
used_ids = set()  # เก็บ ID ที่ใช้แล้ว

logs = []

def distance(box1, box2):
    """คำนวณระยะห่างระหว่างจุดกลางของ 2 boxes"""
    cx1 = (box1[0] + box1[2]) / 2
    cy1 = (box1[1] + box1[3]) / 2
    cx2 = (box2[0] + box2[2]) / 2
    cy2 = (box2[1] + box2[3]) / 2
    return ((cx1 - cx2)**2 + (cy1 - cy2)**2)**0.5

def match_box_to_person(box, tracked_persons):
    """หา person ที่ใกล้ที่สุดกับ box นี้"""
    min_dist = 100  # threshold
    matched_id = None
    
    for pid, pdata in tracked_persons.items():
        if "last_box" in pdata:
            dist = distance(box, pdata["last_box"])
            if dist < min_dist:
                min_dist = dist
                matched_id = pid
    
    return matched_id

print("=== Auto ID Assignment ===")
print("Each detected person gets a random 3-digit ID automatically")
print("ROIs saved every 10 seconds to roi_images/<ID>/")
print("Press 'q' to quit")
print("==========================\n")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, verbose=False)
    current_boxes = []
    person_count = 0

    for box in results[0].boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])

        # class 0 = person
        if cls == 0 and conf > 0.4:
            person_count += 1
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            current_box = (x1, y1, x2, y2)
            
            # Match กับ tracked person
            matched_id = match_box_to_person(current_box, tracked_persons)
            
            if matched_id is not None:
                # อัพเดท box position
                tracked_persons[matched_id]["last_box"] = current_box
                person_name = tracked_persons[matched_id].get("name", f"Person {matched_id}")
                
                # เช็คว่าถึงเวลาบันทึก ROI หรือยัง (ทุก 10 วินาที)
                current_time = time.time()
                last_save = tracked_persons[matched_id].get("last_save", 0)
                
                if person_name != f"Person {matched_id}" and current_time - last_save >= 10:
                    # บันทึก ROI
                    roi = frame[y1:y2, x1:x2]
                    if roi.size > 0:
                        person_folder = tracked_persons[matched_id]["folder"]
                        filename = f"ID{person_name}_{int(current_time)}.jpg"
                        filepath = os.path.join(person_folder, filename)
                        cv2.imwrite(filepath, roi)
                        
                        tracked_persons[matched_id]["last_save"] = current_time
                        
                        # Log
                        logs.append({
                            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "person_id": person_name,
                            "confidence": round(conf, 3),
                            "roi_file": filepath
                        })
                        print(f"Saved: ID {person_name} at {time.strftime('%H:%M:%S')}")
            else:
                # สร้าง person ใหม่พร้อม random ID
                matched_id = person_id_counter
                person_id_counter += 1
                
                # สุ่ม 3-digit ID ที่ยังไม่ซ้ำ
                while True:
                    random_id = f"{random.randint(0, 999):03d}"
                    if random_id not in used_ids:
                        used_ids.add(random_id)
                        break
                
                # สร้างโฟลเดอร์
                person_folder = os.path.join(roi_dir, random_id)
                os.makedirs(person_folder, exist_ok=True)
                
                tracked_persons[matched_id] = {
                    "name": random_id,
                    "last_box": current_box,
                    "last_save": 0,
                    "folder": person_folder
                }
                person_name = random_id
                print(f"New person detected! Assigned ID: {random_id}")
            
            # วาดกรอบ
            color = (0, 255, 0)
            label = f"ID:{person_name} conf:{conf:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # แสดงจำนวนคนรวม
    cv2.putText(frame, f"People: {person_count}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # ย่อขนาดหน้าต่าง (display only)
    display_frame = cv2.resize(frame, (1280, 720))
    cv2.imshow("YOLO Person Detection", display_frame)

    # Check if window was closed
    if cv2.getWindowProperty("YOLO Person Detection", cv2.WND_PROP_VISIBLE) < 1:
        break

    key = cv2.waitKey(1) & 0xFF
    
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# บันทึก log เป็น CSV
df = pd.DataFrame(logs)
df.to_csv("people_with_conf_and_roi.csv", index=False)

print("\n=== Session Summary ===")
print(f"Total unique persons detected: {len(tracked_persons)}")
print("Logs saved to people_with_conf_and_roi.csv")
print("=======================")
