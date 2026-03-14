import cv2
import requests

API_URL = "http://localhost:8000/api/camera-frame"

cap = cv2.VideoCapture(0)

print("Starting LumenAI camera capture. Press 'q' to quit.")

while True:
    ret, frame = cap.read()

    if not ret:
        print("Camera read failed")
        break

    _, img_encoded = cv2.imencode(".jpg", frame)

    files = {"file": ("frame.jpg", img_encoded.tobytes(), "image/jpeg")}

    try:
        requests.post(API_URL, files=files, timeout=1)
    except Exception:
        pass

    cv2.imshow("LumenAI Camera Feed", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
