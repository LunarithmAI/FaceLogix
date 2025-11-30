"""
Face Alignment using similarity transform.

Aligns detected faces to a canonical pose using 5-point landmarks
for consistent embedding generation.
"""

import cv2
import numpy as np
from skimage import transform as trans

from app.core.config import settings


class FaceAligner:
    """
    Face aligner using similarity transform.
    
    Aligns faces to a canonical 112x112 format using 5-point landmarks
    and the standard ArcFace alignment reference points.
    
    Attributes:
        ARCFACE_DST: Reference landmark positions for aligned face
        output_size: Output image dimensions (width, height)
    """
    
    # Standard ArcFace reference landmarks for 112x112 output
    # Order: left_eye, right_eye, nose, left_mouth, right_mouth
    ARCFACE_DST = np.array([
        [38.2946, 51.6963],
        [73.5318, 51.5014],
        [56.0252, 71.7366],
        [41.5493, 92.3655],
        [70.7299, 92.2041]
    ], dtype=np.float32)
    
    def __init__(self):
        """Initialize the face aligner with output size from settings."""
        self.output_size = settings.INPUT_SIZE
    
    def align(
        self,
        image: np.ndarray,
        landmarks: np.ndarray
    ) -> np.ndarray:
        """
        Align face using 5-point landmarks.
        
        Estimates a similarity transform from source landmarks to
        reference ArcFace landmarks and applies it to crop and
        align the face.
        
        Args:
            image: BGR image as numpy array
            landmarks: 5x2 array of landmark coordinates
                [left_eye, right_eye, nose, left_mouth, right_mouth]
                
        Returns:
            Aligned face image of size (112, 112, 3)
        """
        # Estimate similarity transform
        tform = trans.SimilarityTransform()
        tform.estimate(landmarks, self.ARCFACE_DST)
        
        # Extract affine transformation matrix (2x3)
        M = tform.params[0:2, :]
        
        # Apply warp affine transform
        aligned = cv2.warpAffine(
            image,
            M,
            self.output_size,
            borderValue=0.0
        )
        
        return aligned
    
    def align_with_margin(
        self,
        image: np.ndarray,
        landmarks: np.ndarray,
        margin: float = 0.1
    ) -> np.ndarray:
        """
        Align face with additional margin around the face.
        
        Useful for liveness detection and quality assessment where
        more facial context is needed.
        
        Args:
            image: BGR image as numpy array
            landmarks: 5x2 array of landmark coordinates
            margin: Relative margin to add around the face (0.1 = 10%)
            
        Returns:
            Aligned face image with margin of size (112, 112, 3)
        """
        # Scale destination landmarks to add margin
        center = np.mean(self.ARCFACE_DST, axis=0)
        dst_scaled = (self.ARCFACE_DST - center) * (1 + margin) + center
        
        # Estimate similarity transform with scaled landmarks
        tform = trans.SimilarityTransform()
        tform.estimate(landmarks, dst_scaled)
        
        # Extract affine transformation matrix
        M = tform.params[0:2, :]
        
        # Apply warp affine transform
        aligned = cv2.warpAffine(
            image,
            M,
            self.output_size,
            borderValue=0.0
        )
        
        return aligned
    
    def estimate_pose(self, landmarks: np.ndarray) -> dict:
        """
        Estimate face pose (yaw, pitch, roll) from landmarks.
        
        Provides a rough estimate of face orientation based on
        landmark positions relative to expected frontal positions.
        
        Args:
            landmarks: 5x2 array of landmark coordinates
            
        Returns:
            Dictionary with 'yaw', 'pitch', 'roll' estimates in degrees
        """
        left_eye = landmarks[0]
        right_eye = landmarks[1]
        nose = landmarks[2]
        
        # Eye center and distance
        eye_center = (left_eye + right_eye) / 2
        eye_distance = np.linalg.norm(right_eye - left_eye)
        
        if eye_distance < 1:
            return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}
        
        # Yaw: horizontal rotation based on nose offset from eye center
        nose_offset_x = nose[0] - eye_center[0]
        yaw = np.arctan2(nose_offset_x, eye_distance / 2) * 180 / np.pi
        
        # Roll: rotation in image plane based on eye angle
        eye_delta = right_eye - left_eye
        roll = np.arctan2(eye_delta[1], eye_delta[0]) * 180 / np.pi
        
        # Pitch: vertical rotation based on nose-to-eye vertical distance
        expected_nose_y = eye_center[1] + eye_distance * 0.35
        nose_offset_y = nose[1] - expected_nose_y
        pitch = np.arctan2(nose_offset_y, eye_distance * 0.35) * 180 / np.pi
        
        return {
            "yaw": float(yaw),
            "pitch": float(pitch),
            "roll": float(roll)
        }
