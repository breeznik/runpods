@echo off
ssh -p 45514 -i C:\Users\Nikhil\.ssh\id_ed25519 -o StrictHostKeyChecking=no root@38.147.83.30 "rm -rf /workspace/blender; rm -f /workspace/startup.log; chmod +x /workspace/start_blender.sh; nohup /workspace/start_blender.sh > /workspace/startup.log 2>&1 &"
