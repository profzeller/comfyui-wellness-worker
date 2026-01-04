# ComfyUI Wellness Worker

RunPod Serverless worker for ComfyUI-based generation.

## Capabilities

- **FLUX** - High-quality image generation
- **Wan2.2** - Text-to-video and image-to-video generation
- **InfiniteTalk** - Lip-sync video generation (optional)

## Deployment on RunPod

### 1. Fork this repo to your GitHub

### 2. Create a Network Volume (for models)

1. Go to RunPod Console → Storage → Network Volumes
2. Create volume: `comfyui-models` (150GB recommended)
3. Select region closest to your users

### 3. Create Serverless Endpoint

1. Go to Serverless → New Endpoint
2. Source: GitHub repo URL
3. GPU: L40S or A100 (24GB+ VRAM required)
4. Max Workers: 2-3
5. Idle Timeout: 5 seconds
6. Attach Network Volume: `comfyui-models`

### 4. Environment Variables

```
DOWNLOAD_FLUX=true
DOWNLOAD_WAN=true
DOWNLOAD_INFINITETALK=false
HF_TOKEN=your_huggingface_token
```

### 5. First Run

First request will trigger model downloads (~120GB). This takes 10-30 minutes.
Subsequent requests use cached models from the network volume.

## API Usage

### Image Generation (FLUX)

```json
{
  "input": {
    "workflow_type": "flux-image",
    "params": {
      "prompt": "A serene wellness scene with morning sunlight",
      "negative_prompt": "blurry, low quality",
      "width": 1024,
      "height": 1024,
      "seed": 12345
    }
  }
}
```

### Text-to-Video (Wan2.2)

```json
{
  "input": {
    "workflow_type": "wan22-text-to-video",
    "params": {
      "prompt": "A person doing yoga in a peaceful garden",
      "negative_prompt": "blurry, distorted",
      "width": 480,
      "height": 832,
      "num_frames": 120,
      "fps": 24,
      "cfg_scale": 7.5,
      "seed": 12345
    }
  }
}
```

### Image-to-Video (Wan2.2)

```json
{
  "input": {
    "workflow_type": "wan22-image-to-video",
    "params": {
      "source_image_base64": "base64_encoded_image...",
      "prompt": "The person begins to smile and wave",
      "negative_prompt": "blurry, distorted",
      "width": 480,
      "height": 832,
      "num_frames": 120,
      "fps": 24,
      "cfg_scale": 7.5,
      "seed": 12345
    }
  }
}
```

### Custom Workflow

```json
{
  "input": {
    "workflow": {
      // Full ComfyUI workflow JSON
    }
  }
}
```

## Response Format

```json
{
  "outputs": [
    {
      "type": "image|video",
      "filename": "output_00001_.png",
      "base64": "base64_encoded_content..."
    }
  ],
  "image_base64": "...",  // Single image shortcut
  "video_base64": "..."   // Single video shortcut
}
```

## Cost Estimates

| Task | GPU | Time | Cost |
|------|-----|------|------|
| FLUX Image (1024x1024) | L40S | ~15s | ~$0.003 |
| Wan2.2 Video (5s, 480p) | L40S | ~5min | ~$0.06 |
| Wan2.2 Video (5s, 720p) | L40S | ~10min | ~$0.12 |

## Local Development

```bash
# Build
docker build -t comfyui-wellness-worker .

# Run (requires NVIDIA GPU)
docker run --gpus all -p 8188:8188 comfyui-wellness-worker
```

## License

MIT
