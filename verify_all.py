import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))
os.environ["FIREBASE_SERVICE_ACCOUNT_PATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend", "serviceAccountKey.json"))

import httpx
import time
from backend.app.services.firestore_client import firestore_client

def run_tests():
    print("--- 1. Testing Settings Persistence ---")
    current_settings = firestore_client.get_settings()
    print("Current Settings:", current_settings)
    
    # Toggle email alerts
    new_alerts = not current_settings.get("email_alerts", False)
    current_settings["email_alerts"] = new_alerts
    updated_settings = firestore_client.update_settings(current_settings)
    
    print(f"Updated Settings email_alerts to: {updated_settings.get('email_alerts')}")
    if updated_settings.get("email_alerts") == new_alerts:
        print("PASS: Settings persistence verified in Firestore.")
    else:
        print("FAIL: Settings did not persist.")

    print("\n--- 2. Testing Notification History & Missing Credentials ---")
    from backend.app.services.notification_service import trigger_incident_notification
    incident_id = "TEST-NOTIF-" + str(int(time.time()))
    
    # Create dummy incident to test history
    db = firestore_client.db
    db.collection("incidents").document(incident_id).set({
        "status": "OPEN",
        "category": "Test Notification",
        "priority_score": 90,
        "activity_history": [],
        "last_updated": int(time.time() * 1000)
    })
    
    # Development mode (Simulates email/sms)
    os.environ["ENVIRONMENT"] = "development"
    os.environ["SMTP_HOST"] = "" # Force missing
    os.environ["TWILIO_ACCOUNT_SID"] = ""
    trigger_incident_notification(incident_id, "Test Notification", 90, 10.0, 20.0)
    
    doc = db.collection("incidents").document(incident_id).get().to_dict()
    history = doc.get("activity_history", [])
    if len(history) > 0 and history[-1].get("event") in ["EMAIL_NOTIFICATION", "SMS_NOTIFICATION"]:
        print(f"PASS: Notification history recorded successfully. Events: {len(history)}")
        for h in history:
            print(" -", h["event"], h["notes"])
    else:
        print("FAIL: Notification history not recorded.", history)
        
    print("\n--- 3. Testing Production Failure ---")
    os.environ["ENVIRONMENT"] = "production"
    try:
        trigger_incident_notification(incident_id, "Test Notification", 90, 10.0, 20.0)
        print("FAIL: Production did not raise exception on missing credentials!")
    except Exception as e:
        print(f"PASS: Exception raised as expected: {e}")

    print("\n--- 4. Testing Incident Lifecycle (Backend) ---")
    lifecycle_id = "TEST-LIFECYCLE-" + str(int(time.time()))
    db.collection("incidents").document(lifecycle_id).set({
        "status": "CREATED",
        "activity_history": []
    })
    
    res = httpx.post(f"http://localhost:8000/api/dispatch/{lifecycle_id}/action", json={"action": "ASSIGNED", "team": "Water Works"})
    if res.status_code == 200:
        print(f"PASS: Assigned team.")
    else:
        print(f"FAIL: Assign team returned {res.status_code}")
        
    res = httpx.post(f"http://localhost:8000/api/dispatch/{lifecycle_id}/action", json={"action": "WORK_COMPLETED", "notes": "Done"})
    if res.status_code == 200:
        print(f"PASS: Work completed.")
    else:
        print(f"FAIL: Work completed returned {res.status_code}")
        
    doc = db.collection("incidents").document(lifecycle_id).get().to_dict()
    print("Final State:", doc.get("status"))
    print("Activity History length:", len(doc.get("activity_history", [])))
    if doc.get("status") == "WORK_COMPLETED" and len(doc.get("activity_history")) >= 2:
        print("PASS: Lifecycle updated Firestore correctly.")
    else:
        print("FAIL: Lifecycle failed.")

if __name__ == "__main__":
    run_tests()
