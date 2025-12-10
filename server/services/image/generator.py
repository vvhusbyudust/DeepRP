"""
Image Generation Service
Supports: OpenAI (DALL-E), Stable Diffusion, ComfyUI, NovelAI
"""
import httpx
import aiosqlite
import asyncio
import base64
import json
import uuid
import io
import zipfile
from typing import Optional

from models import DATABASE_PATH
from utils import decrypt_api_key, save_image, generate_id


async def get_image_config(config_id: Optional[str] = None) -> Optional[dict]:
    """Get image configuration by ID or get active config."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        if config_id:
            query = "SELECT * FROM image_configs WHERE id = ?"
            params = (config_id,)
        else:
            query = "SELECT * FROM image_configs WHERE is_active = 1"
            params = ()
        
        async with db.execute(query, params) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            
            return {
                "id": row["id"],
                "type": row["type"],
                "base_url": row["base_url"],
                "api_key": decrypt_api_key(row["api_key_encrypted"]),
                "model": row["model"],
                "size": row["size"] or "1024x1024",
                "quality": row["quality"] or "standard",
                # Extended parameters (with fallbacks for old schemas)
                "negative_prompt": row["negative_prompt"] if "negative_prompt" in row.keys() else "",
                "steps": row["steps"] if "steps" in row.keys() else 28,
                "cfg_scale": row["cfg_scale"] if "cfg_scale" in row.keys() else 7.0,
                "sampler": row["sampler"] if "sampler" in row.keys() else "",
                "workflow_json": row["workflow_json"] if "workflow_json" in row.keys() else "",
                "prompt_node_id": row["prompt_node_id"] if "prompt_node_id" in row.keys() else None,
            }


async def generate_image(
    prompt: str,
    chat_session_id: str,
    config_id: Optional[str] = None
) -> str:
    """
    Generate an image using the configured API.
    
    Args:
        prompt: The image generation prompt
        chat_session_id: Chat session ID for saving the image
        config_id: Optional specific config ID
    
    Returns:
        URL path to the saved image
    """
    config = await get_image_config(config_id)
    if not config:
        raise Exception("No image generation configuration found")
    
    if config["type"] == "openai":
        return await generate_openai_image(prompt, chat_session_id, config)
    elif config["type"] == "stable_diffusion":
        return await generate_sd_image(prompt, chat_session_id, config)
    elif config["type"] == "comfyui":
        return await generate_comfyui_image(prompt, chat_session_id, config)
    elif config["type"] == "novelai":
        return await generate_novelai_image(prompt, chat_session_id, config)
    else:
        raise Exception(f"Unknown image API type: {config['type']}")


async def generate_openai_image(
    prompt: str,
    chat_session_id: str,
    config: dict
) -> str:
    """Generate image using OpenAI-compatible API (DALL-E, etc.)."""
    base_url = config["base_url"].rstrip("/")
    api_key = config["api_key"]
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/images/generations",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.get("model", "dall-e-3"),
                "prompt": prompt,
                "n": 1,
                "size": config.get("size", "1024x1024"),
                "quality": config.get("quality", "standard"),
                "response_format": "b64_json",
            },
            timeout=120.0
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.text}")
        
        data = response.json()
        image_b64 = data["data"][0]["b64_json"]
        image_data = base64.b64decode(image_b64)
        
        # Save image
        filename = f"{generate_id()}.png"
        image_url = await save_image(image_data, chat_session_id, filename)
        return image_url


async def generate_sd_image(
    prompt: str,
    chat_session_id: str,
    config: dict
) -> str:
    """Generate image using Stable Diffusion WebUI API (Automatic1111)."""
    base_url = config["base_url"].rstrip("/")
    api_key = config["api_key"]
    
    # Parse size
    size = config.get("size", "1024x1024")
    try:
        width, height = map(int, size.split("x"))
    except ValueError:
        width, height = 1024, 1024
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/sdapi/v1/txt2img",
            headers=headers,
            json={
                "prompt": prompt,
                "negative_prompt": config.get("negative_prompt", ""),
                "steps": config.get("steps", 28),
                "cfg_scale": config.get("cfg_scale", 7.0),
                "width": width,
                "height": height,
                "sampler_name": config.get("sampler", "Euler a") or "Euler a",
            },
            timeout=180.0
        )
        
        if response.status_code != 200:
            raise Exception(f"Stable Diffusion API error: {response.text}")
        
        data = response.json()
        image_b64 = data["images"][0]
        image_data = base64.b64decode(image_b64)
        
        filename = f"{generate_id()}.png"
        image_url = await save_image(image_data, chat_session_id, filename)
        return image_url


async def generate_comfyui_image(
    prompt: str,
    chat_session_id: str,
    config: dict
) -> str:
    """
    Generate image using ComfyUI API with WebSocket polling.
    Supports custom workflow JSON or uses a default txt2img workflow.
    """
    import websockets
    
    print(f"\n=== ComfyUI Image Generation Started ===")
    print(f"  Prompt (first 100 chars): {prompt[:100]}...")
    print(f"  Config type: {config.get('type')}")
    print(f"  Base URL: {config.get('base_url')}")
    print(f"  Prompt Node ID: {config.get('prompt_node_id')}")
    print(f"  Has workflow_json: {bool(config.get('workflow_json'))}")
    
    base_url = config["base_url"].rstrip("/")
    client_id = str(uuid.uuid4())
    
    # Parse size
    size = config.get("size", "1024x1024")
    try:
        width, height = map(int, size.split("x"))
    except ValueError:
        width, height = 1024, 1024
    
    # Build workflow
    print(f"\n[Step 1] Building workflow...")
    if config.get("workflow_json"):
        # Use custom workflow
        try:
            workflow_prompt = json.loads(config["workflow_json"])
            print(f"  Parsed custom workflow with {len(workflow_prompt)} nodes")
            # Inject prompt into the workflow
            workflow_prompt = inject_prompt_into_workflow(
                workflow_prompt, prompt, config.get("negative_prompt", ""),
                prompt_node_id=config.get("prompt_node_id")
            )
            print(f"  Prompt injected into workflow")
        except json.JSONDecodeError as e:
            print(f"  ERROR: Invalid workflow JSON: {e}")
            raise Exception("Invalid workflow JSON format")
    else:
        # Use default txt2img workflow
        print(f"  Using default txt2img workflow")
        workflow_prompt = build_default_comfyui_workflow(
            prompt=prompt,
            negative_prompt=config.get("negative_prompt", "bad quality, blurry, worst quality"),
            width=width,
            height=height,
            steps=config.get("steps", 20),
            cfg=config.get("cfg_scale", 7.0),
            sampler=config.get("sampler", "euler") or "euler",
            model=config.get("model", "sd_xl_base_1.0.safetensors") or "sd_xl_base_1.0.safetensors",
        )
    
    # Queue the prompt
    print(f"\n[Step 2] Queuing prompt to ComfyUI...")
    print(f"  URL: {base_url}/prompt")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/prompt",
                json={"prompt": workflow_prompt, "client_id": client_id},
                timeout=30.0
            )
            
            print(f"  Response status: {response.status_code}")
            if response.status_code != 200:
                error_text = response.text
                print(f"  ERROR: {error_text}")
                raise Exception(f"ComfyUI queue error ({response.status_code}): {error_text}")
            
            result = response.json()
            prompt_id = result["prompt_id"]
            print(f"  Prompt ID: {prompt_id}")
    except httpx.ConnectError as e:
        print(f"  ERROR: Cannot connect to ComfyUI at {base_url}")
        print(f"  Details: {e}")
        raise Exception(f"Cannot connect to ComfyUI at {base_url}. Is ComfyUI running?")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        raise
    
    # Poll via WebSocket for completion
    print(f"\n[Step 3] Waiting for ComfyUI execution (WebSocket)...")
    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
    ws_full_url = f"{ws_url}/ws?clientId={client_id}"
    print(f"  WebSocket URL: {ws_full_url}")
    
    try:
        async with websockets.connect(ws_full_url) as ws:
            print(f"  WebSocket connected")
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=180.0)
                    data = json.loads(msg)
                    
                    msg_type = data.get("type")
                    if msg_type == "status":
                        queue_remaining = data.get("data", {}).get("status", {}).get("exec_info", {}).get("queue_remaining", "?")
                        print(f"  Status: queue_remaining={queue_remaining}")
                    elif msg_type == "executing":
                        exec_data = data.get("data", {})
                        node = exec_data.get("node")
                        if exec_data.get("prompt_id") == prompt_id:
                            if node is None:
                                print(f"  Execution complete!")
                                break
                            else:
                                print(f"  Executing node: {node}")
                    elif msg_type == "execution_error":
                        error_data = data.get("data", {})
                        print(f"  EXECUTION ERROR: {error_data}")
                        raise Exception(f"ComfyUI execution error: {error_data}")
                    elif msg_type == "progress":
                        progress = data.get("data", {})
                        print(f"  Progress: {progress.get('value', 0)}/{progress.get('max', 0)}")
                        
                except asyncio.TimeoutError:
                    print(f"  ERROR: Timeout after 180 seconds")
                    raise Exception("ComfyUI generation timed out after 180 seconds")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"  ERROR: WebSocket closed unexpectedly: {e}")
        raise Exception(f"ComfyUI WebSocket closed: {e}")
    except Exception as e:
        if "websockets" in str(type(e).__module__):
            print(f"  ERROR: WebSocket connection failed: {e}")
            raise Exception(f"ComfyUI WebSocket connection failed: {e}")
        print(f"  ERROR: {type(e).__name__}: {e}")
        raise
    
    # Fetch the history to get the output image
    print(f"\n[Step 4] Fetching execution history...")
    async with httpx.AsyncClient() as client:
        history_url = f"{base_url}/history/{prompt_id}"
        print(f"  URL: {history_url}")
        response = await client.get(history_url, timeout=30.0)
        print(f"  Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"  ERROR: {response.text}")
            raise Exception(f"ComfyUI history fetch error: {response.text}")
        
        history = response.json()
        
        if prompt_id not in history:
            print(f"  ERROR: Prompt ID not found in history")
            raise Exception("ComfyUI execution not found in history")
        
        outputs = history[prompt_id].get("outputs", {})
        print(f"  Found {len(outputs)} output node(s)")
        
        # Find the SaveImage node output
        image_info = None
        for node_id, node_output in outputs.items():
            if "images" in node_output:
                image_info = node_output["images"][0]
                print(f"  Found image in node {node_id}: {image_info}")
                break
        
        if not image_info:
            print(f"  ERROR: No image found in any output node")
            print(f"  Available outputs: {list(outputs.keys())}")
            raise Exception("No image found in ComfyUI output")
        
        # Download the image
        print(f"\n[Step 5] Downloading image...")
        filename = image_info["filename"]
        subfolder = image_info.get("subfolder", "")
        img_type = image_info.get("type", "output")
        
        view_url = f"{base_url}/view?filename={filename}&subfolder={subfolder}&type={img_type}"
        print(f"  URL: {view_url}")
        response = await client.get(view_url, timeout=30.0)
        print(f"  Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"  ERROR: Image download failed")
            raise Exception(f"ComfyUI image download error: {response.status_code}")
        
        image_data = response.content
        print(f"  Downloaded {len(image_data)} bytes")
    
    # Save image
    print(f"\n[Step 6] Saving image locally...")
    save_filename = f"{generate_id()}.png"
    image_url = await save_image(image_data, chat_session_id, save_filename)
    print(f"  Saved as: {image_url}")
    print(f"=== ComfyUI Image Generation Complete ===\n")
    return image_url


def build_default_comfyui_workflow(
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    steps: int,
    cfg: float,
    sampler: str,
    model: str
) -> dict:
    """Build a default txt2img workflow for ComfyUI."""
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": -1,  # Random seed
                "steps": steps,
                "cfg": cfg,
                "sampler_name": sampler,
                "scheduler": "normal",
                "denoise": 1,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            }
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": model}
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1}
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["4", 1]}
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative_prompt, "clip": ["4", 1]}
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]}
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "DeepRP", "images": ["8", 0]}
        }
    }


def inject_prompt_into_workflow(
    workflow: dict, 
    prompt: str, 
    negative_prompt: str,
    prompt_node_id: str = None
) -> dict:
    """
    Inject prompt text into a custom ComfyUI workflow.
    
    Priority:
    1. Node ID mode: If prompt_node_id specified, inject directly into that node
    2. Placeholder mode: Replace {{PROMPT}}, {{NEGATIVE}}, {{SEED}} placeholders
    3. Heuristic mode: Fall back to CLIPTextEncode detection
    """
    import random
    
    # Priority 1: Direct node ID targeting
    if prompt_node_id and prompt_node_id in workflow:
        node = workflow[prompt_node_id]
        inputs = node.get("inputs", {})
        # Inject into the 'text' field (works for most text nodes)
        if "text" in inputs:
            # If text is a string, replace it
            if isinstance(inputs["text"], str):
                inputs["text"] = prompt
            # If text is a list (linked input), we can't replace it - log warning
            else:
                print(f"Warning: Node {prompt_node_id} has linked text input, cannot inject directly")
        else:
            # Try common alternative field names
            for field in ["prompt", "string", "content", "input"]:
                if field in inputs and isinstance(inputs[field], str):
                    inputs[field] = prompt
                    break
        return workflow
    
    # Priority 2: Placeholder mode
    workflow_str = json.dumps(workflow, ensure_ascii=False)
    
    has_prompt_placeholder = "{{PROMPT}}" in workflow_str
    has_negative_placeholder = "{{NEGATIVE}}" in workflow_str
    has_seed_placeholder = "{{SEED}}" in workflow_str
    
    if has_prompt_placeholder or has_negative_placeholder or has_seed_placeholder:
        # Placeholder mode: string replacement
        escaped_prompt = prompt.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
        escaped_negative = negative_prompt.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
        random_seed = str(random.randint(0, 2**32 - 1))
        
        workflow_str = workflow_str.replace("{{PROMPT}}", escaped_prompt)
        workflow_str = workflow_str.replace("{{NEGATIVE}}", escaped_negative)
        workflow_str = workflow_str.replace("{{SEED}}", random_seed)
        
        return json.loads(workflow_str)
    
    # Priority 3: Fall back to CLIPTextEncode heuristic
    for node_id, node in workflow.items():
        if node.get("class_type") == "CLIPTextEncode":
            inputs = node.get("inputs", {})
            current_text = inputs.get("text", "")
            
            # Skip if text is a linked input (list reference to another node)
            if isinstance(current_text, list):
                continue
                
            current_text_lower = current_text.lower()
            
            # Heuristic: if current text contains negative keywords, it's likely the negative prompt
            negative_keywords = ["bad", "worst", "ugly", "blurry", "low quality", "deformed"]
            is_negative = any(kw in current_text_lower for kw in negative_keywords)
            
            if is_negative:
                inputs["text"] = negative_prompt if negative_prompt else current_text
            else:
                inputs["text"] = prompt
    
    return workflow


async def generate_novelai_image(
    prompt: str,
    chat_session_id: str,
    config: dict
) -> str:
    """
    Generate image using NovelAI Image Generation API.
    Uses the official image.novelai.net endpoint.
    """
    api_key = config["api_key"]
    
    # Parse size
    size = config.get("size", "1024x1024")
    try:
        width, height = map(int, size.split("x"))
    except ValueError:
        width, height = 1024, 1024
    
    # Clamp dimensions to NovelAI limits
    width = max(64, min(width, 1024))
    height = max(64, min(height, 1024))
    
    # Model mapping
    model = config.get("model", "nai-diffusion-3") or "nai-diffusion-3"
    
    # Sampler mapping
    sampler = config.get("sampler", "k_euler") or "k_euler"
    valid_samplers = ["k_euler", "k_euler_ancestral", "k_dpmpp_2s_ancestral", 
                      "k_dpmpp_2m", "k_dpmpp_sde", "ddim"]
    if sampler not in valid_samplers:
        sampler = "k_euler"
    
    # Build request
    request_body = {
        "input": prompt,
        "model": model,
        "action": "generate",
        "parameters": {
            "width": width,
            "height": height,
            "scale": config.get("cfg_scale", 7.0),
            "sampler": sampler,
            "steps": config.get("steps", 28),
            "seed": 0,  # Random
            "n_samples": 1,
            "ucPreset": 0,
            "qualityToggle": True,
            "negative_prompt": config.get("negative_prompt", ""),
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://image.novelai.net/ai/generate-image",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/zip",
            },
            json=request_body,
            timeout=180.0
        )
        
        if response.status_code == 401:
            raise Exception("NovelAI authentication failed - check API token")
        elif response.status_code == 402:
            raise Exception("NovelAI insufficient Anlas - check subscription")
        elif response.status_code != 200:
            raise Exception(f"NovelAI API error: {response.status_code} - {response.text[:200]}")
        
        # Response is a ZIP file containing the image
        try:
            zip_data = io.BytesIO(response.content)
            with zipfile.ZipFile(zip_data, 'r') as zip_file:
                # Get the first PNG file
                for name in zip_file.namelist():
                    if name.endswith('.png'):
                        image_data = zip_file.read(name)
                        break
                else:
                    raise Exception("No PNG found in NovelAI response")
        except zipfile.BadZipFile:
            # Some responses might be raw PNG
            if response.content[:8] == b'\x89PNG\r\n\x1a\n':
                image_data = response.content
            else:
                raise Exception("Invalid response format from NovelAI")
    
    # Save image
    filename = f"{generate_id()}.png"
    image_url = await save_image(image_data, chat_session_id, filename)
    return image_url
