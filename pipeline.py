import os
import json
import time
import whisper
from groq import Groq
from dotenv import load_dotenv
from prompts import REFINEMENT_SYSTEM_PROMPT, MINUTES_SYSTEM_PROMPT

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Use two distinct models: LLM #1 for transcript refinement, LLM #2 for structured meeting minutes.
REFINEMENT_MODEL = "qwen/qwen3.8-27b"
MINUTES_MODEL    = "openai/gpt-oss-120b"


def call_with_retry(model, system_prompt, user_prompt, temperature=0.1, max_retries=4, response_format=None):
    """Call Groq API with automatic retry on rate limits (429) and transient connection errors."""
    for attempt in range(max_retries):
        try:
            kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                "temperature": temperature,
                "max_tokens": 4096,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content.strip()

        except Exception as e:
            err = str(e)
            err_lower = err.lower()
            is_rate_limit = "429" in err or "rate_limit" in err_lower
            is_conn_error = any(term in err_lower for term in [
                "connection error", "connecterror", "connection reset", 
                "socket", "timeout", "nodename nor servname", "servfail", "api_connection_error"
            ])

            if (is_rate_limit or is_conn_error) and attempt < max_retries - 1:
                wait = (30 * (attempt + 1)) if is_rate_limit else (4 * (attempt + 1))
                reason = "Rate limit hit" if is_rate_limit else "Transient network/connection error"
                print(f"{reason}. Retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise

    raise ValueError("Max retries exceeded due to rate limiting or connection errors. Please try again in a moment.")


# Runs Whisper locally to avoid API rate limits and keep audio on device.
def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio to raw text using Whisper (runs locally, no rate limits)."""
    supported = {".mp3", ".mp4", ".wav", ".m4a", ".ogg", ".flac", ".webm"}
    ext = os.path.splitext(audio_path)[-1].lower()

    if ext not in supported:
        raise ValueError(f"Unsupported file type '{ext}'. Supported: {', '.join(supported)}")

    if os.path.getsize(audio_path) == 0:
        raise ValueError("The uploaded audio file is empty.")

    try:
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        transcript = result["text"].strip()
    except Exception as e:
        raise ValueError(f"Could not process audio file: {str(e)}")

    if not transcript:
        raise ValueError("No speech detected in the audio file.")

    return transcript


def refine_transcript(raw_transcript: str) -> str:
    """Use LLM #1 (qwen/qwen3.8-27b) to fix domain-specific transcription errors."""
    return call_with_retry(
        model=REFINEMENT_MODEL,
        system_prompt=REFINEMENT_SYSTEM_PROMPT,
        user_prompt=f"Refine this transcript:\n\n{raw_transcript}",
        temperature=0.1,
    )


def generate_meeting_record(refined_transcript: str) -> dict:
    """Use LLM #2 (openai/gpt-oss-120b) to produce structured meeting documentation."""
    raw_output = call_with_retry(
        model=MINUTES_MODEL,
        system_prompt=MINUTES_SYSTEM_PROMPT,
        user_prompt=f"Generate meeting documentation from this transcript:\n\n{refined_transcript}",
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    cleaned = raw_output.strip()
    if "```" in cleaned:
        parts = cleaned.split("```")
        if len(parts) >= 3:
            cleaned = parts[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            data.setdefault("summary", "")
            data.setdefault("minutes", [])
            data.setdefault("decisions", [])
            data.setdefault("action_items", [])
            return data
        return {
            "summary": str(data),
            "minutes": [],
            "decisions": [],
            "action_items": []
        }
    except json.JSONDecodeError:
        return {
            "summary": raw_output,
            "minutes": [],
            "decisions": [],
            "action_items": []
        }


def run_pipeline(audio_path: str) -> dict:
    """Run all 3 stages in order. Returns dict with all outputs and any stage errors."""
    errors = {}

    print("Stage 1: Transcribing audio with Whisper (local)...")
    raw_transcript = transcribe_audio(audio_path)

    refined_transcript = None
    print("Stage 2: Refining transcript with LLM #1...")
    try:
        refined_transcript = refine_transcript(raw_transcript)
    except Exception as e:
        print(f"Error in Stage 2 (refinement): {e}")
        errors["refinement"] = str(e)

    meeting_record = None
    print("Stage 3: Generating meeting record with LLM #2...")
    try:
        # Fallback to raw transcript if Stage 2 refinement fails.
        source_text = refined_transcript if refined_transcript else raw_transcript
        meeting_record = generate_meeting_record(source_text)
    except Exception as e:
        print(f"Error in Stage 3 (meeting record): {e}")
        errors["meeting_record"] = str(e)

    return {
        "raw_transcript":     raw_transcript,
        "refined_transcript": refined_transcript,
        "meeting_record":     meeting_record,
        "errors":             errors,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <audio_file>")
        sys.exit(1)

    results = run_pipeline(sys.argv[1])

    print("\n=== RAW TRANSCRIPT ===")
    print(results["raw_transcript"])

    print("\n=== REFINED TRANSCRIPT ===")
    print(results["refined_transcript"])

    print("\n=== MEETING RECORD ===")
    print(json.dumps(results["meeting_record"], indent=2))
