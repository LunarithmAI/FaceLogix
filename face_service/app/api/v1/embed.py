"""
Face Embedding Generation Endpoint.

Provides API endpoint for generating face embeddings from images.
"""

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from PIL import Image
from PIL.ExifTags import TAGS
import io

from app.core.config import settings
from app.pipeline.aligner import FaceAligner
from app.pipeline.detector import FaceDetector
from app.pipeline.embedder import FaceEmbedder
from app.pipeline.quality import QualityAssessor
from app.schemas.face import BoundingBox, EmbeddingResponse

router = APIRouter()

# Initialize pipeline components
detector = FaceDetector()
aligner = FaceAligner()
embedder = FaceEmbedder()
quality_assessor = QualityAssessor()


def fix_image_orientation(image_bytes: bytes) -> np.ndarray:
    """
    Fix image orientation based on EXIF data.
    
    iOS and some cameras embed rotation info in EXIF rather than 
    actually rotating the pixels. This function applies the rotation.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        Correctly oriented BGR numpy array
    """
    try:
        # Open with PIL to handle EXIF
        pil_image = Image.open(io.BytesIO(image_bytes))
        
        # Get EXIF data
        exif = pil_image._getexif()
        
        if exif:
            # Find orientation tag
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == 'Orientation':
                    if value == 3:
                        pil_image = pil_image.rotate(180, expand=True)
                    elif value == 6:
                        pil_image = pil_image.rotate(270, expand=True)
                    elif value == 8:
                        pil_image = pil_image.rotate(90, expand=True)
                    break
        
        # Convert to RGB then BGR for OpenCV
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        img_array = np.array(pil_image)
        # RGB to BGR
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
    except Exception as e:
        print(f"[EMBED] EXIF handling failed: {e}, falling back to cv2.imdecode")
        # Fallback to standard OpenCV decode
        nparr = np.frombuffer(image_bytes, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)


@router.post("/embed", response_model=EmbeddingResponse)
async def generate_embedding(
    image: UploadFile = File(..., description="Face image (JPEG/PNG)")
) -> EmbeddingResponse:
    """
    Generate face embedding from an image.
    
    Detects the primary face in the image, assesses quality,
    aligns the face, and generates a 512-dimensional normalized
    embedding vector.
    
    Args:
        image: Uploaded image file containing a face
        
    Returns:
        EmbeddingResponse with embedding vector, quality score, and bbox
        
    Raises:
        HTTPException 400: If image is invalid, no face detected,
            or quality is too low
    """
    # Read and decode image with EXIF orientation fix
    contents = await image.read()
    img = fix_image_orientation(contents)
    
    if img is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image format. Please provide a valid JPEG or PNG image."
        )
    
    # Log image info for debugging
    print(f"[EMBED] Image size: {img.shape[1]}x{img.shape[0]}, bytes: {len(contents)}")
    
    # DEBUG: Save image to check what's being received
    debug_path = settings.MODELS_DIR / "debug_last_image.jpg"
    cv2.imwrite(str(debug_path), img)
    print(f"[EMBED] Debug image saved to: {debug_path}")
    
    # Detect faces
    faces = detector.detect(img)
    
    print(f"[EMBED] Faces detected: {len(faces)}")
    
    if not faces:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No face detected in image (size: {img.shape[1]}x{img.shape[0]}). Please provide an image with a visible face."
        )
    
    # Use the face with highest confidence
    face = faces[0]
    
    # Assess image quality
    quality = quality_assessor.assess(img, face)
    
    print(f"[EMBED] Quality score: {quality.overall:.2f} (min: {settings.MIN_QUALITY_SCORE})")
    
    if quality.overall < settings.MIN_QUALITY_SCORE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Face quality too low ({quality.overall:.2f}). "
                "Please provide a clearer image with good lighting and focus."
            )
        )
    
    # Align face for embedding generation
    aligned = aligner.align(img, face.landmarks)
    
    # Generate embedding
    embedding = embedder.generate(aligned)
    
    return EmbeddingResponse(
        embedding=embedding.tolist(),
        quality_score=quality.overall,
        bbox=BoundingBox(
            x1=face.bbox[0],
            y1=face.bbox[1],
            x2=face.bbox[2],
            y2=face.bbox[3],
            confidence=face.confidence
        )
    )
