import logging
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import uuid
import cv2
from challenge_1 import detect_object, extract_features, query_llm, enhance_image

app = FastAPI()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

UPLOAD_DIR = "storage/uploads"
PROCESSED_DIR = "storage/processed"
STATIC_DIR = "storage"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.post("/process")
async def process_image(request: Request, file: UploadFile = File(...)):
    try:
        logging.info("File upload received.")
        
        # Save uploaded file
        file_id = str(uuid.uuid4())
        upload_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
        with open(upload_path, "wb") as buffer:
            buffer.write(await file.read())
        logging.info(f"File saved at {upload_path}")

        # Load and process image
        image = cv2.imread(upload_path)
        if image is None:
            raise ValueError("Invalid image file")
        logging.info(f"Image loaded successfully. Shape: {image.shape}")

        # Detect product and get bbox
        bbox, cropped = detect_object(image)
        logging.info(f"Product detected with bounding box: {bbox}")

        # Extract image features
        features = extract_features(cropped)
        logging.info(f"Extracted features: {features}")

        # Get enhancement parameters from LLM
        recommendations = query_llm(features)
        logging.info(f"Received enhancement recommendations: {recommendations}")

        # Enhance image
        enhanced_image = enhance_image(image, bbox, recommendations)
        logging.info("Image enhancement complete.")

        # Save enhanced image
        output_path = os.path.join(PROCESSED_DIR, f"{file_id}_enhanced.jpg")
        cv2.imwrite(output_path, enhanced_image, [cv2.IMWRITE_JPEG_QUALITY, 95])
        logging.info(f"Enhanced image saved at {output_path}")

        # Return image URL
        base_url = str(request.base_url).rstrip("/")
        image_url = f"{base_url}/static/processed/{os.path.basename(output_path)}"
        return {"image_url": image_url}

    except Exception as e:
        logging.error(f"Error during processing: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})