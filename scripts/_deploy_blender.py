"""Quick deploy script for Blender workstation - bypasses Rich TUI."""
import os, sys, time, subprocess
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

import runpod
runpod.api_key = os.getenv("RUNPOD_API_KEY")
SSH_KEY_PATH = os.path.expanduser(os.getenv("SSH_KEY_PATH", "~/.ssh/id_ed25519"))

POD_CONFIG = {
    "name": "blender-workstation",
    "image_name": "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04",
    "gpu_type_id": "NVIDIA RTX A6000",
    "cloud_type": "SECURE",
    "min_memory_in_gb": 70,
    "volume_in_gb": 150,
    "container_disk_in_gb": 40,
    "ports": "3000/http,5901/http,22/tcp",
    "volume_mount_path": "/workspace",
    "env": {},
}

def main():
    # Check for existing
    pods = runpod.get_pods()
    existing = [p for p in pods if p.get("name") == "blender-workstation" and p.get("desiredStatus") == "RUNNING"]
    
    if existing:
        pod = existing[0]
        print(f"[REUSE] Found existing pod: {pod['id']}")
    else:
        print("[CREATE] Deploying blender-workstation (A6000, 70GB RAM)...")
        try:
            pod = runpod.create_pod(**POD_CONFIG)
        except Exception as e:
            print(f"[ERROR] {e}")
            print("[RETRY] Trying COMMUNITY cloud...")
            POD_CONFIG["cloud_type"] = "COMMUNITY"
            pod = runpod.create_pod(**POD_CONFIG)
    
    pod_id = pod["id"]
    print(f"[WAIT] Waiting for pod {pod_id} to be ready...")
    
    for _ in range(60):
        try:
            pod = runpod.get_pod(pod_id)
        except Exception:
            time.sleep(5)
            continue
        
        if pod.get("desiredStatus") == "RUNNING":
            runtime = pod.get("runtime") or {}
            for p in runtime.get("ports", []):
                if p.get("privatePort") == 22 and p.get("isIpPublic"):
                    break
            else:
                time.sleep(5)
                continue
            break
        time.sleep(5)
    else:
        print("[TIMEOUT] Pod did not become ready in 5 minutes.")
        return
    
    # Extract SSH info
    machine = pod.get("machine", {})
    pod_host_id = machine.get("podHostId", "unknown")
    ssh_ip = f"{pod_host_id}.runpod.io"
    ssh_port = "22"
    
    runtime = pod.get("runtime") or {}
    for p in runtime.get("ports", []):
        if p["privatePort"] == 22:
            ssh_port = str(p["publicPort"])
            ssh_ip = p.get("ip", ssh_ip)
            break
    
    print(f"[OK] Pod is RUNNING!")
    print(f"     Pod ID:  {pod_id}")
    print(f"     SSH:     ssh -p {ssh_port} root@{ssh_ip}")
    
    # Upload and run start_blender.sh
    print("[UPLOAD] Sending start_blender.sh...")
    script_path = ROOT / "docker" / "start_blender.sh"
    scp_cmd = f'scp -P {ssh_port} -i "{SSH_KEY_PATH}" -o StrictHostKeyChecking=no "{script_path}" root@{ssh_ip}:/workspace/'
    subprocess.run(scp_cmd, shell=True, check=True)
    
    print("[RUN] Launching Blender setup (runs in background)...")
    ssh_cmd = f'ssh -p {ssh_port} -i "{SSH_KEY_PATH}" -o StrictHostKeyChecking=no root@{ssh_ip}'
    remote = 'chmod +x /workspace/start_blender.sh && nohup /workspace/start_blender.sh < /dev/null > /workspace/startup.log 2>&1 & sleep 1'
    subprocess.run(f'{ssh_cmd} "{remote}"', shell=True, check=True)
    
    print()
    print("=" * 55)
    print("  BLENDER WORKSTATION DEPLOYED")
    print("=" * 55)
    print(f"  Pod ID:      {pod_id}")
    print(f"  GPU:         NVIDIA RTX A6000 (48GB)")
    print(f"  RAM:         70GB+")
    print(f"  SSH:         ssh -p {ssh_port} root@{ssh_ip}")
    print(f"  FileBrowser: https://{pod_id}-3000.proxy.runpod.net/")
    print(f"  VNC:         Port 5901 via SSH tunnel")
    print(f"  Logs:        ssh ... 'tail -f /workspace/startup.log'")
    print("=" * 55)

if __name__ == "__main__":
    main()
