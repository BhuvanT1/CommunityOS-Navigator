import time
from app.services.firestore_client import firestore_client
from app.core.logging import logger
from google.cloud import firestore

BADGES = {
    "FIRST_REPORT": {"id": "FIRST_REPORT", "name": "First Report", "icon": "🏅"},
    "COMMUNITY_HELPER": {"id": "COMMUNITY_HELPER", "name": "Community Helper", "icon": "🤝"},
    "ROAD_GUARDIAN": {"id": "ROAD_GUARDIAN", "name": "Road Guardian", "icon": "🛣️"},
    "WATER_WATCHER": {"id": "WATER_WATCHER", "name": "Water Guardian", "icon": "💧"},
    "STREETLIGHT_CHAMPION": {"id": "STREETLIGHT_CHAMPION", "name": "Streetlight Guardian", "icon": "💡"},
    "VERIFIED_5": {"id": "VERIFIED_5", "name": "5 Reports", "icon": "🥉"},
    "VERIFIED_10": {"id": "VERIFIED_10", "name": "10 Reports", "icon": "⭐"},
    "VERIFIED_25": {"id": "VERIFIED_25", "name": "25 Reports", "icon": "🌟"},
    "VERIFIED_50": {"id": "VERIFIED_50", "name": "50 Reports", "icon": "💎"},
    "VERIFIED_100": {"id": "VERIFIED_100", "name": "100 Reports", "icon": "🏆"},
    "COMMUNITY_HERO": {"id": "COMMUNITY_HERO", "name": "Community Hero", "icon": "🦸"},
    "TRUSTED_CITIZEN": {"id": "TRUSTED_CITIZEN", "name": "Trusted Citizen", "icon": "🛡️"},
    "EMERGENCY_REPORTER": {"id": "EMERGENCY_REPORTER", "name": "Emergency Reporter", "icon": "🚨"},
    "TOP_CONTRIBUTOR": {"id": "TOP_CONTRIBUTOR", "name": "Top Contributor", "icon": "👑"},
}

def _initialize_user(transaction, user_ref, uid: str):
    """Initializes a new user document if one doesn't exist."""
    snapshot = user_ref.get(transaction=transaction)
    if not snapshot.exists:
        now = int(time.time() * 1000)
        data = {
            "uid": uid,
            "reputation_score": 100,
            "trust_score": 100,
            "contribution_score": 0,
            "reports_submitted": 0,
            "reports_verified": 0,
            "reports_resolved": 0,
            "duplicate_reports": 0,
            "rejected_reports": 0,
            "badges": [],
            "achievements": [],
            "joined_at": now,
            "last_active": now,
            "impact_metrics": {
                "average_resolution_time_hrs": 0,
                "areas_contributed": [],
                "community_percentile": 50,
                "total_issues_helped": 0,
                "daily_contributions": {}
            },
            "settings": {
                "email_notifications": True,
                "browser_notifications": True
            }
        }
        transaction.set(user_ref, data)
        return data
    return snapshot.to_dict()

def _check_and_award_badges(user_data: dict, category: str = None) -> list:
    current_badges = [b["id"] for b in user_data.get("badges", [])]
    new_badges = []
    
    reports_sub = user_data.get("reports_submitted", 0)
    reports_ver = user_data.get("reports_verified", 0)
    
    if reports_sub >= 1 and "FIRST_REPORT" not in current_badges:
        new_badges.append(BADGES["FIRST_REPORT"])
        
    if reports_sub >= 5 and "VERIFIED_5" not in current_badges:
        new_badges.append(BADGES["VERIFIED_5"])

    if reports_sub >= 10 and "VERIFIED_10" not in current_badges:
        new_badges.append(BADGES["VERIFIED_10"])

    if reports_sub >= 25 and "VERIFIED_25" not in current_badges:
        new_badges.append(BADGES["VERIFIED_25"])

    if reports_sub >= 50 and "VERIFIED_50" not in current_badges:
        new_badges.append(BADGES["VERIFIED_50"])
        
    if reports_sub >= 100 and "VERIFIED_100" not in current_badges:
        new_badges.append(BADGES["VERIFIED_100"])
        new_badges.append(BADGES["COMMUNITY_HERO"])
        
    if reports_sub >= 250 and "TOP_CONTRIBUTOR" not in current_badges:
        new_badges.append(BADGES["TOP_CONTRIBUTOR"])

    trust_score = user_data.get("trust_score", 100)
    if trust_score >= 150 and "TRUSTED_CITIZEN" not in current_badges:
        new_badges.append(BADGES["TRUSTED_CITIZEN"])
        
    if category:
        cat_lower = category.lower()
        if "pothole" in cat_lower and "ROAD_GUARDIAN" not in current_badges:
            new_badges.append(BADGES["ROAD_GUARDIAN"])
        elif "water" in cat_lower and "WATER_WATCHER" not in current_badges:
            new_badges.append(BADGES["WATER_WATCHER"])
        elif "light" in cat_lower and "STREETLIGHT_CHAMPION" not in current_badges:
            new_badges.append(BADGES["STREETLIGHT_CHAMPION"])
            
    if new_badges:
        if "badges" not in user_data:
            user_data["badges"] = []
        user_data["badges"].extend(new_badges)
        
    return new_badges

@firestore.transactional
def _update_reputation_transaction(transaction, user_ref, event_type: str, metadata: dict = None):
    metadata = metadata or {}
    user_data = _initialize_user(transaction, user_ref, user_ref.id)
    
    now = int(time.time() * 1000)
    
    rep_change = 0
    trust_change = 0
    contrib_change = 0
    
    if event_type == "REPORT_SUBMITTED":
        user_data["reports_submitted"] = user_data.get("reports_submitted", 0) + 1
        rep_change = 10
        contrib_change = 5
    elif event_type == "REPORT_VERIFIED":
        user_data["reports_verified"] = user_data.get("reports_verified", 0) + 1
        rep_change = 25
        trust_change = 5
        contrib_change = 15
    elif event_type == "REPORT_RESOLVED":
        user_data["reports_resolved"] = user_data.get("reports_resolved", 0) + 1
        rep_change = 20
        trust_change = 10
        contrib_change = 50
        
        # Update impact metrics
        impact = user_data.get("impact_metrics", {})
        total_helped = impact.get("total_issues_helped", 0) + 1
        impact["total_issues_helped"] = total_helped
        
        # Calculate moving average for resolution time
        res_time = metadata.get("resolution_time_hrs")
        if res_time is not None:
            current_avg = impact.get("average_resolution_time_hrs", 0)
            if total_helped == 1:
                impact["average_resolution_time_hrs"] = res_time
            else:
                impact["average_resolution_time_hrs"] = ((current_avg * (total_helped - 1)) + res_time) / total_helped
        
        user_data["impact_metrics"] = impact
        
    elif event_type == "CRITICAL_INCIDENT":
        rep_change = 30
        trust_change = 10
        if "EMERGENCY_REPORTER" not in [b.get("id") for b in user_data.get("badges", [])]:
            new_badges = _check_and_award_badges(user_data, metadata.get("category"))
            new_badges.append(BADGES["EMERGENCY_REPORTER"])
    elif event_type == "REPORT_REJECTED":
        user_data["rejected_reports"] = user_data.get("rejected_reports", 0) + 1
        rep_change = -15
        trust_change = -10
    elif event_type == "REPORT_DUPLICATE":
        user_data["duplicate_reports"] = user_data.get("duplicate_reports", 0) + 1
        rep_change = -5
        trust_change = -2
    elif event_type == "REPORT_SPAM":
        user_data["spam_reports"] = user_data.get("spam_reports", 0) + 1
        rep_change = -30
        trust_change = -20
        
    # Update Daily Contributions
    if rep_change > 0 or contrib_change > 0:
        import datetime
        today_str = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        impact = user_data.get("impact_metrics", {})
        daily = impact.get("daily_contributions", {})
        daily[today_str] = daily.get(today_str, 0) + 1
        impact["daily_contributions"] = daily
        
        # Mock Percentile based on trust score for now (simplified)
        trust = user_data.get("trust_score", 100) + trust_change
        if trust > 200:
            impact["community_percentile"] = 5  # Top 5%
        elif trust > 150:
            impact["community_percentile"] = 10
        elif trust > 120:
            impact["community_percentile"] = 25
        else:
            impact["community_percentile"] = 50
            
        user_data["impact_metrics"] = impact
        
    user_data["reputation_score"] = max(0, user_data.get("reputation_score", 100) + rep_change)
    user_data["trust_score"] = max(0, min(1000, user_data.get("trust_score", 100) + trust_change))
    user_data["contribution_score"] = user_data.get("contribution_score", 0) + contrib_change
    user_data["last_active"] = now
    
    new_badges = _check_and_award_badges(user_data, metadata.get("category"))
    
    transaction.update(user_ref, user_data)
    return new_badges

def update_user_reputation(uid: str, event_type: str, metadata: dict = None):
    """
    Updates a citizen's reputation based on civic events.
    Events: REPORT_SUBMITTED, REPORT_VERIFIED, REPORT_RESOLVED, REPORT_REJECTED, REPORT_DUPLICATE
    """
    if not uid or not firestore_client.db:
        return
        
    try:
        user_ref = firestore_client.db.collection("users").document(uid)
        transaction = firestore_client.db.transaction()
        new_badges = _update_reputation_transaction(transaction, user_ref, event_type, metadata)
        
        if new_badges:
            logger.info(f"User {uid} awarded new badges: {[b['name'] for b in new_badges]}")
            for badge in new_badges:
                create_notification(uid, "", "BADGE_EARNED", f"You earned the {badge['name']} badge!")
            
    except Exception as e:
        logger.error(f"Failed to update reputation for user {uid}: {e}")

def create_notification(uid: str, incident_id: str, notif_type: str, message: str):
    """
    Creates a personal notification in the citizen's notification center.
    """
    if not uid or not firestore_client.db:
        return
        
    try:
        now = int(time.time() * 1000)
        notif_ref = firestore_client.db.collection("notifications").document(uid).collection("user_notifications").document()
        notif_ref.set({
            "id": notif_ref.id,
            "incident_id": incident_id,
            "type": notif_type,
            "message": message,
            "timestamp": now,
            "read": False
        })
    except Exception as e:
        logger.error(f"Failed to create notification for user {uid}: {e}")
