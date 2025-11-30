"""
Face Detection using RetinaFace ONNX model (InsightFace det_10g).

Provides face detection with bounding boxes, confidence scores,
and 5-point facial landmarks.

The det_10g.onnx model uses a Feature Pyramid Network with 3 scales:
- Stride 8:  80x80 grid = 12800 anchors (2 per cell)
- Stride 16: 40x40 grid = 3200 anchors (2 per cell)
- Stride 32: 20x20 grid = 800 anchors (2 per cell)

Outputs (9 total, 3 per scale):
- scores:    (N, 1) - detection confidence
- bboxes:    (N, 4) - bbox deltas (dx, dy, dw, dh)
- landmarks: (N, 10) - landmark deltas (5 points × 2 coords)
"""

from dataclasses import dataclass
from itertools import product
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
    Face detector using RetinaFace ONNX model (InsightFace det_10g).
    
    Handles image preprocessing, model inference, and postprocessing
    to extract face bounding boxes and landmarks from images.
    
    The model uses anchor-based detection with 3 FPN levels.
    """
    
    # Feature pyramid strides and anchor counts
    FPN_STRIDES = [8, 16, 32]
    NUM_ANCHORS = 2  # anchors per grid cell
    
    def __init__(self):
        """Initialize the face detector with the ONNX model."""
        self.session = ModelLoader.get_detector()
        self.input_name = self.session.get_inputs()[0].name
        self.input_size = (640, 640)
        
        # Pre-generate anchors for the input size
        self._anchors_cache = {}
    
    def _generate_anchors(self, height: int, width: int) -> np.ndarray:
        """
        Generate anchor centers for all FPN levels.
        
        Args:
            height: Input image height
            width: Input image width
            
        Returns:
            Array of anchor centers (N, 2) where N = sum of grid cells × num_anchors
        """
        cache_key = (height, width)
        if cache_key in self._anchors_cache:
            return self._anchors_cache[cache_key]
        
        anchors = []
        for stride in self.FPN_STRIDES:
            # Grid dimensions for this stride
            grid_h = height // stride
            grid_w = width // stride
            
            # Generate grid of anchor centers
            for y, x in product(range(grid_h), range(grid_w)):
                # Center coordinates in input space
                cx = (x + 0.5) * stride
                cy = (y + 0.5) * stride
                # Add anchor for each anchor per cell
                for _ in range(self.NUM_ANCHORS):
                    anchors.append([cx, cy])
        
        result = np.array(anchors, dtype=np.float32)
        self._anchors_cache[cache_key] = result
        return result
        
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
        
        print(f"[DETECTOR] Detected {len(faces)} faces after filtering (threshold={settings.DETECTION_THRESHOLD}, min_size={settings.MIN_FACE_SIZE})")
        
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
        
        The det_10g model outputs 9 arrays (3 per FPN level):
        - outputs[0,1,2]: scores for stride 8, 16, 32
        - outputs[3,4,5]: bbox deltas for stride 8, 16, 32  
        - outputs[6,7,8]: landmark deltas for stride 8, 16, 32
        
        Args:
            outputs: Raw model outputs (9 arrays)
            scale: Scale factor used in preprocessing
            pad: Padding applied during preprocessing (pad_w, pad_h)
            img_width: Original image width
            img_height: Original image height
            
        Returns:
            List of DetectedFace objects
        """
        # Concatenate outputs from all FPN levels
        # Order: [stride8_scores, stride16_scores, stride32_scores,
        #         stride8_bboxes, stride16_bboxes, stride32_bboxes,
        #         stride8_landmarks, stride16_landmarks, stride32_landmarks]
        
        scores_list = []
        bboxes_list = []
        landmarks_list = []
        anchor_strides = []  # Track which stride each detection comes from
        
        for idx, stride in enumerate(self.FPN_STRIDES):
            # Get outputs for this FPN level
            scores = outputs[idx]           # (N, 1)
            bboxes = outputs[idx + 3]       # (N, 4) - deltas
            landmarks = outputs[idx + 6]    # (N, 10) - deltas
            
            scores_list.append(scores)
            bboxes_list.append(bboxes)
            landmarks_list.append(landmarks)
            anchor_strides.extend([stride] * len(scores))
        
        # Stack all levels
        all_scores = np.vstack(scores_list).flatten()
        all_bboxes = np.vstack(bboxes_list)
        all_landmarks = np.vstack(landmarks_list)
        anchor_strides = np.array(anchor_strides)
        
        # Get anchors
        anchors = self._generate_anchors(self.input_size[1], self.input_size[0])
        
        # Find detections above threshold (before NMS)
        score_mask = all_scores > settings.DETECTION_THRESHOLD
        
        if not np.any(score_mask):
            return []
        
        # Filter to candidates
        scores = all_scores[score_mask]
        bbox_deltas = all_bboxes[score_mask]
        lmk_deltas = all_landmarks[score_mask]
        anchor_centers = anchors[score_mask]
        strides = anchor_strides[score_mask]
        
        # Decode bounding boxes
        # bbox format: (dx, dy, dw, dh) - distance from anchor center
        bboxes = self._decode_bboxes(anchor_centers, bbox_deltas, strides)
        
        # Decode landmarks
        landmarks = self._decode_landmarks(anchor_centers, lmk_deltas, strides)
        
        # Apply NMS
        keep = self._nms(bboxes, scores, iou_threshold=0.4)
        
        # Build face objects
        faces = []
        for i in keep:
            # Adjust for padding and scale
            x1, y1, x2, y2 = bboxes[i]
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
    
    def _decode_bboxes(
        self,
        anchors: np.ndarray,
        deltas: np.ndarray,
        strides: np.ndarray
    ) -> np.ndarray:
        """
        Decode bounding box deltas relative to anchors.
        
        The model predicts distances from anchor center to box edges,
        scaled by the stride.
        
        Args:
            anchors: Anchor centers (N, 2) as (cx, cy)
            deltas: Predicted deltas (N, 4) as (left, top, right, bottom)
            strides: Stride for each anchor (N,)
            
        Returns:
            Decoded boxes (N, 4) as (x1, y1, x2, y2)
        """
        strides = strides.reshape(-1, 1)
        
        # Deltas are distances from center, scaled by stride
        x1 = anchors[:, 0] - deltas[:, 0] * strides.flatten()
        y1 = anchors[:, 1] - deltas[:, 1] * strides.flatten()
        x2 = anchors[:, 0] + deltas[:, 2] * strides.flatten()
        y2 = anchors[:, 1] + deltas[:, 3] * strides.flatten()
        
        return np.stack([x1, y1, x2, y2], axis=1)
    
    def _decode_landmarks(
        self,
        anchors: np.ndarray,
        deltas: np.ndarray,
        strides: np.ndarray
    ) -> np.ndarray:
        """
        Decode landmark deltas relative to anchors.
        
        Args:
            anchors: Anchor centers (N, 2) as (cx, cy)
            deltas: Predicted deltas (N, 10) for 5 landmarks
            strides: Stride for each anchor (N,)
            
        Returns:
            Decoded landmarks (N, 10)
        """
        strides = strides.reshape(-1, 1)
        landmarks = deltas.copy()
        
        # Each pair of values is (dx, dy) from anchor center
        for i in range(5):
            landmarks[:, i * 2] = anchors[:, 0] + deltas[:, i * 2] * strides.flatten()
            landmarks[:, i * 2 + 1] = anchors[:, 1] + deltas[:, i * 2 + 1] * strides.flatten()
        
        return landmarks
    
    def _nms(
        self,
        bboxes: np.ndarray,
        scores: np.ndarray,
        iou_threshold: float = 0.4
    ) -> List[int]:
        """
        Non-maximum suppression to remove overlapping detections.
        
        Args:
            bboxes: Bounding boxes (N, 4) as (x1, y1, x2, y2)
            scores: Confidence scores (N,)
            iou_threshold: IoU threshold for suppression
            
        Returns:
            List of indices to keep
        """
        x1 = bboxes[:, 0]
        y1 = bboxes[:, 1]
        x2 = bboxes[:, 2]
        y2 = bboxes[:, 3]
        
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            
            if order.size == 1:
                break
            
            # Compute IoU with remaining boxes
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            
            w = np.maximum(0, xx2 - xx1)
            h = np.maximum(0, yy2 - yy1)
            inter = w * h
            
            iou = inter / (areas[i] + areas[order[1:]] - inter)
            
            # Keep boxes with IoU below threshold
            mask = iou <= iou_threshold
            order = order[1:][mask]
        
        return keep
    
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
