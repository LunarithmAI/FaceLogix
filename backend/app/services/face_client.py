import base64
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.exceptions import FaceServiceError


class FaceServiceClient:
    """Client for communicating with the face recognition service."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        self.base_url = base_url or settings.FACE_SERVICE_URL
        self.timeout = timeout or settings.FACE_SERVICE_TIMEOUT

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request to the face service."""
        url = f"{self.base_url}{endpoint}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if files:
                    response = await client.request(
                        method=method,
                        url=url,
                        files=files
                    )
                else:
                    response = await client.request(
                        method=method,
                        url=url,
                        json=json_data
                    )

                if response.status_code >= 400:
                    error_detail = response.json().get("detail", "Unknown error")
                    raise FaceServiceError(
                        message=f"Face service error: {error_detail}",
                        code="FACE_SERVICE_REQUEST_ERROR",
                        details={"status_code": response.status_code}
                    )

                return response.json()

        except httpx.TimeoutException:
            raise FaceServiceError(
                message="Face service request timed out",
                code="FACE_SERVICE_TIMEOUT"
            )
        except httpx.ConnectError:
            raise FaceServiceError(
                message="Could not connect to face service",
                code="FACE_SERVICE_UNAVAILABLE"
            )
        except FaceServiceError:
            raise
        except Exception as e:
            raise FaceServiceError(
                message=f"Face service error: {str(e)}",
                code="FACE_SERVICE_ERROR"
            )

    async def generate_embedding(
        self,
        image_base64: str,
        detect_faces: bool = True
    ) -> Dict[str, Any]:
        """
        Generate face embedding from an image.
        
        Args:
            image_base64: Base64 encoded image data
            detect_faces: Whether to detect faces before embedding
        
        Returns:
            Dict containing:
                - embedding: List[float] - The face embedding vector
                - face_count: int - Number of faces detected
                - quality_score: float - Quality score of the face
                - bounding_box: Dict - Face bounding box coordinates
        
        Raises:
            FaceServiceError: If face service fails or no face detected
        """
        response = await self._make_request(
            method="POST",
            endpoint="/api/v1/embed",
            json_data={
                "image": image_base64,
                "detect_faces": detect_faces
            }
        )

        if not response.get("success", False):
            raise FaceServiceError(
                message=response.get("message", "Failed to generate embedding"),
                code="EMBEDDING_GENERATION_FAILED"
            )

        return response

    async def generate_embeddings_batch(
        self,
        images_base64: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Generate face embeddings for multiple images.
        
        Args:
            images_base64: List of base64 encoded images
        
        Returns:
            List of embedding results
        """
        response = await self._make_request(
            method="POST",
            endpoint="/api/v1/embed/batch",
            json_data={
                "images": images_base64
            }
        )

        return response.get("results", [])

    async def detect_liveness(
        self,
        image_base64: str,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Detect if the face in the image is from a live person.
        
        Args:
            image_base64: Base64 encoded image data
            threshold: Optional liveness threshold (0-1)
        
        Returns:
            Dict containing:
                - is_live: bool - Whether the face appears to be live
                - confidence: float - Confidence score (0-1)
                - details: Dict - Additional liveness detection details
        
        Raises:
            FaceServiceError: If liveness detection fails
        """
        json_data = {"image": image_base64}
        if threshold is not None:
            json_data["threshold"] = threshold

        response = await self._make_request(
            method="POST",
            endpoint="/api/v1/liveness",
            json_data=json_data
        )

        if not response.get("success", False):
            raise FaceServiceError(
                message=response.get("message", "Liveness detection failed"),
                code="LIVENESS_DETECTION_FAILED"
            )

        return response

    async def detect_faces(
        self,
        image_base64: str,
        return_landmarks: bool = False
    ) -> Dict[str, Any]:
        """
        Detect faces in an image.
        
        Args:
            image_base64: Base64 encoded image data
            return_landmarks: Whether to return facial landmarks
        
        Returns:
            Dict containing:
                - faces: List[Dict] - Detected faces with bounding boxes
                - count: int - Number of faces detected
        """
        response = await self._make_request(
            method="POST",
            endpoint="/api/v1/detect",
            json_data={
                "image": image_base64,
                "return_landmarks": return_landmarks
            }
        )

        return response

    async def check_quality(
        self,
        image_base64: str
    ) -> Dict[str, Any]:
        """
        Check the quality of a face image.
        
        Args:
            image_base64: Base64 encoded image data
        
        Returns:
            Dict containing:
                - quality_score: float - Overall quality score (0-1)
                - issues: List[str] - List of quality issues
                - metrics: Dict - Detailed quality metrics
        """
        response = await self._make_request(
            method="POST",
            endpoint="/api/v1/detect",  # Quality is returned from detect endpoint
            json_data={
                "image": image_base64,
                "return_quality": True
            }
        )

        return {
            "quality_score": response.get("quality_score", 0),
            "issues": response.get("quality_issues", []),
            "metrics": response.get("quality_metrics", {})
        }

    async def health_check(self) -> bool:
        """Check if the face service is healthy."""
        try:
            response = await self._make_request(
                method="GET",
                endpoint="/health"
            )
            return response.get("status") == "healthy"
        except FaceServiceError:
            return False
