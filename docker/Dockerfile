FROM pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Clone ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git

# Install ComfyUI dependencies
WORKDIR /workspace/ComfyUI
RUN pip install -r requirements.txt

# Install ComfyUI Manager
WORKDIR /workspace/ComfyUI/custom_nodes
RUN git clone https://github.com/ltdrdata/ComfyUI-Manager.git

# Install LTX-2 specific Python dependencies (transformers, diffusers, etc. if needed)
# Generally ComfyUI updates manage this, but adding core ones for safety
RUN pip install --no-cache-dir diffusers transformers accelerate safetensors imageio-ffmpeg

# Expose the default ComfyUI port
EXPOSE 8188

# Copy startup script
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Set entrypoint
CMD ["/start.sh"]
