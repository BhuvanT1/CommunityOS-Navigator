import math
from app.core.config import settings
from app.core.logging import logger
from app.services.embedding_service import cosine_similarity

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance in meters between two points on the earth."""
    R = 6371000  # Radius of earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi/2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def calculate_merge_score(report: dict, incident: dict) -> dict:
    """
    Evaluates a report against an incident and returns the merge score and reasoning.
    The AI Incident Fusion Engine logic.
    """
    config = settings.CLUSTERING
    weights = config.weights
    thresholds = config.thresholds
    
    reasoning = []
    
    # Gate 1: Hard Vetoes
    if report.get("category") != incident.get("category"):
        return {"score": 0, "decision": "NEW_INCIDENT", "reasoning": ["Category mismatch"]}
        
    if incident.get("status") == "RESOLVED":
        return {"score": 0, "decision": "NEW_INCIDENT", "reasoning": ["Incident already resolved"]}
        
    distance_m = haversine_distance(report["lat"], report["lng"], incident["lat"], incident["lng"])
    if distance_m > thresholds.radius_meters:
        return {"score": 0, "decision": "NEW_INCIDENT", "reasoning": [f"Distance {distance_m:.1f}m exceeds {thresholds.radius_meters}m radius"]}
    
    # Gate 2: Weighted Scoring
    # 1. Semantic (Cosine Similarity)
    semantic_sim = cosine_similarity(report.get("embedding", []), incident.get("embedding", []))
    semantic_score = max(0.0, semantic_sim) * 100
    reasoning.append(f"✓ Semantic similarity: {semantic_sim:.2f}")
    
    # 2. Geo Proximity (Exponential decay)
    geo_score = max(0.0, 100 * (1 - (distance_m / thresholds.radius_meters)))
    reasoning.append(f"✓ Distance: {distance_m:.1f}m")
    
    # 3. Time Proximity
    report_time = report.get("timestamp", 0) 
    incident_time = incident.get("timestamp", 0)
    time_diff_hours = abs(report_time - incident_time) / (1000 * 60 * 60)
    
    if time_diff_hours > thresholds.time_window_hours:
         return {"score": 0, "decision": "NEW_INCIDENT", "reasoning": [f"Time gap {time_diff_hours:.1f}h exceeds {thresholds.time_window_hours}h window"]}
         
    time_score = max(0.0, 100 * (1 - (time_diff_hours / thresholds.time_window_hours)))
    reasoning.append(f"✓ Time difference: {time_diff_hours:.1f} hours")
    
    # 4. Road Context
    road_score = 0
    if report.get("street_name") and incident.get("street_name"):
        if report["street_name"].lower() == incident["street_name"].lower():
            road_score = 100
            reasoning.append(f"✓ Exact street match: {report['street_name']}")
        else:
            road_score = 0
            reasoning.append(f"✗ Different streets: {report['street_name']} vs {incident['street_name']}")
            
    # 5. AI Confidence
    confidence_score = report.get("ai_confidence", 50)
    reasoning.append(f"✓ AI Intake Confidence: {confidence_score}%")
    
    # Final Weighted Math
    final_score = (
        (semantic_score * weights.semantic) +
        (geo_score * weights.geo) +
        (time_score * weights.time) +
        (confidence_score * weights.confidence) +
        (road_score * weights.road_match)
    )
    
    final_score = round(final_score, 1)
    
    from app.services.firestore_client import firestore_client
    app_settings = firestore_client.get_settings()
    dynamic_auto_merge_threshold = int(app_settings.get("auto_merge_threshold", thresholds.auto_merge))
    
    if final_score >= dynamic_auto_merge_threshold:
        decision = "AUTO_MERGE"
    elif final_score >= thresholds.manual_review:
        decision = "MANUAL_REVIEW"
    else:
        decision = "NEW_INCIDENT"
        
    return {
        "score": final_score,
        "decision": decision,
        "reasoning": reasoning,
        "master_incident_id": incident.get("id")
    }

def recalculate_priority(base_priority: int, total_reports: int) -> int:
    """
    Logarithmic priority escalation.
    Priority = Base + 15 * log10(total_reports)
    Maxes out at 100.
    """
    if total_reports <= 1:
        return base_priority
    escalation = 15 * math.log10(total_reports)
    return min(100, int(base_priority + escalation))
