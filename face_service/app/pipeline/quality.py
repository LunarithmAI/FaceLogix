"""
Face Image Quality Assessment.

Evaluates face image quality based on brightness, sharpness,
face size, and face angle to determine suitability for recognition.
"""

from dataclasses import dataclass
from typing import Tuple

import cv2
import numpy as np

from app.pipeline.detector import DetectedFace


@dataclass
class QualityScore:
    """
    Quality assessment scores for a face image.
    
    All scores are in range [0, 1] where 1 is best quality.
    
    Attributes:
        overall: Weighted average of all quality metrics
        brightness: Score for image brightness (not too dark/bright)
        sharpness: Score for image sharpness/focus
        face_size: Score for face size relative to image
        face_angle: Score for how frontal the face is
    """
    overall: float
    brightness: float
    sharpness: float
    face_size: float
    face_angle: float


class QualityAssessor:
    """
    Assesses quality of face images for enrollment and recognition.
    
    Evaluates multiple quality factors and provides component scores
    along with an overall quality score.
    """
    
    def assess(
        self,
        image: np.ndarray,
        face: DetectedFace
    ) -> QualityScore:
        """
        Assess the quality of a detected face.
        
        Args:
            image: BGR image containing the face
            face: DetectedFace with bounding box and landmarks
            
        Returns:
            QualityScore with component and overall scores
        """
        x1, y1, x2, y2 = face.bbox
        
        # Ensure valid crop region
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(image.shape[1], x2)
        y2 = min(image.shape[0], y2)
        
        face_crop = image[y1:y2, x1:x2]
        
        # Handle empty or invalid crops
        if face_crop.size == 0 or face_crop.shape[0] < 2 or face_crop.shape[1] < 2:
            return QualityScore(
                overall=0.0,
                brightness=0.0,
                sharpness=0.0,
                face_size=0.0,
                face_angle=0.0
            )
        
        # Assess individual quality factors
        brightness = self._assess_brightness(face_crop)
        sharpness = self._assess_sharpness(face_crop)
        face_size = self._assess_size(face.bbox, image.shape)
        face_angle = self._assess_angle(face.landmarks)
        
        # Calculate weighted overall score
        overall = (
            brightness * 0.20 +
            sharpness * 0.30 +
            face_size * 0.25 +
            face_angle * 0.25
        )
        
        return QualityScore(
            overall=overall,
            brightness=brightness,
            sharpness=sharpness,
            face_size=face_size,
            face_angle=face_angle
        )
    
    def _assess_brightness(self, face_crop: np.ndarray) -> float:
        """
        Assess if face brightness is in acceptable range.
        
        Ideal brightness is between 80-180 (on 0-255 scale).
        Too dark or too bright images score lower.
        
        Args:
            face_crop: BGR face crop
            
        Returns:
            Brightness score in [0, 1]
        """
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(np.mean(gray))
        
        # Ideal range: 80-180
        if 80 <= mean_brightness <= 180:
            return 1.0
        elif mean_brightness < 40 or mean_brightness > 220:
            return 0.2
        else:
            # Linear interpolation for edge cases
            if mean_brightness < 80:
                return 0.2 + 0.8 * (mean_brightness - 40) / 40
            else:
                return 0.2 + 0.8 * (220 - mean_brightness) / 40
    
    def _assess_sharpness(self, face_crop: np.ndarray) -> float:
        """
        Assess image sharpness using Laplacian variance.
        
        Higher Laplacian variance indicates sharper image with
        more defined edges.
        
        Args:
            face_crop: BGR face crop
            
        Returns:
            Sharpness score in [0, 1]
        """
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Score thresholds based on empirical testing
        if laplacian_var > 500:
            return 1.0
        elif laplacian_var > 100:
            return 0.5 + 0.5 * (laplacian_var - 100) / 400
        else:
            return max(0.0, laplacian_var / 200)
    
    def _assess_size(
        self,
        bbox: Tuple[int, int, int, int],
        image_shape: Tuple[int, ...]
    ) -> float:
        """
        Assess if face is large enough for reliable recognition.
        
        Larger faces provide more detail for embedding generation.
        Minimum recommended size is 50 pixels, ideal is 200+ pixels.
        
        Args:
            bbox: Face bounding box (x1, y1, x2, y2)
            image_shape: Original image shape
            
        Returns:
            Size score in [0, 1]
        """
        x1, y1, x2, y2 = bbox
        face_width = x2 - x1
        face_height = y2 - y1
        face_size = min(face_width, face_height)
        
        # Score based on face pixel size
        if face_size >= 200:
            return 1.0
        elif face_size >= 100:
            return 0.5 + 0.5 * (face_size - 100) / 100
        elif face_size >= 50:
            return 0.2 + 0.3 * (face_size - 50) / 50
        else:
            return max(0.0, face_size / 50 * 0.2)
    
    def _assess_angle(self, landmarks: np.ndarray) -> float:
        """
        Assess how frontal the face is based on landmarks.
        
        Frontal faces score higher as they provide better
        embeddings for recognition.
        
        Args:
            landmarks: 5x2 array of facial landmarks
            
        Returns:
            Angle score in [0, 1] where 1 is perfectly frontal
        """
        left_eye = landmarks[0]
        right_eye = landmarks[1]
        nose = landmarks[2]
        
        # Calculate eye center and distance
        eye_center = (left_eye + right_eye) / 2
        eye_distance = np.linalg.norm(right_eye - left_eye)
        
        if eye_distance < 1:
            return 0.0
        
        # Assess yaw (horizontal rotation)
        nose_offset_x = nose[0] - eye_center[0]
        yaw_ratio = abs(nose_offset_x) / (eye_distance / 2)
        yaw_score = max(0.0, 1.0 - yaw_ratio)
        
        # Assess pitch (vertical rotation)
        eye_y = (left_eye[1] + right_eye[1]) / 2
        nose_y_offset = nose[1] - eye_y
        expected_offset = eye_distance * 0.35
        pitch_ratio = abs(nose_y_offset - expected_offset) / max(expected_offset, 1)
        pitch_score = max(0.0, 1.0 - pitch_ratio)
        
        # Average of yaw and pitch scores
        return (yaw_score + pitch_score) / 2
