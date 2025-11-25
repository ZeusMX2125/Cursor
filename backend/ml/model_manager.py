"""Model management system."""

import os
import json
import datetime
import shutil
from typing import Dict, List, Optional
from loguru import logger

class ModelManager:
    """
    Manages ML model lifecycle: registration, versioning, loading.
    """
    
    REGISTRY_FILE = "models/registry.json"
    
    def __init__(self, models_dir: str = "models"):
        self.models_dir = models_dir
        self.registry: Dict[str, List[Dict]] = self._load_registry()

    def _load_registry(self) -> Dict:
        if os.path.exists(self.REGISTRY_FILE):
            try:
                with open(self.REGISTRY_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load model registry: {e}")
        return {}

    def _save_registry(self):
        os.makedirs(os.path.dirname(self.REGISTRY_FILE), exist_ok=True)
        with open(self.REGISTRY_FILE, "w") as f:
            json.dump(self.registry, f, indent=2)

    def register_model(self, model_name: str, file_path: str, metrics: Dict = None, version: str = None):
        """Register a new model version."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Model file {file_path} not found")
            
        timestamp = datetime.datetime.utcnow().isoformat()
        if not version:
            version = f"v{timestamp.replace(':', '').replace('-', '')}"
            
        # Copy to models dir with version
        ext = os.path.splitext(file_path)[1]
        target_filename = f"{model_name}_{version}{ext}"
        target_path = os.path.join(self.models_dir, target_filename)
        
        os.makedirs(self.models_dir, exist_ok=True)
        shutil.copy2(file_path, target_path)
        
        entry = {
            "version": version,
            "timestamp": timestamp,
            "path": target_path,
            "metrics": metrics or {},
            "active": False
        }
        
        if model_name not in self.registry:
            self.registry[model_name] = []
            
        self.registry[model_name].append(entry)
        self._save_registry()
        logger.info(f"Registered model {model_name} version {version}")

    def set_active_version(self, model_name: str, version: str):
        """Set a specific version as active."""
        if model_name not in self.registry:
            raise ValueError(f"Model {model_name} not found")
            
        found = False
        for entry in self.registry[model_name]:
            if entry["version"] == version:
                entry["active"] = True
                found = True
            else:
                entry["active"] = False
        
        if not found:
            raise ValueError(f"Version {version} not found for {model_name}")
            
        self._save_registry()
        # TODO: Trigger reload in services
        
    def get_active_model_path(self, model_name: str) -> Optional[str]:
        """Get path to the active model version."""
        if model_name not in self.registry:
            return None
            
        # Return active, or latest if none active
        active = next((m for m in self.registry[model_name] if m.get("active")), None)
        if active:
            return active["path"]
            
        if self.registry[model_name]:
            # Default to latest
            return self.registry[model_name][-1]["path"]
            
        return None

model_manager = ModelManager()

