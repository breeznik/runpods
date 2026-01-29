import runpod
import os
import sys
import time
from dotenv import load_dotenv

# Add current directory to sys.path to import sync_manager
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import sync_manager

# Load environment variables
load_dotenv()

RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH")
POD_NAME = "ltx2-comfyui"

if not RUNPOD_API_KEY:
    print("Error: RUNPOD_API_KEY not found in .env")
    sys.exit(1)

runpod.api_key = RUNPOD_API_KEY

def find_active_pod():
    """Finds the active pod with the specified name."""
    print("Searching for active pod...")
    try:
        pods = runpod.get_pods()
        for pod in pods:
            if pod.get("name") == POD_NAME:
                return pod
        return None
    except Exception as e:
        print(f"Error fetching pods: {e}")
        return None

def get_ssh_details(pod):
    """Extracts SSH IP and Port from pod data."""
    if not pod.get("runtime") or not pod["runtime"].get("ports"):
        return None, None
    
    ssh_port = None
    for p in pod["runtime"]["ports"]:
        if p["privatePort"] == 22:
            ssh_port = p["publicPort"]
            break
            
    return pod.get("publicIp"), ssh_port

def main():
    print("========================================")
    print("      RunPod Content Sync (Safe)        ")
    print("========================================")
    
    # 1. Find Pod
    pod = find_active_pod()
    if not pod:
        # Fallback: check for Budget pod name too?
        # For now, stick to main pod name or generic logic.
        print(f"No active pod found with name '{POD_NAME}'.")
        sys.exit(0)
    
    pod_id = pod["id"]
    status = pod.get("desiredStatus", "UNKNOWN")
    print(f"Found pod: {pod_id} ({status})")

    if status != "RUNNING":
        print("Pod is not running. Cannot sync.")
        sys.exit(1)

    # 2. Sync
    ip, port = get_ssh_details(pod)
    if ip and port:
        print("\n[SYNC] Starting file synchronization...")
        remote_src = "/workspace/ComfyUI/output"
        
        # Determine local destination (project_root/output)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local_dst = os.path.join(project_root, "output")
        
        print(f"Source: {remote_src}")
        print(f"Target: {local_dst}")
        print("Downloading...")
        
        try:
            sync_manager.sync_down(ip, port, "root", SSH_KEY_PATH, remote_src, local_dst)
            print("\n[SUCCESS] Synchronization complete!")
            print(f"Files are in: {local_dst}")
        except Exception as e:
            print(f"\n[ERROR] Sync failed: {e}")
            sys.exit(1)
    else:
        print("Error: Could not determine SSH connection details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
