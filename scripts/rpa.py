#!/usr/bin/env python3
"""
rpa.py - RunPod Automation Unified CLI (v3.0)

Modular, beautiful CLI for cloud GPU management.
Uses Rich TUI, YAML config, and clean abstractions.
"""

from __future__ import annotations
import argparse
import os
import platform
import sys
import time
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any, List

# Ensure we can import local modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# === Core Imports ===
from core import get_config, get_tui, SSHManager, PodInfo

# === RunPod SDK ===
try:
    import runpod
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "runpod"], check=True)
    import runpod

# === Global State ===
IS_WINDOWS = platform.system() == "Windows"
config = get_config()
tui = get_tui()
ssh = SSHManager(config.ssh_key_path)

if config.runpod_api_key:
    runpod.api_key = config.runpod_api_key


# ============================================================
# POD HELPERS
# ============================================================

def get_running_pods() -> List[Dict[str, Any]]:
    """Fetch all running pods."""
    try:
        pods = runpod.get_pods()
        return [p for p in pods if p.get("desiredStatus") == "RUNNING"]
    except Exception as e:
        tui.error(f"Failed to fetch pods: {e}")
        return []


def select_pod(running: List[Dict[str, Any]]) -> Optional[PodInfo]:
    """Interactive pod selection if multiple running."""
    if not running:
        tui.warning("No running pods found.")
        return None
    
    if len(running) == 1:
        pod = running[0]
    else:
        tui.pod_table(running)
        choice = tui.prompt(f"Select pod (1-{len(running)})", "1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(running):
                pod = running[idx]
            else:
                pod = running[0]
        except ValueError:
            pod = running[0]
    
    # Extract SSH info
    machine = pod.get('machine', {})
    pod_host_id = machine.get('podHostId', 'unknown')
    
    ssh_ip = f"{pod_host_id}.runpod.io"
    ssh_port = "22"
    
    runtime = pod.get("runtime") or {}
    for p in runtime.get("ports", []):
        if p['privatePort'] == 22:
            ssh_port = str(p['publicPort'])
            ssh_ip = p.get('ip', ssh_ip)
            break
    
    return PodInfo(
        id=pod["id"],
        name=pod.get("name", "Unknown"),
        ip=ssh_ip,
        port=ssh_port,
        gpu_name=machine.get("gpuDisplayName", "Unknown"),
        cost_per_hr=pod.get("costPerHr", 0.0),
    )


def wait_for_pod(pod_id: str, timeout: int = 300) -> Optional[Dict[str, Any]]:
    """Wait for pod to become ready with SSH."""
    with tui.progress_spinner("Waiting for pod...") as progress:
        task = progress.add_task("Initializing...", total=None)
        start = time.time()
        
        while time.time() - start < timeout:
            try:
                pod = runpod.get_pod(pod_id)
                progress.update(task, description=f"Status: {pod.get('desiredStatus', 'unknown')}")
            except Exception:
                time.sleep(2)
                continue
            
            if pod.get("desiredStatus") == "RUNNING":
                runtime = pod.get("runtime") or {}
                for p in runtime.get("ports", []):
                    if p.get("privatePort") == 22 and p.get("isIpPublic"):
                        return pod
            
            time.sleep(5)
    
    return None


# ============================================================
# COMMANDS
# ============================================================

def cmd_deploy(template_key: str, no_setup: bool = False) -> None:
    """Deploy a new pod from template."""
    if template_key not in config.templates:
        tui.error(f"Template '{template_key}' not found.")
        tui.info(f"Available: {list(config.templates.keys())}")
        return
    
    template = config.templates[template_key]
    
    tui.section("Deploying", "🚀")
    tui.info(f"Template: {template_key}")
    tui.status(f"GPU: {template.gpu_type_id}")
    tui.status(f"Cloud: {template.cloud_type}")
    
    # Check for existing pod
    pods = runpod.get_pods()
    existing = [p for p in pods if p.get("name") == template.name and p.get("desiredStatus") == "RUNNING"]
    
    if existing:
        tui.warning(f"Found existing pod {existing[0]['id']}. Reusing.")
        pod = existing[0]
    else:
        tui.status("Creating pod...")
        pod_config = template.to_pod_config(config.default_image, config.hf_token)
        
        try:
            pod = runpod.create_pod(**pod_config)
        except Exception as e:
            tui.error(f"Creation failed: {e}")
            if template.cloud_type == "COMMUNITY":
                tui.info("Retrying with SECURE cloud...")
                pod_config["cloud_type"] = "SECURE"
                pod = runpod.create_pod(**pod_config)
            else:
                return
    
    # Wait for ready
    pod = wait_for_pod(pod["id"])
    if not pod:
        tui.error("Timed out waiting for pod.")
        return
    
    pod_info = select_pod([pod])
    if not pod_info:
        return
    
    # Provisioning
    if not no_setup:
        tui.section("Provisioning", "📦")
        root_dir = Path(__file__).parent.parent
        
        files_to_upload = [
            root_dir / "docker" / template.script,
            root_dir / ".env",
        ]
        
        if template.setup_script:
            files_to_upload.append(root_dir / "scripts" / template.setup_script)
        
        for f in files_to_upload:
            if f.exists():
                tui.status(f"Uploading {f.name}...")
                ssh.upload_file(pod_info, str(f), f"/workspace/{f.name}")
        
        # Run startup script
        tui.status(f"Executing {template.script}...")
        remote_cmd = f"chmod +x /workspace/{template.script} && nohup /workspace/{template.script} < /dev/null > /workspace/startup.log 2>&1 & sleep 1"
        ssh.run_command(pod_info, remote_cmd, timeout=30)
        tui.info("Startup script launched. Use [W] Watch to monitor.")
    
    # Success
    tui.deployment_panel(
        template=template_key,
        pod_id=pod["id"],
        url=pod_info.proxy_url(8888),
        ssh=f"ssh -p {pod_info.port} root@{pod_info.ip}",
    )


def cmd_connect() -> None:
    """Open SSH tunnel and browser."""
    running = get_running_pods()
    pod = select_pod(running)
    if not pod:
        return
    
    tui.section("Connecting", "🔗")
    tui.status("Opening tunnel (8888, 3000, 7860)...")
    
    ssh_cmd = pod.ssh_command(config.ssh_key_path)
    tunnel_args = "-N -L 8888:127.0.0.1:8888 -L 3000:127.0.0.1:3000 -L 7860:127.0.0.1:7860"
    full_cmd = f"{ssh_cmd} {tunnel_args}"
    
    if IS_WINDOWS:
        subprocess.Popen(f'start "RunPod Tunnel" {full_cmd}', shell=True)
    else:
        subprocess.Popen(full_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    tui.info(f"Proxy: {pod.proxy_url(8888)}")
    time.sleep(3)
    
    webbrowser.open("http://127.0.0.1:8888")
    tui.success("Browser launched. Tunnel running in background.")


def cmd_watch() -> None:
    """Watch pod logs."""
    running = get_running_pods()
    pod = select_pod(running)
    if not pod:
        return
    
    tui.section("Watching Logs", "👀")
    
    # Determine log file
    log_file = "/workspace/startup.log"
    if "wan2gp" in pod.name.lower():
        if ssh.check_file_exists(pod, "/workspace/wan2gp_service.log"):
            log_file = "/workspace/wan2gp_service.log"
            tui.info("Watching runtime log...")
        else:
            tui.info("Watching startup log...")
    else:
        tui.info("Watching startup log...")
    
    ssh.tail_log(pod, log_file)


def cmd_status() -> None:
    """Show pod status."""
    running = get_running_pods()
    pod = select_pod(running)
    if not pod:
        return
    
    tui.section("Pod Status", "📊")
    
    status_cmd = (
        "echo '=== DISK ===' && df -h /workspace | tail -1 && "
        "echo '=== RAM ===' && free -h | grep Mem && "
        "echo '=== GPU ===' && nvidia-smi --query-gpu=gpu_name,utilization.gpu,memory.used,memory.total --format=csv,noheader"
    )
    
    result = ssh.run_command(pod, status_cmd, capture=True, timeout=30)
    tui.console.print(result.stdout)


def cmd_pull() -> None:
    """Pull content from pod."""
    running = get_running_pods()
    pod = select_pod(running)
    if not pod:
        return
    
    tui.section("Pulling Content", "📥")
    
    local_out = Path(__file__).parent.parent / "output"
    local_out.mkdir(exist_ok=True)
    
    # Check remote
    result = ssh.run_command(pod, "ls -A /workspace/ComfyUI/output 2>/dev/null", capture=True)
    if not result.stdout.strip():
        tui.warning("No files found in remote output.")
        return
    
    ssh.download_files(pod, "/workspace/ComfyUI/output/*", str(local_out))
    tui.success(f"Synced to {local_out}")


def cmd_wallet() -> None:
    """Show wallet/cost info."""
    running = get_running_pods()
    total = sum(p.get("costPerHr", 0) for p in running)
    tui.wallet_summary(running, total)


def cmd_shell() -> None:
    """Open interactive shell."""
    running = get_running_pods()
    pod = select_pod(running)
    if not pod:
        return
    
    tui.section("Shell", "📟")
    tui.info(f"Connecting to {pod.name}...")
    ssh.interactive_shell(pod)


def cmd_list() -> None:
    """List all pods."""
    try:
        pods = runpod.get_pods()
        if not pods:
            tui.warning("No pods found.")
            return
        tui.pod_table(pods)
    except Exception as e:
        tui.error(f"Error: {e}")


def cmd_terminate(pod_id: Optional[str] = None) -> None:
    """Terminate a pod."""
    if not pod_id:
        running = get_running_pods()
        if not running:
            tui.warning("No active pods to terminate.")
            return
        
        tui.pod_table(running)
        choice = tui.prompt(f"Select pod to terminate (1-{len(running)})")
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(running):
                pod_id = running[idx]["id"]
            else:
                tui.warning("Invalid selection.")
                return
        except ValueError:
            # Allow pasting full ID
            pod_id = choice.strip()
    
    if tui.confirm(f"Terminate {pod_id}?"):
        tui.status("Terminating...")
        runpod.terminate_pod(pod_id)
        tui.success("Pod terminated. Billing stopped.")
    else:
        tui.info("Cancelled.")


# ============================================================
# INTERACTIVE TUI
# ============================================================

def cmd_interactive() -> None:
    """Main interactive menu."""
    while True:
        tui.clear()
        tui.header("RUNPOD COMMAND CENTER", "v3.0 - Modular Architecture")
        
        # Templates section
        tui.section("Deployment", "🚀")
        template_keys = list(config.templates.keys())
        for i, key in enumerate(template_keys, 1):
            t = config.templates[key]
            cloud = "🔒" if t.cloud_type == "SECURE" else "🌐"
            tui.console.print(f"  [{i}] {cloud} {key.ljust(12)} {t.desc}")
        
        # Management section
        tui.section("Management", "🛠️")
        menu_items = [
            ("C", "Connect (Tunnel)", "🔗"),
            ("W", "Watch Logs", "👀"),
            ("S", "Status", "📊"),
            ("P", "Pull Content", "📥"),
            ("$", "Wallet", "💰"),
            ("H", "Shell", "📟"),
            ("L", "List Pods", "📋"),
            ("K", "Terminate", "💀"),
            ("Q", "Quit", "🚪"),
        ]
        
        for key, label, icon in menu_items:
            tui.console.print(f"  [{key}] {icon} {label}")
        
        tui.console.print()
        choice = tui.prompt("Select").strip().upper()
        
        # Numeric = deploy
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(template_keys):
                cmd_deploy(template_keys[idx])
                tui.prompt("\nPress Enter to continue...")
            continue
        
        # Character commands
        if choice == "Q":
            tui.success("Goodbye!")
            sys.exit(0)
        elif choice == "C":
            cmd_connect()
        elif choice == "W":
            cmd_watch()
        elif choice == "S":
            cmd_status()
        elif choice == "P":
            cmd_pull()
        elif choice == "$":
            cmd_wallet()
        elif choice == "H":
            cmd_shell()
        elif choice == "L":
            cmd_list()
        elif choice == "K":
            cmd_terminate()
        else:
            tui.warning("Invalid option.")
        
        tui.prompt("\nPress Enter to continue...")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="RunPod Automation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")
    
    # Deploy
    p_deploy = subparsers.add_parser("deploy", help="Deploy a pod")
    p_deploy.add_argument("template", choices=list(config.templates.keys()))
    p_deploy.add_argument("--no-setup", action="store_true")
    
    # Other commands
    subparsers.add_parser("connect", help="Open SSH tunnel")
    subparsers.add_parser("watch", help="Watch logs")
    subparsers.add_parser("status", help="Pod status")
    subparsers.add_parser("pull", help="Pull content")
    subparsers.add_parser("wallet", help="Cost info")
    subparsers.add_parser("shell", help="Interactive shell")
    subparsers.add_parser("list", help="List pods")
    
    p_term = subparsers.add_parser("terminate", help="Terminate pod")
    p_term.add_argument("pod_id", nargs="?")
    
    subparsers.add_parser("interactive", help="Interactive TUI")
    
    args = parser.parse_args()
    
    commands = {
        "deploy": lambda: cmd_deploy(args.template, args.no_setup),
        "connect": cmd_connect,
        "watch": cmd_watch,
        "status": cmd_status,
        "pull": cmd_pull,
        "wallet": cmd_wallet,
        "shell": cmd_shell,
        "list": cmd_list,
        "terminate": lambda: cmd_terminate(getattr(args, 'pod_id', None)),
        "interactive": cmd_interactive,
    }
    
    if args.command in commands:
        commands[args.command]()
    else:
        # Default to interactive
        cmd_interactive()


if __name__ == "__main__":
    main()
