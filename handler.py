"""
RunPod Serverless Handler for ComfyUI
Supports: FLUX images, Wan2.2 video, InfiniteTalk lip-sync

Based on: https://github.com/ValyrianTech/ComfyUI_with_Flux
"""

import runpod
import json
import os
import sys
import time
import uuid
import base64
import subprocess
import threading
import websocket
from pathlib import Path

# Configuration
COMFY_HOME = os.environ.get("COMFY_HOME", "/comfyui")
COMFY_HOST = "127.0.0.1"
COMFY_PORT = 8188
OUTPUT_DIR = f"{COMFY_HOME}/output"
WORKFLOW_DIR = "/workflows"

# Global ComfyUI process
comfy_process = None


def start_comfyui():
    """Start ComfyUI server if not running."""
    global comfy_process

    if comfy_process is not None and comfy_process.poll() is None:
        return True

    print("[Handler] Starting ComfyUI server...")

    comfy_process = subprocess.Popen(
        [sys.executable, "main.py", "--listen", COMFY_HOST, "--port", str(COMFY_PORT)],
        cwd=COMFY_HOME,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    # Wait for server to be ready
    max_wait = 60
    for i in range(max_wait):
        try:
            import urllib.request
            urllib.request.urlopen(f"http://{COMFY_HOST}:{COMFY_PORT}/")
            print(f"[Handler] ComfyUI ready after {i+1}s")
            return True
        except:
            time.sleep(1)

    print("[Handler] ComfyUI failed to start")
    return False


def queue_prompt(workflow: dict, client_id: str) -> str:
    """Queue a workflow and return the prompt_id."""
    import urllib.request

    data = json.dumps({"prompt": workflow, "client_id": client_id}).encode("utf-8")
    req = urllib.request.Request(
        f"http://{COMFY_HOST}:{COMFY_PORT}/prompt",
        data=data,
        headers={"Content-Type": "application/json"}
    )

    response = urllib.request.urlopen(req)
    result = json.loads(response.read())
    return result.get("prompt_id")


def wait_for_completion(prompt_id: str, client_id: str, timeout: int = 600) -> dict:
    """Wait for workflow completion via WebSocket."""

    ws = websocket.create_connection(f"ws://{COMFY_HOST}:{COMFY_PORT}/ws?clientId={client_id}")

    start_time = time.time()
    outputs = {}

    try:
        while time.time() - start_time < timeout:
            message = ws.recv()

            if isinstance(message, str):
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == "executing":
                    exec_data = data.get("data", {})
                    if exec_data.get("prompt_id") == prompt_id:
                        node = exec_data.get("node")
                        if node is None:
                            # Execution complete
                            print(f"[Handler] Workflow {prompt_id} completed")
                            break
                        else:
                            print(f"[Handler] Executing node: {node}")

                elif msg_type == "executed":
                    exec_data = data.get("data", {})
                    if exec_data.get("prompt_id") == prompt_id:
                        node_id = exec_data.get("node")
                        output = exec_data.get("output", {})
                        outputs[node_id] = output

                elif msg_type == "execution_error":
                    error_data = data.get("data", {})
                    if error_data.get("prompt_id") == prompt_id:
                        raise Exception(f"Execution error: {error_data}")

        else:
            raise TimeoutError(f"Workflow timed out after {timeout}s")

    finally:
        ws.close()

    return outputs


def get_output_files(outputs: dict) -> list:
    """Extract output file paths from execution results."""
    files = []

    for node_id, output in outputs.items():
        # Check for images
        if "images" in output:
            for img in output["images"]:
                if "filename" in img:
                    subfolder = img.get("subfolder", "")
                    filepath = os.path.join(OUTPUT_DIR, subfolder, img["filename"])
                    files.append({"type": "image", "path": filepath, "filename": img["filename"]})

        # Check for videos (VHS_VideoCombine output)
        if "gifs" in output:
            for vid in output["gifs"]:
                if "filename" in vid:
                    subfolder = vid.get("subfolder", "")
                    filepath = os.path.join(OUTPUT_DIR, subfolder, vid["filename"])
                    files.append({"type": "video", "path": filepath, "filename": vid["filename"]})

    return files


def file_to_base64(filepath: str) -> str:
    """Read file and encode to base64."""
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def load_workflow(workflow_type: str) -> dict:
    """Load a predefined workflow template."""
    workflow_file = os.path.join(WORKFLOW_DIR, f"{workflow_type}.json")

    if os.path.exists(workflow_file):
        with open(workflow_file, "r") as f:
            return json.load(f)

    return None


def apply_params_to_workflow(workflow: dict, params: dict) -> dict:
    """Apply parameters to a workflow template."""
    workflow_str = json.dumps(workflow)

    # Replace placeholders
    for key, value in params.items():
        placeholder = f"{{${key}}}"
        if isinstance(value, str):
            workflow_str = workflow_str.replace(placeholder, value)
        else:
            workflow_str = workflow_str.replace(f'"{placeholder}"', json.dumps(value))

    return json.loads(workflow_str)


def handler(job: dict) -> dict:
    """Main RunPod handler function."""

    job_input = job.get("input", {})

    # Health check - respond immediately without starting ComfyUI
    if job_input.get("health_check") or not job_input:
        return {
            "status": "healthy",
            "message": "ComfyUI handler ready. Models loaded from network volume.",
            "supported_workflows": ["flux_image", "wan_video", "infinitetalk"]
        }

    # Get workflow - either provided or from template
    workflow = job_input.get("workflow")
    workflow_type = job_input.get("workflow_type")
    params = job_input.get("params", {})

    if workflow is None and workflow_type:
        workflow = load_workflow(workflow_type)
        if workflow is None:
            return {"error": f"Unknown workflow type: {workflow_type}"}

        # Apply parameters
        if params:
            workflow = apply_params_to_workflow(workflow, params)

    if workflow is None:
        return {"error": "No workflow provided"}

    # Ensure ComfyUI is running
    if not start_comfyui():
        return {"error": "Failed to start ComfyUI"}

    try:
        # Generate unique client ID
        client_id = str(uuid.uuid4())

        # Determine timeout based on workflow type
        timeout = 600  # 10 min default
        if workflow_type and "video" in workflow_type.lower():
            timeout = 1200  # 20 min for video
        if workflow_type and "infinitetalk" in workflow_type.lower():
            timeout = 1800  # 30 min for lip-sync

        print(f"[Handler] Queueing workflow (type: {workflow_type}, timeout: {timeout}s)")

        # Queue the workflow
        prompt_id = queue_prompt(workflow, client_id)
        print(f"[Handler] Prompt ID: {prompt_id}")

        # Wait for completion
        outputs = wait_for_completion(prompt_id, client_id, timeout)

        # Get output files
        files = get_output_files(outputs)

        if not files:
            return {"error": "No output files generated", "raw_outputs": outputs}

        # Encode outputs
        result = {"outputs": []}

        for file_info in files:
            filepath = file_info["path"]

            if os.path.exists(filepath):
                encoded = file_to_base64(filepath)

                result["outputs"].append({
                    "type": file_info["type"],
                    "filename": file_info["filename"],
                    "base64": encoded
                })

                # Clean up file
                os.remove(filepath)
            else:
                print(f"[Handler] Output file not found: {filepath}")

        # For single output, also provide top-level access
        if len(result["outputs"]) == 1:
            output = result["outputs"][0]
            if output["type"] == "image":
                result["image_base64"] = output["base64"]
            elif output["type"] == "video":
                result["video_base64"] = output["base64"]

        return result

    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


# RunPod serverless entry point
runpod.serverless.start({"handler": handler})
