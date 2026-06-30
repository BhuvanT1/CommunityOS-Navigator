from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from app.models.response import APIResponse
from app.services.image_processor import validate_and_preprocess_image
from app.services.gemini_service import analyze_image_with_gemini
from app.services.embedding_service import generate_embedding
from app.services.geo_service import reverse_geocode, compute_geohash
from app.services.clustering_service import calculate_merge_score
from app.repositories.incident_repository import find_candidates_by_geohash
from app.core.logging import logger
import time

router = APIRouter(prefix="/api/reports", tags=["Reports"])

@router.post("/analyze", response_model=APIResponse[dict])
async def analyze_report(
    image: UploadFile = File(...),
    lat: float = Form(...),
    lng: float = Form(...),
    location_source: str = Form("gps"),
    gps_verified: bool = Form(True),
    reporter_uid: str | None = Form(None),
    force: bool = Form(False)
):
    total_start = time.time()
    
    # 1. Validation & Preprocessing
    try:
        # Read the size before passing to validate_and_preprocess_image for logging
        image_content = await image.read()
        logger.info(f"[STAGE 2] Received image upload: {len(image_content)} bytes, filename: {image.filename}, type: {image.content_type}")
        # Reset file pointer for the processor
        await image.seek(0)
        
        processed_image_bytes = await validate_and_preprocess_image(image)
        logger.info(f"[STAGE 2] Processed image bytes: {len(processed_image_bytes)} bytes")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Image preprocessing failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
        
    # 2. AI Analysis
    try:
        ai_result, gemini_latency, ai_versions, raw_ai_output, ai_metrics = await analyze_image_with_gemini(processed_image_bytes)
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected AI Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal AI Service Error")
        
    # 3. Location Trust & Anti-Spoofing
    if abs(lat) < 0.01 and abs(lng) < 0.01:
        raise HTTPException(status_code=400, detail="Invalid location coordinates (0,0 detected).")
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        raise HTTPException(status_code=400, detail="Location coordinates out of bounds.")
        
    ai_confidence = ai_result.decision.confidence
    reporter_reputation = 100
    review_reasons = []

    if location_source == "manual_pin":
        location_confidence = 70
        review_reasons.append("Manual Location")
    elif location_source == "address_search":
        location_confidence = 60
        review_reasons.append("Address Estimated")
    else:
        location_confidence = 100
        if not gps_verified:
            review_reasons.append("Missing GPS Verification")

    if ai_confidence < 70:
        review_reasons.append("Low AI Confidence")

    # Overall Confidence Calculation
    overall_confidence = (ai_confidence * 0.60) + (location_confidence * 0.30) + (reporter_reputation * 0.10)

    # 4. Confidence Validation & Reverse Geocoding
    requires_confirmation = False
    if overall_confidence < 70:
        logger.warning(f"Low overall confidence ({overall_confidence:.1f}%). Flagging for manual review.")
        requires_confirmation = True
        
    street_name, locality = await reverse_geocode(lat, lng)
    ghash = compute_geohash(lat, lng)
    
    # 5. Semantic Embedding
    embedding = await generate_embedding(f"{ai_result.title}. {ai_result.summary}")
    
    # 5b. Upload Image to Storage
    from app.services.firestore_client import firestore_client
    image_url = firestore_client.upload_image(processed_image_bytes)
    
    # 6. AI Incident Fusion Engine
    report_data = {
        "lat": lat,
        "lng": lng,
        "location_source": location_source,
        "gps_verified": gps_verified,
        "location_confidence": location_confidence,
        "overall_confidence": overall_confidence,
        "reporter_reputation": reporter_reputation,
        "review_reasons": review_reasons,
        "category": ai_result.decision.category,
        "street_name": street_name,
        "timestamp": int(time.time() * 1000),
        "embedding": embedding,
        "ai_confidence": ai_result.decision.confidence,
        "analysis": ai_result.model_dump(),
        "image_url": image_url,
        "reporter_uid": reporter_uid
    }
    
    candidates = await find_candidates_by_geohash(ghash, ai_result.decision.category)
    best_merge = {"decision": "NEW_INCIDENT", "score": 0, "reasoning": ["No nearby candidates found in database."]}
    highest_score = 0
    
    for candidate in candidates:
        fusion_result = calculate_merge_score(report_data, candidate)
        if fusion_result["score"] > highest_score:
            highest_score = fusion_result["score"]
            best_merge = fusion_result
            
    # Force MANUAL_REVIEW if confidence is low
    if requires_confirmation and best_merge["decision"] != "MANUAL_REVIEW":
        best_merge["decision"] = "MANUAL_REVIEW"
        best_merge["reasoning"].extend(review_reasons)

    # Execute Persistence
    from app.repositories.incident_repository import create_incident, update_master_incident, add_to_manual_review
    
    # Duplicate Warning Check
    if reporter_uid and not force:
        # Check if user has a recent report of same category nearby
        recent_candidates = [c for c in candidates if c.get("reporter_uid") == reporter_uid and (int(time.time() * 1000) - c.get("timestamp", 0) < 3600000)]
        if recent_candidates:
            # We found a recent report from the same user for this category in the same geohash
            # Return 409 to prompt confirmation on frontend
            raise HTTPException(status_code=409, detail="Duplicate Warning: You recently reported a similar issue nearby. Proceed anyway?")

    persisted_incident_id = None
    
    if best_merge["decision"] == "NEW_INCIDENT":
        persisted_incident_id = await create_incident(report_data)
        if reporter_uid:
            from app.services.reputation_service import update_user_reputation, create_notification
            update_user_reputation(reporter_uid, "REPORT_SUBMITTED", {"category": ai_result.decision.category})
            create_notification(reporter_uid, persisted_incident_id, "REPORT_SUBMITTED", "Your report has been received and is being processed.")
    elif best_merge["decision"] == "AUTO_MERGE":
        persisted_incident_id = await update_master_incident(best_merge["master_incident_id"], report_data)
        if reporter_uid:
            from app.services.reputation_service import update_user_reputation, create_notification
            update_user_reputation(reporter_uid, "REPORT_DUPLICATE", {"category": ai_result.decision.category})
            create_notification(reporter_uid, persisted_incident_id, "REPORT_MERGED", "Your report was merged with an existing active incident.")
    elif best_merge["decision"] == "MANUAL_REVIEW":
        persisted_incident_id = await add_to_manual_review(report_data)
        if reporter_uid:
            from app.services.reputation_service import update_user_reputation, create_notification
            update_user_reputation(reporter_uid, "REPORT_SUBMITTED", {"category": ai_result.decision.category})
            create_notification(reporter_uid, persisted_incident_id, "MANUAL_REVIEW", "Your report requires manual verification.")
            
    # Trigger notifications for critical incidents
    if best_merge["decision"] in ["NEW_INCIDENT", "AUTO_MERGE"] and ai_result.decision.priority >= 80:
        from app.services.notification_service import trigger_incident_notification
        trigger_incident_notification(
            incident_id=persisted_incident_id or best_merge.get("master_incident_id", ""),
            category=ai_result.decision.category,
            priority_score=ai_result.decision.priority,
            lat=lat,
            lng=lng
        )

            
    total_latency = (time.time() - total_start) * 1000
    logger.info(f"Intake pipeline complete. Latency: {total_latency:.2f}ms. Decision: {best_merge['decision']}. ID: {persisted_incident_id}")
    
    return APIResponse.success_response(
        data={
            "incident_id": persisted_incident_id,
            "analysis": ai_result.model_dump(),
            "fusion": best_merge,
            "geo": {
                "street_name": street_name,
                "locality": locality,
                "geohash": ghash
            },
            "raw_ai_output": raw_ai_output,
            "ai_versioning": ai_versions,
            "metrics": {
                "gemini_latency_ms": round(gemini_latency, 2),
                "total_processing_ms": round(total_latency, 2),
                "input_tokens": ai_metrics["input_tokens"],
                "output_tokens": ai_metrics["output_tokens"],
                "estimated_cost_usd": ai_metrics["estimated_cost_usd"]
            },
            "requires_user_confirmation": requires_confirmation
        },
        message="Image analyzed and persisted successfully." if not requires_confirmation else "Analysis complete. Pending manual verification."
    )
