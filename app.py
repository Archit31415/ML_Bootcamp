import os
import json
import tempfile
import gradio as gr
from pipeline import run_pipeline


def format_meeting_record_text(record: dict) -> str:
    """Convert meeting record dict to human-readable text supporting new prompt schemas."""
    lines = []

    lines.append("MEETING SUMMARY")
    lines.append("=" * 50)
    lines.append(record.get("summary", "N/A"))

    lines.append("\nMEETING MINUTES")
    lines.append("=" * 50)
    minutes = record.get("minutes", [])
    if minutes:
        for i, item in enumerate(minutes, 1):
            if isinstance(item, dict):
                topic      = item.get("topic", "Topic")
                raised_by  = item.get("raised_by") or "unspecified"
                discussion = item.get("discussion", "")
                outcome    = item.get("outcome", "")

                header = f"  {i}. {topic}"
                if raised_by and raised_by.lower() != "unspecified":
                    header += f" (Raised by: {raised_by})"
                lines.append(header)

                if discussion:
                    lines.append(f"     Discussion: {discussion}")
                if outcome:
                    lines.append(f"     Outcome: {outcome}")
            else:
                lines.append(f"  • {item}")
    else:
        lines.append("  No minutes recorded.")

    lines.append("\nKEY DECISIONS")
    lines.append("=" * 50)
    decisions = record.get("decisions", [])
    if decisions:
        for i, d in enumerate(decisions, 1):
            if isinstance(d, dict):
                dec_text  = d.get("decision", "")
                dec_type  = d.get("decision_type", "")
                made_by   = d.get("made_by", "")
                context   = d.get("context", "")

                header = f"  {i}. {dec_text}"
                meta = []
                if dec_type and dec_type.lower() != "unspecified":
                    meta.append(f"Type: {dec_type}")
                if made_by and made_by.lower() != "unspecified":
                    meta.append(f"Made by: {made_by}")
                if meta:
                    header += f" [{', '.join(meta)}]"
                lines.append(header)

                if context:
                    lines.append(f"     Context: {context}")
            else:
                lines.append(f"  {i}. {d}")
    else:
        lines.append("  No explicit decisions recorded.")

    lines.append("\nACTION ITEMS")
    lines.append("=" * 50)
    tasks = record.get("action_items", [])
    if tasks:
        for i, t in enumerate(tasks, 1):
            if isinstance(t, dict):
                task_text  = t.get("task", "")
                owner      = t.get("owner") or "unspecified"
                deadline   = t.get("deadline") or "unspecified"
                depends_on = t.get("depends_on")

                lines.append(f"  {i}. {task_text}")
                meta_str = f"     Owner: {owner} | Deadline: {deadline}"
                if depends_on:
                    meta_str += f" | Depends on: {depends_on}"
                lines.append(meta_str)
            else:
                lines.append(f"  {i}. {t}")
    else:
        lines.append("  No action items assigned.")

    return "\n".join(lines)


def save_outputs(raw=None, refined=None, record=None):
    """Save available outputs to temp files and return paths for download."""
    tmp = tempfile.mkdtemp()

    raw_path     = None
    refined_path = None
    minutes_path = None
    json_path    = None

    if raw:
        raw_path = os.path.join(tmp, "raw_transcript.txt")
        with open(raw_path, "w") as f:
            f.write(raw)

    if refined:
        refined_path = os.path.join(tmp, "refined_transcript.txt")
        with open(refined_path, "w") as f:
            f.write(refined)

    if record:
        minutes_path = os.path.join(tmp, "meeting_minutes.txt")
        with open(minutes_path, "w") as f:
            f.write(format_meeting_record_text(record))

        json_path = os.path.join(tmp, "meeting_record.json")
        with open(json_path, "w") as f:
            json.dump(record, f, indent=2)

    return raw_path, refined_path, minutes_path, json_path


def process_audio(audio_file):
    if audio_file is None:
        return (
            "❌ No file uploaded.",
            "", "", "",
            None, None, None, None
        )

    try:
        results = run_pipeline(audio_file)
    except ValueError as e:
        return (f"❌ {e}", "", "", "", None, None, None, None)
    except Exception as e:
        return (f"❌ Unexpected error: {e}", "", "", "", None, None, None, None)

    raw     = results.get("raw_transcript")
    refined = results.get("refined_transcript")
    record  = results.get("meeting_record")
    errors  = results.get("errors", {})

    raw_path, refined_path, minutes_path, json_path = save_outputs(raw, refined, record)

    if "refinement" in errors:
        err_msg = errors["refinement"]
        return (
            f"⚠️ Audio transcribed, but refinement step failed: {err_msg}",
            raw or "",
            f"❌ Refinement step failed: {err_msg}\n\nRaw transcript is displayed above and available for download.",
            "❌ Skipped meeting record generation because refinement step failed.",
            raw_path,
            None,
            None,
            None,
        )

    if "meeting_record" in errors:
        err_msg = errors["meeting_record"]
        return (
            f"⚠️ Audio transcribed and refined, but meeting record generation failed: {err_msg}",
            raw or "",
            refined or "",
            f"❌ Meeting record generation failed: {err_msg}\n\nTranscripts are displayed above and available for download.",
            raw_path,
            refined_path,
            None,
            None,
        )

    readable = format_meeting_record_text(record) if record else ""

    return (
        "✅ Processing complete!",
        raw or "",
        refined or "",
        readable,
        raw_path,
        refined_path,
        minutes_path,
        json_path,
    )


custom_css = r"""
:root {
    --bg: #07090d;
    --surface: rgba(255,255,255,.055);
    --surface-2: rgba(255,255,255,.075);
    --surface-3: rgba(255,255,255,.095);
    --line: rgba(255,255,255,.085);
    --line-strong: rgba(255,255,255,.13);
    --text: #f5f5f7;
    --text-2: rgba(245,245,247,.68);
    --text-3: rgba(245,245,247,.43);
    --blue: #8ab4ff;
    --violet: #b9a2ff;
    --green: #8ee7b5;
    --r-xl: 26px;
    --r-lg: 20px;
    --r-md: 16px;
    --ease: cubic-bezier(.22,1,.36,1);
}

html, body { background: var(--bg) !important; }
body { overflow-x: hidden !important; }

.gradio-container {
    max-width: none !important;
    min-height: 100vh !important;
    padding: 0 !important;
    color: var(--text) !important;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Arial, sans-serif !important;
    background:
        radial-gradient(900px 520px at 12% -5%, rgba(94,139,255,.11), transparent 64%),
        radial-gradient(800px 520px at 91% 5%, rgba(173,132,255,.085), transparent 64%),
        linear-gradient(180deg, #0a0c11 0%, #07090d 52%, #080a0f 100%) !important;
}

.gradio-container::after {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    opacity: .22;
    background-image: radial-gradient(rgba(255,255,255,.11) .45px, transparent .45px);
    background-size: 4px 4px;
    mask-image: linear-gradient(to bottom, black, transparent 72%);
}

#app-shell {
    position: relative;
    z-index: 1;
    width: min(1240px, calc(100% - 96px));
    margin: 0 auto;
    padding: 34px 0 64px;
}

#topbar {
    height: 42px;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    margin-bottom: 46px !important;
}

.brand {
    display: flex;
    align-items: center;
    gap: 10px;
    color: rgba(255,255,255,.92);
    font-size: 14px;
    font-weight: 600;
    letter-spacing: -.015em;
}

.brand-mark {
    width: 28px;
    height: 28px;
    display: grid;
    place-items: center;
    border-radius: 9px;
    color: #fff;
    background: linear-gradient(145deg, rgba(139,180,255,.48), rgba(174,142,255,.32));
    border: 1px solid rgba(255,255,255,.13);
    box-shadow: inset 0 1px rgba(255,255,255,.17), 0 7px 22px rgba(90,110,200,.18);
}

.product-note {
    color: var(--text-3);
    font-size: 12px;
    font-weight: 500;
    letter-spacing: .01em;
}

#hero { margin-bottom: 30px !important; }

.eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    margin-bottom: 13px;
    color: rgba(225,231,242,.54);
    font-size: 10px;
    font-weight: 650;
    letter-spacing: .14em;
    text-transform: uppercase;
}

.eyebrow::before {
    content: "";
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 13px rgba(142,231,181,.7);
}

#hero h1 {
    margin: 0 !important;
    max-width: 800px;
    color: #f5f5f7 !important;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif !important;
    font-size: clamp(40px, 4.25vw, 58px) !important;
    font-weight: 650 !important;
    line-height: 1.02 !important;
    letter-spacing: -.055em !important;
}

#hero h1::after {
    content: ".";
    color: #9dbaff;
}

#hero p {
    max-width: 650px;
    margin: 17px 0 0 !important;
    color: var(--text-2) !important;
    font-size: 15px !important;
    line-height: 1.62 !important;
    letter-spacing: -.012em;
}

#workspace {
    position: relative;
    padding: 18px !important;
    border-radius: var(--r-xl) !important;
    border: 1px solid var(--line) !important;
    background: rgba(255,255,255,.035) !important;
    backdrop-filter: blur(28px) saturate(125%) !important;
    -webkit-backdrop-filter: blur(28px) saturate(125%) !important;
    box-shadow:
        inset 0 1px rgba(255,255,255,.045),
        0 26px 80px rgba(0,0,0,.20) !important;
}

#workspace::before {
    content: "";
    position: absolute;
    left: 22px;
    right: 22px;
    top: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,.12), transparent);
}

#control_row {
    align-items: stretch !important;
    gap: 12px !important;
}

#audio_input {
    min-height: 138px !important;
    border-radius: var(--r-lg) !important;
    border: 1px solid var(--line) !important;
    background: linear-gradient(145deg, rgba(255,255,255,.065), rgba(255,255,255,.028)) !important;
    box-shadow: inset 0 1px rgba(255,255,255,.035) !important;
    overflow: hidden !important;
    transition: border-color .35s var(--ease), background .35s var(--ease), transform .35s var(--ease) !important;
}

#audio_input:hover {
    transform: translateY(-1px);
    border-color: var(--line-strong) !important;
    background: linear-gradient(145deg, rgba(255,255,255,.078), rgba(255,255,255,.032)) !important;
}

#audio_input .wrap,
#audio_input .upload-container,
#audio_input .dropzone {
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
    height: 100% !important;
    border: 0 !important;
    border-radius: inherit !important;
    background: transparent !important;
    box-shadow: none !important;
}

#audio_input .dropzone {
    min-height: 138px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    overflow: hidden !important;
}

#audio_input label {
    margin: 0 !important;
    padding: 15px 16px !important;
    border: 0 !important;
    border-radius: inherit !important;
    background: transparent !important;
}

#audio_input .upload-icon,
#audio_input .audio-container,
#audio_input .recording-container,
#audio_input .audio-editor {
    border-radius: 14px !important;
    border-color: rgba(255,255,255,.07) !important;
    background: #0b0e14 !important;
    box-shadow: none !important;
}

#audio_input button,
#audio_input .icon-button {
    border-radius: 12px !important;
}

#run_btn {
    align-self: center !important;
    flex: 0 0 auto !important;
    width: 166px !important;
    min-width: 166px !important;
    max-width: 166px !important;
    height: 48px !important;
    min-height: 48px !important;
    padding: 0 18px !important;
    border-radius: 14px !important;
    border: 1px solid rgba(171,196,255,.24) !important;
    background: linear-gradient(135deg, rgba(116,157,255,.25), rgba(163,131,255,.19)) !important;
    color: #f8f9ff !important;
    font-family: inherit !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    letter-spacing: -.01em !important;
    box-shadow: inset 0 1px rgba(255,255,255,.11), 0 10px 26px rgba(65,84,155,.15) !important;
    transition: transform .28s var(--ease), border-color .28s var(--ease), box-shadow .28s var(--ease), filter .28s var(--ease) !important;
}

#run_btn:hover {
    transform: translateY(-2px);
    border-color: rgba(205,218,255,.38) !important;
    box-shadow: inset 0 1px rgba(255,255,255,.14), 0 14px 32px rgba(71,91,170,.22) !important;
    filter: brightness(1.06);
}

#run_btn:active { transform: translateY(0) scale(.985); }
#run_btn[disabled] { opacity: .48 !important; transform: none !important; }

#status_box {
    margin: 12px 0 !important;
    border-radius: 14px !important;
    border: 1px solid var(--line) !important;
    background: rgba(255,255,255,.025) !important;
    overflow: hidden !important;
}

#status_box textarea,
#status_box input {
    min-height: 44px !important;
    background: transparent !important;
    border: 0 !important;
    color: rgba(245,245,247,.78) !important;
    font-family: inherit !important;
    font-size: 12px !important;
    font-weight: 500 !important;
}

#output_tabs {
    border-radius: 20px !important;
    border: 1px solid var(--line) !important;
    background: rgba(0,0,0,.10) !important;
    overflow: hidden !important;
    padding: 7px !important;
}

#output_tabs .tab-nav {
    display: flex !important;
    gap: 3px !important;
    padding: 3px !important;
    margin-bottom: 3px !important;
    border: 0 !important;
    border-radius: 13px !important;
    background: rgba(255,255,255,.025) !important;
}

#output_tabs .tab-nav button {
    position: relative;
    border: 1px solid transparent !important;
    border-radius: 10px !important;
    padding: 9px 14px !important;
    color: rgba(235,238,246,.47) !important;
    background: transparent !important;
    font-family: inherit !important;
    font-size: 12px !important;
    font-weight: 560 !important;
    letter-spacing: -.005em !important;
    transition: color .25s var(--ease), background .25s var(--ease), border-color .25s var(--ease), transform .25s var(--ease) !important;
}

#output_tabs .tab-nav button:hover {
    color: rgba(245,245,247,.82) !important;
    background: rgba(255,255,255,.045) !important;
}

#output_tabs .tab-nav button.selected {
    color: #f5f5f7 !important;
    background: rgba(255,255,255,.085) !important;
    border-color: rgba(255,255,255,.075) !important;
    box-shadow: inset 0 1px rgba(255,255,255,.055), 0 5px 18px rgba(0,0,0,.12) !important;
}

.output-panel { padding: 15px 7px 7px !important; }

.output-panel textarea,
.output-panel input,
textarea[data-testid="textbox"],
input[data-testid="textbox"] {
    border: 1px solid rgba(255,255,255,.075) !important;
    border-radius: 15px !important;
    background: #0b0e14 !important;
    color: rgba(246,247,250,.90) !important;
    --input-background-fill: #0b0e14 !important;
    --input-background-fill-hover: #0b0e14 !important;
    --input-background-fill-focus: #0b0e14 !important;
    --input-border-color: rgba(255,255,255,.075) !important;
    --input-border-color-focus: rgba(255,255,255,.12) !important;
    --input-shadow: none !important;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif !important;
    font-size: 13px !important;
    line-height: 1.72 !important;
    padding: 16px !important;
    box-shadow: inset 0 1px rgba(255,255,255,.018) !important;
    transition: border-color .3s var(--ease), background .3s var(--ease), box-shadow .3s var(--ease) !important;
}

.output-panel textarea:focus,
textarea[data-testid="textbox"]:focus {
    outline: none !important;
    border-color: rgba(145,178,255,.28) !important;
    background: #0b0e14 !important;
    box-shadow: 0 0 0 3px rgba(255,255,255,.018), inset 0 1px rgba(255,255,255,.025) !important;
}

label span,
.block-label,
.label-wrap {
    color: rgba(225,230,239,.48) !important;
    font-size: 10px !important;
    font-weight: 650 !important;
    letter-spacing: .075em !important;
    text-transform: uppercase !important;
}

.gradio-container .block.gr-box,
.gradio-container .input-container,
.gradio-container .wrap,
.gradio-container .wrap.svelte-1ipelgc,
.gradio-container [data-testid="textbox"],
.gradio-container [data-testid="textbox"] > div {
    --input-background-fill: #0b0e14 !important;
    --input-background-fill-hover: #0b0e14 !important;
    --input-background-fill-focus: #0b0e14 !important;
}

.output-panel .file-preview,
.output-panel [data-testid="file"],
.output-panel .file-container {
    border-radius: 13px !important;
    border-color: rgba(255,255,255,.07) !important;
    background: rgba(255,255,255,.025) !important;
}

button, input, textarea, .file-preview, .tab-nav button {
    transition-timing-function: var(--ease) !important;
}

* { scrollbar-width: thin; scrollbar-color: rgba(255,255,255,.13) transparent; }
*::-webkit-scrollbar { width: 7px; height: 7px; }
*::-webkit-scrollbar-track { background: transparent; }
*::-webkit-scrollbar-thumb { background: rgba(255,255,255,.13); border-radius: 99px; }
*::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,.21); }

@media (max-width: 900px) {
    #app-shell { width: calc(100% - 36px); padding-top: 24px; }
    #topbar { margin-bottom: 34px !important; }
    #control_row { flex-direction: column !important; }
    #run_btn { width: 166px !important; margin: 4px auto !important; }
}
"""

# Separate raw transcript, refined transcript, and meeting record into inspectable tabs.
with gr.Blocks(
    title="Meeting Assistant",
    css=custom_css,
    theme=gr.themes.Base(
        primary_hue="blue",
        secondary_hue="purple",
        neutral_hue="slate",
        font=("-apple-system", "BlinkMacSystemFont", "SF Pro Text", "SF Pro Display", "Helvetica Neue", "Arial", "sans-serif"),
        font_mono=("SF Mono", "SFMono-Regular", "Menlo", "monospace"),
    ),
) as demo:

    with gr.Column(elem_id="app-shell"):
        with gr.Row(elem_id="topbar"):
            gr.HTML('<div class="brand"><span class="brand-mark">✦</span><span>Meeting Assistant</span></div>')
            gr.HTML('<div class="product-note">Private workspace · AI-powered</div>')

        with gr.Column(elem_id="hero"):
            gr.HTML('<div class="eyebrow">Intelligent meeting workspace</div>')
            gr.Markdown("# AI Meeting Assistant")
            gr.Markdown(
                "Turn a recording into a clear, structured meeting record — with refined transcripts, "
                "decisions, minutes, and follow-ups ready to use."
            )

        with gr.Column(elem_id="workspace"):
            with gr.Row(elem_id="control_row"):
                audio_input = gr.Audio(
                    type="filepath",
                    label="Meeting recording",
                    elem_id="audio_input",
                    scale=1,
                )
                run_btn = gr.Button(
                    "▶  Process Meeting",
                    variant="primary",
                    scale=0,
                    elem_id="run_btn",
                )

            status_box = gr.Textbox(
                label="Status",
                interactive=False,
                elem_id="status_box",
                max_lines=2,
            )

            with gr.Tabs(elem_id="output_tabs"):
                with gr.Tab("📝  Raw Transcript", elem_classes=["output-panel"]):
                    raw_out = gr.Textbox(
                        label="Raw Transcript · Whisper output",
                        lines=15,
                        interactive=False,
                    )
                    dl_raw = gr.File(label="Download Raw Transcript")

                with gr.Tab("✦  Refined Transcript", elem_classes=["output-panel"]):
                    refined_out = gr.Textbox(
                        label="Refined Transcript · domain-corrected",
                        lines=15,
                        interactive=False,
                    )
                    dl_refined = gr.File(label="Download Refined Transcript")

                with gr.Tab("☷  Meeting Record", elem_classes=["output-panel"]):
                    minutes_out = gr.Textbox(
                        label="Minutes · Decisions · Action Items",
                        lines=20,
                        interactive=False,
                    )
                    with gr.Row():
                        dl_minutes = gr.File(label="Download as Text")
                        dl_json = gr.File(label="Download as JSON")

    run_btn.click(
        fn=process_audio,
        inputs=[audio_input],
        outputs=[status_box, raw_out, refined_out, minutes_out,
                 dl_raw, dl_refined, dl_minutes, dl_json]
    )


if __name__ == "__main__":
    demo.launch()
