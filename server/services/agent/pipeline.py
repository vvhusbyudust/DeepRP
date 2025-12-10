"""
Agent Pipeline - Orchestrates Director, Writer, Paint Director, and TTS Actor

Refactored architecture:
- Each stage uses preset (with macros expanded) as the system message
- Interaction content (user message, outline, etc.) goes in the user message
- Macro expansion handled by build_system_prompt from chat router
"""
import re
import json
from typing import AsyncIterator, Optional
from datetime import datetime

from models import AgentConfig
from utils import load_json, save_json, generate_id
from config import settings
from services.llm import stream_completion, get_completion, get_llm_config
from services.image import generate_image
from services.tts import synthesize_speech
from services.regex import process_for_agent_stage


async def get_preset(preset_id: str) -> Optional[dict]:
    """Load a preset from file."""
    path = settings.data_dir / "presets" / f"{preset_id}.json"
    return await load_json(path)


async def get_character(character_id: str) -> Optional[dict]:
    """Load a character from file."""
    path = settings.data_dir / "characters" / f"{character_id}.json"
    return await load_json(path)


async def get_worldbook(worldbook_id: str) -> Optional[dict]:
    """Load a worldbook from file."""
    path = settings.data_dir / "worldbooks" / f"{worldbook_id}.json"
    return await load_json(path)


async def get_session(session_id: str) -> Optional[dict]:
    """Load a chat session from file."""
    path = settings.data_dir / "chats" / f"{session_id}.json"
    return await load_json(path)


def extract_dialogues(text: str) -> list[dict]:
    """Extract character dialogues from text using multiple formats."""
    dialogues = []
    
    # XML format: <dialogue character="NAME" emotion="EMOTION">text</dialogue>
    xml_pattern = r'<dialogue\s+character="([^"]+)"(?:\s+emotion="([^"]+)")?>(.*?)</dialogue>'
    for m in re.findall(xml_pattern, text, re.DOTALL):
        dialogues.append({"character": m[0], "emotion": m[1] or "neutral", "text": m[2].strip()})
    
    # Japanese quotes: 「text」 after character name (NAME: 「text」 or NAME：「text」)
    jp_pattern = r'([A-Za-z\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]+)[：:]\s*「([^」]+)」'
    for m in re.findall(jp_pattern, text):
        if not any(d["text"] == m[1].strip() for d in dialogues):  # Avoid duplicates
            dialogues.append({"character": m[0], "emotion": "neutral", "text": m[1].strip()})
    
    # Smart/curly quotes: "text" after character name (NAME: "text")
    smart_pattern = r'([A-Za-z\u4e00-\u9fff]+)[：:]\s*"([^"]+)"'
    for m in re.findall(smart_pattern, text):
        if not any(d["text"] == m[1].strip() for d in dialogues):
            dialogues.append({"character": m[0], "emotion": "neutral", "text": m[1].strip()})
    
    # Standard quotes: "text" after character name (NAME: "text")
    quote_pattern = r'([A-Za-z\u4e00-\u9fff]+)[：:]\s*"([^"]+)"'
    for m in re.findall(quote_pattern, text):
        if not any(d["text"] == m[1].strip() for d in dialogues):
            dialogues.append({"character": m[0], "emotion": "neutral", "text": m[1].strip()})
    
    return dialogues


def build_agent_system_prompt(
    preset: Optional[dict],
    character: Optional[dict],
    worldbook: Optional[dict],
    chat_history: list[dict]
) -> str:
    """
    Build system prompt for agent stages by expanding preset macros.
    
    Uses the same macro expansion as the main chat flow.
    The preset's prompt_entries (with macros like {{char}}, {{scenario}}, {{wiBefore}})
    are expanded and combined into a single system prompt.
    """
    # Import here to avoid circular imports
    from routers.chat import build_system_prompt
    
    # Debug logging
    print(f"[Agent] build_agent_system_prompt called")
    print(f"[Agent] preset: {preset.get('name') if preset else None}")
    print(f"[Agent] preset has {len(preset.get('prompt_entries', []))} entries" if preset else "[Agent] No preset")
    print(f"[Agent] character: {character.get('data', {}).get('name') if character else None}")
    print(f"[Agent] worldbook: {worldbook.get('name') if worldbook else None}")
    print(f"[Agent] worldbook has {len(worldbook.get('entries', []))} entries" if worldbook else "[Agent] No worldbook")
    print(f"[Agent] chat_history length: {len(chat_history)}")
    
    # Get expanded prompt using chat's macro system
    pre_prompt, post_prompt, depth_entries = build_system_prompt(
        character=character,
        worldbook=worldbook,
        preset=preset,
        messages=chat_history
    )
    
    print(f"[Agent] pre_prompt length: {len(pre_prompt) if pre_prompt else 0}")
    print(f"[Agent] post_prompt length: {len(post_prompt) if post_prompt else 0}")
    print(f"[Agent] depth_entries: {len(depth_entries)}")
    
    # Check if macros were NOT expanded (still present in output)
    combined = f"{pre_prompt}\n\n{post_prompt}" if pre_prompt and post_prompt else (pre_prompt or post_prompt or "")
    if "{{" in combined:
        import re
        unexpanded = re.findall(r'\{\{[^}]+\}\}', combined)
        print(f"[Agent] WARNING: Unexpanded macros found: {unexpanded[:5]}")
    
    # Combine pre and post prompts
    if pre_prompt and post_prompt:
        return f"{pre_prompt}\n\n{post_prompt}"
    return pre_prompt or post_prompt or ""



async def run_director(
    user_message: str,
    chat_history: list[dict],
    character: Optional[dict],
    worldbook: Optional[dict],
    config: AgentConfig
) -> AsyncIterator[tuple[str, Optional[dict]]]:
    """
    Run the Director agent to generate a scene outline (streaming).
    
    Input: Preset (expanded with character, worldbook, context) + User Message
    Output: Yields (chunk, None) during streaming, then (full_outline, request_structure) at end
    """
    llm_config = await get_llm_config(config.director_llm_config_id)
    if not llm_config:
        raise Exception("Director LLM config not found")
    
    preset = await get_preset(config.director_preset_id) if config.director_preset_id else None
    
    # System message = expanded preset
    system_prompt = build_agent_system_prompt(preset, character, worldbook, chat_history)
    
    # Fallback if no preset configured
    if not system_prompt:
        system_prompt = """You are a scene director. Create a brief outline for the next scene including:
1. Scene setting/atmosphere changes
2. Character actions and movements
3. Key emotional beats
4. Any important events or reveals

Provide a concise scene outline (2-3 paragraphs) that a writer can use to craft the response."""
    
    # User message = interaction content
    # Build messages: system prompt → chat history → user message
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add chat history between system prompt and current user message
    for msg in chat_history:
        messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    
    # Add current user message
    messages.append({"role": "user", "content": user_message})
    
    params = {}
    if preset:
        params = {
            "temperature": preset.get("temperature", 0.7),
            "max_tokens": preset.get("max_tokens", 500),
        }
    
    # Build request structure for logging
    request_structure = {
        "messages": messages,
        "params": params,
        "llm_config": {
            "name": llm_config.get("name", "unknown"),
            "model": llm_config.get("default_model", "unknown"),
            "base_url": llm_config.get("base_url", "")
        },
        "preset_name": preset.get("name") if preset else None
    }
    
    # Stream the outline
    full_outline = ""
    async for chunk in stream_completion(messages, llm_config, params):
        full_outline += chunk
        yield (chunk, None)  # Yield chunk during streaming
    
    # Yield final result with request structure
    yield (full_outline, request_structure)


async def run_writer(
    outline: str,
    chat_history: list[dict],
    character: Optional[dict],
    worldbook: Optional[dict],
    config: AgentConfig,
    request_info: Optional[dict] = None
) -> AsyncIterator[str]:
    """
    Run the Writer agent to generate the narrative.
    
    Input: Preset (expanded with character, worldbook, context) + Director's Outline
    Output: Narrative response (streaming)
    
    If request_info dict is provided, it will be populated with the full request structure.
    """
    llm_config = await get_llm_config(config.writer_llm_config_id)
    if not llm_config:
        raise Exception("Writer LLM config not found")
    
    preset = await get_preset(config.writer_preset_id) if config.writer_preset_id else None
    
    # System message = expanded preset
    system_prompt = build_agent_system_prompt(preset, character, worldbook, chat_history)
    
    # Fallback if no preset configured
    char_name = character.get("data", {}).get("name", "Assistant") if character else "Assistant"
    if not system_prompt:
        system_prompt = f"""You are a creative writer crafting an immersive roleplay response as {char_name}.
Be descriptive and immersive. Write dialogue naturally."""
    
    # User message = Director's outline
    # Build messages: system prompt → chat history → outline
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add chat history for context
    for msg in chat_history:
        messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    
    # Add director's outline as the current task
    messages.append({"role": "user", "content": f"Based on this scene outline, write the narrative:\n\n{outline}"})
    
    params = {}
    if preset:
        params = {
            "temperature": preset.get("temperature", 0.9),
            "max_tokens": preset.get("max_tokens", 2048),
            "top_p": preset.get("top_p", 0.95),
        }
    
    # Capture request structure for logging
    if request_info is not None:
        request_info["messages"] = messages
        request_info["params"] = params
        request_info["llm_config"] = {
            "name": llm_config.get("name", "unknown"),
            "model": llm_config.get("default_model", "unknown"),
            "base_url": llm_config.get("base_url", "")
        }
        request_info["preset_name"] = preset.get("name") if preset else None
    
    async for chunk in stream_completion(messages, llm_config, params):
        yield chunk


async def run_paint_director(
    outline: str,
    chat_history: list[dict],
    character: Optional[dict],
    worldbook: Optional[dict],
    session_id: str,
    config: AgentConfig
) -> AsyncIterator[tuple[Optional[str], Optional[str], bool]]:
    """
    Run the Paint Director agent to generate an image (streaming prompt generation).
    
    Input: Preset (expanded with character, worldbook, context) + Director's Outline
    Output: Yields:
        - (chunk, None, False) during streaming prompt generation
        - (image_url, image_prompt, True) at end
    
    Flow:
    1. Paint Director (LLM) generates an image prompt from the scene outline (streaming)
    2. Painter (image backend) generates the actual image from the prompt
    """
    if not config.painter_llm_config_id:
        print("Paint Director ERROR: No painter_llm_config_id configured")
        yield (None, "ERROR: Paint Director LLM not configured in Agent Settings", True)
        return
    
    if not config.image_config_id:
        print("Paint Director ERROR: No image_config_id configured")
        yield (None, "ERROR: Image API not configured in Agent Settings", True)
        return
    
    llm_config = await get_llm_config(config.painter_llm_config_id)
    if not llm_config:
        print(f"Paint Director ERROR: LLM config '{config.painter_llm_config_id}' not found in database")
        yield (None, f"ERROR: Paint Director LLM config not found", True)
        return
    
    preset = await get_preset(config.painter_preset_id) if config.painter_preset_id else None
    
    # System message = expanded preset
    system_prompt = build_agent_system_prompt(preset, character, worldbook, chat_history)
    
    # Fallback if no preset configured
    if not system_prompt:
        system_prompt = """You are an image prompt director. Convert scene descriptions into detailed image generation prompts.
Focus on visual elements: setting, lighting, character appearances, mood, and atmosphere.
Keep it under 200 words. Output ONLY the prompt, no explanations or preamble."""
    
    # User message = Director's outline
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": outline}
    ]
    
    params = {"temperature": 0.7, "max_tokens": 250}
    if preset:
        params["temperature"] = preset.get("temperature", 0.7)
    
    # Stream the image prompt generation
    image_prompt = ""
    async for chunk in stream_completion(messages, llm_config, params):
        image_prompt += chunk
        yield (chunk, None, False)  # Streaming chunk
    
    # Apply regex processing to paint_director output
    preset_regex_ids = preset.get("regex_script_ids", []) if preset else []
    image_prompt = await process_for_agent_stage(
        image_prompt,
        agent_stage="paint_director",
        script_ids=preset_regex_ids if preset_regex_ids else None,
        target="prompt"
    )
    
    # Generate image from the complete prompt
    try:
        image_url = await generate_image(
            prompt=image_prompt.strip(),
            chat_session_id=session_id,
            config_id=config.image_config_id
        )
        yield (image_url, image_prompt.strip(), True)
    except Exception as e:
        print(f"Paint error: {e}")
        yield (None, image_prompt.strip(), True)


async def run_tts_for_dialogues(
    dialogues: list[dict],
    session_id: str,
    config: AgentConfig
) -> list[dict]:
    """
    Generate TTS for extracted dialogues.
    
    Input: Dialogues extracted from Writer's output
    Output: List of {character, emotion, audio_url}
    """
    if not config.tts_config_id or not dialogues:
        return []
    
    results = []
    for dialogue in dialogues:
        try:
            audio_url = await synthesize_speech(
                text=dialogue["text"],
                chat_session_id=session_id,
                character_name=dialogue["character"],
                config_id=config.tts_config_id
            )
            results.append({
                "character": dialogue["character"],
                "emotion": dialogue["emotion"],
                "audio_url": audio_url
            })
        except Exception as e:
            print(f"TTS error for {dialogue['character']}: {e}")
    
    return results


async def run_agent_pipeline(
    user_message: str,
    session_id: str,
    character_id: Optional[str],
    worldbook_ids: list[str],  # Changed from worldbook_id (singular) to worldbook_ids (list)
    config: AgentConfig
) -> AsyncIterator[dict]:
    """
    Run the full agent pipeline with logging.
    
    Pipeline Flow:
    1. Director: Preset + User Message → Scene Outline
    2. Writer: Preset + Outline → Narrative (streaming)
    3. Paint Director: Preset + Outline → Image Prompt
    4. Painter: Image Prompt → Generated Image
    5. TTS Actor: Writer's Output → Dialogue Audio
    
    Yields events:
    - {"type": "run_started", "run_id": "..."}
    - {"type": "stage", "stage": "director|writer|paint_director|tts"}
    - {"type": "outline", "content": "..."}
    - {"type": "content", "content": "..."}
    - {"type": "image", "url": "...", "prompt": "..."}
    - {"type": "audio", "data": [...]}
    - {"type": "stage_complete", "stage": "...", "duration_ms": ...}
    """
    import time
    from services.agent.logging import (
        create_agent_run, start_stage_log, complete_stage_log, 
        skip_stage_log, complete_agent_run
    )
    
    # Upfront validation - check required LLM configs are set
    missing_configs = []
    if not config.director_llm_config_id:
        missing_configs.append("Director LLM Config")
    if not config.writer_llm_config_id:
        missing_configs.append("Writer LLM Config")
    
    if missing_configs:
        error_msg = f"Agent configuration incomplete. Missing: {', '.join(missing_configs)}. Please configure these in the Agent settings tab."
        yield {"type": "error", "error": error_msg}
        return
    
    pipeline_start = time.time()
    
    # Create agent run record
    run_id = await create_agent_run(session_id, user_message, character_id)
    yield {"type": "run_started", "run_id": run_id}
    
    # Load context
    session = await get_session(session_id)
    chat_history = session.get("messages", []) if session else []
    
    character = await get_character(character_id) if character_id else None
    
    # Load worldbooks using the same function as chat flow
    from routers.chat import load_worldbooks
    worldbook = await load_worldbooks(worldbook_ids) if worldbook_ids else None
    
    print(f"[Agent] Loaded context: character={character.get('data', {}).get('name') if character else None}, worldbook={worldbook.get('name') if worldbook else None}")
    
    outline = ""
    full_response = ""
    image_url = None
    image_prompt = None
    audio_results = []
    
    try:
        # Stage 1: Director (streaming)
        yield {"type": "stage", "stage": "director"}
        stage_start = time.time()
        
        # Stream director output to frontend
        outline = ""
        director_request = None
        async for chunk, req_struct in run_director(user_message, chat_history, character, worldbook, config):
            if req_struct is not None:
                # Final yield with request structure
                director_request = req_struct
            else:
                # Streaming chunk
                outline += chunk
                yield {"type": "director_chunk", "content": chunk}
        
        # Log full request structure as JSON
        stage_id = await start_stage_log(
            run_id, "director", json.dumps(director_request, ensure_ascii=False, indent=2) if director_request else user_message,
            config.director_llm_config_id, config.director_preset_id
        )
        
        stage_duration = int((time.time() - stage_start) * 1000)
        await complete_stage_log(stage_id, outline, stage_duration)
        yield {"type": "outline", "content": outline}
        yield {"type": "stage_complete", "stage": "director", "duration_ms": stage_duration}
        
        # Apply regex processing to director output before passing to writer
        # Get preset's regex_script_ids if available
        director_preset = await get_preset(config.director_preset_id) if config.director_preset_id else None
        preset_regex_ids = director_preset.get("regex_script_ids", []) if director_preset else []
        
        outline = await process_for_agent_stage(
            outline, 
            agent_stage="director",
            script_ids=preset_regex_ids if preset_regex_ids else None,
            target="prompt"  # Processing for next agent's prompt
        )
        
        # Stages 2 & 3: Writer and Paint Director (PARALLEL)
        # Both stages run concurrently since they only need the Director's outline
        
        import asyncio
        
        # Event queue for interleaved streaming
        event_queue = asyncio.Queue()
        
        # Completion tracking
        writer_done = asyncio.Event()
        paint_done = asyncio.Event()
        
        # Results storage
        parallel_results = {
            "writer_response": "",
            "writer_request": {},
            "writer_error": None,
            "image_url": None,
            "image_prompt": "",
            "paint_error": None,
        }
        
        async def writer_task():
            """Run Writer stage and push events to queue."""
            nonlocal full_response
            try:
                writer_request = {}
                async for chunk in run_writer(outline, chat_history, character, worldbook, config, writer_request):
                    parallel_results["writer_response"] += chunk
                    await event_queue.put({"type": "content", "content": chunk})
                parallel_results["writer_request"] = writer_request
            except Exception as e:
                parallel_results["writer_error"] = str(e)
                print(f"Writer error: {e}")
            finally:
                writer_done.set()
        
        async def paint_task():
            """Run Paint Director stage and push events to queue."""
            try:
                if not getattr(config, "enable_paint", True):
                    return
                    
                async for chunk_or_url, prompt_or_none, is_final in run_paint_director(
                    outline, chat_history, character, worldbook, session_id, config
                ):
                    if is_final:
                        parallel_results["image_url"] = chunk_or_url
                        parallel_results["image_prompt"] = prompt_or_none or ""
                    else:
                        await event_queue.put({"type": "paint_chunk", "content": chunk_or_url})
            except Exception as e:
                parallel_results["paint_error"] = str(e)
                print(f"Paint Director error: {e}")
            finally:
                paint_done.set()
        
        # Signal parallel stage start
        yield {"type": "stage", "stage": "writer"}
        if getattr(config, "enable_paint", True):
            yield {"type": "stage", "stage": "paint_director"}
        
        parallel_start = time.time()
        
        # Start both tasks concurrently
        writer_task_handle = asyncio.create_task(writer_task())
        paint_task_handle = asyncio.create_task(paint_task())
        
        # Log stage starts
        writer_stage_id = await start_stage_log(
            run_id, "writer", outline,
            config.writer_llm_config_id, config.writer_preset_id
        )
        paint_stage_id = None
        if getattr(config, "enable_paint", True):
            paint_stage_id = await start_stage_log(
                run_id, "paint_director", outline,
                config.painter_llm_config_id, config.painter_preset_id
            )
        
        # Yield events as they arrive (interleaved)
        while not (writer_done.is_set() and paint_done.is_set()):
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=0.05)
                yield event
            except asyncio.TimeoutError:
                continue
        
        # Drain any remaining events in queue
        while not event_queue.empty():
            event = event_queue.get_nowait()
            yield event
        
        # Wait for both tasks to fully complete
        await asyncio.gather(writer_task_handle, paint_task_handle, return_exceptions=True)
        
        # Update full_response from parallel results
        full_response = parallel_results["writer_response"]
        image_url = parallel_results["image_url"]
        image_prompt = parallel_results["image_prompt"]
        
        parallel_duration = int((time.time() - parallel_start) * 1000)
        
        # Log Writer completion
        if parallel_results["writer_error"]:
            await complete_stage_log(
                writer_stage_id, parallel_results["writer_error"], parallel_duration,
                status="error"
            )
            yield {"type": "error", "stage": "writer", "message": parallel_results["writer_error"]}
        else:
            # Update stage log with request structure
            writer_request_json = json.dumps(parallel_results["writer_request"], ensure_ascii=False, indent=2)
            await complete_stage_log(writer_stage_id, full_response, parallel_duration)
        yield {"type": "stage_complete", "stage": "writer", "duration_ms": parallel_duration}
        
        # Log Paint Director completion
        if getattr(config, "enable_paint", True):
            if parallel_results["paint_error"]:
                await complete_stage_log(
                    paint_stage_id, parallel_results["paint_error"], parallel_duration,
                    status="error"
                )
                yield {"type": "error", "stage": "paint_director", "message": parallel_results["paint_error"]}
            else:
                await complete_stage_log(
                    paint_stage_id, image_prompt or "", parallel_duration,
                    status="success" if image_url else "partial"
                )
            
            if image_url:
                yield {"type": "image", "url": image_url, "prompt": image_prompt}
            yield {"type": "stage_complete", "stage": "paint_director", "duration_ms": parallel_duration}
        else:
            await skip_stage_log(run_id, "paint_director", "disabled")
            yield {"type": "stage_skipped", "stage": "paint_director", "reason": "disabled"}
        
        # Stage 4: TTS for dialogues (if enabled)
        if getattr(config, "enable_tts", True):
            yield {"type": "stage", "stage": "tts"}
            stage_start = time.time()
            stage_id = await start_stage_log(run_id, "tts", full_response)
            
            dialogues = extract_dialogues(full_response)
            audio_results = await run_tts_for_dialogues(dialogues, session_id, config)
            
            stage_duration = int((time.time() - stage_start) * 1000)
            await complete_stage_log(
                stage_id, str(len(audio_results)) + " audio files", stage_duration
            )
            
            if audio_results:
                yield {"type": "audio", "data": audio_results}
            yield {"type": "stage_complete", "stage": "tts", "duration_ms": stage_duration}
        else:
            await skip_stage_log(run_id, "tts", "disabled")
            yield {"type": "stage_skipped", "stage": "tts", "reason": "disabled"}
        
        # Complete the run
        total_duration = int((time.time() - pipeline_start) * 1000)
        await complete_agent_run(
            run_id, "success", total_duration,
            director_output=outline,
            writer_output=full_response,
            image_url=image_url,
            image_prompt=image_prompt,
            audio_data=audio_results if audio_results else None
        )
        yield {"type": "run_complete", "run_id": run_id, "duration_ms": total_duration}
        
    except Exception as e:
        # Log error and update run status
        total_duration = int((time.time() - pipeline_start) * 1000)
        await complete_agent_run(
            run_id, "error", total_duration,
            director_output=outline,
            writer_output=full_response,
            error_message=str(e)
        )
        yield {"type": "error", "message": str(e)}
        raise
    
    # Apply regex processing for display
    from services.regex import process_for_display
    processed_response = await process_for_display(full_response, message_role="assistant", message_depth=0)
    
    # Save message to session
    if session:
        # Add user message
        session["messages"].append({
            "id": generate_id(),
            "role": "user",
            "content": user_message,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Add assistant message (with processed content)
        session["messages"].append({
            "id": generate_id(),
            "role": "assistant",
            "content": processed_response,  # Use regex-processed version
            "timestamp": datetime.utcnow().isoformat(),
            "image_url": image_url,
            "image_prompt": image_prompt,
            "audio_data": audio_results if audio_results else None,
        })
        
        session["updated_at"] = datetime.utcnow().isoformat()
        await save_json(settings.data_dir / "chats" / f"{session_id}.json", session)
    
    # Send processed_content in the "content" event for frontend to use
    yield {"type": "processed_content", "content": processed_response}
