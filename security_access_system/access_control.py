import os
import io
import re
import cv2
import sys
import time
import pickle
import base64
import hashlib
import numpy as np
import RPi.GPIO as GPIO
import face_recognition
from picamera2 import Picamera2
from PIL import Image, ImageOps
from anti_spoofing.anti_spoofing import check_liveness
from py532lib.mifare import Mifare, MIFARE_SAFE_RETRIES

from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from admin_dashboard.models import AuthorizedUser, AccessLog


# ============================
# Config 
# ============================
sys.stdout.reconfigure(line_buffering=True)

DISPLAY_MODE = "console"
CV_SCALER = 3
FACE_TIMEOUT = 10
LOCK_PIN = 4
LED_RED_PIN = 5
LED_GREEN_PIN = 6
PWM_GREEN = None

# ============================
# LED & Lock
# ============================

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LOCK_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(LED_RED_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(LED_GREEN_PIN, GPIO.OUT, initial=GPIO.LOW)

    global PWM_GREEN
    PWM_GREEN = GPIO.PWM(LED_GREEN_PIN, 100)
    PWM_GREEN.start(0)

def led_off():
        PWM_GREEN.ChangeDutyCycle(0)
        GPIO.output(LED_RED_PIN, GPIO.LOW)

def led_on(color="yellow"):
    led_off()
    if color == "red":
        GPIO.output(LED_RED_PIN, GPIO.HIGH) 
    elif color == "green":
        PWM_GREEN.ChangeDutyCycle(100)
    else:
        PWM_GREEN.ChangeDutyCycle(33)
        GPIO.output(LED_RED_PIN, GPIO.HIGH)

def access_denied():
    try:
        led_on("red")
        time.sleep(3)
    finally:
        led_off()

def open_lock(duration=3):
    try:
        GPIO.output(LOCK_PIN, GPIO.HIGH)  
        led_on("green")
        time.sleep(duration)
    finally:
        GPIO.output(LOCK_PIN, GPIO.LOW)  
        led_off()

# ============================
# Card verification
# ============================
def setup_nfc():
    card = Mifare()
    card.SAMconfigure()
    card.set_max_retries(MIFARE_SAFE_RETRIES)
    return card

def scan_uid(card):
    uid = card.scan_field()
    if uid:
        return ''.join(f"{b:02X}" for b in uid)
    return None

def hash_uid(uid: str) -> str:
    return hashlib.sha256((settings.SECRET_KEY + uid).encode()).hexdigest()

def get_photo_base64(user):
    first_photo = user.photos.first()
    if not first_photo:
        return None

    photo_path = os.path.join(settings.MEDIA_ROOT, first_photo.photo.name)
    try:
        with Image.open(photo_path) as img:
            img = img.convert('RGB')
            img = ImageOps.exif_transpose(img)
            img.thumbnail((64, 64), Image.LANCZOS)
            
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=100)
            encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
        return f"data:image/jpeg;base64,{encoded}"
    except Exception:
        return None
    

def check_card_in_db(card_uid):
    try:
        hashed = hash_uid(card_uid)
        user = AuthorizedUser.objects.get(uid=hashed)
    except AuthorizedUser.DoesNotExist:
        AccessLog.objects.create(
            user=None,
            uid_hash=hash_uid(card_uid),
            result=AccessLog.Result.DENIED_UNKNOWN,
            device=settings.DEVICE_NAME,
        )
        print("[ACCESS DENIED] Card not in database!")
        return None

    if user.blocked:
        log = AccessLog.objects.create(
            user=user,
            uid_hash=user.uid,
            result=AccessLog.Result.DENIED_BLOCKED,
            device=settings.DEVICE_NAME,
        )
        print(f"[ACCESS DENIED] User {user.email} is blocked!")

        html_message = render_to_string("alert.html", {
            "title": "Access attempt – blocked user",
            "date_time": log.timestamp,
            "photo_url": get_photo_base64(user),
            "email": user.email,
            "uid": user.uid,
            "description": "BLOCKED",
            "device": settings.DEVICE_NAME,
            "dashboard_url": f"{settings.SITE_URL}",
            "log_url": f"{settings.SITE_URL}/logs",
        })

        send_mail(
            subject="Security alert – access attempt by a blocked user",
            message="A blocked user attempted to gain access.",  
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=settings.EMAIL_RECIPIENTS,
            html_message=html_message,
        )

        return None

    print(f"[DB] User found: {user.email}")
    return user


# ============================
# Face Encodings
# ============================
def get_pickle_mtime():
    try:
        return os.path.getmtime(settings.ENCODINGS_PATH)
    except FileNotFoundError:
        return None


def load_face_encodings():
    print("[INFO] Loading face encodings...")
    with open(settings.ENCODINGS_PATH, "rb") as f:
        data = pickle.loads(f.read())
    return data["encodings"], data["names"]



# ============================
# Face Verification
# ============================
def init_camera():
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"format": "RGB888", "size": (1920, 1080)}
    )
    picam2.configure(config)
    return picam2

def process_frame(frame, known_face_encodings, known_face_names):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb)
    face_encodings = face_recognition.face_encodings(rgb, face_locations, model="large")

    face_names = []
    for encoding in face_encodings:
        matches = face_recognition.compare_faces(known_face_encodings, encoding)
        name = "Unknown"
        distances = face_recognition.face_distance(known_face_encodings, encoding)
        best_match = np.argmin(distances)
        if matches[best_match]:
            name = known_face_names[best_match]
        face_names.append(name)

    return face_locations, face_names

def draw_results(frame, face_locations, face_names):
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        top *= CV_SCALER
        right *= CV_SCALER
        bottom *= CV_SCALER
        left *= CV_SCALER
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 3)
        cv2.putText(frame, name, (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    return frame

def run_face_verification(picam2, expected_user, known_face_encodings, known_face_names):
    print(f"[FACE] Detection started...")
    picam2.start()
    time.sleep(0.5)
    start_time = time.time()

    try:
        while time.time() - start_time < FACE_TIMEOUT:
            frame = picam2.capture_array()
            resized = cv2.resize(frame, (0, 0), fx=1 / CV_SCALER, fy=1 / CV_SCALER)
            face_locations, face_names = process_frame(resized, known_face_encodings, known_face_names)

            id_to_email = {str(u.id): u.email for u in AuthorizedUser.objects.all()}

            if face_names:
                display_names = [id_to_email.get(name, name) for name in face_names]
                print("[FACE] Detected:", display_names)

            if str(expected_user.id) in face_names:
                idx = face_names.index(str(expected_user.id))
                face_location = face_locations[idx]

                if not check_liveness(resized, face_location):
                    cv2.imwrite("last_frame.jpg", frame)
                    print("[ACCESS DENIED] Face spoofing detected!")
                    
                    log = AccessLog.objects.create(
                        user=expected_user,
                        uid_hash=expected_user.uid,
                        result=AccessLog.Result.DENIED_SPOOF,
                        device=settings.DEVICE_NAME,
                    )

                    html_message = render_to_string("alert.html", {
                        "title": "Attempt to deceive facial recognition",
                        "date_time": log.timestamp,
                        "email": expected_user.email,
                        "uid": expected_user.uid,
                        "description": "FACE SPOOFING",
                        "device": settings.DEVICE_NAME,
                        "dashboard_url": f"{settings.SITE_URL}",
                        "log_url": f"{settings.SITE_URL}/logs",
                    })

                    send_mail(
                        subject="Security alert – face spoofing attempt",
                        message="An attempt to deceive the facial recognition system was detected.",  
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=settings.EMAIL_RECIPIENTS,
                        html_message=html_message,
                    )
                    return False
                
                AccessLog.objects.create(
                    user=expected_user,
                    uid_hash=expected_user.uid,
                    result=AccessLog.Result.ACCESS_GRANTED,
                    device=settings.DEVICE_NAME,
                )
                print(f"[ACCESS GRANTED] User authorized!")
                cv2.imwrite("last_frame.jpg", draw_results(frame, face_locations, face_names))
                return True
            
            if DISPLAY_MODE == "frame":
                frame = draw_results(frame, face_locations, face_names)
                try:
                    cv2.imshow("Face Verification", frame)
                    cv2.waitKey(1)
                except Exception:
                    pass

            if DISPLAY_MODE == "console":
                time.sleep(0.2)

        AccessLog.objects.create(
            user=expected_user,
            uid_hash=expected_user.uid,
            result=AccessLog.Result.DENIED_FACE,
            device=settings.DEVICE_NAME,
        )
        print("[ACCESS DENIED] Face not recognized!")
        return False

    finally:
        picam2.stop()
        cv2.destroyAllWindows()



# ============================
# Main
# ============================
def main():
    if os.environ.get('RUN_MAIN') != 'true':
        return

    setup_gpio()
    card = setup_nfc()
    known_face_encodings, known_face_names = load_face_encodings()
    last_mtime = get_pickle_mtime()

    picam2 = init_camera()

    log = AccessLog.objects.create(
        user=None,
        uid_hash="abcde",
        result=AccessLog.Result.DENIED_BLOCKED,
        device=settings.DEVICE_NAME,
    )

    print("[NFC] Waiting for card...")

    while True:
        current_mtime = get_pickle_mtime()
        if current_mtime and current_mtime != last_mtime:
            print("[INFO] Encodings updated, reloading...")
            known_face_encodings, known_face_names = load_face_encodings()
            last_mtime = current_mtime

        card_uid = scan_uid(card)
        if not card_uid:
            time.sleep(0.5)
            continue

        print(f"[NFC] Card detected: {":".join(re.findall('..', card_uid))}")
        led_on()

        user = check_card_in_db(card_uid)
        if not user:
            access_denied()
            continue

        if run_face_verification(picam2, user, known_face_encodings, known_face_names):
            open_lock()
        else:
            access_denied()

        print("\n[NFC] Reset. Waiting for next card...")
        time.sleep(2)


if __name__ == "__main__":
    main()