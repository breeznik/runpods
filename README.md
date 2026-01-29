# 🚀 RunPod Automation (RPA) Command Center

A unified, dynamic deployment and management system for AI generation and 3D rendering.

## 🛠️ Quick Start

1.  **Configure:** Copy `.env.example` to `.env` and add your:
    *   `RUNPOD_API_KEY`
    *   `HF_TOKEN`
    *   `SSH_KEY_PATH` (e.g., `~/.ssh/id_ed25519`)
2.  **Launch:** Double-click **`launch.bat`**.
3.  **Deploy:** Select a template and watch it come to life.

---

## 🏗️ Hardware Tiers

The system uses a **Dynamic Template System**. The menu updates automatically based on the `TEMPLATES` configuration in `scripts/rpa.py`.

| Profile | GPU | VRAM | Cloud | Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **🚀 Prod** | RTX A6000 | 48GB | Secure | High-end LTX-2 / Video Gen |
| **💎 Value** | NVIDIA A40 | 48GB | Secure | Best Price/Performance |
| **⚡ Budget** | RTX A5000 | 24GB | Secure | Quantized Hunyuan / Fast Prototyping |

---

## 🕹️ Management Features

The **RPA Console** provides deep integration with your running pods:

*   **🔗 Connect:** Automatically bridges a secure SSH tunnel and launches ComfyUI in your browser.
*   **👀 Watch:** Real-time stream of the pod's startup logs.
*   **📥 Pull:** One-click download of all generated images and videos to your local `output/` folder.
*   **📟 Shell:** Open a direct terminal bridge into the pod.
*   **💰 Wallet:** Check your active hourly burn rate across all running pods.

---

## 🎨 Blender Studio

Deploy a high-performance rendering workstation in minutes.

*   **🎬 CLI Render:** Drag and drop a `.blend` file to render an entire animation on the pod's high-end GPUs.
*   **🖥️ VNC Desktop:** Access a full XFCE4 Desktop environment via VNC to use Blender's GUI remotely.

---

## 📁 Repository Structure

*   `scripts/rpa.py`: The heart of the system. A dynamic, interactive TUI.
*   `docker/`: Startup scripts (`start.sh`, `setup_blender.sh`) for different environments.
*   `scripts/setup_*.py`: Model-specific downloaders (LTX, Hunyuan, etc.).
*   `output/`: Where your generated creations are synced.

---

## ⚠️ Important Notes

*   **Billing:** Always use the **[T] Terminate** option in the menu or the RunPod dashboard to stop billing.
*   **Data:** Pods are ephemeral. Always **[6] Pull Content** before terminating if you want to keep your results.
