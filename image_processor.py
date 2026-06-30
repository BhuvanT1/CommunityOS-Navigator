import io
import math
from PIL import Image, ImageStat
from fastapi import UploadFile, HTTPException
from app.core.logging import logger

MAX_FILE_SIZE_MB = 10
MIN_RESOLUTION = 200

async def validate_and_preprocess_image(file: UploadFile) -> bytes:
    if not file.content_type.startswith("image/"):
        logger.warning(f"Invalid file type uploaded: {file.content_type}")
        raise HTTPException(status_code=400, detail="Invalid file type. Must be an image.")
    
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_MB * 1024 * 1024:
        logger.warning(f"File too large: {len(contents)} bytes")
        raise HTTPException(status_code=400, detail=f"File too large. Max size is {MAX_FILE_SIZE_MB}MB.")
    
    try:
        image = Image.open(io.BytesIO(contents))
        image.verify()  # Verify it's actually an image
        
        # Re-open for resolution check because verify() closes the file pointer
        image = Image.open(io.BytesIO(contents))
        width, height = image.size
        
        if width < MIN_RESOLUTION or height < MIN_RESOLUTION:
            logger.warning(f"Image resolution too low: {width}x{height}")
            raise HTTPException(status_code=400, detail=f"Resolution too low. Minimum is {MIN_RESOLUTION}x{MIN_RESOLUTION}.")
            
        # Variance/Entropy check to prevent solid-color uploads (e.g. covered camera lens)
        stat = ImageStat.Stat(image)
        # Sum of standard deviations of all bands
        stddev_sum = sum(stat.stddev)
        if stddev_sum < 10.0:  # Very low variance means it's basically a solid color
            logger.warning(f"Image rejected due to low variance (solid color): {stddev_sum}")
            raise HTTPException(status_code=400, detail="Image appears to be a solid color or completely obscured. Please ensure the camera lens is clear.")
        
        # EXIF/GPS extraction placeholder (To be expanded in future modules)
        exif = image.getexif()
        if exif:
            logger.info("EXIF data detected in image")
        
        return contents
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image validation failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Corrupted or invalid image file.")
