"""
Face Detection using RetinaFace ONNX model.

Provides face detection with bounding boxes, confidence scores,
and 5-point facial landmarks.
"""

from dataclasses import dataclass
from typing import List, Tuple

import cv2
import numpy as np

from app.core.config import settings
from app.models.loader import ModelLoader


@dataclass
class DetectedFace:
    """
    Represents a detected face with bounding box and landmarks.
    
    Attributes:
        bbox: Bounding box as (x1, y1, x2, y2) coordinates
        confidence: Detection confidence score (0-1)
        landmarks: 5x2 array of facial landmarks
            [left_eye, right_eye, nose, left_mouth, right_mouth]
    """
    bbox: Tuple[int, int, int, int]
    confidence: float
    landmarks: np.ndarray


class FaceDetector:
    """
    Face detector using RetinaFace ONNX model.
    
    Handles image preprocessing, model inference, and postprocessing
    to extract face bounding boxes and landmarks from images.
    
    Attributes:
        session: ONNX inference session
        input_name: Name of the model input tensor
        input_size: Expected input image size (width, height)
    """
    
    def __init__(self):
        """Initialize the face detector with the ONNX model."""
        self.session = ModelLoader.get_detector()
        self.input_name = self.session.get_inputs()[0].name
        self.input_size = (640, 640)
        
    def detect(self, image: np.ndarray) -> List[DetectedFace]:
        """
        Detect faces in an image.
        
        Args:
            image: BGR image as numpy array (H, W, C)
            
        Returns:
            List of DetectedFace objects, sorted by confidence (highest first)
        """
        img_height, img_width = image.shape[:2]
        
        # Preprocess image
        input_img, scale, pad = self._preprocess(image)
        
        # Run inference
        outputs = self.session.run(None, {self.input_name: input_img})
        
        # Post-process outputs
        faces = self._postprocess(outputs, scale, pad, img_width, img_height)
        
        # Filter by size and confidence threshold
        faces = [
            f for f in faces
            if f.confidence >= settings.DETECTION_THRESHOLD
            and self._get_face_size(f.bbox) >= settings.MIN_FACE_SIZE
        ]
        
        # Sort by confidence and limit to max faces
        faces = sorted(faces, key=lambda x: x.confidence, reverse=True)
        return faces[:settings.MAX_FACES]
    
    def _preprocess(
        self, image: np.ndarray
    ) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """
        Preprocess image for model input.
        
        Resizes image maintaining aspect ratio and pads to input size.
        Normalizes pixel values to [-1, 1] range.
        
        Args:
            image: BGR image as numpy array
            
        Returns:
            Tuple of (preprocessed_image, scale_factor, padding)
        """
        img_height, img_width = image.shape[:2]
        
        # Calculate scale to fit in input size
        scale = min(
            self.input_size[0] / img_width,
            self.input_size[1] / img_height
        )
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        # Resize image
        resized = cv2.resize(image, (new_width, new_height))
        
        # Calculate padding
        pad_w = (self.input_size[0] - new_width) // 2
        pad_h = (self.input_size[1] - new_height) // 2
        
        # Create padded image
        padded = np.zeros(
            (self.input_size[1], self.input_size[0], 3),
            dtype=np.uint8
        )
        padded[pad_h:pad_h + new_height, pad_w:pad_w + new_width] = resized
        
        # Normalize to [-1, 1]
        input_img = padded.astype(np.float32)
        input_img = (input_img - 127.5) / 128.0
        
        # Transpose HWC -> CHW
        input_img = input_img.transpose(2, 0, 1)
        
        # Add batch dimension
        input_img = np.expand_dims(input_img, axis=0)
        
        return input_img, scale, (pad_w, pad_h)
    
    def _postprocess(
        self,
        outputs: List[np.ndarray],
        scale: float,
        pad: Tuple[int, int],
        img_width: int,
        img_height: int
    ) -> List[DetectedFace]:
        """
        Post-process model outputs to DetectedFace objects.
        
        Converts raw model outputs to bounding boxes and landmarks,
        adjusting for preprocessing transformations.
        
        Args:
            outputs: Raw model outputs
            scale: Scale factor used in preprocessing
            pad: Padding applied during preprocessing (pad_w, pad_h)
            img_width: Original image width
            img_height: Original image height
            
        Returns:
            List of DetectedFace objects
        """
        faces = []
        
        # RetinaFace output format varies by model version
        # Common format: [bboxes, scores, landmarks] or combined
        if len(outputs) >= 3:
            bboxes = outputs[0]
            scores = outputs[1].flatten() if outputs[1].ndim > 1 else outputs[1]
            landmarks = outputs[2]
        else:
            # Handle single output models (need to parse differently)
            # This is a fallback - actual parsing depends on model
            return faces
        
        for i in range(len(scores)):
            if scores[i] < settings.DETECTION_THRESHOLD:
                continue
            
            # Adjust bounding box for padding and scale
            x1, y1, x2, y2 = bboxes[i][:4]
            x1 = int((x1 - pad[0]) / scale)
            y1 = int((y1 - pad[1]) / scale)
            x2 = int((x2 - pad[0]) / scale)
            y2 = int((y2 - pad[1]) / scale)
            
            # Clamp to image bounds
            x1 = max(0, min(x1, img_width))
            y1 = max(0, min(y1, img_height))
            x2 = max(0, min(x2, img_width))
            y2 = max(0, min(y2, img_height))
            
            # Skip invalid boxes
            if x2 <= x1 or y2 <= y1:
                continue
            
            # Adjust landmarks
            lmk = landmarks[i].reshape(5, 2).copy()
            lmk[:, 0] = (lmk[:, 0] - pad[0]) / scale
            lmk[:, 1] = (lmk[:, 1] - pad[1]) / scale
            
            faces.append(DetectedFace(
                bbox=(x1, y1, x2, y2),
                confidence=float(scores[i]),
                landmarks=lmk
            ))
        
        return faces
    
    def _get_face_size(self, bbox: Tuple[int, int, int, int]) -> int:
        """
        Get the minimum dimension of a face bounding box.
        
        Args:
            bbox: Bounding box as (x1, y1, x2, y2)
            
        Returns:
            Minimum of width and height
        """
        x1, y1, x2, y2 = bbox
        return min(x2 - x1, y2 - y1)
