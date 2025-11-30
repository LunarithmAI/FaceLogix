"""
Face Embedding Generation using ArcFace ONNX model.

Generates 512-dimensional L2-normalized face embeddings for
face recognition and comparison.
"""

from typing import List

import cv2
import numpy as np

from app.core.config import settings
from app.models.loader import ModelLoader


class FaceEmbedder:
    """
    Face embedder using ArcFace ONNX model.
    
    Generates normalized 512-dimensional embeddings from aligned
    face images for identity comparison.
    
    Attributes:
        session: ONNX inference session
        input_name: Name of the model input tensor
        input_size: Expected input image size (width, height)
    """
    
    def __init__(self):
        """Initialize the face embedder with the ONNX model."""
        self.session = ModelLoader.get_embedder()
        self.input_name = self.session.get_inputs()[0].name
        self.input_size = settings.INPUT_SIZE
    
    def generate(self, aligned_face: np.ndarray) -> np.ndarray:
        """
        Generate embedding for a single aligned face.
        
        Args:
            aligned_face: Aligned face image (112x112, BGR format)
            
        Returns:
            L2-normalized 512-dimensional embedding vector
        """
        # Preprocess the aligned face
        input_img = self._preprocess(aligned_face)
        
        # Run inference
        outputs = self.session.run(None, {self.input_name: input_img})
        embedding = outputs[0][0]
        
        # L2 normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    def generate_batch(self, aligned_faces: List[np.ndarray]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple aligned faces.
        
        More efficient than calling generate() multiple times as it
        batches the inference.
        
        Args:
            aligned_faces: List of aligned face images (112x112, BGR)
            
        Returns:
            List of L2-normalized 512-dimensional embedding vectors
        """
        if not aligned_faces:
            return []
        
        # Stack preprocessed images into a batch
        batch = np.stack([
            self._preprocess(face)[0] for face in aligned_faces
        ])
        
        # Run batch inference
        outputs = self.session.run(None, {self.input_name: batch})
        embeddings = outputs[0]
        
        # L2 normalize each embedding
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-10)  # Avoid division by zero
        embeddings = embeddings / norms
        
        return [emb for emb in embeddings]
    
    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess aligned face image for model input.
        
        Resizes if necessary, converts BGR to RGB, normalizes to
        [-1, 1] range, and rearranges to NCHW format.
        
        Args:
            image: BGR face image
            
        Returns:
            Preprocessed image tensor (1, 3, 112, 112)
        """
        # Ensure correct size
        if image.shape[:2] != self.input_size[::-1]:
            image = cv2.resize(image, self.input_size)
        
        # Convert BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Convert to float and normalize to [-1, 1]
        image = image.astype(np.float32)
        image = (image - 127.5) / 127.5
        
        # Transpose HWC -> CHW
        image = image.transpose(2, 0, 1)
        
        # Add batch dimension
        image = np.expand_dims(image, axis=0)
        
        return image
    
    @staticmethod
    def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        For L2-normalized embeddings, this is equivalent to the dot product.
        
        Args:
            emb1: First embedding vector (512-dim, normalized)
            emb2: Second embedding vector (512-dim, normalized)
            
        Returns:
            Cosine similarity in range [-1, 1], where 1 is identical
        """
        return float(np.dot(emb1, emb2))
    
    @staticmethod
    def euclidean_distance(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Calculate Euclidean distance between two embeddings.
        
        Args:
            emb1: First embedding vector (512-dim)
            emb2: Second embedding vector (512-dim)
            
        Returns:
            Euclidean distance (0 is identical)
        """
        return float(np.linalg.norm(emb1 - emb2))
