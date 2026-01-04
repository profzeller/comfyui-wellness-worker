#!/bin/bash
# Model Download Script for ComfyUI Wellness Worker
# Run this on first startup to download all required models

set -e

MODEL_DIR="${COMFYUI_MODEL_PATH:-/runpod-volume/models}"
HF_TOKEN="${HF_TOKEN:-}"

echo "=== ComfyUI Wellness Worker Model Downloader ==="
echo "Model directory: $MODEL_DIR"

# Create directories
mkdir -p "$MODEL_DIR/checkpoints"
mkdir -p "$MODEL_DIR/unet"
mkdir -p "$MODEL_DIR/vae"
mkdir -p "$MODEL_DIR/clip"
mkdir -p "$MODEL_DIR/wan"

# Function to download from HuggingFace
download_hf() {
    local repo=$1
    local file=$2
    local dest=$3

    if [ -f "$dest" ]; then
        echo "Already exists: $dest"
        return 0
    fi

    echo "Downloading: $file from $repo"

    if [ -n "$HF_TOKEN" ]; then
        wget --header="Authorization: Bearer $HF_TOKEN" \
            "https://huggingface.co/$repo/resolve/main/$file" \
            -O "$dest" -q --show-progress
    else
        wget "https://huggingface.co/$repo/resolve/main/$file" \
            -O "$dest" -q --show-progress
    fi
}

# =============================================================================
# FLUX Models (~30GB total)
# =============================================================================

echo ""
echo "=== Downloading FLUX Models ==="

# FLUX Dev (main model)
download_hf "black-forest-labs/FLUX.1-dev" \
    "flux1-dev.safetensors" \
    "$MODEL_DIR/unet/flux1-dev.safetensors"

# FLUX VAE
download_hf "black-forest-labs/FLUX.1-dev" \
    "ae.safetensors" \
    "$MODEL_DIR/vae/ae.safetensors"

# CLIP models for FLUX
download_hf "comfyanonymous/flux_text_encoders" \
    "t5xxl_fp16.safetensors" \
    "$MODEL_DIR/clip/t5xxl_fp16.safetensors"

download_hf "comfyanonymous/flux_text_encoders" \
    "clip_l.safetensors" \
    "$MODEL_DIR/clip/clip_l.safetensors"

# =============================================================================
# Wan2.2 Models (~70GB total)
# =============================================================================

echo ""
echo "=== Downloading Wan2.2 Models ==="

# Wan2.2 Text-to-Video (14B)
download_hf "Wan-AI/Wan2.2-T2V-14B" \
    "wan2.2_t2v_14B_bf16.safetensors" \
    "$MODEL_DIR/checkpoints/wan2.2_t2v_14B_bf16.safetensors"

# Wan2.2 Image-to-Video (14B)
download_hf "Wan-AI/Wan2.2-I2V-14B" \
    "wan2.2_i2v_14B_bf16.safetensors" \
    "$MODEL_DIR/checkpoints/wan2.2_i2v_14B_bf16.safetensors"

# =============================================================================
# InfiniteTalk Models (~20GB total) - Optional
# =============================================================================

if [ "${DOWNLOAD_INFINITETALK:-false}" = "true" ]; then
    echo ""
    echo "=== Downloading InfiniteTalk Models ==="

    # InfiniteTalk main model
    download_hf "MeiGen-AI/InfiniteTalk" \
        "infinitetalk.safetensors" \
        "$MODEL_DIR/checkpoints/infinitetalk.safetensors"

    # Face detection model
    download_hf "MeiGen-AI/InfiniteTalk" \
        "retinaface_resnet50.pth" \
        "$MODEL_DIR/facedetection/retinaface_resnet50.pth"
fi

# =============================================================================
# Summary
# =============================================================================

echo ""
echo "=== Download Complete ==="
echo ""
echo "Model sizes:"
du -sh "$MODEL_DIR"/* 2>/dev/null || echo "No models downloaded yet"

echo ""
echo "Total size:"
du -sh "$MODEL_DIR" 2>/dev/null || echo "Unknown"
