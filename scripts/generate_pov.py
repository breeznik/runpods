import json
import urllib.request
import urllib.parse
import sys
import random

# Pod Config
COMFY_URL = "http://localhost:8888"

# Workflow Settings
PROMPT_TEXT = "POV shot from a camera attached to a cat's collar, running through a lush green garden, low angle, shaky energetic movement, realistic 4k texture, cinematic lighting, motion blur"
NEG_PROMPT = "human hands, blur, distortion, cartoon, animation, text, watermark"
STEPS = 30
CFG = 3.5
SEED = random.randint(1, 1000000000)
VIDEO_FRAMES = 1  # Single image

def get_workflow():
    return {
        "3": {
            "inputs": {
                "seed": SEED,
                "steps": STEPS,
                "cfg": CFG,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler",
            "_meta": {
                "title": "KSampler"
            }
        },
        "4": {
            "inputs": {
                "ckpt_name": "ltx-2-19b-dev-fp8.safetensors"
            },
            "class_type": "CheckpointLoaderSimple",
            "_meta": {
                "title": "Load Checkpoint"
            }
        },
        "5": {
            "inputs": {
                "width": 768,
                "height": 512,
                "batch_size": VIDEO_FRAMES
            },
            "class_type": "EmptyLatentImage",
            "_meta": {
                "title": "Empty Latent Image"
            }
        },
        "6": {
            "inputs": {
                "text": PROMPT_TEXT,
                "clip": ["10", 0]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {
                "title": "CLIP Text Encode (Positive)"
            }
        },
        "7": {
            "inputs": {
                "text": NEG_PROMPT,
                "clip": ["10", 0]
            },
            "class_type": "CLIPTextEncode",
            "_meta": {
                "title": "CLIP Text Encode (Negative)"
            }
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEDecode",
            "_meta": {
                "title": "VAE Decode"
            }
        },
        "9": {
            "inputs": {
                "filename_prefix": "CAT_POV_IMG",
                "images": ["8", 0]
            },
            "class_type": "SaveImage",
            "_meta": {
                "title": "Save Image"
            }
        },
        "10": {
            "inputs": {
                "clip_name": "split_files/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors",
                "type": "stable_diffusion"
            },
            "class_type": "CLIPLoader",
            "_meta": {
                "title": "Load CLIP"
            }
        }
    }

def queue_prompt(workflow):
    p = {"prompt": workflow}
    data = json.dumps(p).encode('utf-8')
    url = f"{COMFY_URL}/prompt"
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    print(f"Sending prompt to {url}...")
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())
    except urllib.error.URLError as e:
        print(f"Error connecting to ComfyUI: {e}")
        sys.exit(1)

def main():
    print(f"Generating POV Cat Video (Seed: {SEED})...")
    workflow = get_workflow()
    resp = queue_prompt(workflow)
    print("Success! Workflow queued.")
    print(f"Prompt ID: {resp.get('prompt_id')}")
    print("Check ComfyUI or Output folder for results.")

if __name__ == "__main__":
    main()
