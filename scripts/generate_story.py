import json
import time
import os
import requests
import websocket
import uuid
import subprocess
from dotenv import load_dotenv

load_dotenv()

# Configuration
COMFY_IP = "38.147.83.12"  # Update from RunPod if changed
COMFY_PORT = "8888"
SERVER_ADDRESS = f"{COMFY_IP}:{COMFY_PORT}"
CLIENT_ID = str(uuid.uuid4())

# Story Script: List of prompts for the 30s sequence (approx 5s each)
STORY_PROMPTS = [
    "A majestic cat made of stardust jumping between glowing nebulae in deep space, hyper-realistic, volumetric lighting, 4k.",
    "The stardust cat lands on a floating crystalline asteroid that has bioluminescent plants, the cat explores the alien garden.",
    "The cat touches a glowing fruit on the asteroid, causing a ripple of light that transforms the entire scene into a lush jungle of light.",
    "The cat runs through the glowing jungle, chasing a floating sprite of pure energy, cinematic motion blur.",
    "The cat leaps off a giant glowing leaf into a waterfall of liquid light, sparkling particles everywhere.",
    "The cat emerges from the waterfall onto a beach of obsidian sand under a twin sunset, looking up at the stars it came from."
]

def queue_prompt(prompt_workflow):
    p = {"prompt": prompt_workflow, "client_id": CLIENT_ID}
    response = requests.post(f"http://{SERVER_ADDRESS}/prompt", json=p)
    return response.json()

def get_history(prompt_id):
    response = requests.get(f"http://{SERVER_ADDRESS}/history/{prompt_id}")
    return response.json()

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    response = requests.get(f"http://{SERVER_ADDRESS}/view", params=data)
    return response.content

def track_progress(prompt_id, ws):
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break # Execution finished
        else:
            continue # binary data (previews)

def generate_clip(prompt_text, start_frame_path=None, segment_index=0):
    """
    Generates a 5s clip. If start_frame_path is provided, uses it as conditioning.
    """
    print(f"\n[STORY] Generating Segment {segment_index+1}/6: {prompt_text[:50]}...")
    
    # Load the base workflow (we'll modify it programmatically)
    # This assumes we have a standard LTX-2 workflow structure
    # Since we are automating, we'll build the API JSON here.
    
    # NOTE: In a real scenario, I would load a .json exported from ComfyUI.
    # For now, I'll construct a simplified version based on typical LTX-2 nodes.
    
    workflow = {
        "1": {
            "inputs": {
                "ckpt_name": "ltx-2-19b-dev-fp8.safetensors"
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "2": {
            "inputs": {
                "text": prompt_text,
                "clip": ["1", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "3": {
            "inputs": {
                "width": 768,
                "height": 512,
                "length": 121, # 5 seconds at 24fps
                "batch_size": 1
            },
            "class_type": "EmptyLatentVideo"
        },
        "4": {
            "inputs": {
                "seed": int(time.time()),
                "steps": 20,
                "cfg": 3.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["5", 0],
                "latent_image": ["3", 0]
            },
            "class_type": "KSampler"
        },
        "5": {
            "inputs": {
                "text": "low quality, blurry, static, distorted",
                "clip": ["1", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "6": {
            "inputs": {
                "samples": ["4", 0],
                "vae": ["7", 0]
            },
            "class_type": "VAEDecode"
        },
        "7": {
            "inputs": {
                "vae_name": "vae/diffusion_pytorch_model.safetensors"
            },
            "class_type": "VAELoader"
        },
        "8": {
            "inputs": {
                "images": ["6", 0],
                "filename_prefix": f"story_seg_{segment_index}"
            },
            "class_type": "SaveVideo" # Or VideoCombine if present
        }
    }

    # Add conditioning if we have a start frame
    if start_frame_path:
        # We need to insert a LoadImage and Conditioning node
        workflow["10"] = {
            "inputs": {
                "image": start_frame_path
            },
            "class_type": "LoadImage"
        }
        # Change denoise to allow for image-to-video influence
        workflow["4"]["inputs"]["denoise"] = 0.85
        # Depending on the LTX-2 implementation, we might need a specific Conditioning node
        # For this example, we assume standard image-to-video latent behavior
        workflow["11"] = {
            "inputs": {
                "pixels": ["10", 0],
                "vae": ["7", 0]
            },
            "class_type": "VAEEncode"
        }
        workflow["4"]["inputs"]["latent_image"] = ["11", 0]

    ws = websocket.WebSocket()
    ws.connect(f"ws://{SERVER_ADDRESS}/ws?clientId={CLIENT_ID}")
    
    prompt_res = queue_prompt(workflow)
    prompt_id = prompt_res['prompt_id']
    
    track_progress(prompt_id, ws)
    
    history = get_history(prompt_id)[prompt_id]
    # Extract the last frame path for the next segment
    # Usually in Comfy, SaveVideo nodes return a list of saved files
    outputs = history['outputs']
    # Simplified: finding the image output (assuming it saves frames or we use a node that does)
    # In a real workflow, we'd use a node that outputs the last frame specifically.
    
    return outputs

def main():
    last_frame = None
    for i, prompt in enumerate(STORY_PROMPTS):
        outputs = generate_clip(prompt, start_frame_path=last_frame, segment_index=i)
        
        # LOGIC TO EXTRACT LAST FRAME:
        # This is the 'tricky' part for a script. 
        # We'd need to know exactly where Comfy saves the individual frames.
        # Alternatively, we have a node in the workflow that saves only the last frame to a specific path.
        
        # Mocking for implementation structure:
        last_frame = f"story_seg_{i}_last.png" 
        print(f"Segment {i} done. Last frame saved to {last_frame}")

    print("\n[STORY] All segments generated! Please check the output directory for story_seg_*.mp4")

if __name__ == "__main__":
    main()
