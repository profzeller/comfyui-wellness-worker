# ComfyUI Wellness Worker for RunPod Serverless
# Includes: FLUX (images), Wan2.2 (video), InfiniteTalk (lip-sync)
#
# Based on: https://github.com/ValyrianTech/ComfyUI_with_Flux

FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV COMFY_HOME=/comfyui

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    python3.11-venv \
    git \
    wget \
    curl \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Create ComfyUI directory
WORKDIR ${COMFY_HOME}

# Clone ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git . && \
    pip install --no-cache-dir -r requirements.txt

# Install PyTorch with CUDA
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install ComfyUI Manager
RUN cd custom_nodes && \
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git

# Install Video Helper Suite (for video encoding)
RUN cd custom_nodes && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    pip install --no-cache-dir -r ComfyUI-VideoHelperSuite/requirements.txt

# Install Wan2.2 nodes
RUN cd custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    pip install --no-cache-dir -r ComfyUI-WanVideoWrapper/requirements.txt

# Install FLUX nodes (already included in base ComfyUI)
# Additional FLUX support
RUN cd custom_nodes && \
    git clone https://github.com/city96/ComfyUI-GGUF.git && \
    pip install --no-cache-dir gguf

# Install InfiniteTalk nodes (if available)
RUN cd custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-InfiniteTalkWrapper.git 2>/dev/null || \
    echo "InfiniteTalk wrapper not yet available - will use direct integration"

# Install additional useful nodes
RUN cd custom_nodes && \
    git clone https://github.com/pythongosssss/ComfyUI-Custom-Scripts.git && \
    git clone https://github.com/WASasquatch/was-node-suite-comfyui.git && \
    pip install --no-cache-dir -r was-node-suite-comfyui/requirements.txt

# Install RunPod SDK
RUN pip install --no-cache-dir runpod requests websocket-client

# Copy handler and workflows
COPY handler.py /handler.py
COPY workflows/ /workflows/

# Model download script (runs on first start if models not present)
COPY scripts/download_models.sh /scripts/download_models.sh
RUN chmod +x /scripts/download_models.sh

# Environment variables for model paths
ENV COMFYUI_MODEL_PATH=/runpod-volume/models
ENV HF_HOME=/runpod-volume/huggingface

# Create symlinks for model directories (will be populated by network volume)
RUN mkdir -p /runpod-volume/models && \
    ln -sf /runpod-volume/models ${COMFY_HOME}/models

# Expose ComfyUI port (for debugging)
EXPOSE 8188

# Start handler
CMD ["python", "-u", "/handler.py"]
