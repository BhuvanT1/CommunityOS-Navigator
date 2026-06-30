import os
import smtplib
import time
from email.message import EmailMessage
from app.core.logging import logger
from app.services.firestore_client import firestore_client
from google.cloud import firestore

def record_notification_history(incident_id: str, channel: str, target: str, status: str, details: str):
    try:
        db = firestore_client.db
        incident_ref = db.collection("incidents").document(incident_id)
        
        event_obj = {
            "event": f"{channel.upper()}_NOTIFICATION",
            "timestamp": int(time.time() * 1000),
            "performed_by": "system",
            "notes": f"Status: {status} | Target: {target} | Details: {details}",
            "team": None,
            "metadata": {
                "channel": channel,
                "target": target,
                "status": status
            }
        }
        
        incident_ref.update({
            "activity_history": firestore.ArrayUnion([event_obj]),
            "last_updated": int(time.time() * 1000)
        })
        logger.info(f"Recorded {channel} notification history for {incident_id}")
    except Exception as e:
        logger.error(f"Failed to record notification history for {incident_id}: {e}")

def send_email_notification(to_email: str, subject: str, body: str, incident_id: str = None):
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = os.environ.get("SMTP_PORT", "587")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASSWORD")

    if not all([smtp_host, smtp_user, smtp_pass]):
        env = os.environ.get("ENVIRONMENT", "development")
        if env == "production":
            logger.error("SMTP credentials missing in production! Failing loudly.")
            if incident_id: record_notification_history(incident_id, "EMAIL", to_email, "FAILED", "SMTP credentials missing")
            raise Exception("SMTP credentials not fully configured. Email notifications cannot be sent in production.")
        
        logger.warning(f"SMTP credentials not fully configured. Simulating email to {to_email}")
        logger.info(f"[SIMULATED EMAIL]\nTo: {to_email}\nSubject: {subject}\nBody: {body}\n")
        if incident_id: record_notification_history(incident_id, "EMAIL", to_email, "SIMULATED", "Dev Mode Simulation")
        return

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = smtp_user
        msg['To'] = to_email

        server = smtplib.SMTP(smtp_host, int(smtp_port))
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        logger.info(f"Email notification sent to {to_email}")
        if incident_id: record_notification_history(incident_id, "EMAIL", to_email, "SUCCESS", "Email sent")
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")
        if incident_id: record_notification_history(incident_id, "EMAIL", to_email, "FAILED", str(e))

def trigger_incident_notification(incident_id: str, category: str, priority_score: float, lat: float, lng: float):
    # Retrieve settings to see if email alerts are enabled
    settings = firestore_client.get_settings()
    
    if settings.get("email_alerts", False):
        subject = f"URGENT: New Critical Incident Reported - {category} (Priority: {priority_score})"
        body = (
            f"A new critical incident has been reported and requires immediate attention.\n\n"
            f"Incident ID: {incident_id}\n"
            f"Category: {category}\n"
            f"Priority Score: {priority_score}/100\n"
            f"Location: {lat}, {lng}\n\n"
            f"Please log in to the CommunityOS Command Center to dispatch a crew or escalate the issue."
        )
        # Default destination email. In a real system, this would be fetched from settings/departments.
        dispatch_email = os.environ.get("DISPATCH_EMAIL", "dispatch@metropoliscity.gov")
        send_email_notification(dispatch_email, subject, body, incident_id)
        
    if settings.get("sms_alerts", False):
        import httpx
        
        twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")
        twilio_from = os.environ.get("TWILIO_FROM_NUMBER")
        dispatch_phone = os.environ.get("DISPATCH_PHONE", "+1234567890")
        
        if not all([twilio_sid, twilio_token, twilio_from]):
            env = os.environ.get("ENVIRONMENT", "development")
            if env == "production":
                logger.error("Twilio credentials missing in production! Failing loudly.")
                record_notification_history(incident_id, "SMS", dispatch_phone, "FAILED", "Twilio credentials missing")
                raise Exception("Twilio credentials not fully configured. SMS notifications cannot be sent in production.")
            
            logger.warning(f"Twilio credentials not configured. Simulating SMS to {dispatch_phone}")
            logger.info(f"[SIMULATED SMS]\nTo: {dispatch_phone}\nBody: URGENT: {category} reported at {lat}, {lng}. Priority: {priority_score}\n")
            record_notification_history(incident_id, "SMS", dispatch_phone, "SIMULATED", "Dev Mode Simulation")
        else:
            try:
                sms_body = f"URGENT: {category} reported at {lat}, {lng}. Priority: {priority_score}"
                url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
                auth = (twilio_sid, twilio_token)
                data = {
                    "From": twilio_from,
                    "To": dispatch_phone,
                    "Body": sms_body
                }
                import requests
                resp = requests.post(url, auth=auth, data=data, timeout=10)
                if resp.status_code in [200, 201]:
                    logger.info(f"SMS notification sent to {dispatch_phone}")
                    record_notification_history(incident_id, "SMS", dispatch_phone, "SUCCESS", "SMS sent")
                else:
                    logger.error(f"Failed to send SMS. Twilio responded with {resp.status_code}: {resp.text}")
                    record_notification_history(incident_id, "SMS", dispatch_phone, "FAILED", f"Status {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"Failed to send SMS notification: {e}")
                record_notification_history(incident_id, "SMS", dispatch_phone, "FAILED", str(e))
