from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel
import yaml
import os

class ClusteringThresholds(BaseModel):
    auto_merge: int
    manual_review: int
    radius_meters: int
    time_window_hours: int

class ClusteringWeights(BaseModel):
    semantic: float
    geo: float
    time: float
    confidence: float
    road_match: float

class ClusteringSettings(BaseModel):
    thresholds: ClusteringThresholds
    weights: ClusteringWeights

def load_clustering_config() -> ClusteringSettings:
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "clustering_config.yaml")
    try:
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
        return ClusteringSettings(**data)
    except FileNotFoundError:
        # Fallback defaults if the file is missing during tests
        return ClusteringSettings(
            thresholds=ClusteringThresholds(auto_merge=85, manual_review=70, radius_meters=50, time_window_hours=48),
            weights=ClusteringWeights(semantic=0.35, geo=0.25, time=0.15, confidence=0.10, road_match=0.15)
        )

class Settings(BaseSettings):
    PROJECT_NAME: str = "CommunityOS"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    
    # AI & Maps
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "models/gemini-3.1-pro-preview"
    GOOGLE_MAPS_API_KEY: str = ""
    
    # Firebase Service Account
    FIREBASE_SERVICE_ACCOUNT_PATH: str = "serviceAccountKey.json"
    FIREBASE_STORAGE_BUCKET: str = ""

    # Clustering configuration loaded at startup
    CLUSTERING: ClusteringSettings = load_clustering_config()

    # Pydantic Settings will automatically read from the .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
