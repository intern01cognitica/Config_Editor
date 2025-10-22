

import cv2
import yaml
from datetime import datetime
import numpy as np
import os

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

cam_id = config['camera_pos']
cam_index = config['cam_id']

clicked_points = []
background_key = f'background_p{cam_index}'
zone_key = f'p{cam_index}_zone_coords'

if zone_key not in config:
    raise KeyError(f"Missing zone config section: '{zone_key}'")
zone_coords = config[zone_key]
# Determine camera series based on zone complexity
series_type = "S" if zone_coords.get("num_zones", 1) == 1 else "M"
# Determine series based on number of zones
if series_type == "M":
    if isinstance(cam_index, int):
        camera_label = {
            0: "Front Camera",
            1: "Left Camera",
            2: "Right Camera",
            3: "Back Camera"
        }.get(cam_index, f"Camera {cam_index}")
    else:
        camera_label = "M Series IP Camera"
else:
    if isinstance(cam_index, int):
        camera_label = {
            0: "Cam 1",
            1: "Cam 2",
            2: "Cam 3",
            3: "Cam 4",
            4: "Cam 5",
            5: "Cam 6"
        }.get(cam_index, f"S Cam {cam_index}")
    else:
        camera_label = "IP Camera"

window_name = f"{camera_label} "
# Ensure config is complete
if background_key not in config:
    raise KeyError(f"Missing config section: '{background_key}'")

bg_config = config[background_key]
rotate = bg_config.get('rotate', 0)
required_keys = ['window_place_x', 'window_place_y', 'window_size_x', 'window_size_y']
for key in required_keys:
    if key not in bg_config:
        raise KeyError(f"Missing '{key}' in config under {background_key}")

# Extract window parameters
place_x = bg_config['window_place_x']
place_y = bg_config['window_place_y']
size_x = bg_config['window_size_x']
size_y = bg_config['window_size_y']
flip = bg_config.get('flip', 0)
rotate = bg_config.get('rotate', 0)
resized_size = (size_x, size_y)



def draw_lane(image, coords):
    if coords['num_zones'] == 3:
        pts = np.array(coords['blue'], dtype=np.int32)
        cv2.polylines(image, [pts], isClosed=True, color=(255, 0, 0), thickness=coords['line_thickness'])

    if coords['num_zones'] >= 2:
        pts = np.array(coords['orange'], dtype=np.int32)
        cv2.polylines(image, [pts], isClosed=True, color=(44, 208, 250), thickness=coords['line_thickness'])

    if coords['num_zones'] >= 1:
        pts = np.array(coords['red'], dtype=np.int32)
        cv2.polylines(image, [pts], isClosed=True, color=(0, 0, 255), thickness=coords['line_thickness'])

    return image

def on_mouse(event, x, y, flags, param):
    rotated_size = param[0]   # (rotated_w, rotated_h)
    resized_size = param[1]   # (resized_w, resized_h)

    rotated_w, rotated_h = rotated_size
    resized_w, resized_h = resized_size

    if event == cv2.EVENT_LBUTTONDOWN:
        scale_x = rotated_w / resized_w
        scale_y = rotated_h / resized_h

        rx = int(x * scale_x)
        ry = int(y * scale_y)

        if flip == 1:
            rx = rotated_w - rx - 1

        # If left camera (rotate = 1)
        if rotate == 1:
            rx, ry = ry, rx
            rx = original_size[0] - rx - 1   # ✅ Flip x once more
        elif rotate == 2:  # Right camera (rotate = 2)
            rx, ry = ry, rotated_w - rx - 1
            

        print(f"{camera_label} Camera Clicked at (x={rx}, y={ry})")
        clicked_points.append([rx, ry])



try:
    cap = cv2.VideoCapture(cam_id)
    if not cap.isOpened():
        raise Exception(f"Could not open camera: {cam_id}")

    ret, original_frame = cap.read()
    if not ret or original_frame is None:
        raise Exception(f"Failed to read frame from camera: {cam_id}")

except Exception as e:
    import traceback
    print("Error:", repr(e))
    traceback.print_exc()
    exit(1)

original_size = (original_frame.shape[1], original_frame.shape[0])  # (width, height)
cv2.namedWindow(window_name, flags=cv2.WINDOW_GUI_NORMAL + cv2.WINDOW_AUTOSIZE)
# cv2.resizeWindow(window_name, size_x, size_y)
# import subprocess, time, platform
# if platform.system() == "Linux":
#     time.sleep(0.5)
#     subprocess.call(["wmctrl", "-r", window_name, "-b", "add,above"])



print(f"Running {camera_label} — click to get original resolution coordinates.\nPress ESC to close window.")

# Main loop
while True:
    ret, frame = cap.read()
    if not ret:
        print(f"Failed to read frame from camera {cam_index}")
        break
   
    if flip == 1:
        frame = cv2.flip(frame, 1)
    frame = draw_lane(frame, zone_coords)


    if rotate == 1:
        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif rotate == 2:
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    elif rotate == 3:
        frame = cv2.rotate(frame, cv2.ROTATE_180)


    frame_shape = (frame.shape[1], frame.shape[0]) 
    cv2.setMouseCallback(window_name, on_mouse, param=(frame_shape, resized_size))

    resized_frame = cv2.resize(frame, resized_size)
    cv2.imshow(window_name, resized_frame)
    cv2.moveWindow(window_name, place_x, place_y)


    key = cv2.waitKey(1)
    if key == 27 or key == 81 or key == 83: # ESC key
        if clicked_points:
            for pt in clicked_points:
                print(f"    - {pt}")
        else:
            print("    No points clicked.")
        break
    elif key == ord('s'):
        folder = "/home/cai_test_wi/maha/Co_Ord/Frames"  # your specific folder
        if not os.path.exists(folder):
            os.makedirs(folder)  # create folder if it doesn't exist

        filename = f"frame_{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.png"
        full_path = os.path.join(folder, filename)  # safely join folder + filename
        cv2.imwrite(full_path, resized_frame)

cap.release()
cv2.destroyWindow(window_name)
print("Camera window closed.")
