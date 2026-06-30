from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.firestore_client import firestore_client
from app.services.notification_service import trigger_incident_notification
import time
from app.models.response import APIResponse

router = APIRouter(prefix="/api/dispatch", tags=["Dispatch"])

class DispatchActionRequest(BaseModel):
    action: str
    dispatcher_id: str = "auto-dispatcher"
    notes: Optional[str] = None
    target_team: Optional[str] = None

@router.post("/{incident_id}/action", response_model=APIResponse[dict])
async def execute_dispatch_action(incident_id: str, request: DispatchActionRequest):
    try:
        doc_ref = firestore_client.db.collection('incidents').document(incident_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Incident not found")
            
        incident = doc.to_dict()
        
        now = int(time.time() * 1000)
        updates = {"last_updated": now}
        
        # New history entry
        history_entry = {
            "event": request.action,
            "timestamp": now,
            "performed_by": request.dispatcher_id,
            "admin_uid": request.dispatcher_id,
            "citizen_uid": incident.get("reporter_uid"),
            "incident_id": incident_id,
            "previous_status": incident.get("status", "OPEN"),
            "new_status": incident.get("status", "OPEN"), # Updated in actions
            "action": request.action,
            "reason": request.notes or f"Action: {request.action}",
            "notes": request.notes or f"Action: {request.action}",
            "team": request.target_team,
            "metadata": {}
        }
        
        # Current history
        history = incident.get("activity_history", [])
        history.append(history_entry)
        updates["activity_history"] = history
        
        # Change status based on action
        if request.action == "DISPATCH_TEAM":
            updates["status"] = "ASSIGNED"
            history_entry["new_status"] = "ASSIGNED"
            updates["assigned_team"] = request.target_team or "Rapid Response"
            updates["assigned_time"] = now
            updates["dispatcher"] = request.dispatcher_id
            
            # Send Notification
            # Get category and priority
            analysis = incident.get("analysis", {})
            decision = analysis.get("decision", {})
            trigger_incident_notification(
                incident_id=incident_id,
                category=decision.get("category", "General"),
                priority_score=decision.get("priority", 50),
                lat=incident.get("lat", 0),
                lng=incident.get("lng", 0)
            )
            
            reporter_uid = incident.get("reporter_uid")
            if reporter_uid:
                from app.services.reputation_service import create_notification
                create_notification(reporter_uid, incident_id, "TEAM_DISPATCHED", f"Team {request.target_team or 'Rapid Response'} has been dispatched.")
            
        elif request.action == "CREW_ACCEPTED":
            updates["status"] = "CREW_ACCEPTED"
            history_entry["new_status"] = "CREW_ACCEPTED"
            updates["crew_accept_time"] = now
            
        elif request.action == "ON_THE_WAY":
            updates["status"] = "ON_THE_WAY"
            history_entry["new_status"] = "ON_THE_WAY"
            updates["departure_time"] = now
            reporter_uid = incident.get("reporter_uid")
            if reporter_uid:
                from app.services.reputation_service import create_notification
                create_notification(reporter_uid, incident_id, "TEAM_EN_ROUTE", "The repair team is on the way to the incident location.")
            
        elif request.action == "ARRIVED":
            updates["status"] = "ARRIVED"
            history_entry["new_status"] = "ARRIVED"
            updates["arrival_time"] = now
            reporter_uid = incident.get("reporter_uid")
            if reporter_uid:
                from app.services.reputation_service import create_notification
                create_notification(reporter_uid, incident_id, "TEAM_ARRIVED", "The repair team has arrived at the incident location.")
            
        elif request.action == "WORK_STARTED":
            updates["status"] = "WORK_STARTED"
            history_entry["new_status"] = "WORK_STARTED"
            updates["started_time"] = now
            reporter_uid = incident.get("reporter_uid")
            if reporter_uid:
                from app.services.reputation_service import create_notification
                create_notification(reporter_uid, incident_id, "WORK_STARTED", "Repair work has officially started.")
            
        elif request.action == "WORK_COMPLETED":
            updates["status"] = "WORK_COMPLETED"
            history_entry["new_status"] = "WORK_COMPLETED"
            updates["completed_time"] = now
            reporter_uid = incident.get("reporter_uid")
            if reporter_uid:
                from app.services.reputation_service import create_notification
                create_notification(reporter_uid, incident_id, "WORK_COMPLETED", "Repair work has been completed and is awaiting verification.")
            
        elif request.action == "VERIFIED":
            updates["status"] = "VERIFIED"
            history_entry["new_status"] = "VERIFIED"
            updates["verified_time"] = now
            updates["verified_by"] = request.dispatcher_id
            if request.notes:
                updates["verification_notes"] = request.notes
            reporter_uid = incident.get("reporter_uid")
            if reporter_uid:
                from app.services.reputation_service import create_notification
                create_notification(reporter_uid, incident_id, "REPAIR_VERIFIED", "The completed repair work has been officially verified.")
                
        elif request.action == "MARK_RESOLVED":
            updates["status"] = "RESOLVED"
            history_entry["new_status"] = "RESOLVED"
            updates["resolved_time"] = now
            if request.notes:
                updates["resolution_notes"] = request.notes
                
            reporter_uid = incident.get("reporter_uid")
            if reporter_uid:
                resolution_time_hrs = 0
                if "timestamp" in incident: # Or created_at
                    # Let's assume created_at is timestamp in incident
                    created_at = incident.get("timestamp", now)
                    resolution_time_hrs = (now - created_at) / (1000 * 60 * 60)
                
                from app.services.reputation_service import update_user_reputation, create_notification
                update_user_reputation(reporter_uid, "REPORT_RESOLVED", {
                    "category": incident.get("category", ""),
                    "resolution_time_hrs": resolution_time_hrs
                })
                create_notification(reporter_uid, incident_id, "REPORT_RESOLVED", "Your report has been successfully resolved!")
            
        elif request.action == "ARCHIVE":
            updates["status"] = "ARCHIVED"
            history_entry["new_status"] = "ARCHIVED"
            updates["archived_time"] = now
            
        elif request.action == "ESCALATE":
            updates["escalated"] = True
            history_entry["new_status"] = "ESCALATED"
            updates["priority_bump"] = True
            
        # Execute update
        doc_ref.set(updates, merge=True)
        
        # Retrieve updated doc
        updated_doc = doc_ref.get().to_dict()
        
        return APIResponse.success_response(
            data={"incident_id": incident_id, "updates": updates},
            message=f"Dispatch action '{request.action}' executed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
