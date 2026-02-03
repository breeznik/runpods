"""
config.py - Configuration Management for RPA

Loads templates from YAML, manages environment variables, and provides
centralized configuration access.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Try to import YAML
try:
    import yaml
except ImportError:
    import subprocess
    import sys
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pyyaml"], check=True)
    import yaml

# Load environment
load_dotenv()


@dataclass
class Template:
    """Pod template configuration."""
    name: str
    gpu_type_id: str
    script: str
    desc: str
    cloud_type: str = "SECURE"
    min_vram: int = 48
    system_ram: int = 48
    container_disk: int = 40
    volume_disk: int = 150
    image_name: Optional[str] = None
    setup_script: Optional[str] = None
    
    def to_pod_config(self, default_image: str, hf_token: str = "") -> Dict[str, Any]:
        """Generate RunPod API config from template."""
        return {
            "name": self.name,
            "image_name": self.image_name or default_image,
            "gpu_type_id": self.gpu_type_id,
            "cloud_type": self.cloud_type,
            "min_memory_in_gb": self.system_ram,
            "volume_in_gb": self.volume_disk,
            "container_disk_in_gb": self.container_disk,
            "ports": "8888/http,8188/http,3000/http,22/tcp",
            "volume_mount_path": "/workspace",
            "env": {
                "HF_TOKEN": hf_token,
                "COMFYUI_LISTEN": "0.0.0.0",
                "COMFYUI_PORT": "8888",
            },
        }


@dataclass
class Config:
    """Application configuration."""
    runpod_api_key: str = ""
    ssh_key_path: str = "~/.ssh/id_ed25519"
    hf_token: str = ""
    default_image: str = "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"
    templates: Dict[str, Template] = field(default_factory=dict)
    model_folders: list = field(default_factory=list)
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from YAML file and environment."""
        config = cls(
            runpod_api_key=os.getenv("RUNPOD_API_KEY", ""),
            ssh_key_path=os.getenv("SSH_KEY_PATH", "~/.ssh/id_ed25519"),
            hf_token=os.getenv("HF_TOKEN", ""),
        )
        
        # Default config path
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f)
            
            # Load default image
            config.default_image = data.get("default_image", config.default_image)
            
            # Load model folders
            config.model_folders = data.get("model_folders", [
                "checkpoints", "unet", "diffusion_models", "clip",
                "text_encoders", "vae", "loras", "clip_vision",
                "latent_upscale_models", "controlnet", "upscale_models"
            ])
            
            # Load templates
            for key, t in data.get("templates", {}).items():
                config.templates[key] = Template(
                    name=t["name"],
                    gpu_type_id=t["gpu_type_id"],
                    script=t["script"],
                    desc=t["desc"],
                    cloud_type=t.get("cloud_type", "SECURE"),
                    min_vram=t.get("min_vram", 48),
                    system_ram=t.get("system_ram", 48),
                    container_disk=t.get("container_disk", 40),
                    volume_disk=t.get("volume_disk", 150),
                    image_name=t.get("image_name"),
                    setup_script=t.get("setup_script"),
                )
        else:
            # Fallback to defaults if no config file
            config._load_default_templates()
        
        return config
    
    def _load_default_templates(self) -> None:
        """Load default templates when no config file exists."""
        self.templates = {
            "prod": Template(
                name="ltx2-comfyui-prod",
                gpu_type_id="NVIDIA RTX A6000",
                cloud_type="SECURE",
                min_vram=48,
                script="start.sh",
                desc="RTX A6000 (48GB) - High Performance"
            ),
            "value": Template(
                name="ltx2-comfyui-value",
                gpu_type_id="NVIDIA A40",
                cloud_type="COMMUNITY",
                min_vram=48,
                script="start.sh",
                desc="NVIDIA A40 (48GB) - Best Value"
            ),
            "wan2gp": Template(
                name="wan2gp-video-gen",
                gpu_type_id="NVIDIA A40",
                cloud_type="COMMUNITY",
                min_vram=48,
                script="start_wan2gp.sh",
                desc="NVIDIA A40 (48GB) - Wan2GP Standard"
            ),
        }


# Singleton config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = Config.load()
    return _config
