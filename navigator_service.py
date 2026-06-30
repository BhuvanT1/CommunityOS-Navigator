import os
import json
import logging
from typing import Dict, Any, List
from google import genai
from google.genai import types
from app.core.config import settings
from app.services.firestore_client import firestore_client

logger = logging.getLogger(__name__)

class NavigatorService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            self.model_name = settings.GEMINI_MODEL
        else:
            raise RuntimeError("Missing GEMINI_API_KEY")

    def _get_system_prompt(self, context_data: str) -> str:
        return f"""You are the CommunityOS Navigator, an AI-native Municipal Decision Interface.
Your role is to act as an operational layer for the Municipality Command Center.
You MUST output a structured JSON response. Do not output markdown code blocks.

You have access to the following live Firestore incident data:
{context_data}

Rules:
1. Base your verbal answers ONLY on the provided Firestore context. Do not hallucinate. 
2. Provide a concise natural language `answer`.
3. Provide a UI `action` payload to manipulate the dashboard. Supported actions:
   - "APPLY_FILTERS": {{"payload": {{"category": "Pothole"|null, "priority": "CRITICAL"|"HIGH"|"MEDIUM"|"LOW"|null, "status": "OPEN"|"RESOLVED"|null}}}}
   - "FILTER_AND_ZOOM": {{"payload": {{"lat": float, "lng": float, "zoom": int, "highlight": "incident_id"}}}}
   - "SHOW_REGION": {{"payload": {{"lat": float, "lng": float, "zoom": int}}}}
   - "NAVIGATE": {{"payload": {{"route": "/admin/review" | "/admin/reports" | "/admin/settings" | "/admin/map" | "/admin"}}}}
   - "UPDATE_INCIDENT": {{"payload": {{"incident_id": "INC-123", "action": "DISPATCH_TEAM" | "MARK_RESOLVED" | "ESCALATE", "target_team": "optional_team"}}}}
   - "NO_OP": {{"payload": {{}}}}
4. Action Examples:
   - "Show critical potholes" -> APPLY_FILTERS with priority CRITICAL and category Pothole.
   - "Highlight flooding incidents" -> APPLY_FILTERS with category Flooding.
   - "Assign a crew to INC-123" -> UPDATE_INCIDENT with action DISPATCH_TEAM.
   - "Zoom to Main Street" -> SHOW_REGION with lat/lng of Main Street (derive from incidents on Main St).
   - "Which area needs immediate dispatch?" -> FILTER_AND_ZOOM to the highest priority unresolved incident.
   - "Open manual review" -> NAVIGATE with route "/admin/review".
   - "Show duplicate reports" -> NAVIGATE with route "/admin/reports" or NO_OP and explain.
   - "How many reports today?" -> NO_OP and answer verbally.
5. Always provide `reasoning` as a list of bullet points explaining your logic.
6. Provide `metadata` containing `confidence` (percentage), `data_freshness` (e.g. "Live"), and `references` (Array of incident IDs).
7. Suggest 1-2 `follow_ups` actions for the user.

Output Format:
{{
  "answer": "string",
  "action": {{ "type": "string", "payload": {{}} }},
  "metadata": {{ "confidence": "string", "data_freshness": "string", "references": ["string"] }},
  "reasoning": ["string"],
  "follow_ups": ["string"]
}}
"""

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Processes a natural language query using RAG over Firestore.
        """
        # Step 1: Retrieve context
        active_incidents = firestore_client.get_active_incidents()
        context_data = json.dumps(active_incidents, indent=2)

        # Step 2: Check for API Key
        if not self.client:
            raise RuntimeError("Navigator is not initialized due to missing GEMINI_API_KEY.")

        # Step 3: Real Gemini Execution
        try:
            system_prompt = self._get_system_prompt(context_data)
            prompt = f"{system_prompt}\n\nUser Query: {query}\n\nRespond with valid JSON only."
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            )
            
            response_json = json.loads(response.text)
            
            # Execute backend workflows if needed
            action_type = response_json.get("action", {}).get("type")
            payload = response_json.get("action", {}).get("payload", {})
            
            if action_type == "UPDATE_INCIDENT":
                import time
                incident_id = payload.get("incident_id")
                action = payload.get("action")
                target_team = payload.get("target_team")
                
                if incident_id and action:
                    doc_ref = firestore_client.db.collection('incidents').document(incident_id)
                    doc = doc_ref.get()
                    if doc.exists:
                        incident = doc.to_dict()
                        updates = {}
                        if action == "DISPATCH_TEAM":
                            updates["status"] = "ASSIGNED"
                            updates["assigned_team"] = target_team or "Auto-Assigned Navigator Crew"
                        elif action == "MARK_RESOLVED":
                            updates["status"] = "RESOLVED"
                            updates["resolved_at"] = int(time.time() * 1000)
                        elif action == "ESCALATE":
                            updates["escalated"] = True
                            
                        # Append history
                        history = incident.get("merge_history", [])
                        history.append({
                            "timestamp": int(time.time() * 1000),
                            "action": action,
                            "dispatcher_id": "navigator-bot",
                            "notes": "Action executed via Navigator AI command"
                        })
                        updates["merge_history"] = history
                        doc_ref.set(updates, merge=True)
            
            return response_json
            
        except Exception as e:
            logger.error(f"Gemini API failure: {e}")
            raise Exception("Failed to process query through Gemini")

navigator_service = NavigatorService()
