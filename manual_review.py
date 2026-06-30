from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.firestore_client import firestore_client
from firebase_admin import firestore
from app.services.notification_service import trigger_incident_notification
import time
from app.models.response import APIResponse

router = APIRouter(prefix="/api/manual-review", tags=["Manual Review"])

class ManualReviewActionRequest(BaseModel):
    action: str  # APPROVE, REJECT, MERGE, REQUEST_MORE_PHOTOS
    target_incident_id: Optional[str] = None
    reviewer_id: str = "human_reviewer"
    notes: Optional[str] = None

@router.post("/{incident_id}/action", response_model=APIResponse[dict])
async def execute_manual_review_action(incident_id: str, request: ManualReviewActionRequest):
    try:
        doc_ref = firestore_client.db.collection('incidents').document(incident_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Incident not found")
            
        incident = doc.to_dict()
        
        now = int(time.time() * 1000)
        updates = {"last_updated": now}
        
        history_entry = {
            "event": f"MANUAL_REVIEW_{request.action}",
            "timestamp": now,
            "performed_by": request.reviewer_id,
            "admin_uid": request.reviewer_id,
            "citizen_uid": incident.get("reporter_uid"),
            "incident_id": incident_id,
            "previous_status": incident.get("status", "NEW_INCIDENT"),
            "new_status": incident.get("status", "NEW_INCIDENT"), # Updated later
            "action": request.action,
            "reason": request.notes or f"Manual review action: {request.action}",
            "notes": request.notes or f"Manual review action: {request.action}",
            "team": None,
            "metadata": {}
        }
        
        history = incident.get("activity_history", [])
        history.append(history_entry)
        updates["activity_history"] = history
        
        if request.action == "APPROVE":
            updates["status"] = "OPEN"
            history_entry["new_status"] = "OPEN"
            history.append({
                "event": "APPROVED",
                "timestamp": now,
                "performed_by": request.reviewer_id,
                "admin_uid": request.reviewer_id,
                "citizen_uid": incident.get("reporter_uid"),
                "incident_id": incident_id,
                "previous_status": incident.get("status", "NEW_INCIDENT"),
                "new_status": "OPEN",
                "action": "APPROVE",
                "reason": "Incident approved for dispatch.",
                "notes": "Incident approved for dispatch.",
                "team": None,
                "metadata": {}
            })
            
            # Send critical notification if applicable
            analysis = incident.get("analysis", {})
            decision = analysis.get("decision", {})
            if decision.get("priority", 0) >= 80:
                trigger_incident_notification(
                    incident_id=incident_id,
                    category=decision.get("category", "General"),
                    priority_score=decision.get("priority", 50),
                    lat=incident.get("lat", 0),
                    lng=incident.get("lng", 0)
                )
            
            reporter_uid = incident.get("reporter_uid")
            if reporter_uid:
                from app.services.reputation_service import update_user_reputation, create_notification
                update_user_reputation(reporter_uid, "REPORT_VERIFIED", {"category": decision.get("category")})
                create_notification(reporter_uid, incident_id, "REPORT_APPROVED", "Your report has been verified and approved by the city.")
        elif request.action == "REJECT":
            updates["status"] = "REJECTED"
            history_entry["new_status"] = "REJECTED"
            updates["archived_time"] = now
            history.append({
                "event": "ARCHIVED",
                "timestamp": now,
                "performed_by": request.reviewer_id,
                "admin_uid": request.reviewer_id,
                "citizen_uid": incident.get("reporter_uid"),
                "incident_id": incident_id,
                "previous_status": "OPEN",
                "new_status": "REJECTED",
                "action": "ARCHIVE",
                "reason": "Incident rejected and archived.",
                "notes": "Incident rejected and archived.",
                "team": None,
                "metadata": {}
            })
            
            reporter_uid = incident.get("reporter_uid")
            if reporter_uid:
                from app.services.reputation_service import update_user_reputation, create_notification
                update_user_reputation(reporter_uid, "REPORT_REJECTED")
                create_notification(reporter_uid, incident_id, "REPORT_REJECTED", "Your report was reviewed and rejected.")
            
        elif request.action == "MERGE":
            if not request.target_incident_id:
                raise HTTPException(status_code=400, detail="target_incident_id is required for MERGE action")
            updates["status"] = "MERGED"
            history_entry["new_status"] = "MERGED"
            updates["merged_into"] = request.target_incident_id
            updates["archived_time"] = now
            history.append({
                "event": "ARCHIVED",
                "timestamp": now,
                "performed_by": request.reviewer_id,
                "admin_uid": request.reviewer_id,
                "citizen_uid": incident.get("reporter_uid"),
                "incident_id": incident_id,
                "previous_status": incident.get("status"),
                "new_status": "MERGED",
                "action": "ARCHIVE",
                "reason": f"Merged into {request.target_incident_id}",
                "notes": f"Merged into {request.target_incident_id}",
                "team": None,
                "metadata": {}
            })
            
            reporter_uid = incident.get("reporter_uid")
            if reporter_uid:
                from app.services.reputation_service import update_user_reputation, create_notification
                update_user_reputation(reporter_uid, "REPORT_DUPLICATE")
                create_notification(reporter_uid, incident_id, "REPORT_MERGED", "Your report has been merged with an existing incident.")
            
            # Also update target incident
            target_ref = firestore_client.db.collection('incidents').document(request.target_incident_id)
            if target_ref.get().exists:
                target_ref.set({
                    "activity_history": firestore.firestore.ArrayUnion([{
                        "event": "MERGED_IN",
                        "timestamp": now,
                        "performed_by": request.reviewer_id,
                        "admin_uid": request.reviewer_id,
                        "citizen_uid": None,
                        "incident_id": request.target_incident_id,
                        "previous_status": "ANY",
                        "new_status": "ANY",
                        "action": "MERGE_IN",
                        "reason": "Manual merge received.",
                        "notes": "Manual merge received.",
                        "team": None,
                        "metadata": {"source_incident_id": incident_id}
                    }]),
                    "merged_report_count": firestore.firestore.Increment(1),
                    "last_updated": now
                }, merge=True)
                
        elif request.action == "REQUEST_MORE_PHOTOS":
            updates["status"] = "PENDING_VERIFICATION"
            history_entry["new_status"] = "PENDING_VERIFICATION"
            updates["requires_more_photos"] = True
            
            reporter_uid = incident.get("reporter_uid")
            if reporter_uid:
                from app.services.reputation_service import create_notification
                create_notification(reporter_uid, incident_id, "REQUEST_MORE_PHOTOS", "More photos are requested for your report.")
            
        # Execute update
        doc_ref.set(updates, merge=True)
        
        return APIResponse.success_response(
            data={"incident_id": incident_id, "updates": updates},
            message=f"Manual review action '{request.action}' executed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
