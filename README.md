# AI Meeting Assistant

Turn any meeting recording into a structured record - refined transcript, minutes, decisions, and action items - in three automated stages.

---

## What it does

1. **Transcribes** the audio locally using OpenAI Whisper (no internet required for this stage).
2. **Refines** the raw transcript using a large language model to fix domain-specific ASR errors - technical jargon, acronyms, verbalized punctuation, and whitespace-corrupted terms.
3. **Generates** a structured meeting record (summary, minutes, key decisions, action items) using a second large language model and exports it as both a readable text file and a JSON file.

All LLM inference runs on the Groq free tier. No paid API is required.

---

## Requirements

* Python 3.9 or later
* A free [Groq API key](https://console.groq.com) (sign up → API Keys → Create)
* `ffmpeg` installed on your system (required by Whisper for audio decoding)

### Install ffmpeg

**macOS**

```bash
brew install ffmpeg
```

**Ubuntu / Debian**

```bash
sudo apt install ffmpeg
```

**Windows**
Download from https://ffmpeg.org/download.html and add to your PATH.

---

## Setup

### 1\. Clone or extract the project

```bash
# If using git
git clone <repo-url>
cd ML_Bootcamp
```

### 2\. Create and activate a virtual environment (recommended)

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3\. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** The first run will also download the Whisper `base` model weights (~140 MB). This happens automatically and only once.

### 4\. Set your Groq API key

Create a file named `.env` in the project root:

```
GROQ_API_KEY=your_groq_api_key_here
```

Replace `your_groq_api_key_here` with your actual key from the Groq console.

---

## Running the app

```bash
python app.py
```

Then open the URL printed in your terminal in a browser.

---

## Using the app

1. **Upload** a meeting recording using the audio input (drag-and-drop or click to browse).  
Supported formats: `.mp3`, `.mp4`, `.wav`, `.m4a`, `.ogg`, `.flac`, `.webm`
2. Click **Process Meeting** and wait - progress is shown in the status bar.
3. Switch between the three output tabs:

   * **Raw Transcript** - unprocessed Whisper output
   * **Refined Transcript** - domain-corrected version
   * **Meeting Record** - summary, minutes, decisions, and action items
4. Use the **Download** buttons in each tab to save outputs as `.txt` or `.json`.

---
## Supported audio formats

`.mp3` · `.mp4` · `.wav` · `.m4a` · `.ogg` · `.flac` · `.webm`

---

