---
description: Restore RunPod environment (Upload scripts & Start services)
---

This workflow automates the recovery of a RunPod instance, ensuring ComfyUI and FileBrowser are installed and running.

1. **Verify Connectivity**
   Ensure the pod is reachable via SSH.
   ```bash
   ssh -p $RUNPOD_PORT -i $SSH_KEY_PATH -o StrictHostKeyChecking=no root@$RUNPOD_HOST "echo Connection OK"
   ```

2. **Upload Provisioning Scripts**
   Upload the vital scripts to the pod.
   ```bash
   scp -P $RUNPOD_PORT -i $SSH_KEY_PATH -o StrictHostKeyChecking=no d:\projects\personal\runpods\scripts\setup_models.py root@$RUNPOD_HOST:/workspace/setup_models.py
   // turbo
   scp -P $RUNPOD_PORT -i $SSH_KEY_PATH -o StrictHostKeyChecking=no d:\projects\personal\runpods\docker\start.sh root@$RUNPOD_HOST:/workspace/start_services.sh
   ```

3. **Execute Startup Sequence**
   Fix line endings (Windows compatibility) and launch the provisioning robot in the background.
   ```bash
   ssh -p $RUNPOD_PORT -i $SSH_KEY_PATH -o StrictHostKeyChecking=no root@$RUNPOD_HOST "sed -i 's/\r$//' /workspace/start_services.sh && chmod +x /workspace/start_services.sh && nohup /workspace/start_services.sh > /workspace/startup.log 2>&1 &"
   ```

4. **Monitor Progress**
   Tail the log to confirm the robot is working.
   ```bash
   ssh -p $RUNPOD_PORT -i $SSH_KEY_PATH -o StrictHostKeyChecking=no root@$RUNPOD_HOST "tail -f /workspace/startup.log"
   ```
