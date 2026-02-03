# 🚀 RunPod Automation (RPA) Command Center

A unified, dynamic deployment and management system for AI generation and 3D rendering.

## 🌟 New in v3.0: Modular Architecture & Rich UI

The system has been completely re-architected for enterprise-grade stability and ease of use.

*   **🎨 Rich TUI:** Beautiful terminal interface with tables, progress bars, and status panels.
*   **🧩 Modular Core:** Split into `core/` modules (Config, SSH, TUI) for better maintainability.
*   **⚙️ YAML Config:** All templates and settings are now in `config.yaml` - no code changes needed to add tiers.
*   **�️ Robustness:** Cross-platform tunnels (Windows/Mac/Linux), retry logic, and modernized resource handling.

## �🛠️ Quick Start

1.  **Configure:** Copy `.env.example` to `.env` and add your:
    *   `RUNPOD_API_KEY`
    *   `HF_TOKEN`
    *   `SSH_KEY_PATH` (e.g., `~/.ssh/id_ed25519`)
2.  **Launch:** Double-click **`launch.bat`** (or run `python scripts/rpa.py`).
3.  **Deploy:** Select a template from the interactive menu.

---

## 🏗️ Hardware Tiers (Configurable via `config.yaml`)

| Profile | GPU | VRAM | Cloud | Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **🚀 Prod** | RTX A6000 | 48GB | Secure | High-end LTX-2 / Video Gen |
| **💎 Value** | NVIDIA A40 | 48GB | Secure | Best Price/Performance |
| **⚡ Budget** | RTX A5000 | 24GB | Secure | Quantized Hunyuan / Fast Prototyping |
| **🎬 Wan2GP** | NVIDIA A40 | 48GB | Community | Standard Wan2GP Video Generation |
| **🔥 Extreme** | RTX 5090 | 32GB | Community | Blackwell Testing (PyTorch 2.6+) |

---

## 🕹️ Console Features

The **RPA Console** provides deep integration with your running pods:

*   **🔗 Connect:** Automatically bridges secure SSH tunnels for ComfyUI (8888), FileBrowser (3000), and Wan2GP (7860).
*   **👀 Watch:** Real-time stream of the pod's startup and runtime logs.
*   **� Status:** Live dashboard of GPU utilization, VRAM, RAM, and Disk usage.
*   **�📥 Pull:** One-click sync of generated content to your local `output/` folder.
*   **� Wallet:** Live monitoring of your active hourly burn rate.
*   **� Shell:** Direct interactive terminal access.

---

## 📁 Repository Structure

```
runpods/
├── config.yaml           # ⚙️ Master configuration (templates, paths)
├── scripts/
│   ├── rpa.py            # 🚀 Main entry point (v3.0)
│   ├── core/             # 🧩 Modular core package
│   │   ├── config.py     #    - YAML loading & dataclasses
│   │   ├── ssh.py        #    - SSH abstraction & retry logic
│   │   └── tui.py        #    - Rich UI components
│   └── setup_models.py   # 📥 Model downloader
├── docker/               # 🐳 Startup scripts
│   ├── start.sh          #    - Universal startup
│   └── start_wan2gp.sh   #    - Hardened Wan2GP deployment
└── output/               # 📂 Local sync destination
```

---

## ⚠️ Important Notes

*   **Billing:** Always use the **[T] Terminate** option to stop billing when finished.
*   **Persistence:** Pods are ephemeral. Always **[P] Pull Content** before terminating to save your work.
