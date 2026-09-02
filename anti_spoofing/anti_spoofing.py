import os
from .minifasnet import MiniFASNetDemo

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")

detector = MiniFASNetDemo(model_dir=MODEL_DIR)

def check_liveness(frame_bgr, face_location):
    top, right, bottom, left = face_location
    bbox = [left , top, right - left, bottom - top]

    try:
        result = detector.predict(frame_bgr, bbox)
        print(f"[LIVENESS] {result['label_text']} confidence={result['confidence']:.2f} "
              f"paper={result['scores']['paper']:.2f} "
              f"real={result['scores']['real']:.2f} "
              f"screen={result['scores']['screen']:.2f}")
        return result['is_real']
    except Exception as e:
        print(f"[LIVENESS ERROR] {e}")
        return False
    