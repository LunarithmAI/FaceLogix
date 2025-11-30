"""
Liveness Detection using two-frame movement analysis.

Detects presentation attacks (photo/video) by analyzing
natural facial micro-movements between consecutive frames.
"""

from dataclasses import dataclass

import numpy as np

from app.core.config import settings
from app.pipeline.detector import FaceDetector


@dataclass
class LivenessResult:
    """
    Result of liveness detection check.
    
    Attributes:
        is_live: Whether the face is from a live person
        confidence: Confidence score in [0, 1]
        reason: Human-readable explanation of the result
    """
    is_live: bool
    confidence: float
    reason: str


class LivenessDetector:
    """
    Liveness detector using two-frame movement analysis.
    
    Analyzes micro-movements between two consecutive frames to
    distinguish between live faces and presentation attacks
    (photos, videos, masks).
    
    This is a basic implementation - production systems should
    use more sophisticated methods like texture analysis or
    dedicated liveness models.
    
    Attributes:
        detector: Face detector for locating faces in frames
        movement_threshold: Minimum expected movement for live face
    """
    
    def __init__(self):
        """Initialize the liveness detector with a face detector."""
        self.detector = FaceDetector()
        self.movement_threshold = settings.LIVENESS_MOVEMENT_THRESHOLD
    
    def check_liveness(
        self,
        frame1: np.ndarray,
        frame2: np.ndarray
    ) -> LivenessResult:
        """
        Check if the face is from a live person.
        
        Analyzes movement between two frames to detect natural
        micro-movements present in live subjects but absent in
        static presentation attacks.
        
        Args:
            frame1: First BGR frame
            frame2: Second BGR frame (captured ~500ms later)
            
        Returns:
            LivenessResult with is_live, confidence, and reason
        """
        # Detect faces in both frames
        faces1 = self.detector.detect(frame1)
        faces2 = self.detector.detect(frame2)
        
        # Validate face detection
        if not faces1:
            return LivenessResult(
                is_live=False,
                confidence=0.0,
                reason="No face detected in first frame"
            )
        
        if not faces2:
            return LivenessResult(
                is_live=False,
                confidence=0.0,
                reason="No face detected in second frame"
            )
        
        # Use primary face (highest confidence) from each frame
        face1 = faces1[0]
        face2 = faces2[0]
        
        # Calculate landmark movement
        movement = self._calculate_movement(
            face1.landmarks,
            face2.landmarks
        )
        
        # Analyze movement patterns
        # Too static: likely a photo
        if movement < 0.001:
            return LivenessResult(
                is_live=False,
                confidence=0.2,
                reason="No movement detected - possible photo attack"
            )
        
        # Too much movement: suspicious or unstable
        if movement > 0.15:
            return LivenessResult(
                is_live=False,
                confidence=0.3,
                reason="Excessive movement - please hold still"
            )
        
        # Check for eye region movement (potential blink)
        eye_movement = self._check_eye_movement(
            face1.landmarks,
            face2.landmarks
        )
        
        # Calculate overall liveness confidence
        confidence = self._calculate_confidence(movement, eye_movement)
        
        # Determine liveness
        is_live = confidence >= 0.7
        
        if is_live:
            reason = "Natural movement patterns detected"
        elif confidence >= 0.5:
            reason = "Insufficient movement variation - try again"
        else:
            reason = "Movement patterns inconsistent with live subject"
        
        return LivenessResult(
            is_live=is_live,
            confidence=confidence,
            reason=reason
        )
    
    def _calculate_movement(
        self,
        landmarks1: np.ndarray,
        landmarks2: np.ndarray
    ) -> float:
        """
        Calculate normalized movement between landmark sets.
        
        Normalizes movement by eye distance to make it
        scale-invariant.
        
        Args:
            landmarks1: First frame landmarks (5x2)
            landmarks2: Second frame landmarks (5x2)
            
        Returns:
            Normalized movement score
        """
        # Calculate per-point displacement
        displacement = np.linalg.norm(landmarks2 - landmarks1, axis=1)
        
        # Normalize by eye distance for scale invariance
        eye_distance = np.linalg.norm(landmarks1[0] - landmarks1[1])
        
        if eye_distance < 1:
            return 0.0
        
        normalized = displacement / eye_distance
        
        return float(np.mean(normalized))
    
    def _check_eye_movement(
        self,
        landmarks1: np.ndarray,
        landmarks2: np.ndarray
    ) -> float:
        """
        Check for eye region movement (potential blink).
        
        Analyzes vertical movement of eye landmarks which may
        indicate natural blinking behavior.
        
        Args:
            landmarks1: First frame landmarks (5x2)
            landmarks2: Second frame landmarks (5x2)
            
        Returns:
            Eye movement magnitude
        """
        # Compare vertical position of eye landmarks
        left_eye_diff = abs(landmarks2[0, 1] - landmarks1[0, 1])
        right_eye_diff = abs(landmarks2[1, 1] - landmarks1[1, 1])
        
        return float((left_eye_diff + right_eye_diff) / 2)
    
    def _calculate_confidence(
        self,
        movement: float,
        eye_movement: float
    ) -> float:
        """
        Calculate liveness confidence score.
        
        Combines movement score with eye movement bonus.
        Ideal movement range is 0.005-0.08 (natural micro-movements).
        
        Args:
            movement: Normalized landmark movement
            eye_movement: Eye region movement magnitude
            
        Returns:
            Confidence score in [0, 1]
        """
        # Score based on natural movement range (0.005 - 0.08)
        movement_score = 0.0
        if 0.005 <= movement <= 0.08:
            # Peak score at ~0.03 movement
            deviation = abs(movement - 0.03) / 0.05
            movement_score = max(0.0, 1.0 - deviation)
        elif movement > 0.08:
            # Reduced score for higher movement
            movement_score = max(0.0, 0.5 - (movement - 0.08) / 0.14)
        
        # Eye movement bonus (natural blinks/micro-movements)
        eye_score = min(eye_movement * 10, 0.3)
        
        return min(movement_score + eye_score, 1.0)
