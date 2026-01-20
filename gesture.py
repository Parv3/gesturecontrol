import cv2
import mediapipe as mp
import time
import webbrowser
import subprocess
import os

# -----------------------------
# Configuration
# -----------------------------


GESTURE_ACTIONS = {
    "THUMB_UP": lambda: webbrowser.open("https://www.youtube.com"),
    "PEACE": lambda: subprocess.Popen(["spotify.exe"]),
    "FIST": lambda: webbrowser.open("https://chatgpt.com/"),
    "OK_SIGN": lambda: webbrowser.open("https://www.google.com"),
    "INDEX_UP": lambda: subprocess.Popen(["notepad.exe"]),
    "TWO_DOWN": lambda: webbrowser.open("https://mail.google.com/mail/u/0/#inbox")
}

# -----------------------------
# Setup
# -----------------------------
import mediapipe.python.solutions as mp_solutions

mp_hands = mp_solutions.hands
mp_draw = mp_solutions.drawing_utils
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)


# -----------------------------
# Detection Logic
# -----------------------------
def detect_gesture(hand_landmarks):
    tip_ids = [4, 8, 12, 16, 20]
    fingers = []

    # Thumb (Right Hand Logic)
    if hand_landmarks.landmark[tip_ids[0]].x < hand_landmarks.landmark[tip_ids[0] - 1].x:
        fingers.append(1)
    else:
        fingers.append(0)

    # 4 Fingers
    for id in range(1, 5):
        if hand_landmarks.landmark[tip_ids[id]].y < hand_landmarks.landmark[tip_ids[id] - 2].y:
            fingers.append(1)
        else:
            fingers.append(0)

    # Patterns
    if fingers == [1, 0, 0, 0, 0]:
        return "THUMB_UP"
    elif fingers == [0, 0, 0, 0, 0]:
        return "FIST"
    elif fingers == [0, 1, 1, 0, 0]:
        return "PEACE"
    elif fingers == [1, 1, 1, 0, 0]:
        return "OK_SIGN"  # Remember: this is actually "3" fingers
    elif fingers == [0, 1, 0, 0, 0]:
        return "INDEX_UP"
    elif fingers == [0, 0, 1, 1, 0]:
        return "TWO_DOWN"
    else:
        return "NONE"


# -----------------------------
# Main Loop (With Stability Fix)
# -----------------------------
cap = cv2.VideoCapture(0)

# Stability Variables
current_gesture = "NONE"  # The gesture strictly seen in this frame
confirmed_gesture = "NONE"  # The gesture we trust (held for X frames)
prev_confirmed_gesture = "NONE"
stability_counter = 1  # Counts how many frames the gesture has held steady
REQUIRED_FRAMES = 5     # Adjust this: Higher = Slower but more stable

# Action Cooldown
last_action_time = 0
action_cooldown = 1.5

while True:
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    current_gesture = "NONE"

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            current_gesture = detect_gesture(hand_landmarks)

    # --- STABILITY LOGIC STARTS HERE ---

    # 1. Check if the gesture is consistent with the last frame
    if current_gesture == confirmed_gesture:
        stability_counter += 1
    else:
        # If it flickered, reset the counter and track the new candidate
        confirmed_gesture = current_gesture
        stability_counter = 0

    # 2. Only trigger action if we have held it for REQUIRED_FRAMES
    if stability_counter >= REQUIRED_FRAMES:
        # Now we trust this gesture is real
        if confirmed_gesture != prev_confirmed_gesture:

            # Draw "LOCKED" indicator on screen
            cv2.circle(frame, (600, 30), 10, (0, 255, 0), -1)

            # Trigger Action (with time cooldown)
            now = time.time()
            if now - last_action_time > action_cooldown:
                action = GESTURE_ACTIONS.get(confirmed_gesture)
                if action:
                    print(f"--> ACTION LOCKED: {confirmed_gesture}")
                    action()
                    last_action_time = now

            prev_confirmed_gesture = confirmed_gesture

    # --- UI Display ---
    # Show what the computer sees vs what is locked
    cv2.putText(frame, f"Seeing: {current_gesture}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
    cv2.putText(frame, f"Locked: {prev_confirmed_gesture}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # Visual stability bar
    bar_width = int((stability_counter / REQUIRED_FRAMES) * 100)
    cv2.rectangle(frame, (10, 80), (10 + bar_width, 90), (0, 255, 255), -1)

    cv2.imshow("Gesture Control", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()