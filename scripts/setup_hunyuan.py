#!/usr/bin/env python3
"""
setup_hunyuan.py - Automated model downloader for HunyuanVideo (Budget/GGUF)

Downloads quantized models optimized for 24GB VRAM cards (A5000/3090/4090).
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
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()

MODELS = {
    "hunyuan_gguf": {
        "repo": "city96/HunyuanVideo-gguf",
        "files": ["hunyuan-video-t2v-720p-Q4_K_M.gguf"], # Capital Q
        "dest": f"{COMFYUI_BASE}/models/unet", 
        "gated": False,
        "type": "single"
    },
    # === NEW: Wan 2.1 (1.3B) GGUF ===
    "wan_1_3b_gguf": {
        "repo": "City96/Wan2.1-T2V-1.3B-GGUF", 
        "files": ["wan2.1-t2v-1.3b-q8_0.gguf"], 
        "dest": f"{COMFYUI_BASE}/models/unet",
        "gated": False,
        "type": "single"
    },
    # === NEW: Flux.1 [Schnell] (GGUF) ===
    "flux_schnell_gguf": {
        "repo": "City96/FLUX.1-schnell-gguf",
        "files": ["flux1-schnell-Q4_K_M.gguf"], # Capital Q
        "dest": f"{COMFYUI_BASE}/models/unet",
        "gated": False,
        "type": "single"
    },
    # === NEW: AudioLDM-2 (Base) ===
    "audioldm2": {
        "repo": "haoheliu/audio-ldm-2-base", # Smaller base model for budget
        "files": ["pytorch_model.bin", "config.json", "vocab.json"], 
        "dest": f"{COMFYUI_BASE}/models/audioldm2", 
        "type": "snapshot",
        "gated": False,
    },
    "vae": {
        "repo": "Tencent-Hunyuan/HunyuanVideo",
        "files": ["vae/pytorch_model.pt"],
        "dest": f"{COMFYUI_BASE}/models/vae",
        "rename": {"vae/pytorch_model.pt": "hunyuan_vae.pt"},
        "gated": False,
        "type": "single"
    },
    "clip_encoder": {
        "repo": "openai/clip-vit-large-patch14",
        "files": ["config.json", "pytorch_model.bin", "preprocessor_config.json", "tokenizer.json", "vocab.json", "merges.txt"],
        "dest": f"{COMFYUI_BASE}/models/clip/clip-vit-large-patch14",
        "gated": False,
        "type": "folder"
    },
    "llava_encoder": {
        "repo": "xtuner/llava-llama-3-8b-v1_1-transformers",
        "files": ["config.json", "pytorch_model.bin", "generation_config.json", "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json"], # Simplified list, usually handled by snapshot if folder
        "dest": f"{COMFYUI_BASE}/models/LLM/llava-llama-3-8b-v1_1-transformers",
        "gated": False,
        "type": "snapshot" # Use snapshot for complex transformer models
    }
}

def check_file_exists(path):
    p = Path(path)
    return p.exists() and p.stat().st_size > 0

def download_item(key, config, dry_run=False):
    dest_dir = Path(config["dest"])
    repo = config["repo"]
    
    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n[{key}] Processing {repo}...")
    
    if config.get("type") == "snapshot":
        if dry_run:
            print(f"  → Would snapshot download to {dest_dir}")
            return True
        print(f"  Downloading snapshot to {dest_dir}...")
        try:
            snapshot_download(repo_id=repo, local_dir=dest_dir, token=HF_TOKEN)
            print("  ✓ Complete")
            return True
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            return False

    # Single files
    files = config.get("files", [])
    success = True
    
    for filename in files:
        final_name = config.get("rename", {}).get(filename, Path(filename).name)
        final_path = dest_dir / final_name
        
        if check_file_exists(final_path):
            print(f"  ✓ {final_name} (exists)")
            continue
            
        if dry_run:
            print(f"  → Would download {filename} to {final_path}")
            continue
            
        print(f"  ⏳ Downloading {filename}...")
        try:
            download_path = hf_hub_download(
                repo_id=repo,
                filename=filename,
                local_dir=dest_dir,
                token=HF_TOKEN
            )
            # Rename if needed (hf_hub_download keeps original name in local_dir structure usually, 
            # but we want flat structure for models usually, or specific structure.)
            # Actually hf_hub_download with local_dir preserves structure. 
            # We will move it if rename is requested.
            
            # Simple move logic for flat directories like 'unet' or 'vae'
            if config.get("rename"):
                 src = dest_dir / filename
                 if src.exists() and src != final_path:
                     src.rename(final_path)
            
            print(f"  ✓ Saved")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            success = False
            
    return success

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    # Pre-flight check for folder structure needed for ComfyUI-GGUF
    # GGUF nodes usually look in models/unet or models/checkpoints
    # We put it in models/unet as it is a U-Net model.
    
    print("Starting Budget (Hunyuan) Model Setup...")
    
    output_base = Path(COMFYUI_BASE)
    
    # Custom nodes might need specific folder hacks, but standard ComfyUI uses 'models/unet' for unets now.
    
    for key, config in MODELS.items():
        download_item(key, config, args.dry_run)
        
    print("\nAll downloads processed.")

if __name__ == "__main__":
    main()
