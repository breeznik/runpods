"""
ssh.py - SSH/SCP Connection Manager

Provides a clean abstraction for SSH operations with retry logic,
connection pooling concepts, and consistent error handling.
"""

from __future__ import annotations
import os
import subprocess
import time
import logging
from dataclasses import dataclass
from functools import wraps
from typing import Optional, Callable, Any, Tuple

log = logging.getLogger("rpa.ssh")


def retry(max_attempts: int = 3, delay: float = 2.0, backoff: float = 1.5):
    """Decorator to retry failed operations with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_error = None
            current_delay = delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts:
                        log.warning(f"  Attempt {attempt}/{max_attempts} failed: {e}")
                        log.warning(f"  Retrying in {current_delay:.1f}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        log.error(f"  All {max_attempts} attempts failed.")
            
            raise last_error
        return wrapper
    return decorator


@dataclass
class PodInfo:
    """Pod connection information."""
    id: str
    name: str
    ip: str
    port: str
    gpu_name: str = "Unknown"
    cost_per_hr: float = 0.0
    
    def proxy_url(self, port: int = 8888) -> str:
        """Generate RunPod proxy URL."""
        return f"https://{self.id}-{port}.proxy.runpod.net/"
    
    def ssh_command(self, key_path: str) -> str:
        """Generate base SSH command."""
        expanded_key = os.path.expanduser(key_path)
        return f'ssh -p {self.port} -i "{expanded_key}" -o StrictHostKeyChecking=no root@{self.ip}'


class SSHManager:
    """Manages SSH connections and operations."""
    
    def __init__(self, key_path: str = "~/.ssh/id_ed25519"):
        self.key_path = os.path.expanduser(key_path)
    
    def get_base_cmd(self, pod: PodInfo) -> str:
        """Get base SSH command for a pod."""
        return f'ssh -p {pod.port} -i "{self.key_path}" -o StrictHostKeyChecking=no root@{pod.ip}'
    
    @retry(max_attempts=3, delay=2.0)
    def run_command(
        self, 
        pod: PodInfo, 
        command: str, 
        capture: bool = False,
        timeout: Optional[int] = None
    ) -> subprocess.CompletedProcess:
        """Execute a command on the pod via SSH."""
        ssh_cmd = f'{self.get_base_cmd(pod)} "{command}"'
        
        return subprocess.run(
            ssh_cmd,
            shell=True,
            capture_output=capture,
            text=True,
            timeout=timeout
        )
    
    def run_background(self, pod: PodInfo, command: str) -> None:
        """Run a command in the background on the pod."""
        # nohup with proper detach
        remote_cmd = f"nohup {command} < /dev/null > /dev/null 2>&1 &"
        self.run_command(pod, remote_cmd, timeout=10)
    
    @retry(max_attempts=2, delay=1.0)
    def upload_file(
        self, 
        pod: PodInfo, 
        local_path: str, 
        remote_path: str
    ) -> subprocess.CompletedProcess:
        """Upload a file to the pod via SCP."""
        scp_cmd = (
            f'scp -P {pod.port} -i "{self.key_path}" '
            f'-o StrictHostKeyChecking=no "{local_path}" root@{pod.ip}:{remote_path}'
        )
        
        return subprocess.run(scp_cmd, shell=True, check=True, capture_output=True)
    
    @retry(max_attempts=2, delay=1.0)
    def download_files(
        self, 
        pod: PodInfo, 
        remote_path: str, 
        local_path: str,
        recursive: bool = True
    ) -> subprocess.CompletedProcess:
        """Download files from the pod via SCP."""
        r_flag = "-r" if recursive else ""
        scp_cmd = (
            f'scp -P {pod.port} -i "{self.key_path}" '
            f'-o StrictHostKeyChecking=no {r_flag} root@{pod.ip}:{remote_path} "{local_path}"'
        )
        
        return subprocess.run(scp_cmd, shell=True, check=True)
    
    def check_file_exists(self, pod: PodInfo, path: str) -> bool:
        """Check if a file exists on the pod."""
        result = self.run_command(
            pod, 
            f'test -f {path} && echo YES || echo NO',
            capture=True,
            timeout=10
        )
        return result.stdout.strip() == "YES"
    
    def check_process_running(self, pod: PodInfo, process_name: str) -> bool:
        """Check if a process is running on the pod."""
        result = self.run_command(
            pod,
            f'pgrep -f "{process_name}"',
            capture=True,
            timeout=10
        )
        return bool(result.stdout.strip())
    
    def tail_log(self, pod: PodInfo, log_path: str) -> None:
        """Tail a log file on the pod (blocking)."""
        ssh_cmd = f'{self.get_base_cmd(pod)} "tail -f {log_path}"'
        subprocess.run(ssh_cmd, shell=True)
    
    def interactive_shell(self, pod: PodInfo) -> None:
        """Open an interactive shell to the pod."""
        os.system(self.get_base_cmd(pod))
