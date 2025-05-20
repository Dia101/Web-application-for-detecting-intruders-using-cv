import torch
import numpy as np
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# Взаимодействие с моделью и обнаружение человека

model = torch.hub.load("ultralytics/yolov5", "yolov5s", pretrained=True)


def detect_person(frame: np.ndarray, conf_threshold: float = 0.5):

    results = model(frame)
    detections = results.pandas().xyxy[0]

    persons = []
    for _, row in detections.iterrows():
        if row["name"] == "person" and row["confidence"] >= conf_threshold:
            persons.append({
                "confidence": float(row["confidence"]),
                "bbox": {
                    "xmin": int(row["xmin"]),
                    "ymin": int(row["ymin"]),
                    "xmax": int(row["xmax"]),
                    "ymax": int(row["ymax"]),
                }
            })

    return persons
