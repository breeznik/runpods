import argparse
import os
import subprocess
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_command(command):
    print(f"Running: {command}")
    try:
        subprocess.check_call(command, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        sys.exit(1)

def sync_up(ip, port, user, key_path, source, target):
    """Syncs from local source to remote target using SCP."""
    # Ensure source directory exists
    if not os.path.isdir(source):
        print(f"Error: Source directory {source} does not exist.")
        sys.exit(1)
        
    print(f"Syncing {source} -> {user}@{ip}:{target}")
    # Using -r for recursive copy
    cmd = f"scp -P {port} -i \"{key_path}\" -o StrictHostKeyChecking=no -r \"{source}\"/* {user}@{ip}:{target}"
    run_command(cmd)

def sync_down(ip, port, user, key_path, source, target):
    """Syncs from remote source to local target using SCP."""
    print(f"Syncing {user}@{ip}:{source} -> {target}")
    
    if not os.path.exists(target):
        os.makedirs(target)
        
    cmd = f"scp -P {port} -i \"{key_path}\" -o StrictHostKeyChecking=no -r {user}@{ip}:{source}/* \"{target}\""
    run_command(cmd)

def main():
    parser = argparse.ArgumentParser(description="Sync Manager for RunPod")
    parser.add_argument("action", choices=["up", "down"], help="Direction of sync")
    parser.add_argument("--ip", help="RunPod IP address")
    parser.add_argument("--port", help="RunPod SSH Port")
    parser.add_argument("--user", help="SSH Username")
    parser.add_argument("--key", help="Path to SSH private key")
    parser.add_argument("--local-dir", default="./local_workspace", help="Local workspace directory")
    parser.add_argument("--remote-dir", default="/workspace/ComfyUI", help="Remote ComfyUI directory")

    args = parser.parse_args()
    
    # Resolve configuration (Args > Env > Defaults)
    ip = args.ip or os.getenv('RUNPOD_HOST')
    port = args.port or os.getenv('RUNPOD_PORT', '22')
    user = args.user or os.getenv('RUNPOD_USER', 'root')
    key_path = args.key or os.getenv('SSH_KEY_PATH', '~/.ssh/id_ed25519')
    
    if not ip:
        print("Error: IP address not specified in args or .env (RUNPOD_HOST).")
        sys.exit(1)

    # Normalize paths
    args.local_dir = os.path.abspath(args.local_dir)

    print(f"Syncing {args.action}...")
    
    # Check key path exists because we're about to use it
    if not os.path.exists(os.path.expanduser(key_path)):
       print(f"Warning: SSH Key not found at {key_path}")

    if args.action == "up":
        # logic: sync local_dir contents -> remote_dir
        sync_up(ip, port, user, key_path, args.local_dir, args.remote_dir)

    elif args.action == "down":
        # Sync outputs back
        # remote: /workspace/ComfyUI/output -> local: ./local_workspace/output
        remote_src = f"{args.remote_dir}/output"
        local_dst = os.path.join(args.local_dir, "output")
        sync_down(ip, port, user, key_path, remote_src, local_dst)

    print("Sync complete.")

if __name__ == "__main__":
    main()
