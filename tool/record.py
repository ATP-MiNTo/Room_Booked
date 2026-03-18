import cv2
import time
import os

CAM_INDEXES = [0, 1, 2, 3]

CAM_NAMES = {
    0: "Front_right",
    1: "Front_left",
    2: "Back_left",
    3: "Back_right",
}

record_seconds = 7200

fps = 20
frame_width = 1280
frame_height = 720

# get script directory (root/tool)
script_dir = os.path.dirname(os.path.abspath(__file__))

# go one level up -> root
root_dir = os.path.dirname(script_dir)

# output folder -> root/test_vid
save_dir = os.path.join(root_dir, "test_vid")
os.makedirs(save_dir, exist_ok=True)

caps = []
writers = []

fourcc = cv2.VideoWriter_fourcc(*'XVID')

# open cameras
for cam_index in CAM_INDEXES:
    cap = cv2.VideoCapture(cam_index)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

    if not cap.isOpened():
        print(f"Camera {cam_index} failed to open")
        continue

    cam_name = CAM_NAMES[cam_index]
    filename = os.path.join(save_dir, f"{cam_name}.avi")

    writer = cv2.VideoWriter(filename, fourcc, fps, (frame_width, frame_height))

    caps.append(cap)
    writers.append(writer)

print("Recording started...")

start_time = time.time()

while True:
    if time.time() - start_time > record_seconds:
        break

    for cap, writer in zip(caps, writers):
        ret, frame = cap.read()
        if ret:
            writer.write(frame)

print("Recording finished.")

for cap in caps:
    cap.release()

for writer in writers:
    writer.release()

cv2.destroyAllWindows()

print("Videos saved to:", save_dir)