import os
import json
import logging
from typing import List, Dict, Any
from typing import List, Dict, Any
import firebase_admin
from firebase_admin import credentials, firestore, storage
import uuid

logger = logging.getLogger(__name__)

class FirestoreClient:
    def __init__(self):
        self.db = None
        self._initialized = False
        
        try:
            if not firebase_admin._apps:
                from app.core.config import settings
                cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') or os.environ.get('FIREBASE_SERVICE_ACCOUNT_PATH') or settings.FIREBASE_SERVICE_ACCOUNT_PATH
                options = {}
                if settings.FIREBASE_STORAGE_BUCKET:
                    options['storageBucket'] = settings.FIREBASE_STORAGE_BUCKET

                if cred_path and os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred, options)
                else:
                    logger.info("Using Application Default Credentials (ADC) for Cloud Run.")
                    cred = credentials.ApplicationDefault()
                    firebase_admin.initialize_app(cred, options)
                
                self.db = firestore.client()
                self._initialized = True
                logger.info("FirestoreClient initialized successfully with real Firestore.")
            else:
                self.db = firestore.client()
                self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Firestore: {e}")
            raise e

    def get_active_incidents(self) -> List[Dict[str, Any]]:
        """
        Retrieves all active incidents from Firestore.
        This serves as the RAG context for the CommunityOS Navigator.
        """
        if not self._initialized:
            raise RuntimeError("Firestore is not initialized.")

        try:
            # Real Firestore Query
            incidents_ref = self.db.collection('incidents')
            query = incidents_ref.where('status', 'in', ['OPEN', 'PENDING_VERIFICATION', 'ASSIGNED'])
            docs = query.stream()
            
            incidents = []
            for doc in docs:
                data = doc.to_dict()
                data['incident_id'] = doc.id
                incidents.append(data)
                
            return incidents
        except Exception as e:
            logger.error(f"Firestore query failed: {e}")
            return []

    def upload_image(self, image_bytes: bytes, filename: str = None) -> str:
        """
        Uploads image bytes to Firebase Storage and returns the public URL.
        """
        if not self._initialized:
            raise RuntimeError("Firestore is not initialized.")
            
        try:
            import urllib.parse
            import uuid
            
            bucket = storage.bucket()
            filename = f"incidents/{filename or uuid.uuid4().hex}.jpg"
            blob = bucket.blob(filename)
            
            # Create a Firebase download token to allow public access
            download_token = uuid.uuid4().hex
            blob.metadata = {"firebaseStorageDownloadTokens": download_token}
            
            blob.upload_from_string(image_bytes, content_type='image/jpeg')
            
            # Construct standard Firebase Storage URL with the token
            encoded_path = urllib.parse.quote(filename, safe='')
            public_url = f"https://firebasestorage.googleapis.com/v0/b/{bucket.name}/o/{encoded_path}?alt=media&token={download_token}"
            
            logger.info(f"[STAGE 3] Uploaded image to Firebase Storage. URL: {public_url}")
            return public_url
        except Exception as e:
            logger.error(f"Failed to upload image to Firebase Storage: {e}")
            return ""

    def get_settings(self) -> Dict[str, Any]:
        """Retrieves global system settings from Firestore."""
        default_settings = {
            "municipality_name": "Metropolis City Command",
            "auto_merge_threshold": 85,
            "email_alerts": True,
            "sms_alerts": False,
            "push_notifications": True,
            "strictness_level": "High",
            "max_tokens": 2048,
            "retention_period": "90 Days"
        }
        if not self._initialized:
            raise RuntimeError("Firestore is not initialized.")
            
        try:
            doc = self.db.collection('config').document('main').get()
            if doc.exists:
                return {**default_settings, **doc.to_dict()}
            return default_settings
        except Exception as e:
            logger.error(f"Firestore get_settings failed: {e}")
            return default_settings

    def update_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Updates global system settings in Firestore."""
        if not self._initialized:
            raise RuntimeError("Firestore is not initialized.")
            
        try:
            doc_ref = self.db.collection('config').document('main')
            doc_ref.set(new_settings, merge=True)
            return doc_ref.get().to_dict()
        except Exception as e:
            logger.error(f"Firestore update_settings failed: {e}")
            raise e

firestore_client = FirestoreClient()
