import cv2
import numpy as np
import string
import onnxruntime as ort
from ultralytics import YOLO

# Define the Standard PARSeq Character Set (94 characters)
# PARSeq outputs 95 classes: 94 printable characters + 1 [EOS] (End of Sequence) token.
# The [EOS] token is at index 0, followed by the printable characters.
PARSEQ_CHARSET = list(string.digits + string.ascii_lowercase + string.ascii_uppercase + string.punctuation)

def preprocess_plate_for_parseq(plate_img):
    """
    Resizes, normalizes, and transforms the cropped plate image 
    to match PARSeq's expected input tensor: [1, 3, 32, 128] of type FP32.
    """
    # Resize to exact expected dimensions (width=128, height=32)
    resized = cv2.resize(plate_img, (128, 32), interpolation=cv2.INTER_LINEAR)
    
    # Convert BGR (OpenCV default) to RGB
    img_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    
    # Convert to float32 and scale from [0, 255] to [0.0, 1.0]
    img_float = img_rgb.astype(np.float32) / 255.0
    
    # Apply standard ImageNet normalization (mean, std)
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    normalized = (img_float - mean) / std
    
    # Transpose from (H, W, C) to (C, H, W)
    transposed = np.transpose(normalized, (2, 0, 1))
    
    # Add batch dimension to create shape [1, 3, 32, 128]
    input_tensor = np.expand_dims(transposed, axis=0)
    
    return input_tensor

def decode_parseq_output(logits):
    """
    Applies greedy decoding (argmax) on the output tensor [1, 26, 95]
    to reconstruct the predicted alphanumeric string.
    """
    # Remove batch dimension -> shape becomes [26, 95]
    sequence_logits = logits[0]
    
    # Take the argmax along the class probability axis
    predicted_indices = np.argmax(sequence_logits, axis=-1)
    
    recognized_text = []
    for idx in predicted_indices:
        # Index 0 is usually the [EOS] token. Once encountered, decoding terminates.
        if idx == 0:
            break
        # Shift index by -1 to map to the 94-character list safely
        if 1 <= idx <= len(PARSEQ_CHARSET):
            recognized_text.append(PARSEQ_CHARSET[idx - 1])
            
    return "".join(recognized_text)

def main():
    # Initialize Models
    print("Loading YOLOv8 model...")
    yolo_model = YOLO("C:/Users/Acer/Documents/pymodels/yolo.pt")  
    
    print("Loading PARSeq ONNX session...")
    parseq_session = ort.InferenceSession("C:/Users/Acer/Documents/pymodels/model.onnx")  
    parseq_input_name = parseq_session.get_inputs()[0].name

    # Initialize OpenCV VideoCapture (0 for default webcam)
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open video feed.")
        return

    print("Pipeline ready. Press 'q' in the video window to exit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame or video ended.")
            break

        # Run YOLO inference on the current frame
        results = yolo_model(frame, verbose=False)
        
        # Parse detections
        for box in results[0].boxes:
            # Get class ID (cast to int)
            cls_id = int(box.cls[0].item())
            conf = box.conf[0].item()
            
            # Class 1 is 'plate'
            if cls_id == 1 and conf > 0.5:
                # Extract integer bounding box coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                
                # Ensure coordinates are strictly within frame boundaries
                h_frame, w_frame, _ = frame.shape
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w_frame, x2), min(h_frame, y2)
                
                # Avoid processing invalid or empty crops
                if x2 - x1 < 10 or y2 - y1 < 10:
                    continue

                # Crop the plate region from the original frame
                plate_crop = frame[y1:y2, x1:x2]
                
                # Preprocess the crop for PARSeq
                parseq_input = preprocess_plate_for_parseq(plate_crop)
                
                # Run PARSeq OCR inference
                parseq_outputs = parseq_session.run(None, {parseq_input_name: parseq_input})
                
                # Decode the output tensor
                plate_text = decode_parseq_output(parseq_outputs[0])
                
                # Visual Feedback Overlay
                # Draw green bounding box around the plate
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Overlay the recognized text and confidence score above the box
                display_text = f"{plate_text} ({conf:.2f})"
                cv2.putText(frame, display_text, (x1, max(y1 - 10, 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # Display the live processed feed
        cv2.imshow("ANPR Pipeline Prototype", frame)

        # Break the loop if the user hits the 'q' key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Clean up resources
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()