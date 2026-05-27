import asyncio
import base64
import cv2
import json
import numpy as np
import string
import onnxruntime as ort
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from ultralytics import YOLO
import torch
import os


app = FastAPI(title="ANPR Backend API")

print(f"CUDA Available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"Device: {torch.cuda.get_device_name(0)}")


# Standard PARSeq Character Set
PARSEQ_CHARSET = list(string.digits + string.ascii_lowercase + string.ascii_uppercase + string.punctuation)

def preprocess_plate_for_parseq(plate_img):
    resized = cv2.resize(plate_img, (128, 32), interpolation=cv2.INTER_LINEAR)
    img_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    img_float = img_rgb.astype(np.float32) / 255.0
    
    # Apply standard ImageNet normalization
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    normalized = (img_float - mean) / std
    
    transposed = np.transpose(normalized, (2, 0, 1))
    return np.expand_dims(transposed, axis=0)

def decode_parseq_output(logits):
    sequence_logits = logits[0]
    predicted_indices = np.argmax(sequence_logits, axis=-1)
    
    recognized_text = []
    for idx in predicted_indices:
        if idx == 0:  # [EOS] token
            break
        if 1 <= idx <= len(PARSEQ_CHARSET):
            recognized_text.append(PARSEQ_CHARSET[idx - 1])
            
    return "".join(recognized_text)

# Load Models Globally on Startup
# Get dynamic paths relative to this script
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
yolo_path = os.path.join(base_dir, "models", "yolo.pt")
parseq_path = os.path.join(base_dir, "models", "model.onnx")

print("Loading YOLOv8 model...")
yolo_model = YOLO(yolo_path)

print("Loading PARSeq ONNX session...")
parseq_session = ort.InferenceSession(parseq_path, providers=["CPUExecutionProvider"])
parseq_input_name = parseq_session.get_inputs()[0].name


    

print("Opening camera...")
    
    # Initialize Camera
cap = cv2.VideoCapture(0)
    # Lower resolution slightly if WebSocket transmission lags over local network
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
0
print("Camera opened")


@app.websocket("/ws/stream")
async def video_stream_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint that streams live frames and detection data.
    """
    await websocket.accept()
    print("WebSocket connected")

    # For buffering plate detections across frames to confirm recognition
    plate_buffer_counts = {}
    last_confirmed_plate = None

    try:
        while True:
            # Offload blocking camera read to a separate thread to keep asyncio non-blocking
            ret, frame = await asyncio.to_thread(cap.read)
            if not ret:
                await asyncio.sleep(0.01)
                continue

            # Separate payloads for drawing vs. logging
            frame_detections = []
            new_confirmed_events = []
            
            # Keep track of plates currently visible to clear old buffers
            current_frame_plates = set()
            
            # Run YOLO detection
            results = await asyncio.to_thread(yolo_model, frame, verbose=False)

            for box in results[0].boxes:
                cls_id = int(box.cls[0].item())
                conf = box.conf[0].item()
                
                # Context mapping: {0: 'vehicle', 1: 'plate'}
                if cls_id == 1 and conf > 0.25:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    
                    # Boundary checks
                    h_frame, w_frame, _ = frame.shape
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w_frame, x2), min(h_frame, y2)
                    
                    if x2 - x1 < 10 or y2 - y1 < 10:
                        continue

                    # Crop and run OCR
                    plate_crop = frame[y1:y2, x1:x2]
                    parseq_input = preprocess_plate_for_parseq(plate_crop)
                    
                    # Run PARSeq in a thread-safe manner
                    parseq_outputs = await asyncio.to_thread(
                        parseq_session.run, None, {parseq_input_name: parseq_input}
                    )
                    plate_text = decode_parseq_output(parseq_outputs[0])
                    
                    # Mark this plate as seen in the current frame
                    current_frame_plates.add(plate_text)
                    
                    # 1. Always append to frame_detections for the live UI overlay
                    frame_detections.append({
                        "text": plate_text,
                        "confidence": float(f"{conf:.2f}"),
                        "bounding_box": [x1, y1, x2, y2]
                    })
                    
                    # 2. Add to 3-frame buffer count
                    plate_buffer_counts[plate_text] = plate_buffer_counts.get(plate_text, 0) + 1
                    
                    # 3. Check for 3-frame confirmation and deduplication
                    if plate_buffer_counts[plate_text] >= 3:
                        if plate_text != last_confirmed_plate:
                            last_confirmed_plate = plate_text
                            new_confirmed_events.append({
                                "text": plate_text,
                                "confidence": float(f"{conf:.2f}")
                            })
                        
                        # Cap the count to prevent number incrementing indefinitely
                        plate_buffer_counts[plate_text] = 3
                    
                    # Draw UI overlay directly onto the outgoing frame
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, f"{plate_text} ({conf:.2f})", (x1, max(y1 - 10, 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            # This resets the counter if a misread happens for only 1 or 2 frames
            keys_to_remove = [p for p in plate_buffer_counts if p not in current_frame_plates]
            for p in keys_to_remove:
                del plate_buffer_counts[p]

            # Encode frame as JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_base64 = base64.b64encode(buffer).decode('utf-8')

            # Construct the comprehensive JSON message with separated lists
            message = {
                "status": "success",
                "live_overlay": frame_detections,        # Use for live feed boxes
                "new_recognitions": new_confirmed_events, # Use for recording entries
                "image": f"data:image/jpeg;base64,{frame_base64}"
            }

            # Send payload to the Node.js client
            await websocket.send_text(json.dumps(message))
            
            # Yield control back to the event loop
            await asyncio.sleep(0.001)

    except WebSocketDisconnect:
        print("Client disconnected from WebSocket stream.")
    finally:
        cap.release()

if __name__ == "__main__":
    import uvicorn
    # Run server locally on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)