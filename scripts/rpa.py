#!/usr/bin/env python3
"""
rpa.py - RunPod Automation Unified CLI

Manages deployments, templates, and lifecycle for ComfyUI pods.
Templates:
    - prod:   RTX A6000 (48GB) - LTX-2 Full
    - value:  NVIDIA A40 (48GB) - LTX-2 Full (Cheaper)
    - budget: RTX A5000 (24GB) - Hunyuan Quantized
"""

import argparse
import os
import sys
import time
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load Env
load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Try to import runpod
try:
    import runpod
except ImportError:
    print("Installing runpod...")
    os.system("pip install -q runpod")
    import runpod

# Configuration
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH", "~/.ssh/id_ed25519")
HF_TOKEN = os.getenv("HF_TOKEN")

if RUNPOD_API_KEY:
    runpod.api_key = RUNPOD_API_KEY

# Templates
TEMPLATES = {
    "prod": {
        "name": "ltx2-comfyui-prod",
        "gpu_type_id": "NVIDIA RTX A6000",
        "cloud_type": "SECURE",
        "min_vram": 48,
        "script": "start.sh",
        "desc": "RTX A6000 (48GB) - High Performance"
    },
    "value": {
        "name": "ltx2-comfyui-value",
        "gpu_type_id": "NVIDIA A40",
        "cloud_type": "COMMUNITY",
        "min_vram": 48,
        "script": "start.sh",
        "desc": "NVIDIA A40 (48GB) - Best Value"
    },
    "budget": {
        "name": "hunyuan-comfyui-budget",
        "gpu_type_id": "NVIDIA RTX A5000",
        "cloud_type": "SECURE",
        "min_vram": 24,
        "script": "start_budget.sh",
        "setup_script": "setup_hunyuan.py", # Specific setup
        "desc": "RTX A5000 (24GB) - Quantized Hunyuan"
    }
}

MODEL_FOLDERS = [
    "checkpoints",
    "unet",
    "diffusion_models",
    "clip",
    "text_encoders",
    "vae",
    "loras",
    "clip_vision",
    "latent_upscale_models",
    "controlnet",
    "upscale_models"
]

DEFAULT_IMAGE = "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04"

def get_pod_config(template_key):
    t = TEMPLATES[template_key]
    
    config = {
        "name": t["name"],
        "image_name": DEFAULT_IMAGE,
        "gpu_type_id": t["gpu_type_id"],
        "cloud_type": t.get("cloud_type", "SECURE"),
        "volume_in_gb": 150,
        "container_disk_in_gb": 40,
        "ports": "8888/http,8188/http,3000/http,22/tcp",
        "volume_mount_path": "/workspace",
        "env": {
            "HF_TOKEN": HF_TOKEN or "",
            "COMFYUI_LISTEN": "0.0.0.0",
            "COMFYUI_PORT": "8888",
        },
    }
    return config

def wait_for_pod(pod_id, timeout=300):
    print(f"Waiting for pod {pod_id}...")
    start = time.time()
    while time.time() - start < timeout:
        pod = runpod.get_pod(pod_id)
        if pod.get("desiredStatus") == "RUNNING":
             # Check for SSH
            runtime = pod.get("runtime") or {}
            ports = runtime.get("ports", [])
            for p in ports:
                if p.get("privatePort") == 22 and p.get("isIpPublic"):
                    return pod
        time.sleep(5)
    raise TimeoutError("Pod failed to start.")

def cmd_deploy(args):
    template = args.template
    if template not in TEMPLATES:
        print(f"Error: Template '{template}' not found. Options: {list(TEMPLATES.keys())}")
        return

    t = TEMPLATES[template]
    print(f"Deploying Template: {template.upper()}")
    print(f"GPU: {t['desc']}")
    
    config = get_pod_config(template)
    
    # Check existing
    pods = runpod.get_pods()
    existing = [p for p in pods if p.get("name") == config["name"] and p.get("desiredStatus") == "RUNNING"]
    
    if existing:
        print(f"Found existing pod {existing[0]['id']}. Reusing.")
        pod = existing[0]
    else:
        print("Creating pod...")
        try:
            pod = runpod.create_pod(**config)
        except Exception as e:
            print(f"Creation failed: {e}")
            if t["cloud_type"] == "COMMUNITY":
                print("Retrying with SECURE cloud...")
                config["cloud_type"] = "SECURE"
                pod = runpod.create_pod(**config)
            else:
                return

    try:
        pod = wait_for_pod(pod["id"])
    except TimeoutError:
        print("Timed out waiting for pod.")
        return

    # Info
    pod_id = pod["id"]
    machine = pod.get('machine', {})
    pod_host_id = machine.get('podHostId', 'unknown')
    
    ssh_ip = pod_host_id + ".runpod.io"
    ssh_port = "22"
    runtime = pod.get("runtime") or {}
    ports = runtime.get("ports", [])
    
    for p in ports:
        if p['privatePort'] == 22:
            ssh_port = p['publicPort']
            ssh_ip = p.get('ip', ssh_ip)
            break
            
    # Provisioning
    if not args.no_setup:
        print("Provisioning...")
        time.sleep(5)
        root_dir = Path(__file__).parent.parent
        
        # Determine scripts to upload based on template
        START_SCRIPT = t["script"]
        SETUP_SCRIPT = t.get("setup_script", "setup_models.py") # Default to LTX setup
        
        files = [
            root_dir / "docker" / START_SCRIPT,
            root_dir / "scripts" / SETUP_SCRIPT,
            root_dir / ".env"
        ]
        
        key_path = os.path.expanduser(SSH_KEY_PATH)
        
        for f in files:
            if f.exists():
                print(f"  Uploading {f.name}...")
                dest = f"/workspace/{f.name}"
                subprocess.run(f'scp -P {ssh_port} -i "{key_path}" -o StrictHostKeyChecking=no "{f}" root@{ssh_ip}:{dest}', shell=True, check=True, stdout=subprocess.DEVNULL)
        
        print(f"  Triggering startup ({START_SCRIPT})...")
        # Use a more robust detach method: nohup ... < /dev/null > log 2>&1 &
        # And allow a brief moment for it to fork before ssh disconnects
        remote_cmd = f"chmod +x /workspace/{START_SCRIPT} && nohup /workspace/{START_SCRIPT} < /dev/null > /workspace/startup.log 2>&1 & sleep 1"
        subprocess.run(f'ssh -p {ssh_port} -i "{key_path}" -o StrictHostKeyChecking=no root@{ssh_ip} "{remote_cmd}"', shell=True, check=True)

    print("\n" + "="*50)
    print(f"DEPLOYMENT COMPLETE ({template})")
    print(f"URL: https://{pod_id}-8888.proxy.runpod.net")
    print(f"SSH: ssh -p {ssh_port} root@{ssh_ip}")
    print("="*50 + "\n")

def get_running_pod_info(args):
    """Helper to find the target running pod (PROD/VALUE/BUDGET)."""
    try:
        pods = runpod.get_pods()
        running = [p for p in pods if p.get("desiredStatus") == "RUNNING"]
    except Exception as e:
        print(f"Error fetching pods: {e}")
        return None
    
    if not running:
        return None
        
    # If multiple pods, ask the user
    if len(running) > 1:
        print("\nMultiple active pods detected:")
        for i, p in enumerate(running):
            gpu = p.get("machine", {}).get("gpuDisplayName", "Unknown")
            print(f"  [{i+1}] {p['id']:<20} {p.get('name'):<25} ({gpu})")
        
        choice = input(f"\nSelect target pod (1-{len(running)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(running):
            pod = running[int(choice)-1]
        else:
            print("Invalid choice, defaulting to first pod.")
            pod = running[0]
    else:
        pod = running[0]

    pod_id = pod["id"]
    
    # Extract SSH info
    machine = pod.get('machine', {})
    pod_host_id = machine.get('podHostId', 'unknown')
    
    ssh_ip = pod_host_id + ".runpod.io"
    ssh_port = "22"
    runtime = pod.get("runtime") or {}
    ports = runtime.get("ports", [])
    
    for p in ports:
        if p['privatePort'] == 22:
            ssh_port = p['publicPort']
            ssh_ip = p.get('ip', ssh_ip)
            break
            
    return {"id": pod_id, "ip": ssh_ip, "port": ssh_port, "name": pod.get("name"), "cost": pod.get("costPerHr")}

def cmd_connect(args):
    import webbrowser
    info = get_running_pod_info(args)
    if not info:
        print("No running pods found.")
        return
        
    print(f"🔗 Bridging to {info['name']}...")
    key_path = os.path.expanduser(SSH_KEY_PATH)
    
    # Start SSH Tunnel in background
    print("   Opening Tunnel (localhost:8888 -> pod:8888)...")
    # Windows: start /B for background
    tunnel_cmd = f'start /B ssh -p {info["port"]} -i "{key_path}" -o StrictHostKeyChecking=no -N -L 8888:localhost:8888 root@{info["ip"]}'
    os.system(tunnel_cmd)
    
    print("   Waiting for handshake...")
    time.sleep(3)
    
    print("🚀 Launching Browser...")
    webbrowser.open("http://localhost:8888")
    print("Done. (Tunnel runs in background. Close terminal to kill it).")

def cmd_watch(args):
    info = get_running_pod_info(args)
    if not info:
        print("No running pods found.")
        return
        
    print(f"👀 Watching logs on {info['name']}...")
    key_path = os.path.expanduser(SSH_KEY_PATH)
    
    # Tail the startup log
    cmd = f'ssh -p {info["port"]} -i "{key_path}" -o StrictHostKeyChecking=no root@{info["ip"]} "tail -f /workspace/startup.log"'
    os.system(cmd)

def cmd_pull(args):
    info = get_running_pod_info(args)
    if not info:
        print("No running pods found.")
        return
        
    local_out = Path(__file__).parent.parent / "output"
    local_out.mkdir(exist_ok=True)
    
    print(f"📥 Pulling media from {info['name']}...")
    key_path = os.path.expanduser(SSH_KEY_PATH)
    
    # SCP recursive from ComfyUI output
    # Wildcard match for images/videos
    # Actually, simpler to just sync the whole output folder
    remote_path = "/workspace/ComfyUI/output/*"
    
    cmd = f'scp -P {info["port"]} -i "{key_path}" -o StrictHostKeyChecking=no -r root@{info["ip"]}:{remote_path} "{local_out}"'
    os.system(cmd)
    
    print(f"✅ Synced to {local_out}")

def cmd_push(args):
    if not args.files:
        print("Usage: rpa push <file1.json> <file2.json> ...")
        return

    info = get_running_pod_info(args)
    if not info:
        print("No running pods found.")
        return

    print(f"📤 Pushing workflows to {info['name']}...")
    key_path = os.path.expanduser(SSH_KEY_PATH)
    
    # Official ComfyUI workflow standard location (for Sidebar access)
    remote_dir = "/workspace/ComfyUI/user/default/workflows"
    mkdir_cmd = f'ssh -p {info["port"]} -i "{key_path}" -o StrictHostKeyChecking=no root@{info["ip"]} "mkdir -p {remote_dir}"'
    subprocess.run(mkdir_cmd, shell=True, check=True)

    for f in args.files:
        print(f"   Transferring {f}...")
        scp_cmd = f'scp -P {info["port"]} -i "{key_path}" -o StrictHostKeyChecking=no "{f}" root@{info["ip"]}:{remote_dir}/'
        os.system(scp_cmd)
        
    print("✅ Upload complete. (Check 'Workflows' in Comfy sidebar)")

def cmd_wallet(args):
    try:
        pods = runpod.get_pods()
        running = [p for p in pods if p.get("desiredStatus") == "RUNNING"]
        total_hourly = sum([p.get("costPerHr", 0) for p in running])
        
        print(f"\n💰 Active Burn Rate: ${total_hourly:.3f}/hr")
        print(f"   Active Pods: {len(running)}")
        if running:
            print("   (Don't forget to terminate when done!)")
        # print("")
    except:
        print("Error fetching wallet info.")

def ensure_blender(info):
    """Checks if blender is installed remotely, if not runs setup."""
    print("Checking Blender installation...")
    key_path = os.path.expanduser(SSH_KEY_PATH)
    
    # Check if /workspace/blender/blender exists
    check_cmd = f'ssh -p {info["port"]} -i "{key_path}" -o StrictHostKeyChecking=no root@{info["ip"]} "test -f /workspace/blender/blender && echo YES || echo NO"'
    result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True).stdout.strip()
    
    if result != "YES":
        print("🛠️ Blender not found. Installing (this takes ~3 mins)...")
        # Upload setup script
        setup_script = Path(__file__).parent.parent / "docker" / "setup_blender.sh"
        scp_cmd = f'scp -P {info["port"]} -i "{key_path}" -o StrictHostKeyChecking=no "{setup_script}" root@{info["ip"]}:/workspace/'
        subprocess.run(scp_cmd, shell=True, check=True)
        
        # Run it
        run_cmd = f'ssh -p {info["port"]} -i "{key_path}" -o StrictHostKeyChecking=no root@{info["ip"]} "chmod +x /workspace/setup_blender.sh && /workspace/setup_blender.sh"'
        subprocess.run(run_cmd, shell=True, check=True)
        print("✅ Blender Installed.")
    else:
        print("✅ Blender is ready.")

def cmd_render(args):
    if not args.file:
        print("Usage: rpa render <file.blend>")
        return

    info = get_running_pod_info(args)
    if not info:
        print("No running pods found.")
        return
        
    ensure_blender(info)
    
    key_path = os.path.expanduser(SSH_KEY_PATH)
    file_path = Path(args.file)
    remote_blend = f"/workspace/{file_path.name}"
    
    # 1. Upload
    print(f"📤 Uploading {file_path.name}...")
    scp_cmd = f'scp -P {info["port"]} -i "{key_path}" -o StrictHostKeyChecking=no "{file_path}" root@{info["ip"]}:{remote_blend}'
    subprocess.run(scp_cmd, shell=True, check=True)
    
    # 2. Render
    print("🎬 Starting Remote Render (Cycles)...")
    render_cmd = f'/workspace/blender/blender -b "{remote_blend}" -a'
    
    # We run this synchronously so we see the output
    ssh_cmd = f'ssh -p {info["port"]} -i "{key_path}" -o StrictHostKeyChecking=no root@{info["ip"]} "{render_cmd}"'
    os.system(ssh_cmd)
    
    print("\n✅ Render Complete.")
    print("   Run 'rpa pull' (or Option 6) to download the frames.")

def cmd_vnc(args):
    import webbrowser
    info = get_running_pod_info(args)
    if not info:
        print("No running pods found.")
        return
        
    ensure_blender(info) # Setup script also installs VNC
    
    print(f"🖥️  Connecting to Desktop (VNC)...")
    key_path = os.path.expanduser(SSH_KEY_PATH)
    
    # Start Tunnel for VNC (5901 -> 5901)
    print("   Opening Tunnel (localhost:5901 -> pod:5901)...")
    tunnel_cmd = f'start /B ssh -p {info["port"]} -i "{key_path}" -o StrictHostKeyChecking=no -N -L 5901:localhost:5901 root@{info["ip"]}'
    os.system(tunnel_cmd)
    
    print("   Waiting for handshake...")
    time.sleep(3)
    
    print("\n✅ Tunnel Active.")
    print("   Open your VNC Viewer (RealVNC/TigerVNC) and connect to: localhost:5901")
    print("   Password: runpod")
    print("   (Tunnel runs in background. Close terminal to kill it).")

def cmd_shell(args):
    info = get_running_pod_info(args)
    if not info:
        print("No running pods found.")
        return
        
    print(f"📟 Opening Remote Shell to {info['name']}...")
    key_path = os.path.expanduser(SSH_KEY_PATH)
    
    # Launch direct SSH session
    ssh_cmd = f'ssh -p {info["port"]} -i "{key_path}" -o StrictHostKeyChecking=no root@{info["ip"]}'
    os.system(ssh_cmd)

def guess_category(url):
    """Attempt to auto-detect the destination folder from the URL path"""
    url_lower = url.lower()
    
    # Sort folders by length descending to ensure we match 'clip_vision' before 'clip'
    sorted_folders = sorted(MODEL_FOLDERS, key=len, reverse=True)
    
    # Check for direct subfolder names in the URL path parts
    parts = url_lower.split("/")
    for folder in sorted_folders:
        if folder in parts:
            return folder
            
    # Fallback: check if the keyword shows up anywhere
    for folder in sorted_folders:
        if folder in url_lower:
             return folder
             
    return None

def cmd_ingest(args):
    info = get_running_pod_info(args)
    if not info:
        print("No running pods found.")
        return
        
    print("\n--- 📥 SMART BATCH INGEST ---")
    print("Paste Hugging Face URLs (separate multiple with spaces or newline).")
    
    lines = []
    while True:
        line = input("URL(s) [Press Enter on empty line to start]: ").strip()
        if not line: break
        lines.append(line)
        
    if not lines: return
    
    # Flatten and clean URLs
    all_raw = " ".join(lines).replace(",", " ")
    urls = [u.strip() for u in all_raw.split() if u.strip().startswith("http")]
    
    if not urls:
        print("No valid URLs detected.")
        return

    key_path = os.path.expanduser(SSH_KEY_PATH)
    
    ready_to_download = []
    needs_review = []
    
    # Phase 1: Categorization
    for url in urls:
        folder_name = guess_category(url)
        if folder_name:
            ready_to_download.append((url, folder_name))
        else:
            needs_review.append(url)
            
    # Phase 2: Automatic Downloads
    if ready_to_download:
        print(f"\n⚡ Starting automatic ingestion ({len(ready_to_download)} files)...")
        for url, folder_name in ready_to_download:
            filename = url.split("/")[-1].split("?")[0]
            dest_path = f"/workspace/ComfyUI/models/{folder_name}"
            print(f"   [AUTO] {filename} -> {folder_name}")
            
            # Use --show-progress and bar:force:noscroll. Avoid -q to ensure we see the progress bar.
            # We wrap the command in quotes for SSH.
            remote_cmd = f"mkdir -p {dest_path} && cd {dest_path} && wget -c --show-progress --progress=bar:force:noscroll --content-disposition '{url}'"
            ssh_cmd = f'ssh -p {info["port"]} -i "{key_path}" -o StrictHostKeyChecking=no root@{info["ip"]} "{remote_cmd}"'
            os.system(ssh_cmd)
            
    # Phase 3: Deferred Review
    if needs_review:
        print(f"\n🧐 Reviewing {len(needs_review)} unknown links...")
        for url in needs_review:
            filename = url.split("/")[-1].split("?")[0]
            print(f"\n❓ File: {filename}")
            print(f"   Link: {url}")
            
            for i, f in enumerate(MODEL_FOLDERS):
                print(f"  [{i+1}] {f}")
            print(f"  [0] Skip this file")
            
            c_idx = input("Select Category: ").strip()
            if not c_idx.isdigit() or int(c_idx) == 0:
                print("Skipped.")
                continue
                
            folder_name = MODEL_FOLDERS[min(int(c_idx)-1, len(MODEL_FOLDERS)-1)]
            dest_path = f"/workspace/ComfyUI/models/{folder_name}"
            
            print(f"   [USER] Downloading to {folder_name}...")
            remote_cmd = f"mkdir -p {dest_path} && cd {dest_path} && wget -c --show-progress --progress=bar:force:noscroll --content-disposition '{url}'"
            ssh_cmd = f'ssh -p {info["port"]} -i "{key_path}" -o StrictHostKeyChecking=no root@{info["ip"]} "{remote_cmd}"'
            os.system(ssh_cmd)
            
    print("\n✅ All ingest tasks finished.")

# --- Dynamic TUI ---
def cmd_interactive(args):
    """The Main Menu Loop"""
    while True:
        # Clear Screen
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("==================================================")
        print("           RUNPOD COMMAND CENTER (v2.1)")
        print("==================================================")
        print("")
        
        # 1. Dynamic Deployment Section
        print("   --- 🚀 DEPLOYMENT ---")
        idx = 1
        template_keys = list(TEMPLATES.keys())
        for key in template_keys:
            t = TEMPLATES[key]
            print(f"   [{idx}] Deploy {key.capitalize():<10} ({t['desc']})")
            idx += 1
            
        print("")
        
        # 2. Dynamic Management Section
        print("   --- 🛠️  MANAGEMENT ---")
        mgmt_opts = [
            ("Connect (Tunnel)", "connect"),
            ("Watch Logs", "watch"),
            ("Pull Content", "pull"),
            ("Wallet Check", "wallet"),
            ("Open Shell (Terminal)", "shell"),
            ("Ingest Models (URL)", "ingest"),
        ]
        
        start_mgmt_idx = idx
        for i, (label, cmd) in enumerate(mgmt_opts):
             print(f"   [{idx+i}] {label}")
        
        idx += len(mgmt_opts)
        print("")

        # 3. Blender Section
        print("   --- 🎨 BLENDER ---")
        print(f"   [B] Render File")
        print(f"   [V] VNC Desktop")
        print("")

        # 4. Admin Section
        print("   --- ⚙️  ADMIN ---")
        print("   [L] List Pods")
        print("   [T] Terminate Pod")
        print("   [Q] Quit")
        print("")
        print("==================================================")
        
        choice = input("Select Option: ").strip().upper()
        
        # Handle Template Selection
        if choice.isdigit():
            c = int(choice)
            # Template Range
            if 1 <= c <= len(template_keys):
                t_key = template_keys[c-1]
                # Synthesize args for deploy
                args.template = t_key
                args.no_setup = False
                cmd_deploy(args)
                input("\nPress Enter to continue...")
                continue
            
            # Management Range
            mgmt_c = c - start_mgmt_idx
            if 0 <= mgmt_c < len(mgmt_opts):
                cmd_name = mgmt_opts[mgmt_c][1]
                
                if cmd_name == "connect": cmd_connect(args)
                elif cmd_name == "watch": cmd_watch(args)
                elif cmd_name == "pull": cmd_pull(args)
                elif cmd_name == "wallet": cmd_wallet(args)
                elif cmd_name == "shell": cmd_shell(args)
                elif cmd_name == "ingest": cmd_ingest(args)
                
                input("\nPress Enter to continue...")
                continue
        
        # Handle Char Options
        if choice == "B":
            f = input("Drag .blend file here: ").strip().strip('"')
            if f:
                args.file = f
                cmd_render(args)
            else:
                print("Cancelled.")
            input("\nPress Enter to continue...")
            
        elif choice == "V":
            cmd_vnc(args)
            input("\nPress Enter to continue...")
            
        elif choice == "L":
            cmd_list(args)
            input("\nPress Enter to continue...")
            
        elif choice == "T":
            args.pod_id = None # Reset
            # Interactive terminate
            cmd_terminate(args)
            input("\nPress Enter to continue...")
            
        elif choice == "Q":
            print("Bye!")
            sys.exit(0)

def cmd_list(args):
    try:
        pods = runpod.get_pods()
        print(f"{'ID':<20} {'Name':<25} {'GPU':<20} {'Status':<10} {'Cost'}")
        print("-" * 90)
        for p in pods:
            gpu = p.get("machine", {}).get("gpuDisplayName", "Unknown")
            print(f"{p['id']:<20} {p.get('name'):<25} {gpu:<20} {p['desiredStatus']:<10} {p.get('costPerHr')}")
    except Exception as e:
        print(f"Error listing: {e}")

def cmd_terminate(args):
    pid = args.pod_id
    
    if not pid:
        # Interactive Mode: Fetch and Ask
        try:
            pods = runpod.get_pods()
            running = [p for p in pods if p.get("desiredStatus") == "RUNNING"]
            
            if not running:
                print("No active pods found to terminate.")
                return
                
            print("\nActive Pods:")
            print(f"{'#':<3} {'ID':<20} {'Name':<25} {'Cost'}")
            print("-" * 60)
            
            for i, p in enumerate(running):
                 print(f"{i+1:<3} {p['id']:<20} {p.get('name'):<25} ${p.get('costPerHr')}/hr")
            print("-" * 60)
            
            choice = input(f"\nSelect Pod # to Terminate (1-{len(running)}) or Enter to Cancel: ").strip()
            
            if not choice:
                print("Cancelled.")
                return
                
            if choice.isdigit() and 1 <= int(choice) <= len(running):
                pid = running[int(choice)-1]['id']
            else:
                # Allow pasting full ID
                pid = choice
                
        except Exception as e:
            print(f"Error fetching pods: {e}")
            return

    if pid:
        confirm = input(f"Are you sure you want to terminate {pid}? (y/N): ").lower()
        if confirm == 'y':
            print(f"Terminating {pid}...")
            runpod.terminate_pod(pid)
            print("Done. (Billing stopped)")
        else:
            print("Operation cancelled.")

def main():
    parser = argparse.ArgumentParser(description="RunPod Automation (RPA)")
    subparsers = parser.add_subparsers(dest="command")
    
    # Deploy
    p_deploy = subparsers.add_parser("deploy")
    p_deploy.add_argument("--no-setup", action="store_true", help="Skip script upload")
    p_deploy.add_argument("template", choices=TEMPLATES.keys(), help="Template name")
    
    # List
    p_list = subparsers.add_parser("list")
    
    # Terminate
    p_term = subparsers.add_parser("terminate")
    p_term.add_argument("pod_id", nargs="?", help="Pod ID (Optional if only one running)")
    
    # New Commands
    subparsers.add_parser("connect")
    subparsers.add_parser("watch")
    subparsers.add_parser("pull")
    subparsers.add_parser("wallet")
    subparsers.add_parser("shell")
    subparsers.add_parser("ingest")
    
    # Dynamic TUI
    subparsers.add_parser("interactive")

    # Blender
    p_render = subparsers.add_parser("render")
    p_render.add_argument("file", help="Path to .blend file")
    
    subparsers.add_parser("vnc")
    
    p_push = subparsers.add_parser("push")
    p_push.add_argument("files", nargs="+", help="Workflow JSON files to upload")
    
    args = parser.parse_args()
    
    if args.command == "deploy":
        if not args.template:
             print("Error: Template argument required for CLI mode (e.g. 'prod').")
             return
        cmd_deploy(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "terminate":
        cmd_terminate(args)
    elif args.command == "connect":
        cmd_connect(args)
    elif args.command == "watch":
        cmd_watch(args)
    elif args.command == "pull":
        cmd_pull(args)
    elif args.command == "push":
        cmd_push(args)
    elif args.command == "wallet":
        cmd_wallet(args)
    elif args.command == "shell":
        cmd_shell(args)
    elif args.command == "ingest":
        cmd_ingest(args)
    elif args.command == "render":
        cmd_render(args)
    elif args.command == "vnc":
        cmd_vnc(args)
    elif args.command == "interactive":
        cmd_interactive(args)
    else:
        # Default to interactive if no args, or print help
        # parser.print_help()
        # Make default interactive for smooth experience
        cmd_interactive(args)

if __name__ == "__main__":
    main()
