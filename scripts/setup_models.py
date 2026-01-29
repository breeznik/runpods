#!/usr/bin/env python3
"""
setup_models.py - Automated model downloader for ComfyUI LTX-2 workflow

Downloads all required models to appropriate directories.
Supports resume on interrupted downloads.
"""

import os
import sys
from pathlib import Path

try:
    from huggingface_hub import hf_hub_download, snapshot_download
except ImportError:
    print("Installing huggingface_hub...")
    os.system("pip install -q huggingface_hub")
    from huggingface_hub import hf_hub_download, snapshot_download

# Configuration
COMFYUI_BASE = os.getenv("COMFYUI_PATH", "/workspace/ComfyUI")
HF_TOKEN = os.getenv("HF_TOKEN")

# Model registry - Updated with nikhil-file preferred models
MODELS = {
    "ace_step": {
        "repo": "Comfy-Org/ACE-Step_ComfyUI_repackaged",
        "files": ["all_in_one/ace_step_v1_3.5b.safetensors"],
        "dest": f"{COMFYUI_BASE}/models/checkpoints",
        "gated": False,
    },
    "ltx_checkpoint": {
        "repo": "Lightricks/LTX-2",
        "files": ["ltx-2-19b-dev-fp8.safetensors"],
        "dest": f"{COMFYUI_BASE}/models/checkpoints",
        "gated": False,
    },
    # === NEW: Wan 2.1 (14B) ===
    "wan_checkpoint": {
        "repo": "Wan-AI/Wan2.1-I2V-14B-720P",
        "files": ["Wan2_1-I2V-14B-720P_fp8_e4m3fn.safetensors"],
        "dest": f"{COMFYUI_BASE}/models/diffusion_models", # Usually diffusion_models or UNET
        "rename": {"Wan2_1-I2V-14B-720P_fp8_e4m3fn.safetensors": "wan2.1_i2v_14b_fp8.safetensors"},
        "gated": False,
    },
    # === NEW: Flux.1 [Schnell] (Image) ===
    "flux_schnell": {
        "repo": "Kijai/flux-fp8",
        "files": ["flux1-schnell-fp8.safetensors"],
        "dest": f"{COMFYUI_BASE}/models/unet",
        "gated": False,
    },
    # === NEW: AudioLDM-2 (Large) ===
    "audioldm2": {
        "repo": "cvssp/audioldm2-large",
        "files": ["audioldm2-large.pruned.safetensors"], # Assuming a consolidated checkpoint, typically needs full repo download or specific comfy wrapper. 
        # Using a reliable ComfyUI repack if available, otherwise direct from huggingface
        # For simplicity, AudioLDM usually needs the whole folder structure or specific checkpoints.
        "files": ["model.safetensors", "config.json"], # Simplified placeholder.
        # Actually, let's use the ComfyUI-AudioLDM2 specific wrapper if possible.
        # Reverting to base logic: Download main model.
        "repo": "haoheliu/audio-ldm-2-large",
        "files": ["pytorch_model.bin", "config.json", "vocab.json"], # Raw files
        "dest": f"{COMFYUI_BASE}/models/audioldm2", 
        "type": "snapshot", # Smarter to snapshot this one
        "gated": False,
    },
    "stable_audio": {
        "repo": "stabilityai/stable-audio-open-1.0",
        "files": ["model.safetensors"],
        "dest": f"{COMFYUI_BASE}/models/checkpoints",
        "gated": True, # Requires Token
    },
    "gemma_encoder": {
        "repo": "Comfy-Org/ltx-2",
        "files": [
            "split_files/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors",
        ],
        "dest": f"{COMFYUI_BASE}/models/text_encoders",
        "gated": False,
    },
    "spatial_upscaler": {
        "repo": "Lightricks/LTX-2",
        "files": ["ltx-2-spatial-upscaler-x2-1.0.safetensors"],
        "dest": f"{COMFYUI_BASE}/models/latent_upscale_models",
        "gated": False,
    },
    "4x_ultrasharp": {
        "repo": "uwg/upscaler",
        "files": ["4x-UltraSharp.pth"],
        "dest": f"{COMFYUI_BASE}/models/upscale_models",
        "gated": False,
    },
    "controlnets": {
        "repo": "xinsir/controlnet-union-sdxl-1.0", # Placeholder for Flux Controlnet if available, or SDXL.
        # Flux ControlNets are specific. Let's use X-Labs or similar.
        "repo": "XLabs-AI/flux-controlnet-collections",
        "files": ["flux-canny-controlnet-v3.safetensors", "flux-depth-controlnet-v3.safetensors"],
        "dest": f"{COMFYUI_BASE}/models/controlnet",
        "gated": False,
    },
    "loras": {
        "repo": "Lightricks/LTX-2",
        "files": [
            "ltx-2-19b-distilled-lora-384.safetensors",
        ],
        "dest": f"{COMFYUI_BASE}/models/loras",
        "gated": False,
    },
    "lora_camera": {
        "repo": "Lightricks/LTX-2-19b-LoRA-Camera-Control-Dolly-Left",
        "files": [
            "ltx-2-19b-lora-camera-control-dolly-left.safetensors",
        ],
        "dest": f"{COMFYUI_BASE}/models/loras",
        "gated": False,
    },
    "vae": {
        "repo": "Lightricks/LTX-Video",
        "files": ["vae/diffusion_pytorch_model.safetensors"],
        "dest": f"{COMFYUI_BASE}/models/vae",
        "gated": False,
    },
}


def check_model_exists(dest_dir: str, filename: str) -> bool:
    """Check if a model file already exists and has non-zero size."""
    filepath = Path(dest_dir) / Path(filename).name
    return filepath.exists() and filepath.stat().st_size > 0


def download_model(config: dict, dry_run: bool = False) -> bool:
    """Download a single model configuration."""
    repo = config["repo"]
    dest = config["dest"]
    gated = config["gated"]
    
    os.makedirs(dest, exist_ok=True)
    
    success = True
    for filename in config["files"]:
        # Check if already downloaded
        if check_model_exists(dest, filename):
            print(f"  ✓ {filename} (already exists)")
            continue
        
        if dry_run:
            print(f"  → Would download: {filename}")
            continue
        
        print(f"  ⏳ Downloading: {filename}...")
        try:
            token = HF_TOKEN if gated else None
            hf_hub_download(
                repo_id=repo,
                filename=filename,
                local_dir=dest,
                token=token,
            )
            print(f"  ✓ {filename}")
        except Exception as e:
            print(f"  ✗ {filename}: {e}")
            success = False
    
    return success


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Download ComfyUI models")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded")
    parser.add_argument("--model", choices=list(MODELS.keys()), help="Download specific model only")
    args = parser.parse_args()
    
    if not HF_TOKEN and not args.dry_run:
        print("⚠️  Warning: HF_TOKEN not set. Gated models may fail to download.")
        print("   Set it with: export HF_TOKEN=hf_xxxxx")
    
    print(f"\n{'='*50}")
    print("ComfyUI Model Setup")
    print(f"{'='*50}")
    print(f"Base path: {COMFYUI_BASE}")
    print(f"HF Token: {'Set' if HF_TOKEN else 'Not set'}")
    print(f"Mode: {'Dry run' if args.dry_run else 'Download'}")
    print(f"{'='*50}\n")
    
    models_to_download = {args.model: MODELS[args.model]} if args.model else MODELS
    
    all_success = True
    for name, config in models_to_download.items():
        print(f"\n[{name}] {config['repo']}")
        print(f"  Destination: {config['dest']}")
        if not download_model(config, args.dry_run):
            all_success = False
    
    print(f"\n{'='*50}")
    if all_success:
        print("✅ All models ready!")
    else:
        print("⚠️  Some downloads failed. Re-run to retry.")
    print(f"{'='*50}\n")
    
    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
