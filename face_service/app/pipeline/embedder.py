"""
Face Embedding Generation using ArcFace ONNX model.

Generates 512-dimensional L2-normalized face embeddings for
face recognition and comparison.
"""

from typing import cast

import cv2
import numpy as np
import onnxruntime as ort


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

    def __init__(self, session: ort.InferenceSession):
        self.session = session
        input_node = self.session.get_inputs()[0]
        self.input_name = input_node.name
        self.input_size = (cast(int, input_node.shape[3]), cast(int, input_node.shape[2]))

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

        outputs = self.session.run(None, {self.input_name: input_img})
        embedding = np.asarray(outputs[0]).reshape(-1)
        if embedding.size != 512 or not np.isfinite(embedding).all():
            raise RuntimeError("Embedding inference returned invalid output")
        norm = float(np.linalg.norm(embedding))
        if not np.isfinite(norm) or norm <= 0:
            raise RuntimeError("Embedding inference returned a zero vector")
        return embedding / norm

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
