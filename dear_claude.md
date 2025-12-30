Your interface wouln't let you load this, and it wouldn't let me paste it.... so.... Here is .... "most" of the code for wlk.... I Include some here just to try and keep it smaller but hopefully it gives you the just.... let me know if you need something else specific out of it:

/home/charlie/Projects/WhisperLiveKit/CONTRIBUTING.md
```markdown
# Contributing

Thank you for considering contributing ! We appreciate your time and effort to help make this project better.

## Before You Start

1. **Search for Existing Issues or Discussions:**
   - Before opening a new issue or discussion, please check if there's already an existing one related to your topic. This helps avoid duplicates and keeps discussions centralized.

2. **Discuss Your Contribution:**
   - If you plan to make a significant change, it's advisable to discuss it in an issue first. This ensures that your contribution aligns with the project's goals and avoids duplicated efforts.

3. **General questions about whisper streaming web:**
   - For general questions about whisper streaming web, use the discussion space on GitHub. This helps in fostering a collaborative environment and encourages knowledge-sharing.

## Opening Issues

If you encounter a problem with WhisperLiveKit or want to suggest an improvement, please follow these guidelines when opening an issue:

- **Bug Reports:**
  - Clearly describe the error. **Please indicate the parameters you use, especially the model(s)**
  - Provide a minimal, reproducible example that demonstrates the issue.

- **Feature Requests:**
  - Clearly outline the new feature you are proposing.
  - Explain how it would benefit the project.

## Opening Pull Requests

We welcome and appreciate contributions! To ensure a smooth review process, please follow these guidelines when opening a pull request:

- **Commit Messages:**
  - Write clear and concise commit messages, explaining the purpose of each change.

- **Documentation:**
  - Update documentation when introducing new features or making changes that impact existing functionality.

- **Tests:**
  - If applicable, add or update tests to cover your changes.

- **Discuss Before Major Changes:**
  - If your PR includes significant changes, discuss it in an issue first.

## Thank You

Your contributions make WhisperLiveKit better for everyone. Thank you for your time and dedication!

```
CONTRIBUTING.md

/home/charlie/Projects/WhisperLiveKit/DEV_NOTES.md
```markdown
# 1. Simulstreaming: Decouple the encoder for faster inference

Simulstreaming encoder time (whisperlivekit/simul_whisper/simul_whisper.py l. 397) experimentations :

On macOS Apple Silicon M4 :

| Encoder | base.en | small |
|--------|---------|-------|
| WHISPER (no modification) | 0.35s | 1.09s |
| FASTER_WHISPER | 0.4s | 1.20s |
| MLX_WHISPER | 0.07s | 0.20s |

Memory saved by only loading encoder for optimized framework:

For tiny.en, mlx whisper:
Sizes MLX whisper:
Decoder weights: 59110771 bytes
Encoder weights: 15268874 bytes


# 2. Translation: Faster model for each system

## Benchmark Results

Testing on MacBook M3 with NLLB-200-distilled-600M model:

### Standard Transformers vs CTranslate2

| Test Text | Standard Inference Time | CTranslate2 Inference Time | Speedup |
|-----------|-------------------------|---------------------------|---------|
| UN Chief says there is no military solution in Syria | 0.9395s | 2.0472s | 0.5x |
| The rapid advancement of AI technology is transforming various industries | 0.7171s | 1.7516s | 0.4x |
| Climate change poses a significant threat to global ecosystems | 0.8533s | 1.8323s | 0.5x |
| International cooperation is essential for addressing global challenges | 0.7209s | 1.3575s | 0.5x |
| The development of renewable energy sources is crucial for a sustainable future | 0.8760s | 1.5589s | 0.6x |

**Results:**
- Total Standard time: 4.1068s
- Total CTranslate2 time: 8.5476s
- CTranslate2 is slower on this system --> Use Transformers, and ideally we would have an mlx implementation.


# 3. SortFormer Diarization: 4-to-2 Speaker Constraint Algorithm

Transform a diarization model that predicts up to 4 speakers into one that predicts up to 2 speakers by mapping the output predictions.

## Problem Statement
- Input: `self.total_preds` with shape `(x, x, 4)` - predictions for 4 speakers
- Output: Constrained predictions with shape `(x, x, 2)` - predictions for 2 speakers

#
### Initial Setup
For each time step `i`, we have a ranking of 4 speaker predictions (1-4). When only 2 speakers are present, the model will have close predictions for the 2 active speaker positions.

Instead of `np.argmax(preds_np, axis=1)`, we take the top 2 predictions and build a dynamic 4→2 mapping that can evolve over time.

### Algorithm

```python
top_2_speakers = np.argsort(preds_np, axis=1)[:, -2:]
```

- `DS_a_{i}`: Top detected speaker for prediction i
- `DS_b_{i}`: Second detected speaker for prediction i  
- `AS_{i}`: Attributed speaker for prediction i
- `GTS_A`: Ground truth speaker A
- `GTS_B`: Ground truth speaker B
- `DIST(a, b)`: Distance between detected speakers a and b

3. **Attribution Logic**

```
AS_0 ← A

AS_1 ← B

IF DIST(DS_a_0, DS_a_1) < DIST(DS_a_0, DS_a_2) AND 
    DIST(DS_a_0, DS_a_1) < DIST(DS_a_1, DS_a_2):
    # Likely that DS_a_0 = DS_a_1 (same speaker)
    AS_1 ← A
    AS_2 ← B

ELIF DIST(DS_a_0, DS_a_2) < DIST(DS_a_0, DS_a_1) AND 
    DIST(DS_a_0, DS_a_2) < DIST(DS_a_1, DS_a_2):
    AS_2 ← A

ELSE:
    AS_2 ← B

to finish
```

```
DEV_NOTES.md

/home/charlie/Projects/WhisperLiveKit/README.md
```markdown
<h1 align="center">WLK</h1>
<p align="center"><b>WhisperLiveKit: Ultra-low-latency, self-hosted speech-to-text with speaker identification</b></p>


<p align="center">
<img src="https://raw.githubusercontent.com/QuentinFuxa/WhisperLiveKit/refs/heads/main/demo.png" alt="WhisperLiveKit Demo" width="730">
</p>


<p align="center">
<a href="https://pypi.org/project/whisperlivekit/"><img alt="PyPI Version" src="https://img.shields.io/pypi/v/whisperlivekit?color=g"></a>
<a href="https://pepy.tech/project/whisperlivekit"><img alt="PyPI Downloads" src="https://static.pepy.tech/personalized-badge/whisperlivekit?period=total&units=international_system&left_color=grey&right_color=brightgreen&left_text=installations"></a>
<a href="https://pypi.org/project/whisperlivekit/"><img alt="Python Versions" src="https://img.shields.io/badge/python-3.9--3.15-dark_green"></a>
<a href="https://huggingface.co/qfuxa/whisper-base-french-lora">
  <img alt="Hugging Face Weights" src="https://img.shields.io/badge/🤗-Hugging%20Face%20Weights-yellow" />
</a>
<a href="https://github.com/QuentinFuxa/WhisperLiveKit/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/badge/License-Apache 2.0-dark_green"></a>
</p>


#### Powered by Leading Research:

- Simul-[Whisper](https://arxiv.org/pdf/2406.10052)/[Streaming](https://arxiv.org/abs/2506.17077) (SOTA 2025) - Ultra-low latency transcription using [AlignAtt policy](https://arxiv.org/pdf/2305.11408)
- [NLLW](https://github.com/QuentinFuxa/NoLanguageLeftWaiting) (2025), based on [distilled](https://huggingface.co/entai2965/nllb-200-distilled-600M-ctranslate2) [NLLB](https://arxiv.org/abs/2207.04672) (2022, 2024) - Simulatenous translation from & to 200 languages.
- [WhisperStreaming](https://github.com/ufal/whisper_streaming) (SOTA 2023) - Low latency transcription using [LocalAgreement policy](https://www.isca-archive.org/interspeech_2020/liu20s_interspeech.pdf)
- [Streaming Sortformer](https://arxiv.org/abs/2507.18446) (SOTA 2025) - Advanced real-time speaker diarization
- [Diart](https://github.com/juanmc2005/diart) (SOTA 2021) - Real-time speaker diarization
- [Silero VAD](https://github.com/snakers4/silero-vad) (2024) - Enterprise-grade Voice Activity Detection


> **Why not just run a simple Whisper model on every audio batch?** Whisper is designed for complete utterances, not real-time chunks. Processing small segments loses context, cuts off words mid-syllable, and produces poor transcription. WhisperLiveKit uses state-of-the-art simultaneous speech research for intelligent buffering and incremental processing.


### Architecture

<img alt="Architecture" src="https://raw.githubusercontent.com/QuentinFuxa/WhisperLiveKit/refs/heads/main/architecture.png" />

*The backend supports multiple concurrent users. Voice Activity Detection reduces overhead when no voice is detected.*

### Installation & Quick Start

```bash
pip install whisperlivekit
```
> You can also clone the repo and `pip install -e .` for the latest version.

#### Quick Start
1. **Start the transcription server:**
   ```bash
   wlk --model base --language en
   ```

2. **Open your browser** and navigate to `http://localhost:8000`. Start speaking and watch your words appear in real-time!


> - See [here](https://github.com/QuentinFuxa/WhisperLiveKit/blob/main/whisperlivekit/simul_whisper/whisper/tokenizer.py) for the list of all available languages.
> - Check the [troubleshooting guide](docs/troubleshooting.md) for step-by-step fixes collected from recent GPU setup/env issues.
> - The CLI entry point is exposed as both `wlk` and `whisperlivekit-server`; they are equivalent.
> - For HTTPS requirements, see the **Parameters** section for SSL configuration options.


#### Use it to capture audio from web pages.

Go to `chrome-extension` for instructions.

<p align="center">
<img src="https://raw.githubusercontent.com/QuentinFuxa/WhisperLiveKit/refs/heads/main/chrome-extension/demo-extension.png" alt="WhisperLiveKit Demo" width="600">
</p>



#### Optional Dependencies

| Optional | `pip install` |
|-----------|-------------|
| **Windows/Linux optimizations** | `faster-whisper` |
| **Apple Silicon optimizations** | `mlx-whisper` |
| **Translation** | `nllw` |
| **Speaker diarization** | `git+https://github.com/NVIDIA/NeMo.git@main#egg=nemo_toolkit[asr]` |
| OpenAI API | `openai` |
| *[Not recommanded]*  Speaker diarization with Diart | `diart` |

See  **Parameters & Configuration** below on how to use them.



### Usage Examples

**Command-line Interface**: Start the transcription server with various options:

```bash
# Large model and translate from french to danish
wlk --model large-v3 --language fr --target-language da

# Diarization and server listening on */80 
wlk --host 0.0.0.0 --port 80 --model medium --diarization --language fr
```


**Python API Integration**: Check [basic_server](https://github.com/QuentinFuxa/WhisperLiveKit/blob/main/whisperlivekit/basic_server.py) for a more complete example of how to use the functions and classes.

```python
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from whisperlivekit import AudioProcessor, TranscriptionEngine, parse_args

transcription_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global transcription_engine
    transcription_engine = TranscriptionEngine(model="medium", diarization=True, lan="en")
    yield

app = FastAPI(lifespan=lifespan)

async def handle_websocket_results(websocket: WebSocket, results_generator):
    async for response in results_generator:
        await websocket.send_json(response)
    await websocket.send_json({"type": "ready_to_stop"})

@app.websocket("/asr")
async def websocket_endpoint(websocket: WebSocket):
    global transcription_engine

    # Create a new AudioProcessor for each connection, passing the shared engine
    audio_processor = AudioProcessor(transcription_engine=transcription_engine)    
    results_generator = await audio_processor.create_tasks()
    results_task = asyncio.create_task(handle_websocket_results(websocket, results_generator))
    await websocket.accept()
    while True:
        message = await websocket.receive_bytes()
        await audio_processor.process_audio(message)        
```

**Frontend Implementation**: The package includes an HTML/JavaScript implementation [here](https://github.com/QuentinFuxa/WhisperLiveKit/blob/main/whisperlivekit/web/live_transcription.html). You can also import it using `from whisperlivekit import get_inline_ui_html` & `page = get_inline_ui_html()`


## Parameters & Configuration


| Parameter | Description | Default |
|-----------|-------------|---------|
| `--model` | Whisper model size. List and recommandations [here](https://github.com/QuentinFuxa/WhisperLiveKit/blob/main/docs/default_and_custom_models.md) | `small` |
| `--model-path` | Local .pt file/directory **or** Hugging Face repo ID containing the Whisper model. Overrides `--model`. Recommandations [here](https://github.com/QuentinFuxa/WhisperLiveKit/blob/main/docs/default_and_custom_models.md) | `None` |
| `--language` | List [here](docs/supported_languages.md). If you use `auto`, the model attempts to detect the language automatically, but it tends to bias towards English. | `auto` |
| `--target-language` | If sets, translates using [NLLW](https://github.com/QuentinFuxa/NoLanguageLeftWaiting). [200 languages available](docs/supported_languages.md). If you want to translate to english, you can also use `--direct-english-translation`. The STT model will try to directly output the translation. | `None` |
| `--diarization` | Enable speaker identification | `False` |
| `--backend-policy` | Streaming strategy: `1`/`simulstreaming` uses AlignAtt SimulStreaming, `2`/`localagreement` uses the LocalAgreement policy | `simulstreaming` |
| `--backend` | Whisper implementation selector. `auto` picks MLX on macOS (if installed), otherwise Faster-Whisper, otherwise vanilla Whisper. You can also force `mlx-whisper`, `faster-whisper`, `whisper`, or `openai-api` (LocalAgreement only) | `auto` |
| `--no-vac` | Disable Voice Activity Controller. NOT ADVISED | `False` |
| `--no-vad` | Disable Voice Activity Detection. NOT ADVISED | `False` |
| `--warmup-file` | Audio file path for model warmup | `jfk.wav` |
| `--host` | Server host address | `localhost` |
| `--port` | Server port | `8000` |
| `--ssl-certfile` | Path to the SSL certificate file (for HTTPS support) | `None` |
| `--ssl-keyfile` | Path to the SSL private key file (for HTTPS support) | `None` |
| `--forwarded-allow-ips` | Ip or Ips allowed to reverse proxy the whisperlivekit-server. Supported types are  IP Addresses (e.g. 127.0.0.1), IP Networks (e.g. 10.100.0.0/16), or Literals (e.g. /path/to/socket.sock) | `None` |
| `--pcm-input` | raw PCM (s16le) data is expected as input and FFmpeg will be bypassed. Frontend will use AudioWorklet instead of MediaRecorder | `False` |
| `--lora-path` | Path or Hugging Face repo ID for LoRA adapter weights (e.g., `qfuxa/whisper-base-french-lora`). Only works with native Whisper backend (`--backend whisper`) | `None` |

| Translation options | Description | Default |
|-----------|-------------|---------|
| `--nllb-backend` | `transformers` or `ctranslate2` | `ctranslate2` |
| `--nllb-size` | `600M` or `1.3B` | `600M` |

| Diarization options | Description | Default |
|-----------|-------------|---------|
| `--diarization-backend` |  `diart` or `sortformer` | `sortformer` |
| `--disable-punctuation-split` | [NOT FUNCTIONAL IN 0.2.15 / 0.2.16] Disable punctuation based splits. See #214 | `False` |
| `--segmentation-model` | Hugging Face model ID for Diart segmentation model. [Available models](https://github.com/juanmc2005/diart/tree/main?tab=readme-ov-file#pre-trained-models) | `pyannote/segmentation-3.0` |
| `--embedding-model` | Hugging Face model ID for Diart embedding model. [Available models](https://github.com/juanmc2005/diart/tree/main?tab=readme-ov-file#pre-trained-models) | `speechbrain/spkrec-ecapa-voxceleb` |

| SimulStreaming backend options | Description | Default |
|-----------|-------------|---------|
| `--disable-fast-encoder` | Disable Faster Whisper or MLX Whisper backends for the encoder (if installed). Inference can be slower but helpful when GPU memory is limited | `False` |
| `--custom-alignment-heads` | Use your own alignment heads, useful when `--model-dir` is used. Use `scripts/determine_alignment_heads.py` to extract them. <img src="scripts/alignment_heads.png" alt="WhisperLiveKit Demo" width="300">
 | `None` |
| `--frame-threshold` | AlignAtt frame threshold (lower = faster, higher = more accurate) | `25` |
| `--beams` | Number of beams for beam search (1 = greedy decoding) | `1` |
| `--decoder` | Force decoder type (`beam` or `greedy`) | `auto` |
| `--audio-max-len` | Maximum audio buffer length (seconds) | `30.0` |
| `--audio-min-len` | Minimum audio length to process (seconds) | `0.0` |
| `--cif-ckpt-path` | Path to CIF model for word boundary detection | `None` |
| `--never-fire` | Never truncate incomplete words | `False` |
| `--init-prompt` | Initial prompt for the model | `None` |
| `--static-init-prompt` | Static prompt that doesn't scroll | `None` |
| `--max-context-tokens` | Maximum context tokens | Depends on model used, but usually 448. |



| WhisperStreaming backend options | Description | Default |
|-----------|-------------|---------|
| `--confidence-validation` | Use confidence scores for faster validation | `False` |
| `--buffer_trimming` | Buffer trimming strategy (`sentence` or `segment`) | `segment` |




> For diarization using Diart, you need to accept user conditions [here](https://huggingface.co/pyannote/segmentation) for the `pyannote/segmentation` model, [here](https://huggingface.co/pyannote/segmentation-3.0) for the `pyannote/segmentation-3.0` model and [here](https://huggingface.co/pyannote/embedding) for the `pyannote/embedding` model. **Then**, login to HuggingFace: `huggingface-cli login`

### 🚀 Deployment Guide

To deploy WhisperLiveKit in production:
 
1. **Server Setup**: Install production ASGI server & launch with multiple workers
   ```bash
   pip install uvicorn gunicorn
   gunicorn -k uvicorn.workers.UvicornWorker -w 4 your_app:app
   ```

2. **Frontend**: Host your customized version of the `html` example & ensure WebSocket connection points correctly

3. **Nginx Configuration** (recommended for production):
    ```nginx    
   server {
       listen 80;
       server_name your-domain.com;
        location / {
            proxy_pass http://localhost:8000;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
    }}
    ```

4. **HTTPS Support**: For secure deployments, use "wss://" instead of "ws://" in WebSocket URL

## 🐋 Docker

Deploy the application easily using Docker with GPU or CPU support.

### Prerequisites
- Docker installed on your system
- For GPU support: NVIDIA Docker runtime installed

### Quick Start

**With GPU acceleration (recommended):**
```bash
docker build -t wlk .
docker run --gpus all -p 8000:8000 --name wlk wlk
```

**CPU only:**
```bash
docker build -f Dockerfile.cpu -t wlk .
docker run -p 8000:8000 --name wlk wlk
```

### Advanced Usage

**Custom configuration:**
```bash
# Example with custom model and language
docker run --gpus all -p 8000:8000 --name wlk wlk --model large-v3 --language fr
```

### Memory Requirements
- **Large models**: Ensure your Docker runtime has sufficient memory allocated


#### Customization

- `--build-arg` Options:
  - `EXTRAS="translation"` - Add extras to the image's installation (no spaces). Remember to set necessary container options!
  - `HF_PRECACHE_DIR="./.cache/"` - Pre-load a model cache for faster first-time start
  - `HF_TKN_FILE="./token"` - Add your Hugging Face Hub access token to download gated models

## 🔮 Use Cases
Capture discussions in real-time for meeting transcription, help hearing-impaired users follow conversations through accessibility tools, transcribe podcasts or videos automatically for content creation, transcribe support calls with speaker identification for customer service...

```
README.md

/home/charlie/Projects/WhisperLiveKit/docs/API.md
```markdown
# WhisperLiveKit WebSocket API Documentation

> !! **Note**: The new API structure described in this document is currently under deployment. 
This documentation is intended for devs who want to build custom frontends.

WLK provides real-time speech transcription, speaker diarization, and translation through a WebSocket API. The server sends incremental updates as audio is processed, allowing clients to display live transcription results with minimal latency.

---

## Legacy API (Current)

### Message Structure

The current API sends complete state snapshots on each update (several time per second)

```typescript
{
  "type": str,
  "status": str,
  "lines": [
    {
      "speaker": int,
      "text": str,
      "start": float,
      "end": float,
      "translation": str | null,
      "detected_language": str
    }
  ],
  "buffer_transcription": str,
  "buffer_diarization": str,
  "remaining_time_transcription": float,
  "remaining_time_diarization": float
}
```

---

## New API (Under Development)

### Philosophy

Principles:

- **Incremental Updates**: Only updates and new segments are sent
- **Ephemeral Buffers**: Temporary, unvalidated data displayed in real-time but overwritten on next update, at speaker level


## Message Format


```typescript
{
  "type": "transcript_update",
  "status": "active_transcription" | "no_audio_detected",
  "segments": [
    {
      "id": number,
      "speaker": number,
      "text": string,
      "start_speaker": float,
      "start": float,
      "end": float,
      "language": string | null,
      "translation": string,
      "words": [
        {
          "text": string,
          "start": float,
          "end": float,
          "validated": {
            "text": boolean,
            "speaker": boolean,
          }
        }
      ],
      "buffer": {
        "transcription": string,
        "diarization": string,
        "translation": string
      }
    }
  ],
  "metadata": {
    "remaining_time_transcription": float,
    "remaining_time_diarization": float
  }
}
```

### Other Message Types

#### Config Message (sent on connection)
```json
{
  "type": "config",
  "useAudioWorklet": true / false
}
```

#### Ready to Stop Message (sent after processing complete)
```json
{
  "type": "ready_to_stop"
}
```

---

## Field Descriptions

### Segment Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `number` | Unique identifier for this segment. Used by clients to update specific segments efficiently. |
| `speaker` | `number` | Speaker ID (1, 2, 3...). Special value `-2` indicates silence. |
| `text` | `string` | Validated transcription text for this update. Should be **appended** to the segment's text on the client side.  |
| `start_speaker` | `float` | Timestamp (seconds) when this speaker segment began. |
| `start` | `float` | Timestamp (seconds) of the first word in this update. |
| `end` | `float` | Timestamp (seconds) of the last word in this update. |
| `language` | `string \| null` | ISO language code (e.g., "en", "fr"). `null` until language is detected. |
| `translation` | `string` | Validated translation text for this update. Should be **appended** to the segment's translation on the client side. |
| `words` | `Array` | Array of word-level objects with timing and validation information. |
| `buffer` | `Object` | Per-segment temporary buffers, see below |

### Word Object

| Field | Type | Description |
|-------|------|-------------|
| `text` | `string` | The word text. |
| `start` | `number` | Start timestamp (seconds) of this word. |
| `end` | `number` | End timestamp (seconds) of this word. |
| `validated.text` | `boolean` | Whether the transcription text has been validated. if false, word is also in buffer: transcription |
| `validated.speaker` | `boolean` | Whether the speaker assignment has been validated. if false, word is also in buffer: diarization |
| `validated.language` | `boolean` | Whether the language detection has been validated. if false, word is also in buffer: translation |

### Buffer Object (Per-Segment)

Buffers are **ephemeral**. They should be displayed to the user but not stored permanently in the frontend. Each update may contain a completely different buffer value, and previous buffer is likely to be in the next validated text.

| Field | Type | Description |
|-------|------|-------------|
| `transcription` | `string` | Pending transcription text. Displayed immediately but **overwritten** on next update. |
| `diarization` | `string` | Pending diarization text (text waiting for speaker assignment). Displayed immediately but **overwritten** on next update. |
| `translation` | `string` | Pending translation text. Displayed immediately but **overwritten** on next update. |


### Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `remaining_time_transcription` | `float` | Seconds of audio waiting for transcription processing. |
| `remaining_time_diarization` | `float` | Seconds of audio waiting for speaker diarization. |

### Status Values

| Status | Description |
|--------|-------------|
| `active_transcription` | Normal operation, transcription is active. |
| `no_audio_detected` | No audio has been detected yet. |

---

## Update Behavior

### Incremental Updates

The API sends **only changed or new segments**. Clients should:

1. Maintain a local map of segments by ID
2. When receiving an update, merge/update segments by ID
3. Render only the changed segments

### Language Detection

When language is detected for a segment:

```jsonc
// Update 1: No language yet
{
  "segments": [
    {"id": 1, "speaker": 1, "text": "May see", "language": null}
  ]
}

// Update 2: Same segment ID, language now detected
{
  "segments": [
    {"id": 1, "speaker": 1, "text": "Merci", "language": "fr"}
  ]
}
```

**Client behavior**: **Replace** the existing segment with the same ID.

### Buffer Behavior

Buffers are **per-segment** to handle multi-speaker scenarios correctly.

#### Example: Translation with diarization and translation

```jsonc
// Update 1
{
  "segments": [
    {
      "id": 1,
      "speaker": 1,
      "text": "Hello world, how are",
      "translation": "",
      "buffer": {
        "transcription": "",
        "diarization": " you on",
        "translation": "Bonjour le monde"
      }
    }
  ]
}


// ==== Frontend ====
// <SPEAKER>1</SPEAKER>
// <TRANSCRIPTION>Hello world, how are <DIARIZATION BUFFER> you on</DIARIZATION BUFFER></TRANSCRIPTION>
// <TRANSLATION><TRANSLATION BUFFER>Bonjour le monde</TRANSLATION BUFFER></TRANSLATION>


// Update 2
{
  "segments": [
    {
      "id": 1,
      "speaker": 1,
      "text": " you on this",
      "translation": "Bonjour tout le monde",
      "buffer": {
        "transcription": "",
        "diarization": " beautiful day",
        "translation": ",comment"
      }
    },
  ]
}


// ==== Frontend ====
// <SPEAKER>1</SPEAKER>
// <TRANSCRIPTION>Hello world, how are you on this<DIARIZATION BUFFER>  beautiful day</DIARIZATION BUFFER></TRANSCRIPTION>
// <TRANSLATION>Bonjour tout le monde<TRANSLATION BUFFER>, comment</TRANSLATION BUFFER><TRANSLATION>
```

### Silence Segments

Silence is represented with the speaker id = `-2`:

```jsonc
{
  "id": 5,
  "speaker": -2,
  "text": "",
  "start": 10.5,
  "end": 12.3
}
```

```
API.md

/home/charlie/Projects/WhisperLiveKit/docs/alignement_principles.md
```markdown
### Alignment between STT Tokens and Diarization Segments 

- Example 1: The punctuation from STT and the speaker change from Diariation come in the prediction `t`
- Example 2: The punctuation from STT comes from prediction `t`, but the speaker change from Diariation come in the prediction `t-1`
- Example 3: The punctuation from STT comes from prediction `t-1`, but the speaker change from Diariation come in the prediction `t`

> `#` Is the split between the `t-1` prediction and `t` prediction.  


## Example 1:
```text
punctuations_segments : __#_______.__________________!____
diarization_segments:
SPK1                    __#____________
SPK2                      #            ___________________
-->
ALIGNED SPK1            __#_______.
ALIGNED SPK2              #        __________________!____

t-1 output:
SPK1:                   __#
SPK2: NO
DIARIZATION BUFFER: NO

t output:
SPK1:                       __#__.
SPK2:                             __________________!____
DIARIZATION BUFFER: No
```

## Example 2:
```text
punctuations_segments : _____#__.___________
diarization_segments:
SPK1                    ___  #
SPK2                       __#______________
-->
ALIGNED SPK1            _____#__.
ALIGNED SPK2                 #   ___________

t-1 output:
SPK1:                   ___  #
SPK2:
DIARIZATION BUFFER:        __#

t output:
SPK1:                      __#__.
SPK2:                            ___________
DIARIZATION BUFFER: No
```

## Example 3:
```text
punctuations_segments : ___.__#__________
diarization_segments:
SPK1                    ______#__
SPK2                          #  ________
-->
ALIGNED SPK1            ___.  #
ALIGNED SPK2                __#__________

t-1 output:
SPK1:                   ___.  #
SPK2:
DIARIZATION BUFFER:         __#

t output:
SPK1:                         #
SPK2:                       __#___________
DIARIZATION BUFFER: NO
```

```
alignement_principles.md

/home/charlie/Projects/WhisperLiveKit/docs/default_and_custom_models.md
```markdown
# Models and Model Paths

## Defaults

**Default Whisper Model**: `base`  
When no model is specified, WhisperLiveKit uses the `base` model, which provides a good balance of speed and accuracy for most use cases.

**Default Model Cache Directory**: `~/.cache/whisper`  
Models are automatically downloaded from OpenAI's model hub and cached in this directory. You can override this with `--model_cache_dir`.

**Default Translation Model**: `600M` (NLLB-200-distilled)  
When translation is enabled, the 600M distilled NLLB model is used by default. This provides good quality with minimal resource usage.

**Default Translation Backend**: `transformers`  
The translation backend defaults to Transformers. On Apple Silicon, this automatically uses MPS acceleration for better performance.

---


## Available Whisper model sizes:

| Available Model    | Speed    | Accuracy  | Multilingual | Translation | Hardware Requirements | Best Use Case                   |
|--------------------|----------|-----------|--------------|-------------|----------------------|----------------------------------|
| tiny(.en)          | Fastest  | Basic     | Yes/No       | Yes/No      | ~1GB VRAM            | Real-time, low resources         |
| base(.en)          | Fast     | Good      | Yes/No       | Yes/No      | ~1GB VRAM            | Balanced performance             |
| small(.en)         | Medium   | Better    | Yes/No       | Yes/No      | ~2GB VRAM            | Quality on limited hardware      |
| medium(.en)        | Slow     | High      | Yes/No       | Yes/No      | ~5GB VRAM            | High quality, moderate resources |
| large-v2           | Slowest  | Excellent | Yes          | Yes         | ~10GB VRAM           | Good overall accuracy & language support          |
| large-v3           | Slowest  | Excellent | Yes          | Yes         | ~10GB VRAM           | Best overall accuracy & language support                |
| large-v3-turbo     | Fast     | Excellent | Yes          | No          | ~6GB VRAM            | Fast, high-quality transcription |


### How to choose?

#### Language Support
- **English only**: Use `.en` (ex: `base.en`) models for better accuracy and faster processing when you only need English transcription
- **Multilingual**: Do not use `.en` models.
      
#### Special Cases
- **No translation needed**: Use `large-v3-turbo`
  - Same transcription quality as `large-v2` but significantly faster
  - **Important**: Does not translate correctly, only transcribes

### Additional Considerations

**Model Performance**:
- Accuracy improves significantly from tiny to large models
- English-only models are ~10-15% more accurate for English audio
- Newer versions (v2, v3) have better punctuation and formatting

**Audio Quality Impact**:
- Clean, clear audio: smaller models may suffice
- Noisy, accented, or technical audio: larger models recommended
- Phone/low-quality audio: use at least `small` model

_______________________


# Custom Models:

The `--model-path` parameter accepts:

## File Path
- **`.pt` / `.bin` / `.safetensor` formats** Should be openable by pytorch/safetensor.

## Directory Path (recommended)
Must contain:
- **`.pt` / `.bin` / `.safetensor` file** (required for decoder)

May optionally contain:
- **`.bin` file** - faster-whisper model for encoder (requires faster-whisper)
- **`weights.npz`** or **`weights.safetensors`** - for encoder (requires whisper-mlx)

## Hugging Face Repo ID
- Provide the repo ID (e.g. `openai/whisper-large-v3`) and WhisperLiveKit will download and cache the snapshot automatically. For gated repos, authenticate via `huggingface-cli login` first.

To improve speed/reduce hallucinations, you may want to use `scripts/determine_alignment_heads.py` to determine the alignment heads to use for your model, and use the `--custom-alignment-heads` to pass them to WLK. If not, alignment heads are set to be all the heads of the last half layer of decoder.


_______________________

# Translation Models and Backend

**Language Support**: ~200 languages

## Distilled Model Sizes Available

| Model | Size | Parameters | VRAM (FP16) | VRAM (INT8) | Quality |
|-------|------|------------|-------------|-------------|---------|
| 600M | 2.46 GB | 600M | ~1.5GB | ~800MB | Good, understandable |
| 1.3B | 5.48 GB | 1.3B | ~3GB | ~1.5GB | Better accuracy, context |

**Quality Impact**: 1.3B has ~15-25% better BLEU scores vs 600M across language pairs.

## Backend Performance

| Backend | Speed vs Base | Memory Usage | Quality Loss |
|---------|---------------|--------------|--------------|
| CTranslate2 | 6-10x faster | 40-60% less | ~5% BLEU drop |
| Transformers | Baseline | High | None |
| Transformers + MPS (on Apple Silicon) | 2x faster | Medium | None |

**Metrics**:
- CTranslate2: 50-100+ tokens/sec
- Transformers: 10-30 tokens/sec
- Apple Silicon with MPS: Up to 2x faster than CTranslate2

```
default_and_custom_models.md

/home/charlie/Projects/WhisperLiveKit/docs/supported_languages.md
```markdown
# Transcription: Supported Language

WLK supports transcription in the following languages:

| ISO Code | Language Name        |
|----------|---------------------|
| en       | English             |
| zh       | Chinese             |
| de       | German              |
| es       | Spanish             |
| ru       | Russian             |
| ko       | Korean              |
| fr       | French              |
| ja       | Japanese            |
| pt       | Portuguese          |
| tr       | Turkish             |
| pl       | Polish              |
| ca       | Catalan             |
| nl       | Dutch               |
| ar       | Arabic              |
| sv       | Swedish             |
| it       | Italian             |
| id       | Indonesian          |
| hi       | Hindi               |
| fi       | Finnish             |
| vi       | Vietnamese          |
| he       | Hebrew              |
| uk       | Ukrainian           |
| el       | Greek               |
| ms       | Malay               |
| cs       | Czech               |
| ro       | Romanian            |
| da       | Danish              |
| hu       | Hungarian           |
| ta       | Tamil               |
| no       | Norwegian           |
| th       | Thai                |
| ur       | Urdu                |
| hr       | Croatian            |
| bg       | Bulgarian           |
| lt       | Lithuanian          |
| la       | Latin               |
| mi       | Maori               |
| ml       | Malayalam           |
| cy       | Welsh               |
| sk       | Slovak              |
| te       | Telugu              |
| fa       | Persian             |
| lv       | Latvian             |
| bn       | Bengali             |
| sr       | Serbian             |
| az       | Azerbaijani         |
| sl       | Slovenian           |
| kn       | Kannada             |
| et       | Estonian            |
| mk       | Macedonian          |
| br       | Breton              |
| eu       | Basque              |
| is       | Icelandic           |
| hy       | Armenian            |
| ne       | Nepali              |
| mn       | Mongolian           |
| bs       | Bosnian             |
| kk       | Kazakh              |
| sq       | Albanian            |
| sw       | Swahili             |
| gl       | Galician            |
| mr       | Marathi             |
| pa       | Punjabi             |
| si       | Sinhala             |
| km       | Khmer               |
| sn       | Shona               |
| yo       | Yoruba              |
| so       | Somali              |
| af       | Afrikaans           |
| oc       | Occitan             |
| ka       | Georgian            |
| be       | Belarusian          |
| tg       | Tajik               |
| sd       | Sindhi              |
| gu       | Gujarati            |
| am       | Amharic             |
| yi       | Yiddish             |
| lo       | Lao                 |
| uz       | Uzbek               |
| fo       | Faroese             |
| ht       | Haitian Creole      |
| ps       | Pashto              |
| tk       | Turkmen             |
| nn       | Nynorsk             |
| mt       | Maltese             |
| sa       | Sanskrit            |
| lb       | Luxembourgish       |
| my       | Myanmar             |
| bo       | Tibetan             |
| tl       | Tagalog             |
| mg       | Malagasy            |
| as       | Assamese            |
| tt       | Tatar               |
| haw      | Hawaiian            |
| ln       | Lingala             |
| ha       | Hausa               |
| ba       | Bashkir             |
| jw       | Javanese            |
| su       | Sundanese           |
| yue      | Cantonese           |


# Translation: Supported Languages 

WLK supports translation into **201 languages** from the FLORES-200 dataset through the [NLLW](https://github.com/QuentinFuxa/NoLanguageLeftWaiting) translation system. 

## How to Specify Languages

You can specify languages in **three different ways**:

1. **Language Name** (case-insensitive): `"English"`, `"French"`, `"Spanish"`
2. **ISO Language Code**: `"en"`, `"fr"`, `"es"`
3. **NLLB Code** (FLORES-200): `"eng_Latn"`, `"fra_Latn"`, `"spa_Latn"`

## Usage Examples

### Command Line
```bash
# Using language name
whisperlivekit-server --target-language "French"

# Using ISO code
whisperlivekit-server --target-language fr

# Using NLLB code
whisperlivekit-server --target-language fra_Latn
```

### Python API
```python
from nllw.translation import get_language_info

# Get language information by name
lang_info = get_language_info("French")
print(lang_info)
# {'name': 'French', 'nllb': 'fra_Latn', 'language_code': 'fr'}

# Get language information by ISO code
lang_info = get_language_info("fr")

# Get language information by NLLB code
lang_info = get_language_info("fra_Latn")

# All three return the same result
```

## Complete Language List

The following table lists all 201 supported languages with their corresponding codes:

| Language Name | ISO Code | NLLB Code |
|---------------|----------|-----------|
| Acehnese (Arabic script) | ace_Arab | ace_Arab |
| Acehnese (Latin script) | ace_Latn | ace_Latn |
| Mesopotamian Arabic | acm_Arab | acm_Arab |
| Ta'izzi-Adeni Arabic | acq_Arab | acq_Arab |
| Tunisian Arabic | aeb_Arab | aeb_Arab |
| Afrikaans | af | afr_Latn |
| South Levantine Arabic | ajp_Arab | ajp_Arab |
| Akan | ak | aka_Latn |
| Tosk Albanian | als | als_Latn |
| Amharic | am | amh_Ethi |
| North Levantine Arabic | apc_Arab | apc_Arab |
| Modern Standard Arabic | ar | arb_Arab |
| Modern Standard Arabic (Romanized) | arb_Latn | arb_Latn |
| Najdi Arabic | ars_Arab | ars_Arab |
| Moroccan Arabic | ary_Arab | ary_Arab |
| Egyptian Arabic | arz_Arab | arz_Arab |
| Assamese | as | asm_Beng |
| Asturian | ast | ast_Latn |
| Awadhi | awa | awa_Deva |
| Central Aymara | ay | ayr_Latn |
| South Azerbaijani | azb | azb_Arab |
| North Azerbaijani | az | azj_Latn |
| Bashkir | ba | bak_Cyrl |
| Bambara | bm | bam_Latn |
| Balinese | ban | ban_Latn |
| Belarusian | be | bel_Cyrl |
| Bemba | bem | bem_Latn |
| Bengali | bn | ben_Beng |
| Bhojpuri | bho | bho_Deva |
| Banjar (Arabic script) | bjn_Arab | bjn_Arab |
| Banjar (Latin script) | bjn_Latn | bjn_Latn |
| Standard Tibetan | bo | bod_Tibt |
| Bosnian | bs | bos_Latn |
| Buginese | bug | bug_Latn |
| Bulgarian | bg | bul_Cyrl |
| Catalan | ca | cat_Latn |
| Cebuano | ceb | ceb_Latn |
| Czech | cs | ces_Latn |
| Chokwe | cjk | cjk_Latn |
| Central Kurdish | ckb | ckb_Arab |
| Crimean Tatar | crh | crh_Latn |
| Welsh | cy | cym_Latn |
| Danish | da | dan_Latn |
| German | de | deu_Latn |
| Southwestern Dinka | dik | dik_Latn |
| Dyula | dyu | dyu_Latn |
| Dzongkha | dz | dzo_Tibt |
| Greek | el | ell_Grek |
| English | en | eng_Latn |
| Esperanto | eo | epo_Latn |
| Estonian | et | est_Latn |
| Basque | eu | eus_Latn |
| Ewe | ee | ewe_Latn |
| Faroese | fo | fao_Latn |
| Fijian | fj | fij_Latn |
| Finnish | fi | fin_Latn |
| Fon | fon | fon_Latn |
| French | fr | fra_Latn |
| Friulian | fur-IT | fur_Latn |
| Nigerian Fulfulde | fuv | fuv_Latn |
| West Central Oromo | om | gaz_Latn |
| Scottish Gaelic | gd | gla_Latn |
| Irish | ga-IE | gle_Latn |
| Galician | gl | glg_Latn |
| Guarani | gn | grn_Latn |
| Gujarati | gu-IN | guj_Gujr |
| Haitian Creole | ht | hat_Latn |
| Hausa | ha | hau_Latn |
| Hebrew | he | heb_Hebr |
| Hindi | hi | hin_Deva |
| Chhattisgarhi | hne | hne_Deva |
| Croatian | hr | hrv_Latn |
| Hungarian | hu | hun_Latn |
| Armenian | hy-AM | hye_Armn |
| Igbo | ig | ibo_Latn |
| Ilocano | ilo | ilo_Latn |
| Indonesian | id | ind_Latn |
| Icelandic | is | isl_Latn |
| Italian | it | ita_Latn |
| Javanese | jv | jav_Latn |
| Japanese | ja | jpn_Jpan |
| Kabyle | kab | kab_Latn |
| Jingpho | kac | kac_Latn |
| Kamba | kam | kam_Latn |
| Kannada | kn | kan_Knda |
| Kashmiri (Arabic script) | kas_Arab | kas_Arab |
| Kashmiri (Devanagari script) | kas_Deva | kas_Deva |
| Georgian | ka | kat_Geor |
| Kazakh | kk | kaz_Cyrl |
| Kabiyè | kbp | kbp_Latn |
| Kabuverdianu | kea | kea_Latn |
| Halh Mongolian | mn | khk_Cyrl |
| Khmer | km | khm_Khmr |
| Kikuyu | ki | kik_Latn |
| Kinyarwanda | rw | kin_Latn |
| Kyrgyz | ky | kir_Cyrl |
| Kimbundu | kmb | kmb_Latn |
| Northern Kurdish | kmr | kmr_Latn |
| Central Kanuri (Arabic script) | knc_Arab | knc_Arab |
| Central Kanuri (Latin script) | knc_Latn | knc_Latn |
| Kikongo | kg | kon_Latn |
| Korean | ko | kor_Hang |
| Lao | lo | lao_Laoo |
| Ligurian | lij | lij_Latn |
| Limburgish | li | lim_Latn |
| Lingala | ln | lin_Latn |
| Lithuanian | lt | lit_Latn |
| Lombard | lmo | lmo_Latn |
| Latgalian | ltg | ltg_Latn |
| Luxembourgish | lb | ltz_Latn |
| Luba-Kasai | lua | lua_Latn |
| Ganda | lg | lug_Latn |
| Luo | luo | luo_Latn |
| Mizo | lus | lus_Latn |
| Standard Latvian | lv | lvs_Latn |
| Magahi | mag | mag_Deva |
| Maithili | mai | mai_Deva |
| Malayalam | ml-IN | mal_Mlym |
| Marathi | mr | mar_Deva |
| Minangkabau (Arabic script) | min_Arab | min_Arab |
| Minangkabau (Latin script) | min_Latn | min_Latn |
| Macedonian | mk | mkd_Cyrl |
| Maltese | mt | mlt_Latn |
| Meitei (Bengali script) | mni | mni_Beng |
| Mossi | mos | mos_Latn |
| Maori | mi | mri_Latn |
| Burmese | my | mya_Mymr |
| Dutch | nl | nld_Latn |
| Norwegian Nynorsk | nn-NO | nno_Latn |
| Norwegian Bokmål | nb | nob_Latn |
| Nepali | ne-NP | npi_Deva |
| Northern Sotho | nso | nso_Latn |
| Nuer | nus | nus_Latn |
| Nyanja | ny | nya_Latn |
| Occitan | oc | oci_Latn |
| Odia | or | ory_Orya |
| Pangasinan | pag | pag_Latn |
| Eastern Panjabi | pa | pan_Guru |
| Papiamento | pap | pap_Latn |
| Southern Pashto | pbt | pbt_Arab |
| Western Persian | fa | pes_Arab |
| Plateau Malagasy | mg | plt_Latn |
| Polish | pl | pol_Latn |
| Portuguese | pt-PT | por_Latn |
| Dari | fa-AF | prs_Arab |
| Ayacucho Quechua | qu | quy_Latn |
| Romanian | ro | ron_Latn |
| Rundi | rn | run_Latn |
| Russian | ru | rus_Cyrl |
| Sango | sg | sag_Latn |
| Sanskrit | sa | san_Deva |
| Santali | sat | sat_Olck |
| Sicilian | scn | scn_Latn |
| Shan | shn | shn_Mymr |
| Sinhala | si-LK | sin_Sinh |
| Slovak | sk | slk_Latn |
| Slovenian | sl | slv_Latn |
| Samoan | sm | smo_Latn |
| Shona | sn | sna_Latn |
| Sindhi | sd | snd_Arab |
| Somali | so | som_Latn |
| Southern Sotho | st | sot_Latn |
| Spanish | es-ES | spa_Latn |
| Sardinian | sc | srd_Latn |
| Serbian | sr | srp_Cyrl |
| Swati | ss | ssw_Latn |
| Sundanese | su | sun_Latn |
| Swedish | sv-SE | swe_Latn |
| Swahili | sw | swh_Latn |
| Silesian | szl | szl_Latn |
| Tamil | ta | tam_Taml |
| Tamasheq (Latin script) | taq_Latn | taq_Latn |
| Tamasheq (Tifinagh script) | taq_Tfng | taq_Tfng |
| Tatar | tt-RU | tat_Cyrl |
| Telugu | te | tel_Telu |
| Tajik | tg | tgk_Cyrl |
| Tagalog | tl | tgl_Latn |
| Thai | th | tha_Thai |
| Tigrinya | ti | tir_Ethi |
| Tok Pisin | tpi | tpi_Latn |
| Tswana | tn | tsn_Latn |
| Tsonga | ts | tso_Latn |
| Turkmen | tk | tuk_Latn |
| Tumbuka | tum | tum_Latn |
| Turkish | tr | tur_Latn |
| Twi | tw | twi_Latn |
| Central Atlas Tamazight | tzm | tzm_Tfng |
| Uyghur | ug | uig_Arab |
| Ukrainian | uk | ukr_Cyrl |
| Umbundu | umb | umb_Latn |
| Urdu | ur | urd_Arab |
| Northern Uzbek | uz | uzn_Latn |
| Venetian | vec | vec_Latn |
| Vietnamese | vi | vie_Latn |
| Waray | war | war_Latn |
| Wolof | wo | wol_Latn |
| Xhosa | xh | xho_Latn |
| Eastern Yiddish | yi | ydd_Hebr |
| Yoruba | yo | yor_Latn |
| Yue Chinese | yue | yue_Hant |
| Chinese (Simplified) | zh-CN | zho_Hans |
| Chinese (Traditional) | zh-TW | zho_Hant |
| Standard Malay | ms | zsm_Latn |
| Zulu | zu | zul_Latn |

## Special Features

### Multiple Script Support
Several languages are available in multiple scripts (e.g., Arabic and Latin):
- **Acehnese**: Arabic (`ace_Arab`) and Latin (`ace_Latn`)
- **Banjar**: Arabic (`bjn_Arab`) and Latin (`bjn_Latn`)
- **Kashmiri**: Arabic (`kas_Arab`) and Devanagari (`kas_Deva`)
- **Minangkabau**: Arabic (`min_Arab`) and Latin (`min_Latn`)
- **Tamasheq**: Latin (`taq_Latn`) and Tifinagh (`taq_Tfng`)
- **Central Kanuri**: Arabic (`knc_Arab`) and Latin (`knc_Latn`)
```
supported_languages.md

/home/charlie/Projects/WhisperLiveKit/docs/technical_integration.md
```markdown
# Technical Integration Guide

This document introduce how to reuse the core components when you do **not** want to ship the bundled frontend, FastAPI server, or even the provided CLI.

---

## 1. Runtime Components

| Layer | File(s) | Purpose |
|-------|---------|---------|
| Transport | `whisperlivekit/basic_server.py`, any ASGI/WebSocket server | Accepts audio over WebSocket (MediaRecorder WebM or raw PCM chunks) and streams JSON updates back |
| Audio processing | `whisperlivekit/audio_processor.py` | Buffers audio, orchestrates transcription, diarization, translation, handles FFmpeg/PCM input |
| Engines | `whisperlivekit/core.py`, `whisperlivekit/simul_whisper/*`, `whisperlivekit/local_agreement/*` | Load models once (SimulStreaming or LocalAgreement), expose `TranscriptionEngine` and helpers |
| Frontends | `whisperlivekit/web/*`, `chrome-extension/*` | Optional UI layers feeding the WebSocket endpoint |

**Key idea:** The server boundary is just `AudioProcessor.process_audio()` for incoming bytes and the async generator returned by `AudioProcessor.create_tasks()` for outgoing updates (`FrontData`). Everything else is optional.

---

## 2. Running Without the Bundled Frontend

1. Start the server/engine however you like:
   ```bash
   wlk --model small --language en --host 0.0.0.0 --port 9000
   # or launch your own app that instantiates TranscriptionEngine(...)
   ```
2. Build your own client (browser, mobile, desktop) that:
   - Opens `ws(s)://<host>:<port>/asr`
   - Sends either MediaRecorder/Opus WebM blobs **or** raw PCM (`--pcm-input` on the server tells the client to use the AudioWorklet).
   - Consumes the JSON payload defined in `docs/API.md`.

---

## 3. Running Without FastAPI

`whisperlivekit/basic_server.py` is just an example. Any async framework works, as long as you:

1. Create a global `TranscriptionEngine` (expensive to initialize; reuse it).
2. Instantiate `AudioProcessor(transcription_engine=engine)` for each connection.
3. Call `create_tasks()` to get the async generator, `process_audio()` with incoming bytes, and ensure `cleanup()` runs when the client disconnects.


If you prefer to send compressed audio, instantiate `AudioProcessor(pcm_input=False)` and pipe encoded chunks through `FFmpegManager` transparently. Just ensure `ffmpeg` is available.
```
technical_integration.md

/home/charlie/Projects/WhisperLiveKit/docs/troubleshooting.md
```markdown
# Troubleshooting


## GPU drivers & cuDNN visibility

### Linux error: `Unable to load libcudnn_ops.so* / cudnnCreateTensorDescriptor`
> Reported in issue #271 (Arch/CachyOS)

`faster-whisper` (used for the SimulStreaming encoder) dynamically loads cuDNN.  
If the runtime cannot find `libcudnn_*`, verify that CUDA and cuDNN match the PyTorch build you installed:

1. **Install CUDA + cuDNN** (Arch/CachyOS example):
   ```bash
   sudo pacman -S cuda cudnn
   sudo ldconfig
   ```
2. **Make sure the shared objects are visible**:
   ```bash
   ls /usr/lib/libcudnn*
   ```
3. **Check what CUDA version PyTorch expects** and match that with the driver you installed:
   ```bash
   python - <<'EOF'
   import torch
   print(torch.version.cuda)
   EOF
   nvcc --version
   ```
4. If you installed CUDA in a non-default location, export `CUDA_HOME` and add `$CUDA_HOME/lib64` to `LD_LIBRARY_PATH`.

Once the CUDA/cuDNN versions match, `whisperlivekit-server` starts normally.

### Windows error: `Could not locate cudnn_ops64_9.dll`
> Reported in issue #286 (Conda on Windows)

PyTorch bundles cuDNN DLLs inside your environment (`<env>\Lib\site-packages\torch\lib`).  
When `ctranslate2` or `faster-whisper` cannot find `cudnn_ops64_9.dll`:

1. Locate the DLL shipped with PyTorch, e.g.
   ```
   E:\conda\envs\WhisperLiveKit\Lib\site-packages\torch\lib\cudnn_ops64_9.dll
   ```
2. Add that directory to your `PATH` **or** copy the `cudnn_*64_9.dll` files into a directory that is already on `PATH` (such as the environment's `Scripts/` folder).
3. Restart the shell before launching `wlk`.

Installing NVIDIA's standalone cuDNN 9.x and pointing `PATH`/`CUDNN_PATH` to it works as well, but is usually not required.

---

## PyTorch / CTranslate2 GPU builds

### `Torch not compiled with CUDA enabled`
> Reported in issue #284

If `torch.zeros(1).cuda()` raises that assertion it means you installed a CPU-only wheel.  
Install the GPU-enabled wheels that match your CUDA toolkit:

```bash
pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
```

Replace `cu130` with the CUDA version supported by your driver (see [PyTorch install selector](https://pytorch.org/get-started/locally/)).  
Validate with:

```python
import torch
print(torch.cuda.is_available(), torch.cuda.get_device_name())
```

### `CTranslate2 device count: 0` or `Could not infer dtype of ctranslate2._ext.StorageView`
> Follow-up in issue #284

`ctranslate2` publishes separate CPU and CUDA wheels. The default `pip install ctranslate2` brings the CPU build, which makes WhisperLiveKit fall back to CPU tensors and leads to the dtype error above.

1. Uninstall the CPU build: `pip uninstall -y ctranslate2`.
2. Install the CUDA wheel that matches your toolkit (example for CUDA 13.0):
   ```bash
   pip install ctranslate2==4.5.0 -f https://opennmt.net/ctranslate2/whl/cu130
   ```
   (See the [CTranslate2 installation table](https://opennmt.net/CTranslate2/installation.html) for other CUDA versions.)
3. Verify:
   ```python
   import ctranslate2
   print("CUDA devices:", ctranslate2.get_cuda_device_count())
   print("CUDA compute types:", ctranslate2.get_supported_compute_types("cuda", 0))
   ```

**Note for aarch64 systems (e.g., NVIDIA DGX Spark):** Pre-built CUDA wheels may not be available for all CUDA versions on ARM architectures. If the wheel installation fails, you may need to compile CTranslate2 from source with CUDA support enabled.

If you intentionally want CPU inference, run `wlk --backend whisper` to avoid mixing CPU-only CTranslate2 with a GPU Torch build.

---

## Hopper / Blackwell (`sm_121a`) systems
> Reported in issues #276 and #284 (NVIDIA DGX Spark)

CUDA 12.1a GPUs (e.g., NVIDIA GB10 on DGX Spark) ship before some toolchains know about the architecture ID, so Triton/PTXAS need manual configuration.

### Error: `ptxas fatal : Value 'sm_121a' is not defined for option 'gpu-name'`

If you encounter this error after compiling CTranslate2 from source on aarch64 systems, Triton's bundled `ptxas` may not support the `sm_121a` architecture. The solution is to replace Triton's `ptxas` with the system's CUDA `ptxas`:

```bash
# Find your Python environment's Triton directory
python -c "import triton; import os; print(os.path.dirname(triton.__file__))"

# Copy the system ptxas to Triton's backend directory
# Replace <triton_path> with the output above
cp /usr/local/cuda/bin/ptxas <triton_path>/backends/nvidia/bin/ptxas
```

For example, in a virtual environment:
```bash
cp /usr/local/cuda/bin/ptxas ~/wlk/lib/python3.12/site-packages/triton/backends/nvidia/bin/ptxas
```

**Note:** On DGX Spark systems, CUDA is typically already in `PATH` (`/usr/local/cuda/bin`), so explicit `CUDA_HOME` and `PATH` exports may not be necessary. Verify with `which ptxas` before copying.

### Alternative: Environment variable approach

If the above doesn't work, you can try setting environment variables (though this may not resolve the `sm_121a` issue on all systems):

```bash
export CUDA_HOME="/usr/local/cuda-13.0"
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:$LD_LIBRARY_PATH"

# Tell Triton where the new ptxas lives
export TRITON_PTXAS_PATH="$CUDA_HOME/bin/ptxas"

# Force PyTorch to JIT kernels for all needed architectures
export TORCH_CUDA_ARCH_LIST="8.0 9.0 10.0 12.0 12.1a"
```

After applying the fix, restart `wlk`. Incoming streams will now compile kernels targeting `sm_121a` without crashing.

---

Need help with another recurring issue? Open a GitHub discussion or PR and reference this document so we can keep it current.


```
troubleshooting.md

/home/charlie/Projects/WhisperLiveKit/whisperlivekit/__init__.py
```python
from .audio_processor import AudioProcessor
from .core import TranscriptionEngine
from .parse_args import parse_args
from .web.web_interface import get_inline_ui_html, get_web_interface_html

__all__ = [
    "TranscriptionEngine",
    "AudioProcessor",
    "parse_args",
    "get_web_interface_html",
    "get_inline_ui_html",
    "download_simulstreaming_backend",
]

```
__init__.py

/home/charlie/Projects/WhisperLiveKit/whisperlivekit/audio_processor.py
```python
import asyncio
import logging
import traceback
from time import time
from typing import Any, AsyncGenerator, List, Optional, Union

import numpy as np

from whisperlivekit.core import (TranscriptionEngine,
                                 online_diarization_factory, online_factory,
                                 online_translation_factory)
from whisperlivekit.ffmpeg_manager import FFmpegManager, FFmpegState
from whisperlivekit.silero_vad_iterator import FixedVADIterator, OnnxWrapper, load_jit_vad
from whisperlivekit.timed_objects import (ASRToken, ChangeSpeaker, FrontData,
                                          Segment, Silence, State, Transcript)
from whisperlivekit.tokens_alignment import TokensAlignment

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

SENTINEL = object() # unique sentinel object for end of stream marker
MIN_DURATION_REAL_SILENCE = 5

async def get_all_from_queue(queue: asyncio.Queue) -> Union[object, Silence, np.ndarray, List[Any]]:
    items: List[Any] = []

    first_item = await queue.get()
    queue.task_done()
    if first_item is SENTINEL:
        return first_item
    if isinstance(first_item, Silence):
        return first_item
    items.append(first_item)

    while True:
        if not queue._queue:
            break
        next_item = queue._queue[0]
        if next_item is SENTINEL:
            break
        if isinstance(next_item, Silence):
            break
        items.append(await queue.get())
        queue.task_done()
    if isinstance(items[0], np.ndarray):
        return np.concatenate(items)
    else: #translation
        return items

class AudioProcessor:
    """
    Processes audio streams for transcription and diarization.
    Handles audio processing, state management, and result formatting.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the audio processor with configuration, models, and state."""

        if 'transcription_engine' in kwargs and isinstance(kwargs['transcription_engine'], TranscriptionEngine):
            models = kwargs['transcription_engine']
        else:
            models = TranscriptionEngine(**kwargs)

        # Audio processing settings
        self.args = models.args
        self.sample_rate = 16000
        self.channels = 1
        self.samples_per_sec = int(self.sample_rate * self.args.min_chunk_size)
        self.bytes_per_sample = 2
        self.bytes_per_sec = self.samples_per_sec * self.bytes_per_sample
        self.max_bytes_per_sec = 32000 * 5  # 5 seconds of audio at 32 kHz
        self.is_pcm_input = self.args.pcm_input

        # State management
        self.is_stopping: bool = False
        self.current_silence: Optional[Silence] = None
        self.state: State = State()
        self.lock: asyncio.Lock = asyncio.Lock()
        self.sep: str = " "  # Default separator
        self.last_response_content: FrontData = FrontData()

        self.tokens_alignment: TokensAlignment = TokensAlignment(self.state, self.args, self.sep)
        self.beg_loop: Optional[float] = None

        # Models and processing
        self.asr: Any = models.asr
        self.vac: Optional[FixedVADIterator] = None

        if self.args.vac:
            if models.vac_session is not None:
                vac_model = OnnxWrapper(session=models.vac_session)
                self.vac = FixedVADIterator(vac_model)
            else:
                self.vac = FixedVADIterator(load_jit_vad())
        self.ffmpeg_manager: Optional[FFmpegManager] = None
        self.ffmpeg_reader_task: Optional[asyncio.Task] = None
        self._ffmpeg_error: Optional[str] = None

        if not self.is_pcm_input:
            self.ffmpeg_manager = FFmpegManager(
                sample_rate=self.sample_rate,
                channels=self.channels
            )
            async def handle_ffmpeg_error(error_type: str):
                logger.error(f"FFmpeg error: {error_type}")
                self._ffmpeg_error = error_type
            self.ffmpeg_manager.on_error_callback = handle_ffmpeg_error

        self.transcription_queue: Optional[asyncio.Queue] = asyncio.Queue() if self.args.transcription else None
        self.diarization_queue: Optional[asyncio.Queue] = asyncio.Queue() if self.args.diarization else None
        self.translation_queue: Optional[asyncio.Queue] = asyncio.Queue() if self.args.target_language else None
        self.pcm_buffer: bytearray = bytearray()
        self.total_pcm_samples: int = 0
        self.transcription_task: Optional[asyncio.Task] = None
        self.diarization_task: Optional[asyncio.Task] = None
        self.translation_task: Optional[asyncio.Task] = None
        self.watchdog_task: Optional[asyncio.Task] = None
        self.all_tasks_for_cleanup: List[asyncio.Task] = []

        self.transcription: Optional[Any] = None
        self.translation: Optional[Any] = None
        self.diarization: Optional[Any] = None

        if self.args.transcription:
            self.transcription = online_factory(self.args, models.asr)
            self.sep = self.transcription.asr.sep
        if self.args.diarization:
            self.diarization = online_diarization_factory(self.args, models.diarization_model)
        if models.translation_model:
            self.translation = online_translation_factory(self.args, models.translation_model)

    async def _push_silence_event(self) -> None:
        if self.transcription_queue:
            await self.transcription_queue.put(self.current_silence)
        if self.args.diarization and self.diarization_queue:
            await self.diarization_queue.put(self.current_silence)
        if self.translation_queue:
            await self.translation_queue.put(self.current_silence)

    async def _begin_silence(self) -> None:
        if self.current_silence:
            return
        now = time() - self.beg_loop
        self.current_silence = Silence(
            is_starting=True, start=now
        )
        await self._push_silence_event()

    async def _end_silence(self) -> None:
        if not self.current_silence:
            return
        now = time() - self.beg_loop
        self.current_silence.end = now
        self.current_silence.is_starting=False
        self.current_silence.has_ended=True
        self.current_silence.compute_duration()
        if self.current_silence.duration > MIN_DURATION_REAL_SILENCE:
            self.state.new_tokens.append(self.current_silence)
        await self._push_silence_event()
        self.current_silence = None

    async def _enqueue_active_audio(self, pcm_chunk: np.ndarray) -> None:
        if pcm_chunk is None or pcm_chunk.size == 0:
            return
        if self.transcription_queue:
            await self.transcription_queue.put(pcm_chunk.copy())
        if self.args.diarization and self.diarization_queue:
            await self.diarization_queue.put(pcm_chunk.copy())

    def _slice_before_silence(self, pcm_array: np.ndarray, chunk_sample_start: int, silence_sample: Optional[int]) -> Optional[np.ndarray]:
        if silence_sample is None:
            return None
        relative_index = int(silence_sample - chunk_sample_start)
        if relative_index <= 0:
            return None
        split_index = min(relative_index, len(pcm_array))
        if split_index <= 0:
            return None
        return pcm_array[:split_index]

    def convert_pcm_to_float(self, pcm_buffer: Union[bytes, bytearray]) -> np.ndarray:
        """Convert PCM buffer in s16le format to normalized NumPy array."""
        return np.frombuffer(pcm_buffer, dtype=np.int16).astype(np.float32) / 32768.0

    async def get_current_state(self) -> State:
        """Get current state."""
        async with self.lock:
            current_time = time()

            remaining_transcription = 0
            if self.state.end_buffer > 0:
                remaining_transcription = max(0, round(current_time - self.beg_loop - self.state.end_buffer, 1))

            remaining_diarization = 0
            if self.state.tokens:
                latest_end = max(self.state.end_buffer, self.state.tokens[-1].end if self.state.tokens else 0)
                remaining_diarization = max(0, round(latest_end - self.state.end_attributed_speaker, 1))

            self.state.remaining_time_transcription = remaining_transcription
            self.state.remaining_time_diarization = remaining_diarization

            return self.state

    async def ffmpeg_stdout_reader(self) -> None:
        """Read audio data from FFmpeg stdout and process it into the PCM pipeline."""
        beg = time()
        while True:
            try:
                if self.is_stopping:
                    logger.info("Stopping ffmpeg_stdout_reader due to stopping flag.")
                    break

                state = await self.ffmpeg_manager.get_state() if self.ffmpeg_manager else FFmpegState.STOPPED
                if state == FFmpegState.FAILED:
                    logger.error("FFmpeg is in FAILED state, cannot read data")
                    break
                elif state == FFmpegState.STOPPED:
                    logger.info("FFmpeg is stopped")
                    break
                elif state != FFmpegState.RUNNING:
                    await asyncio.sleep(0.1)
                    continue

                current_time = time()
                elapsed_time = max(0.0, current_time - beg)
                buffer_size = max(int(32000 * elapsed_time), 4096)  # dynamic read
                beg = current_time

                chunk = await self.ffmpeg_manager.read_data(buffer_size)
                if not chunk:
                    # No data currently available
                    await asyncio.sleep(0.05)
                    continue

                self.pcm_buffer.extend(chunk)
                await self.handle_pcm_data()

            except asyncio.CancelledError:
                logger.info("ffmpeg_stdout_reader cancelled.")
                break
            except Exception as e:
                logger.warning(f"Exception in ffmpeg_stdout_reader: {e}")
                logger.debug(f"Traceback: {traceback.format_exc()}")
                await asyncio.sleep(0.2)

        logger.info("FFmpeg stdout processing finished. Signaling downstream processors if needed.")
        if self.transcription_queue:
            await self.transcription_queue.put(SENTINEL)
        if self.diarization:
            await self.diarization_queue.put(SENTINEL)
        if self.translation:
            await self.translation_queue.put(SENTINEL)

    async def transcription_processor(self) -> None:
        """Process audio chunks for transcription."""
        cumulative_pcm_duration_stream_time = 0.0

        while True:
            try:
                # item = await self.transcription_queue.get()
                item = await get_all_from_queue(self.transcription_queue)
                if item is SENTINEL:
                    logger.debug("Transcription processor received sentinel. Finishing.")
                    break

                asr_internal_buffer_duration_s = len(getattr(self.transcription, 'audio_buffer', [])) / self.transcription.SAMPLING_RATE
                transcription_lag_s = max(0.0, time() - self.beg_loop - self.state.end_buffer)
                asr_processing_logs = f"internal_buffer={asr_internal_buffer_duration_s:.2f}s | lag={transcription_lag_s:.2f}s |"
                stream_time_end_of_current_pcm = cumulative_pcm_duration_stream_time
                new_tokens = []
                current_audio_processed_upto = self.state.end_buffer

                if isinstance(item, Silence):
                    if item.is_starting:
                        new_tokens, current_audio_processed_upto = await asyncio.to_thread(
                            self.transcription.start_silence
                        )
                        asr_processing_logs += f" + Silence starting"
                    if item.has_ended:
                        asr_processing_logs += f" + Silence of = {item.duration:.2f}s"
                        cumulative_pcm_duration_stream_time += item.duration
                        current_audio_processed_upto = cumulative_pcm_duration_stream_time
                        self.transcription.end_silence(item.duration, self.state.tokens[-1].end if self.state.tokens else 0)
                    if self.state.tokens:
                        asr_processing_logs += f" | last_end = {self.state.tokens[-1].end} |"
                    logger.info(asr_processing_logs)
                    new_tokens = new_tokens or []
                    current_audio_processed_upto = max(current_audio_processed_upto, stream_time_end_of_current_pcm)
                elif isinstance(item, ChangeSpeaker):
                    self.transcription.new_speaker(item)
                    continue
                elif isinstance(item, np.ndarray):
                    pcm_array = item
                    logger.info(asr_processing_logs)
                    cumulative_pcm_duration_stream_time += len(pcm_array) / self.sample_rate
                    stream_time_end_of_current_pcm = cumulative_pcm_duration_stream_time
                    self.transcription.insert_audio_chunk(pcm_array, stream_time_end_of_current_pcm)
                    new_tokens, current_audio_processed_upto = await asyncio.to_thread(self.transcription.process_iter)
                    new_tokens = new_tokens or []

                _buffer_transcript = self.transcription.get_buffer()
                buffer_text = _buffer_transcript.text

                if new_tokens:
                    validated_text = self.sep.join([t.text for t in new_tokens])
                    if buffer_text.startswith(validated_text):
                        _buffer_transcript.text = buffer_text[len(validated_text):].lstrip()

                candidate_end_times = [self.state.end_buffer]

                if new_tokens:
                    candidate_end_times.append(new_tokens[-1].end)

                if _buffer_transcript.end is not None:
                    candidate_end_times.append(_buffer_transcript.end)

                candidate_end_times.append(current_audio_processed_upto)

                async with self.lock:
                    self.state.tokens.extend(new_tokens)
                    self.state.buffer_transcription = _buffer_transcript
                    self.state.end_buffer = max(candidate_end_times)
                    self.state.new_tokens.extend(new_tokens)
                    self.state.new_tokens_buffer = _buffer_transcript

                if self.translation_queue:
                    for token in new_tokens:
                        await self.translation_queue.put(token)
            except Exception as e:
                logger.warning(f"Exception in transcription_processor: {e}")
                logger.warning(f"Traceback: {traceback.format_exc()}")
                if 'pcm_array' in locals() and pcm_array is not SENTINEL : # Check if pcm_array was assigned from queue
                    self.transcription_queue.task_done()

        if self.is_stopping:
            logger.info("Transcription processor finishing due to stopping flag.")
            if self.diarization_queue:
                await self.diarization_queue.put(SENTINEL)
            if self.translation_queue:
                await self.translation_queue.put(SENTINEL)

        logger.info("Transcription processor task finished.")


    async def diarization_processor(self) -> None:
        while True:
            try:
                item = await get_all_from_queue(self.diarization_queue)
                if item is SENTINEL:
                    break
                elif type(item) is Silence:
                    if item.has_ended:
                        self.diarization.insert_silence(item.duration)
                    continue
                self.diarization.insert_audio_chunk(item)
                diarization_segments = await self.diarization.diarize()
                diar_end = 0.0
                if diarization_segments:
                    diar_end = max(getattr(s, "end", 0.0) for s in diarization_segments)
                async with self.lock:
                    self.state.new_diarization = diarization_segments
                    self.state.end_attributed_speaker = max(self.state.end_attributed_speaker, diar_end)
            except Exception as e:
                logger.warning(f"Exception in diarization_processor: {e}")
                logger.warning(f"Traceback: {traceback.format_exc()}")
        logger.info("Diarization processor task finished.")

    async def translation_processor(self) -> None:
        # the idea is to ignore diarization for the moment. We use only transcription tokens.
        # And the speaker is attributed given the segments used for the translation
        # in the future we want to have different languages for each speaker etc, so it will be more complex.
        while True:
            try:
                item = await get_all_from_queue(self.translation_queue)
                if item is SENTINEL:
                    logger.debug("Translation processor received sentinel. Finishing.")
                    break
                elif type(item) is Silence:
                    if item.is_starting:
                        new_translation, new_translation_buffer = self.translation.validate_buffer_and_reset()
                    if item.has_ended:
                        self.translation.insert_silence(item.duration)
                        continue
                elif isinstance(item, ChangeSpeaker):
                    new_translation, new_translation_buffer = self.translation.validate_buffer_and_reset()
                    pass
                else:
                    self.translation.insert_tokens(item)
                    new_translation, new_translation_buffer = await asyncio.to_thread(self.translation.process)
                async with self.lock:
                    self.state.new_translation.append(new_translation)
                    self.state.new_translation_buffer = new_translation_buffer
            except Exception as e:
                logger.warning(f"Exception in translation_processor: {e}")
                logger.warning(f"Traceback: {traceback.format_exc()}")
        logger.info("Translation processor task finished.")

    async def results_formatter(self) -> AsyncGenerator[FrontData, None]:
        """Format processing results for output."""
        while True:
            try:
                if self._ffmpeg_error:
                    yield FrontData(status="error", error=f"FFmpeg error: {self._ffmpeg_error}")
                    self._ffmpeg_error = None
                    await asyncio.sleep(1)
                    continue

                self.tokens_alignment.update()
                lines, buffer_diarization_text, buffer_translation_text = self.tokens_alignment.get_lines(
                    diarization=self.args.diarization,
                    translation=bool(self.translation),
                    current_silence=self.current_silence
                )
                state = await self.get_current_state()

                buffer_transcription_text = state.buffer_transcription.text if state.buffer_transcription else ''

                response_status = "active_transcription"
                if not lines and not buffer_transcription_text and not buffer_diarization_text:
                    response_status = "no_audio_detected"

                response = FrontData(
                    status=response_status,
                    lines=lines,
                    buffer_transcription=buffer_transcription_text,
                    buffer_diarization=buffer_diarization_text,
                    buffer_translation=buffer_translation_text,
                    remaining_time_transcription=state.remaining_time_transcription,
                    remaining_time_diarization=state.remaining_time_diarization if self.args.diarization else 0
                )

                should_push = (response != self.last_response_content)
                if should_push:
                    yield response
                    self.last_response_content = response

                if self.is_stopping and self._processing_tasks_done():
                    logger.info("Results formatter: All upstream processors are done and in stopping state. Terminating.")
                    return

                await asyncio.sleep(0.05)

            except Exception as e:
                logger.warning(f"Exception in results_formatter. Traceback: {traceback.format_exc()}")
                await asyncio.sleep(0.5)

    async def create_tasks(self) -> AsyncGenerator[FrontData, None]:
        """Create and start processing tasks."""
        self.all_tasks_for_cleanup = []
        processing_tasks_for_watchdog: List[asyncio.Task] = []

        # If using FFmpeg (non-PCM input), start it and spawn stdout reader
        if not self.is_pcm_input:
            success = await self.ffmpeg_manager.start()
            if not success:
                logger.error("Failed to start FFmpeg manager")
                async def error_generator() -> AsyncGenerator[FrontData, None]:
                    yield FrontData(
                        status="error",
                        error="FFmpeg failed to start. Please check that FFmpeg is installed."
                    )
                return error_generator()
            self.ffmpeg_reader_task = asyncio.create_task(self.ffmpeg_stdout_reader())
            self.all_tasks_for_cleanup.append(self.ffmpeg_reader_task)
            processing_tasks_for_watchdog.append(self.ffmpeg_reader_task)

        if self.transcription:
            self.transcription_task = asyncio.create_task(self.transcription_processor())
            self.all_tasks_for_cleanup.append(self.transcription_task)
            processing_tasks_for_watchdog.append(self.transcription_task)

        if self.diarization:
            self.diarization_task = asyncio.create_task(self.diarization_processor())
            self.all_tasks_for_cleanup.append(self.diarization_task)
            processing_tasks_for_watchdog.append(self.diarization_task)

        if self.translation:
            self.translation_task = asyncio.create_task(self.translation_processor())
            self.all_tasks_for_cleanup.append(self.translation_task)
            processing_tasks_for_watchdog.append(self.translation_task)

        # Monitor overall system health
        self.watchdog_task = asyncio.create_task(self.watchdog(processing_tasks_for_watchdog))
        self.all_tasks_for_cleanup.append(self.watchdog_task)

        return self.results_formatter()

    async def watchdog(self, tasks_to_monitor: List[asyncio.Task]) -> None:
        """Monitors the health of critical processing tasks."""
        tasks_remaining: List[asyncio.Task] = [task for task in tasks_to_monitor if task]
        while True:
            try:
                if not tasks_remaining:
                    logger.info("Watchdog task finishing: all monitored tasks completed.")
                    return

                await asyncio.sleep(10)

                for i, task in enumerate(list(tasks_remaining)):
                    if task.done():
                        exc = task.exception()
                        task_name = task.get_name() if hasattr(task, 'get_name') else f"Monitored Task {i}"
                        if exc:
                            logger.error(f"{task_name} unexpectedly completed with exception: {exc}")
                        else:
                            logger.info(f"{task_name} completed normally.")
                        tasks_remaining.remove(task)

            except asyncio.CancelledError:
                logger.info("Watchdog task cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in watchdog task: {e}", exc_info=True)

    async def cleanup(self) -> None:
        """Clean up resources when processing is complete."""
        logger.info("Starting cleanup of AudioProcessor resources.")
        self.is_stopping = True
        for task in self.all_tasks_for_cleanup:
            if task and not task.done():
                task.cancel()

        created_tasks = [t for t in self.all_tasks_for_cleanup if t]
        if created_tasks:
            await asyncio.gather(*created_tasks, return_exceptions=True)
        logger.info("All processing tasks cancelled or finished.")

        if not self.is_pcm_input and self.ffmpeg_manager:
            try:
                await self.ffmpeg_manager.stop()
                logger.info("FFmpeg manager stopped.")
            except Exception as e:
                logger.warning(f"Error stopping FFmpeg manager: {e}")
        if self.diarization:
            self.diarization.close()
        logger.info("AudioProcessor cleanup complete.")

    def _processing_tasks_done(self) -> bool:
        """Return True when all active processing tasks have completed."""
        tasks_to_check = [
            self.transcription_task,
            self.diarization_task,
            self.translation_task,
            self.ffmpeg_reader_task,
        ]
        return all(task.done() for task in tasks_to_check if task)


    async def process_audio(self, message: Optional[bytes]) -> None:
        """Process incoming audio data."""

        if not self.beg_loop:
            self.beg_loop = time()
            self.current_silence = Silence(start=0.0, is_starting=True)
            self.tokens_alignment.beg_loop = self.beg_loop

        if not message:
            logger.info("Empty audio message received, initiating stop sequence.")
            self.is_stopping = True

            if self.transcription_queue:
                await self.transcription_queue.put(SENTINEL)

            if not self.is_pcm_input and self.ffmpeg_manager:
                await self.ffmpeg_manager.stop()

            return

        if self.is_stopping:
            logger.warning("AudioProcessor is stopping. Ignoring incoming audio.")
            return

        if self.is_pcm_input:
            self.pcm_buffer.extend(message)
            await self.handle_pcm_data()
        else:
            if not self.ffmpeg_manager:
                logger.error("FFmpeg manager not initialized for non-PCM input.")
                return
            success = await self.ffmpeg_manager.write_data(message)
            if not success:
                ffmpeg_state = await self.ffmpeg_manager.get_state()
                if ffmpeg_state == FFmpegState.FAILED:
                    logger.error("FFmpeg is in FAILED state, cannot process audio")
                else:
                    logger.warning("Failed to write audio data to FFmpeg")

    async def handle_pcm_data(self) -> None:
        # Process when enough data
        if len(self.pcm_buffer) < self.bytes_per_sec:
            return

        if len(self.pcm_buffer) > self.max_bytes_per_sec:
            logger.warning(
                f"Audio buffer too large: {len(self.pcm_buffer) / self.bytes_per_sec:.2f}s. "
                f"Consider using a smaller model."
            )

        chunk_size = min(len(self.pcm_buffer), self.max_bytes_per_sec)
        aligned_chunk_size = (chunk_size // self.bytes_per_sample) * self.bytes_per_sample

        if aligned_chunk_size == 0:
            return
        pcm_array = self.convert_pcm_to_float(self.pcm_buffer[:aligned_chunk_size])
        self.pcm_buffer = self.pcm_buffer[aligned_chunk_size:]

        num_samples = len(pcm_array)
        chunk_sample_start = self.total_pcm_samples
        chunk_sample_end = chunk_sample_start + num_samples

        res = None
        if self.args.vac:
            res = self.vac(pcm_array)

        if res is not None:
            if "start" in res and self.current_silence:
                await self._end_silence()

            if "end" in res and not self.current_silence:
                pre_silence_chunk = self._slice_before_silence(
                    pcm_array, chunk_sample_start, res.get("end")
                )
                if pre_silence_chunk is not None and pre_silence_chunk.size > 0:
                    await self._enqueue_active_audio(pre_silence_chunk)
                await self._begin_silence()

        if not self.current_silence:
            await self._enqueue_active_audio(pcm_array)

        self.total_pcm_samples = chunk_sample_end

        if not self.args.transcription and not self.args.diarization:
            await asyncio.sleep(0.1)

```
audio_processor.py

/home/charlie/Projects/WhisperLiveKit/whisperlivekit/backend_support.py
```python
import importlib.util
import logging
import platform

logger = logging.getLogger(__name__)


def module_available(module_name):
    """Return True if the given module can be imported."""
    return importlib.util.find_spec(module_name) is not None


def mlx_backend_available(warn_on_missing = False):
    is_macos = platform.system() == "Darwin"
    is_arm = platform.machine() == "arm64"
    available = (
        is_macos
        and is_arm
        and module_available("mlx_whisper")
    )
    if not available and warn_on_missing and is_macos and is_arm:
        logger.warning(
            "=" * 50
            + "\nMLX Whisper not found but you are on Apple Silicon. "
              "Consider installing mlx-whisper for better performance: "
              "`pip install mlx-whisper`\n"
            + "=" * 50
        )
    return available


def faster_backend_available(warn_on_missing = False):
    available = module_available("faster_whisper")
    if not available and warn_on_missing and platform.system() != "Darwin":
        logger.warning(
            "=" * 50
            + "\nFaster-Whisper not found. Consider installing faster-whisper "
              "for better performance: `pip install faster-whisper`\n"
            + "=" * 50
        )
    return available

```
backend_support.py

/home/charlie/Projects/WhisperLiveKit/whisperlivekit/basic_server.py
```python
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from whisperlivekit import (AudioProcessor, TranscriptionEngine,
                            get_inline_ui_html, parse_args)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.getLogger().setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

args = parse_args()
transcription_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):    
    global transcription_engine
    transcription_engine = TranscriptionEngine(
        **vars(args),
    )
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def get():
    return HTMLResponse(get_inline_ui_html())


async def handle_websocket_results(websocket, results_generator):
    """Consumes results from the audio processor and sends them via WebSocket."""
    try:
        async for response in results_generator:
            await websocket.send_json(response.to_dict())
        # when the results_generator finishes it means all audio has been processed
        logger.info("Results generator finished. Sending 'ready_to_stop' to client.")
        await websocket.send_json({"type": "ready_to_stop"})
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected while handling results (client likely closed connection).")
    except Exception as e:
        logger.exception(f"Error in WebSocket results handler: {e}")


@app.websocket("/asr")
async def websocket_endpoint(websocket: WebSocket):
    global transcription_engine
    audio_processor = AudioProcessor(
        transcription_engine=transcription_engine,
    )
    await websocket.accept()
    logger.info("WebSocket connection opened.")

    try:
        await websocket.send_json({"type": "config", "useAudioWorklet": bool(args.pcm_input)})
    except Exception as e:
        logger.warning(f"Failed to send config to client: {e}")
            
    results_generator = await audio_processor.create_tasks()
    websocket_task = asyncio.create_task(handle_websocket_results(websocket, results_generator))

    try:
        while True:
            message = await websocket.receive_bytes()
            await audio_processor.process_audio(message)
    except KeyError as e:
        if 'bytes' in str(e):
            logger.warning(f"Client has closed the connection.")
        else:
            logger.error(f"Unexpected KeyError in websocket_endpoint: {e}", exc_info=True)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client during message receiving loop.")
    except Exception as e:
        logger.error(f"Unexpected error in websocket_endpoint main loop: {e}", exc_info=True)
    finally:
        logger.info("Cleaning up WebSocket endpoint...")
        if not websocket_task.done():
            websocket_task.cancel()
        try:
            await websocket_task
        except asyncio.CancelledError:
            logger.info("WebSocket results handler task was cancelled.")
        except Exception as e:
            logger.warning(f"Exception while awaiting websocket_task completion: {e}")
            
        await audio_processor.cleanup()
        logger.info("WebSocket endpoint cleaned up successfully.")

def main():
    """Entry point for the CLI command."""
    import uvicorn
    
    uvicorn_kwargs = {
        "app": "whisperlivekit.basic_server:app",
        "host":args.host, 
        "port":args.port, 
        "reload": False,
        "log_level": "info",
        "lifespan": "on",
    }
    
    ssl_kwargs = {}
    if args.ssl_certfile or args.ssl_keyfile:
        if not (args.ssl_certfile and args.ssl_keyfile):
            raise ValueError("Both --ssl-certfile and --ssl-keyfile must be specified together.")
        ssl_kwargs = {
            "ssl_certfile": args.ssl_certfile,
            "ssl_keyfile": args.ssl_keyfile
        }

    if ssl_kwargs:
        uvicorn_kwargs = {**uvicorn_kwargs, **ssl_kwargs}
    if args.forwarded_allow_ips:
        uvicorn_kwargs = { **uvicorn_kwargs, "forwarded_allow_ips" : args.forwarded_allow_ips }

    uvicorn.run(**uvicorn_kwargs)

if __name__ == "__main__":
    main()

```
basic_server.py

/home/charlie/Projects/WhisperLiveKit/whisperlivekit/core.py
```python
import logging
import sys
from argparse import Namespace

from whisperlivekit.local_agreement.online_asr import OnlineASRProcessor
from whisperlivekit.local_agreement.whisper_online import backend_factory
from whisperlivekit.simul_whisper import SimulStreamingASR


def update_with_kwargs(_dict, kwargs):
    _dict.update({
        k: v for k, v in kwargs.items() if k in _dict
    })
    return _dict


logger = logging.getLogger(__name__)

class TranscriptionEngine:
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, **kwargs):
        if TranscriptionEngine._initialized:
            return

        global_params = {
            "host": "localhost",
            "port": 8000,
            "diarization": False,
            "punctuation_split": False,
            "target_language": "",
            "vac": True,
            "vac_chunk_size": 0.04,
            "log_level": "DEBUG",
            "ssl_certfile": None,
            "ssl_keyfile": None,
            "forwarded_allow_ips": None,
            "transcription": True,
            "vad": True,
            "pcm_input": False,
            "disable_punctuation_split" : False,
            "diarization_backend": "sortformer",
            "backend_policy": "simulstreaming",
            "backend": "auto",
        }
        global_params = update_with_kwargs(global_params, kwargs)

        transcription_common_params = {
            "warmup_file": None,
            "min_chunk_size": 0.1,
            "model_size": "base",
            "model_cache_dir": None,
            "model_dir": None,
            "model_path": None,
            "lora_path": None,
            "lan": "auto",
            "direct_english_translation": False,
        }
        transcription_common_params = update_with_kwargs(transcription_common_params, kwargs)                                            

        if transcription_common_params['model_size'].endswith(".en"):
            transcription_common_params["lan"] = "en"
        if 'no_transcription' in kwargs:
            global_params['transcription'] = not global_params['no_transcription']
        if 'no_vad' in kwargs:
            global_params['vad'] = not kwargs['no_vad']
        if 'no_vac' in kwargs:
            global_params['vac'] = not kwargs['no_vac']

        self.args = Namespace(**{**global_params, **transcription_common_params})
        
        self.asr = None
        self.tokenizer = None
        self.diarization = None
        self.vac_session = None
        
        if self.args.vac:
            from whisperlivekit.silero_vad_iterator import is_onnx_available
            
            if is_onnx_available():
                from whisperlivekit.silero_vad_iterator import load_onnx_session
                self.vac_session = load_onnx_session()
            else:
                logger.warning(
                    "onnxruntime not installed. VAC will use JIT model which is loaded per-session. "
                    "For multi-user scenarios, install onnxruntime: pip install onnxruntime"
                )
        backend_policy = self.args.backend_policy
        if self.args.transcription:
            if backend_policy == "simulstreaming":                 
                simulstreaming_params = {
                    "disable_fast_encoder": False,
                    "custom_alignment_heads": None,
                    "frame_threshold": 25,
                    "beams": 1,
                    "decoder_type": None,
                    "audio_max_len": 20.0,
                    "audio_min_len": 0.0,
                    "cif_ckpt_path": None,
                    "never_fire": False,
                    "init_prompt": None,
                    "static_init_prompt": None,
                    "max_context_tokens": None,
                }
                simulstreaming_params = update_with_kwargs(simulstreaming_params, kwargs)
                
                self.tokenizer = None        
                self.asr = SimulStreamingASR(
                    **transcription_common_params,
                    **simulstreaming_params,
                    backend=self.args.backend,
                )
                logger.info(
                    "Using SimulStreaming policy with %s backend",
                    getattr(self.asr, "encoder_backend", "whisper"),
                )
            else:
                
                whisperstreaming_params = {
                    "buffer_trimming": "segment",
                    "confidence_validation": False,
                    "buffer_trimming_sec": 15,
                }
                whisperstreaming_params = update_with_kwargs(whisperstreaming_params, kwargs)
                
                self.asr = backend_factory(
                    backend=self.args.backend,
                    **transcription_common_params,
                    **whisperstreaming_params,
                )
                logger.info(
                    "Using LocalAgreement policy with %s backend",
                    getattr(self.asr, "backend_choice", self.asr.__class__.__name__),
                )

        if self.args.diarization:
            if self.args.diarization_backend == "diart":
                from whisperlivekit.diarization.diart_backend import \
                    DiartDiarization
                diart_params = {
                    "segmentation_model": "pyannote/segmentation-3.0",
                    "embedding_model": "pyannote/embedding",
                }
                diart_params = update_with_kwargs(diart_params, kwargs)
                self.diarization_model = DiartDiarization(
                    block_duration=self.args.min_chunk_size,
                    **diart_params
                )
            elif self.args.diarization_backend == "sortformer":
                from whisperlivekit.diarization.sortformer_backend import \
                    SortformerDiarization
                self.diarization_model = SortformerDiarization()
        
        self.translation_model = None
        if self.args.target_language:
            if self.args.lan == 'auto' and backend_policy != "simulstreaming":
                raise Exception('Translation cannot be set with language auto when transcription backend is not simulstreaming')
            else:
                try:
                    from nllw import load_model
                except:
                    raise Exception('To use translation, you must install nllw: `pip install nllw`')
                translation_params = { 
                    "nllb_backend": "transformers",
                    "nllb_size": "600M"
                }
                translation_params = update_with_kwargs(translation_params, kwargs)
                self.translation_model = load_model([self.args.lan], **translation_params) #in the future we want to handle different languages for different speakers
        TranscriptionEngine._initialized = True


def online_factory(args, asr):
    if args.backend_policy == "simulstreaming":
        from whisperlivekit.simul_whisper import SimulStreamingOnlineProcessor
        return SimulStreamingOnlineProcessor(asr)
    return OnlineASRProcessor(asr)
  
  
def online_diarization_factory(args, diarization_backend):
    if args.diarization_backend == "diart":
        online = diarization_backend
        # Not the best here, since several user/instances will share the same backend, but diart is not SOTA anymore and sortformer is recommended
    
    if args.diarization_backend == "sortformer":
        from whisperlivekit.diarization.sortformer_backend import \
            SortformerDiarizationOnline
        online = SortformerDiarizationOnline(shared_model=diarization_backend)
    return online


def online_translation_factory(args, translation_model):
    #should be at speaker level in the future:
    #one shared nllb model for all speaker
    #one tokenizer per speaker/language
    from nllw import OnlineTranslation
    return OnlineTranslation(translation_model, [args.lan], [args.target_language])

```
core.py

/home/charlie/Projects/WhisperLiveKit/whisperlivekit/web/live_transcription.css
```css
:root {
  --bg: #ffffff;
  --text: #111111;
  --muted: #666666;
  --border: #e5e5e5;
  --chip-bg: rgba(0, 0, 0, 0.04);
  --chip-text: #000000;
  --spinner-border: #8d8d8d5c;
  --spinner-top: #b0b0b0;
  --silence-bg: #f3f3f3;
  --loading-bg: rgba(255, 77, 77, 0.06);
  --button-bg: #ffffff;
  --button-border: #e9e9e9;
  --wave-stroke: #000000;
  --label-dia-text: #868686;
  --label-trans-text: #111111;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0b0b0b;
    --text: #e6e6e6;
    --muted: #9aa0a6;
    --border: #333333;
    --chip-bg: rgba(255, 255, 255, 0.08);
    --chip-text: #e6e6e6;
    --spinner-border: #555555;
    --spinner-top: #dddddd;
    --silence-bg: #1a1a1a;
    --loading-bg: rgba(255, 77, 77, 0.12);
    --button-bg: #111111;
    --button-border: #333333;
    --wave-stroke: #e6e6e6;
    --label-dia-text: #b3b3b3;
    --label-trans-text: #ffffff;
  }
}

:root[data-theme="dark"] {
  --bg: #0b0b0b;
  --text: #e6e6e6;
  --muted: #9aa0a6;
  --border: #333333;
  --chip-bg: rgba(255, 255, 255, 0.08);
  --chip-text: #e6e6e6;
  --spinner-border: #555555;
  --spinner-top: #dddddd;
  --silence-bg: #1a1a1a;
  --loading-bg: rgba(255, 77, 77, 0.12);
  --button-bg: #111111;
  --button-border: #333333;
  --wave-stroke: #e6e6e6;
  --label-dia-text: #b3b3b3;
  --label-trans-text: #ffffff;
}

:root[data-theme="light"] {
  --bg: #ffffff;
  --text: #111111;
  --muted: #666666;
  --border: #e5e5e5;
  --chip-bg: rgba(0, 0, 0, 0.04);
  --chip-text: #000000;
  --spinner-border: #8d8d8d5c;
  --spinner-top: #b0b0b0;
  --silence-bg: #f3f3f3;
  --loading-bg: rgba(255, 77, 77, 0.06);
  --button-bg: #ffffff;
  --button-border: #e9e9e9;
  --wave-stroke: #000000;
  --label-dia-text: #868686;
  --label-trans-text: #111111;
}

html.is-extension
{
    width: 350px;
    height: 500px;
}

body {
  font-family: ui-sans-serif, system-ui, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji';
  margin: 0;
  text-align: center;
  background-color: var(--bg);
  color: var(--text);
  height: 100vh;
  display: flex;
  flex-direction: column;
}

/* Record button */
#recordButton {
  width: 50px;
  height: 50px;
  border: none;
  border-radius: 50%;
  background-color: var(--button-bg);
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid var(--button-border);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

#recordButton.recording {
  width: 180px;
  border-radius: 40px;
  justify-content: flex-start;
  padding-left: 20px;
}

#recordButton:active {
  transform: scale(0.95);
}

.shape-container {
  width: 25px;
  height: 25px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.shape {
  width: 25px;
  height: 25px;
  background-color: rgb(209, 61, 53);
  border-radius: 50%;
  transition: all 0.3s ease;
}

#recordButton:disabled .shape {
  background-color: #6e6d6d;
}

#recordButton.recording .shape {
  border-radius: 5px;
  width: 25px;
  height: 25px;
}

/* Recording elements */
.recording-info {
  display: none;
  align-items: center;
  margin-left: 15px;
  flex-grow: 1;
}

#recordButton.recording .recording-info {
  display: flex;
}

.wave-container {
  width: 60px;
  height: 30px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

#waveCanvas {
  width: 100%;
  height: 100%;
}

.timer {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  margin-left: 10px;
}

#status {
  margin-top: 15px;
  font-size: 16px;
  color: var(--text);
  margin-bottom: 0;
}

.header-container {
  position: sticky;
  top: 0;
  background-color: var(--bg);
  z-index: 100;
  padding: 20px;
}

/* Settings */
.settings-container {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
  position: relative;
  flex-wrap: wrap;
}

.buttons-container {
  display: flex;
  align-items: center;
  gap: 15px;
}

.settings {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 12px;
}

.settings-toggle {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 50%;
  background-color: var(--button-bg);
  border: 1px solid var(--button-border);
  cursor: pointer;
  display: none;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.settings-toggle:hover {
  background-color: var(--chip-bg);
}

.settings-toggle.active {
  background-color: var(--chip-bg);
}

.settings-toggle img {
  width: 20px;
  height: 20px;
}

@media (max-width: 10000px) {
  .settings-toggle {
    display: flex;
  }
  
  .settings {
    display: none;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 12px;
  }
  
  .settings.visible {
    display: flex;
  }
}

@media (max-width: 600px) {
  .settings-container {
    flex-direction: column;
    align-items: center;
    gap: 10px;
  }
  
  .buttons-container {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 15px;
  }
}

.field {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 3px;
}

#chunkSelector,
#websocketInput,
#themeSelector,
#microphoneSelect {
  font-size: 16px;
  padding: 5px 8px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background-color: var(--button-bg);
  color: var(--text);
  max-height: 30px;
}

#microphoneSelect {
  width: 100%;
  max-width: 190px;
  min-width: 120px;
}

#chunkSelector:focus,
#websocketInput:focus,
#themeSelector:focus,
#microphoneSelect:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.15);
}

label {
  font-size: 13px;
  color: var(--muted);
}

.ws-default {
  font-size: 12px;
  color: var(--muted);
}

/* Segmented pill control for Theme */
.segmented {
  display: inline-flex;
  align-items: stretch;
  border: 1px solid var(--button-border);
  background-color: var(--button-bg);
  border-radius: 999px;
  overflow: hidden;
}

.segmented input[type="radio"] {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.theme-selector-container {
  display: flex;
  align-items: center;
  margin-top: 17px;
}

.segmented label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 14px;
  color: var(--muted);
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.segmented label span {
  display: none;
}

.segmented label:hover span {
  display: inline;
}

.segmented label:hover {
  background-color: var(--chip-bg);
}

.segmented img {
  width: 16px;
  height: 16px;
}

.segmented input[type="radio"]:checked + label {
  background-color: var(--chip-bg);
  color: var(--text);
}

.segmented input[type="radio"]:focus-visible + label,
.segmented input[type="radio"]:focus + label {
  outline: 2px solid #007bff;
  outline-offset: 2px;
  border-radius: 999px;
}

.transcript-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.transcript-container::-webkit-scrollbar {
  display: none;
}

/* Transcript area */
#linesTranscript {
  margin: 0 auto;
  max-width: 700px;
  text-align: left;
  font-size: 16px;
}

#linesTranscript p {
  margin: 0px 0;
}

#linesTranscript strong {
  color: var(--text);
}

#speaker {
  border: 1px solid var(--border);
  border-radius: 100px;
  padding: 2px 10px;
  font-size: 14px;
  margin-bottom: 0px;
}

.label_diarization {
  background-color: var(--chip-bg);
  border-radius: 100px;
  padding: 2px 10px;
  margin-left: 10px;
  display: inline-block;
  white-space: nowrap;
  font-size: 14px;
  margin-bottom: 0px;
  color: var(--label-dia-text);
}

.label_transcription {
  background-color: var(--chip-bg);
  border-radius: 100px;
  padding: 2px 10px;
  display: inline-block;
  white-space: nowrap;
  margin-left: 10px;
  font-size: 14px;
  margin-bottom: 0px;
  color: var(--label-trans-text);
}

.label_translation {
  background-color: var(--chip-bg);
  display: inline-flex;
  border-radius: 10px;
  padding: 4px 8px;
  margin-top: 4px;
  font-size: 14px;
  color: var(--text);
  align-items: flex-start;
  gap: 4px;
}

.lag-diarization-value {
    margin-left: 10px;
}

.label_translation img {
  margin-top: 2px;
}

.label_translation img {
  width: 12px;
  height: 12px;
}

#timeInfo {
  color: var(--muted);
  margin-left: 0px;
}

.textcontent {
  font-size: 16px;
  padding-left: 10px;
  margin-bottom: 10px;
  margin-top: 1px;
  padding-top: 5px;
  border-radius: 0px 0px 0px 10px;
}

.buffer_diarization {
  color: var(--label-dia-text);
}

.buffer_transcription {
  color: #7474748c;
  margin-left: 4px;
}

.buffer_translation {
  color: #a0a0a0;
  margin-left: 6px;
}

.spinner {
  display: inline-block;
  width: 8px;
  height: 8px;
  border: 2px solid var(--spinner-border);
  border-top: 2px solid var(--spinner-top);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  vertical-align: middle;
  margin-bottom: 2px;
  margin-right: 5px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.silence {
  color: var(--muted);
  background-color: var(--silence-bg);
  font-size: 13px;
  border-radius: 30px;
  padding: 2px 10px;
}

.loading {
  color: var(--muted);
  background-color: var(--loading-bg);
  border-radius: 8px 8px 8px 0px;
  padding: 2px 10px;
  font-size: 14px;
  margin-bottom: 0px;
}

/* for smaller screens */
@media (max-width: 200px) {
  .header-container {
    padding: 15px;
  }
  
  .settings-container {
    flex-direction: column;
    gap: 10px;
  }
  
  .buttons-container {
    gap: 10px;
  }
  
  .settings {
    justify-content: center;
    gap: 8px;
  }
  
  .field {
    align-items: center;
  }
  
  #websocketInput,
  #microphoneSelect {
    min-width: 100px;
    max-width: 160px;
  }
  
  .theme-selector-container {
    margin-top: 10px;
  }
  
  .transcript-container {
    padding: 15px;
  }
}

@media (max-width: 480px) {
  .header-container {
    padding: 10px;
  }
  
  .settings {
    flex-direction: column;
    align-items: center;
    gap: 6px;
  }
  
  #websocketInput,
  #microphoneSelect {
    max-width: 140px;
  }
  
  .segmented label {
    padding: 4px 8px;
    font-size: 12px;
  }
  
  .segmented img {
    width: 14px;
    height: 14px;
  }
  
  .transcript-container {
    padding: 10px;
  }
}

.label_language {
  background-color: var(--chip-bg);
  margin-bottom: 0px;
  border-radius: 100px;
  padding: 2px 8px;
  margin-left: 10px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: var(--muted);
}


.speaker-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  margin-left: -5px;
  border-radius: 50%;
  font-size: 11px;
  line-height: 1;
  font-weight: 800;
  color: var(--muted);
}

```
live_transcription.css

/home/charlie/Projects/WhisperLiveKit/whisperlivekit/web/live_transcription.html
```html
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>WhisperLiveKit</title>
    <link rel="stylesheet" href="live_transcription.css" />
</head>

<body>
    <div class="header-container">
        <div class="settings-container">
            <div class="buttons-container">
                <button id="recordButton">
                    <div class="shape-container">
                        <div class="shape"></div>
                    </div>
                    <div class="recording-info">
                        <div class="wave-container">
                            <canvas id="waveCanvas"></canvas>
                        </div>
                        <div class="timer">00:00</div>
                    </div>
                </button>

                <button id="settingsToggle" class="settings-toggle" title="Show/hide settings">
                    <img src="web/src/settings.svg" alt="Settings" />
                </button>
            </div>

            <div class="settings">
                <div class="field">
                    <label for="websocketInput">Websocket URL</label>
                    <input id="websocketInput" type="text" placeholder="ws://host:port/asr" />
                </div>

                <div class="field">
                    <label id="microphoneSelectLabel" for="microphoneSelect">Select Microphone</label>
                    <select id="microphoneSelect">
                        <option value="">Default Microphone</option>
                    </select>
                </div>

                <div class="theme-selector-container">
                    <div class="segmented" role="radiogroup" aria-label="Theme selector">
                        <input type="radio" id="theme-system" name="theme" value="system" />
                        <label for="theme-system" title="System">
                            <img src="/web/src/system_mode.svg" alt="" />
                            <span>System</span>
                        </label>

                        <input type="radio" id="theme-light" name="theme" value="light" />
                        <label for="theme-light" title="Light">
                            <img src="/web/src/light_mode.svg" alt="" />
                            <span>Light</span>
                        </label>

                        <input type="radio" id="theme-dark" name="theme" value="dark" />
                        <label for="theme-dark" title="Dark">
                            <img src="/web/src/dark_mode.svg" alt="" />
                            <span>Dark</span>
                        </label>
                    </div>
                </div>
            </div>
        </div>
        
        <p id="status"></p>
    </div>

    <div class="transcript-container">
        <div id="linesTranscript"></div>
    </div>

    <script src="live_transcription.js"></script>
</body>

</html>

```
live_transcription.html

/home/charlie/Projects/WhisperLiveKit/whisperlivekit/web/live_transcription.js
```javascript
const isExtension = typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.getURL;
if (isExtension) {
  document.documentElement.classList.add('is-extension');
}
const isWebContext = !isExtension;

let isRecording = false;
let websocket = null;
let recorder = null;
let chunkDuration = 100;
let websocketUrl = "ws://localhost:8000/asr";
let userClosing = false;
let wakeLock = null;
let startTime = null;
let timerInterval = null;
let audioContext = null;
let analyser = null;
let microphone = null;
let workletNode = null;
let recorderWorker = null;
let waveCanvas = document.getElementById("waveCanvas");
let waveCtx = waveCanvas.getContext("2d");
let animationFrame = null;
let waitingForStop = false;
let lastReceivedData = null;
let lastSignature = null;
let availableMicrophones = [];
let selectedMicrophoneId = null;
let serverUseAudioWorklet = null;
let configReadyResolve;
const configReady = new Promise((r) => (configReadyResolve = r));
let outputAudioContext = null;
let audioSource = null;

waveCanvas.width = 60 * (window.devicePixelRatio || 1);
waveCanvas.height = 30 * (window.devicePixelRatio || 1);
waveCtx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);

const statusText = document.getElementById("status");
const recordButton = document.getElementById("recordButton");
const chunkSelector = document.getElementById("chunkSelector");
const websocketInput = document.getElementById("websocketInput");
const websocketDefaultSpan = document.getElementById("wsDefaultUrl");
const linesTranscriptDiv = document.getElementById("linesTranscript");
const timerElement = document.querySelector(".timer");
const themeRadios = document.querySelectorAll('input[name="theme"]');
const microphoneSelect = document.getElementById("microphoneSelect");

const settingsToggle = document.getElementById("settingsToggle");
const settingsDiv = document.querySelector(".settings");

// if (isExtension) {
//   chrome.runtime.onInstalled.addListener((details) => {
//     if (details.reason.search(/install/g) === -1) {
//       return;
//     }
//     chrome.tabs.create({
//       url: chrome.runtime.getURL("welcome.html"),
//       active: true
//     });
//   });
// }

const translationIcon = `<svg xmlns="http://www.w3.org/2000/svg" height="12px" viewBox="0 -960 960 960" width="12px" fill="#5f6368"><path d="m603-202-34 97q-4 11-14 18t-22 7q-20 0-32.5-16.5T496-133l152-402q5-11 15-18t22-7h30q12 0 22 7t15 18l152 403q8 19-4 35.5T868-80q-13 0-22.5-7T831-106l-34-96H603ZM362-401 188-228q-11 11-27.5 11.5T132-228q-11-11-11-28t11-28l174-174q-35-35-63.5-80T190-640h84q20 39 40 68t48 58q33-33 68.5-92.5T484-720H80q-17 0-28.5-11.5T40-760q0-17 11.5-28.5T80-800h240v-40q0-17 11.5-28.5T360-880q17 0 28.5 11.5T400-840v40h240q17 0 28.5 11.5T680-760q0 17-11.5 28.5T640-720h-76q-21 72-63 148t-83 116l96 98-30 82-122-125Zm266 129h144l-72-204-72 204Z"/></svg>`
const silenceIcon = `<svg xmlns="http://www.w3.org/2000/svg" style="vertical-align: text-bottom;" height="14px" viewBox="0 -960 960 960" width="14px" fill="#5f6368"><path d="M514-556 320-752q9-3 19-5.5t21-2.5q66 0 113 47t47 113q0 11-1.5 22t-4.5 22ZM40-200v-32q0-33 17-62t47-44q51-26 115-44t141-18q26 0 49.5 2.5T456-392l-56-54q-9 3-19 4.5t-21 1.5q-66 0-113-47t-47-113q0-11 1.5-21t4.5-19L84-764q-11-11-11-28t11-28q12-12 28.5-12t27.5 12l675 685q11 11 11.5 27.5T816-80q-11 13-28 12.5T759-80L641-200h39q0 33-23.5 56.5T600-120H120q-33 0-56.5-23.5T40-200Zm80 0h480v-32q0-14-4.5-19.5T580-266q-36-18-92.5-36T360-320q-71 0-127.5 18T140-266q-9 5-14.5 14t-5.5 20v32Zm240 0Zm560-400q0 69-24.5 131.5T829-355q-12 14-30 15t-32-13q-13-13-12-31t12-33q30-38 46.5-85t16.5-98q0-51-16.5-97T767-781q-12-15-12.5-33t12.5-32q13-14 31.5-13.5T829-845q42 51 66.5 113.5T920-600Zm-182 0q0 32-10 61.5T700-484q-11 15-29.5 15.5T638-482q-13-13-13.5-31.5T633-549q6-11 9.5-24t3.5-27q0-14-3.5-27t-9.5-25q-9-17-8.5-35t13.5-31q14-14 32.5-13.5T700-716q18 25 28 54.5t10 61.5Z"/></svg>`;
const languageIcon = `<svg xmlns="http://www.w3.org/2000/svg" height="12" viewBox="0 -960 960 960" width="12" fill="#5f6368"><path d="M480-80q-82 0-155-31.5t-127.5-86Q143-252 111.5-325T80-480q0-83 31.5-155.5t86-127Q252-817 325-848.5T480-880q83 0 155.5 31.5t127 86q54.5 54.5 86 127T880-480q0 82-31.5 155t-86 127.5q-54.5 54.5-127 86T480-80Zm0-82q26-36 45-75t31-83H404q12 44 31 83t45 75Zm-104-16q-18-33-31.5-68.5T322-320H204q29 50 72.5 87t99.5 55Zm208 0q56-18 99.5-55t72.5-87H638q-9 38-22.5 73.5T584-178ZM170-400h136q-3-20-4.5-39.5T300-480q0-21 1.5-40.5T306-560H170q-5 20-7.5 39.5T160-480q0 21 2.5 40.5T170-400Zm216 0h188q3-20 4.5-39.5T580-480q0-21-1.5-40.5T574-560H386q-3 20-4.5 39.5T380-480q0 21 1.5 40.5T386-400Zm268 0h136q5-20 7.5-39.5T800-480q0-21-2.5-40.5T790-560H654q3 20 4.5 39.5T660-480q0 21-1.5 40.5T654-400Zm-16-240h118q-29-50-72.5-87T584-782q18 33 31.5 68.5T638-640Zm-234 0h152q-12-44-31-83t-45-75q-26 36-45 75t-31 83Zm-200 0h118q9-38 22.5-73.5T376-782q-56 18-99.5 55T204-640Z"/></svg>`
const speakerIcon = `<svg xmlns="http://www.w3.org/2000/svg" height="16px" style="vertical-align: text-bottom;" viewBox="0 -960 960 960" width="16px" fill="#5f6368"><path d="M480-480q-66 0-113-47t-47-113q0-66 47-113t113-47q66 0 113 47t47 113q0 66-47 113t-113 47ZM160-240v-32q0-34 17.5-62.5T224-378q62-31 126-46.5T480-440q66 0 130 15.5T736-378q29 15 46.5 43.5T800-272v32q0 33-23.5 56.5T720-160H240q-33 0-56.5-23.5T160-240Zm80 0h480v-32q0-11-5.5-20T700-306q-54-27-109-40.5T480-360q-56 0-111 13.5T260-306q-9 5-14.5 14t-5.5 20v32Zm240-320q33 0 56.5-23.5T560-640q0-33-23.5-56.5T480-720q-33 0-56.5 23.5T400-640q0 33 23.5 56.5T480-560Zm0-80Zm0 400Z"/></svg>`;

function getWaveStroke() {
  const styles = getComputedStyle(document.documentElement);
  const v = styles.getPropertyValue("--wave-stroke").trim();
  return v || "#000";
}

let waveStroke = getWaveStroke();
function updateWaveStroke() {
  waveStroke = getWaveStroke();
}

function applyTheme(pref) {
  if (pref === "light") {
    document.documentElement.setAttribute("data-theme", "light");
  } else if (pref === "dark") {
    document.documentElement.setAttribute("data-theme", "dark");
  } else {
    document.documentElement.removeAttribute("data-theme");
  }
  updateWaveStroke();
}

// Persisted theme preference
const savedThemePref = localStorage.getItem("themePreference") || "system";
applyTheme(savedThemePref);
if (themeRadios.length) {
  themeRadios.forEach((r) => {
    r.checked = r.value === savedThemePref;
    r.addEventListener("change", () => {
      if (r.checked) {
        localStorage.setItem("themePreference", r.value);
        applyTheme(r.value);
      }
    });
  });
}

// React to OS theme changes when in "system" mode
const darkMq = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)");
const handleOsThemeChange = () => {
  const pref = localStorage.getItem("themePreference") || "system";
  if (pref === "system") updateWaveStroke();
};
if (darkMq && darkMq.addEventListener) {
  darkMq.addEventListener("change", handleOsThemeChange);
} else if (darkMq && darkMq.addListener) {
  // deprecated, but included for Safari compatibility
  darkMq.addListener(handleOsThemeChange);
}

async function enumerateMicrophones() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach(track => track.stop());

    const devices = await navigator.mediaDevices.enumerateDevices();
    availableMicrophones = devices.filter(device => device.kind === 'audioinput');

    populateMicrophoneSelect();
    console.log(`Found ${availableMicrophones.length} microphone(s)`);
  } catch (error) {
    console.error('Error enumerating microphones:', error);
    statusText.textContent = "Error accessing microphones. Please grant permission.";
  }
}

function populateMicrophoneSelect() {
  if (!microphoneSelect) return;

  microphoneSelect.innerHTML = '<option value="">Default Microphone</option>';

  availableMicrophones.forEach((device, index) => {
    const option = document.createElement('option');
    option.value = device.deviceId;
    option.textContent = device.label || `Microphone ${index + 1}`;
    microphoneSelect.appendChild(option);
  });

  const savedMicId = localStorage.getItem('selectedMicrophone');
  if (savedMicId && availableMicrophones.some(mic => mic.deviceId === savedMicId)) {
    microphoneSelect.value = savedMicId;
    selectedMicrophoneId = savedMicId;
  }
}

function handleMicrophoneChange() {
  selectedMicrophoneId = microphoneSelect.value || null;
  localStorage.setItem('selectedMicrophone', selectedMicrophoneId || '');

  const selectedDevice = availableMicrophones.find(mic => mic.deviceId === selectedMicrophoneId);
  const deviceName = selectedDevice ? selectedDevice.label : 'Default Microphone';

  console.log(`Selected microphone: ${deviceName}`);
  statusText.textContent = `Microphone changed to: ${deviceName}`;

  if (isRecording) {
    statusText.textContent = "Switching microphone... Please wait.";
    stopRecording().then(() => {
      setTimeout(() => {
        toggleRecording();
      }, 1000);
    });
  }
}

// Helpers
function fmt1(x) {
  const n = Number(x);
  return Number.isFinite(n) ? n.toFixed(1) : x;
}

let host, port, protocol;
port = 8000;
if (isExtension) {
    host = "localhost";
    protocol = "ws";
} else {
    host = window.location.hostname || "localhost";
    port = window.location.port;
    protocol = window.location.protocol === "https:" ? "wss" : "ws";
}
const defaultWebSocketUrl = `${protocol}://${host}${port ? ":" + port : ""}/asr`;

// Populate default caption and input
if (websocketDefaultSpan) websocketDefaultSpan.textContent = defaultWebSocketUrl;
websocketInput.value = defaultWebSocketUrl;
websocketUrl = defaultWebSocketUrl;

// Optional chunk selector (guard for presence)
if (chunkSelector) {
  chunkSelector.addEventListener("change", () => {
    chunkDuration = parseInt(chunkSelector.value);
  });
}

// WebSocket input change handling
websocketInput.addEventListener("change", () => {
  const urlValue = websocketInput.value.trim();
  if (!urlValue.startsWith("ws://") && !urlValue.startsWith("wss://")) {
    statusText.textContent = "Invalid WebSocket URL (must start with ws:// or wss://)";
    return;
  }
  websocketUrl = urlValue;
  statusText.textContent = "WebSocket URL updated. Ready to connect.";
});

function setupWebSocket() {
  return new Promise((resolve, reject) => {
    try {
      websocket = new WebSocket(websocketUrl);
    } catch (error) {
      statusText.textContent = "Invalid WebSocket URL. Please check and try again.";
      reject(error);
      return;
    }

    websocket.onopen = () => {
      statusText.textContent = "Connected to server.";
      resolve();
    };

    websocket.onclose = () => {
      if (userClosing) {
        if (waitingForStop) {
          statusText.textContent = "Processing finalized or connection closed.";
          if (lastReceivedData) {
          renderLinesWithBuffer(
              lastReceivedData.lines || [],
              lastReceivedData.buffer_diarization || "",
              lastReceivedData.buffer_transcription || "",
              lastReceivedData.buffer_translation || "",
              0,
              0,
              true
            );
          }
        }
      } else {
        statusText.textContent = "Disconnected from the WebSocket server. (Check logs if model is loading.)";
        if (isRecording) {
          stopRecording();
        }
      }
      isRecording = false;
      waitingForStop = false;
      userClosing = false;
      lastReceivedData = null;
      websocket = null;
      updateUI();
    };

    websocket.onerror = () => {
      statusText.textContent = "Error connecting to WebSocket.";
      reject(new Error("Error connecting to WebSocket"));
    };

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "config") {
        serverUseAudioWorklet = !!data.useAudioWorklet;
        statusText.textContent = serverUseAudioWorklet
          ? "Connected. Using AudioWorklet (PCM)."
          : "Connected. Using MediaRecorder (WebM).";
        if (configReadyResolve) configReadyResolve();
        return;
      }

      if (data.type === "ready_to_stop") {
        console.log("Ready to stop received, finalizing display and closing WebSocket.");
        waitingForStop = false;

        if (lastReceivedData) {
          renderLinesWithBuffer(
            lastReceivedData.lines || [],
            lastReceivedData.buffer_diarization || "",
            lastReceivedData.buffer_transcription || "",
            lastReceivedData.buffer_translation || "",
            0,
            0,
            true
          );
        }
        statusText.textContent = "Finished processing audio! Ready to record again.";
        recordButton.disabled = false;

        if (websocket) {
          websocket.close();
        }
        return;
      }

      lastReceivedData = data;

      const {
        lines = [],
        buffer_transcription = "",
        buffer_diarization = "",
        buffer_translation = "",
        remaining_time_transcription = 0,
        remaining_time_diarization = 0,
        status = "active_transcription",
      } = data;

      renderLinesWithBuffer(
        lines,
        buffer_diarization,
        buffer_transcription,
        buffer_translation,
        remaining_time_diarization,
        remaining_time_transcription,
        false,
        status
      );
    };
  });
}

function renderLinesWithBuffer(
  lines,
  buffer_diarization,
  buffer_transcription,
  buffer_translation,
  remaining_time_diarization,
  remaining_time_transcription,
  isFinalizing = false,
  current_status = "active_transcription"
) {
  if (current_status === "no_audio_detected") {
    linesTranscriptDiv.innerHTML =
      "<p style='text-align: center; color: var(--muted); margin-top: 20px;'><em>No audio detected...</em></p>";
    return;
  }

  const showLoading = !isFinalizing && (lines || []).some((it) => it.speaker == 0);
  const showTransLag = !isFinalizing && remaining_time_transcription > 0;
  const showDiaLag = !isFinalizing && !!buffer_diarization && remaining_time_diarization > 0;
  const signature = JSON.stringify({
    lines: (lines || []).map((it) => ({ speaker: it.speaker, text: it.text, start: it.start, end: it.end, detected_language: it.detected_language })),
    buffer_transcription: buffer_transcription || "",
    buffer_diarization: buffer_diarization || "",
    buffer_translation: buffer_translation,
    status: current_status,
    showLoading,
    showTransLag,
    showDiaLag,
    isFinalizing: !!isFinalizing,
  });
  if (lastSignature === signature) {
    const t = document.querySelector(".lag-transcription-value");
    if (t) t.textContent = fmt1(remaining_time_transcription);
    const d = document.querySelector(".lag-diarization-value");
    if (d) d.textContent = fmt1(remaining_time_diarization);
    const ld = document.querySelector(".loading-diarization-value");
    if (ld) ld.textContent = fmt1(remaining_time_diarization);
    return;
  }
  lastSignature = signature;

  const linesHtml = (lines || [])
    .map((item, idx) => {
      let timeInfo = "";
      if (item.start !== undefined && item.end !== undefined) {
        timeInfo = ` ${item.start} - ${item.end}`;
      }

      let speakerLabel = "";
      if (item.speaker === -2) {
        speakerLabel = `<span class="silence">${silenceIcon}<span id='timeInfo'>${timeInfo}</span></span>`;
      } else if (item.speaker == 0 && !isFinalizing) {
        speakerLabel = `<span class='loading'><span class="spinner"></span><span id='timeInfo'><span class="loading-diarization-value">${fmt1(
          remaining_time_diarization
        )}</span> second(s) of audio are undergoing diarization</span></span>`;
      } else if (item.speaker !== 0) {
        const speakerNum = `<span class="speaker-badge">${item.speaker}</span>`;
        speakerLabel = `<span id="speaker">${speakerIcon}${speakerNum}<span id='timeInfo'>${timeInfo}</span></span>`;

        if (item.detected_language) {
          speakerLabel += `<span class="label_language">${languageIcon}<span>${item.detected_language}</span></span>`;
        }
      }

      let currentLineText = item.text || "";

      if (idx === lines.length - 1) {
        if (!isFinalizing && item.speaker !== -2) {
            speakerLabel += `<span class="label_transcription"><span class="spinner"></span>Transcription lag <span id='timeInfo'><span class="lag-transcription-value">${fmt1(
              remaining_time_transcription
            )}</span>s</span></span>`;

          if (buffer_diarization && remaining_time_diarization) {
            speakerLabel += `<span class="label_diarization"><span class="spinner"></span>Diarization lag<span id='timeInfo'><span class="lag-diarization-value">${fmt1(
              remaining_time_diarization
            )}</span>s</span></span>`;
          }
        }

        if (buffer_diarization) {
          if (isFinalizing) {
            currentLineText +=
              (currentLineText.length > 0 && buffer_diarization.trim().length > 0 ? " " : "") + buffer_diarization.trim();
          } else {
            currentLineText += `<span class="buffer_diarization">${buffer_diarization}</span>`;
          }
        }
        if (buffer_transcription) {
          if (isFinalizing) {
            currentLineText +=
              (currentLineText.length > 0 && buffer_transcription.trim().length > 0 ? " " : "") +
              buffer_transcription.trim();
          } else {
            currentLineText += `<span class="buffer_transcription">${buffer_transcription}</span>`;
          }
        }
      }
      let translationContent = "";
      if (item.translation) {
        translationContent += item.translation.trim();
      }
      if (idx === lines.length - 1 && buffer_translation) {
        const bufferPiece = isFinalizing
          ? buffer_translation
          : `<span class="buffer_translation">${buffer_translation}</span>`;
        translationContent += translationContent ? `${bufferPiece}` : bufferPiece;
      }
      if (translationContent.trim().length > 0) {
        currentLineText += `
            <div>
                <div class="label_translation">
                    ${translationIcon}
                    <span class="translation_text">${translationContent}</span>
                </div>
            </div>`;
      }

      return currentLineText.trim().length > 0 || speakerLabel.length > 0
        ? `<p>${speakerLabel}<br/><div class='textcontent'>${currentLineText}</div></p>`
        : `<p>${speakerLabel}<br/></p>`;
    })
    .join("");

  linesTranscriptDiv.innerHTML = linesHtml;
  const transcriptContainer = document.querySelector('.transcript-container');
  if (transcriptContainer) {
    transcriptContainer.scrollTo({ top: transcriptContainer.scrollHeight, behavior: "smooth" });
  }
}

function updateTimer() {
  if (!startTime) return;

  const elapsed = Math.floor((Date.now() - startTime) / 1000);
  const minutes = Math.floor(elapsed / 60).toString().padStart(2, "0");
  const seconds = (elapsed % 60).toString().padStart(2, "0");
  timerElement.textContent = `${minutes}:${seconds}`;
}

function drawWaveform() {
  if (!analyser) return;

  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);
  analyser.getByteTimeDomainData(dataArray);

  waveCtx.clearRect(
    0,
    0,
    waveCanvas.width / (window.devicePixelRatio || 1),
    waveCanvas.height / (window.devicePixelRatio || 1)
  );
  waveCtx.lineWidth = 1;
  waveCtx.strokeStyle = waveStroke;
  waveCtx.beginPath();

  const sliceWidth = (waveCanvas.width / (window.devicePixelRatio || 1)) / bufferLength;
  let x = 0;

  for (let i = 0; i < bufferLength; i++) {
    const v = dataArray[i] / 128.0;
    const y = (v * (waveCanvas.height / (window.devicePixelRatio || 1))) / 2;

    if (i === 0) {
      waveCtx.moveTo(x, y);
    } else {
      waveCtx.lineTo(x, y);
    }

    x += sliceWidth;
  }

  waveCtx.lineTo(
    waveCanvas.width / (window.devicePixelRatio || 1),
    (waveCanvas.height / (window.devicePixelRatio || 1)) / 2
  );
  waveCtx.stroke();

  animationFrame = requestAnimationFrame(drawWaveform);
}

async function startRecording() {
  try {
    try {
      wakeLock = await navigator.wakeLock.request("screen");
    } catch (err) {
      console.log("Error acquiring wake lock.");
    }

    let stream;
    
    // chromium extension. in the future, both chrome page audio and mic will be used
    if (isExtension) {
      try {
        stream = await new Promise((resolve, reject) => {
          chrome.tabCapture.capture({audio: true}, (s) => {
            if (s) {
              resolve(s);
            } else {
              reject(new Error('Tab capture failed or not available'));
            }
          });
        });
        
        try {
          outputAudioContext = new (window.AudioContext || window.webkitAudioContext)();
          audioSource = outputAudioContext.createMediaStreamSource(stream);
          audioSource.connect(outputAudioContext.destination);
        } catch (audioError) {
          console.warn('could not preserve system audio:', audioError);
        }
        
        statusText.textContent = "Using tab audio capture.";
      } catch (tabError) {
        console.log('Tab capture not available, falling back to microphone', tabError);
        const audioConstraints = selectedMicrophoneId
          ? { audio: { deviceId: { exact: selectedMicrophoneId } } }
          : { audio: true };
        stream = await navigator.mediaDevices.getUserMedia(audioConstraints);
        statusText.textContent = "Using microphone audio.";
      }
    } else if (isWebContext) {
      const audioConstraints = selectedMicrophoneId 
        ? { audio: { deviceId: { exact: selectedMicrophoneId } } }
        : { audio: true };
      stream = await navigator.mediaDevices.getUserMedia(audioConstraints);
    }

    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    microphone = audioContext.createMediaStreamSource(stream);
    microphone.connect(analyser);

    if (serverUseAudioWorklet) {
      if (!audioContext.audioWorklet) {
        throw new Error("AudioWorklet is not supported in this browser");
      }
      await audioContext.audioWorklet.addModule("/web/pcm_worklet.js");
      workletNode = new AudioWorkletNode(audioContext, "pcm-forwarder", { numberOfInputs: 1, numberOfOutputs: 0, channelCount: 1 });
      microphone.connect(workletNode);

      recorderWorker = new Worker("/web/recorder_worker.js");
      recorderWorker.postMessage({
        command: "init",
        config: {
          sampleRate: audioContext.sampleRate,
        },
      });

      recorderWorker.onmessage = (e) => {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
          websocket.send(e.data.buffer);
        }
      };

      workletNode.port.onmessage = (e) => {
        const data = e.data;
        const ab = data instanceof ArrayBuffer ? data : data.buffer;
        recorderWorker.postMessage(
          {
            command: "record",
            buffer: ab,
          },
          [ab]
        );
      };
    } else {
      try {
        recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      } catch (e) {
        recorder = new MediaRecorder(stream);
      }
      recorder.ondataavailable = (e) => {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
          if (e.data && e.data.size > 0) {
            websocket.send(e.data);
          }
        }
      };
      recorder.start(chunkDuration);
    }

    startTime = Date.now();
    timerInterval = setInterval(updateTimer, 1000);
    drawWaveform();

    isRecording = true;
    updateUI();
  } catch (err) {
    if (window.location.hostname === "0.0.0.0") {
      statusText.textContent =
        "Error accessing microphone. Browsers may block microphone access on 0.0.0.0. Try using localhost:8000 instead.";
    } else {
      statusText.textContent = "Error accessing microphone. Please allow microphone access.";
    }
    console.error(err);
  }
}

async function stopRecording() {
  if (wakeLock) {
    try {
      await wakeLock.release();
    } catch (e) {
      // ignore
    }
    wakeLock = null;
  }

  userClosing = true;
  waitingForStop = true;

  if (websocket && websocket.readyState === WebSocket.OPEN) {
    const emptyBlob = new Blob([], { type: "audio/webm" });
    websocket.send(emptyBlob);
    statusText.textContent = "Recording stopped. Processing final audio...";
  }

  if (recorder) {
    try {
      recorder.stop();
    } catch (e) {
    }
    recorder = null;
  }

  if (recorderWorker) {
    recorderWorker.terminate();
    recorderWorker = null;
  }
  
  if (workletNode) {
    try {
      workletNode.port.onmessage = null;
    } catch (e) {}
    try {
      workletNode.disconnect();
    } catch (e) {}
    workletNode = null;
  }

  if (microphone) {
    microphone.disconnect();
    microphone = null;
  }

  if (analyser) {
    analyser = null;
  }

  if (audioContext && audioContext.state !== "closed") {
    try {
      await audioContext.close();
    } catch (e) {
      console.warn("Could not close audio context:", e);
    }
    audioContext = null;
  }

  if (audioSource) {
    audioSource.disconnect();
    audioSource = null;
  }

  if (outputAudioContext && outputAudioContext.state !== "closed") {
    outputAudioContext.close()
    outputAudioContext = null;
  }

  if (animationFrame) {
    cancelAnimationFrame(animationFrame);
    animationFrame = null;
  }

  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
  timerElement.textContent = "00:00";
  startTime = null;

  isRecording = false;
  updateUI();
}

async function toggleRecording() {
  if (!isRecording) {
    if (waitingForStop) {
      console.log("Waiting for stop, early return");
      return;
    }
    console.log("Connecting to WebSocket");
    try {
      if (websocket && websocket.readyState === WebSocket.OPEN) {
        await configReady;
        await startRecording();
      } else {
        await setupWebSocket();
        await configReady;
        await startRecording();
      }
    } catch (err) {
      statusText.textContent = "Could not connect to WebSocket or access mic. Aborted.";
      console.error(err);
    }
  } else {
    console.log("Stopping recording");
    stopRecording();
  }
}

function updateUI() {
  recordButton.classList.toggle("recording", isRecording);
  recordButton.disabled = waitingForStop;

  if (waitingForStop) {
    if (statusText.textContent !== "Recording stopped. Processing final audio...") {
      statusText.textContent = "Please wait for processing to complete...";
    }
  } else if (isRecording) {
    statusText.textContent = "";
  } else {
    if (
      statusText.textContent !== "Finished processing audio! Ready to record again." &&
      statusText.textContent !== "Processing finalized or connection closed."
    ) {
      statusText.textContent = "Click to start transcription";
    }
  }
  if (!waitingForStop) {
    recordButton.disabled = false;
  }
}

recordButton.addEventListener("click", toggleRecording);

if (microphoneSelect) {
  microphoneSelect.addEventListener("change", handleMicrophoneChange);
}
document.addEventListener('DOMContentLoaded', async () => {
  try {
    await enumerateMicrophones();
  } catch (error) {
    console.log("Could not enumerate microphones on load:", error);
  }
});
navigator.mediaDevices.addEventListener('devicechange', async () => {
  console.log('Device change detected, re-enumerating microphones');
  try {
    await enumerateMicrophones();
  } catch (error) {
    console.log("Error re-enumerating microphones:", error);
  }
});


settingsToggle.addEventListener("click", () => {
settingsDiv.classList.toggle("visible");
settingsToggle.classList.toggle("active");
});

if (isExtension) {
  async function checkAndRequestPermissions() {
    const micPermission = await navigator.permissions.query({
      name: "microphone",
    });

    const permissionDisplay = document.getElementById("audioPermission");
    if (permissionDisplay) {
      permissionDisplay.innerText = `MICROPHONE: ${micPermission.state}`;
    }

    // if (micPermission.state !== "granted") {
    //   chrome.tabs.create({ url: "welcome.html" });
    // }

    const intervalId = setInterval(async () => {
      const micPermission = await navigator.permissions.query({
        name: "microphone",
      });
      if (micPermission.state === "granted") {
        if (permissionDisplay) {
          permissionDisplay.innerText = `MICROPHONE: ${micPermission.state}`;
        }
        clearInterval(intervalId);
      }
    }, 100);
  }

  void checkAndRequestPermissions();
}

```
live_transcription.js

/home/charlie/Projects/WhisperLiveKit/whisperlivekit/web/recorder_worker.js
```javascript
let sampleRate = 48000;
let targetSampleRate = 16000;

self.onmessage = function (e) {
  switch (e.data.command) {
    case 'init':
      init(e.data.config);
      break;
    case 'record':
      record(e.data.buffer);
      break;
  }
};

function init(config) {
  sampleRate = config.sampleRate;
  targetSampleRate = config.targetSampleRate || 16000;
}

function record(inputBuffer) {
  const buffer = new Float32Array(inputBuffer);
  const resampledBuffer = resample(buffer, sampleRate, targetSampleRate);
  const pcmBuffer = toPCM(resampledBuffer);
  self.postMessage({ buffer: pcmBuffer }, [pcmBuffer]);
}

function resample(buffer, from, to) {
    if (from === to) {
        return buffer;
    }
    const ratio = from / to;
    const newLength = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
        const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
        let accum = 0, count = 0;
        for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
            accum += buffer[i];
            count++;
        }
        result[offsetResult] = accum / count;
        offsetResult++;
        offsetBuffer = nextOffsetBuffer;
    }
    return result;
}

function toPCM(input) {
  const buffer = new ArrayBuffer(input.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }
  return buffer;
}

```
recorder_worker.js

/home/charlie/Projects/WhisperLiveKit/whisperlivekit/web/web_interface.py
```python
import base64
import importlib.resources as resources
import logging

logger = logging.getLogger(__name__)

def get_web_interface_html():
    """Loads the HTML for the web interface using importlib.resources."""
    try:
        with resources.files('whisperlivekit.web').joinpath('live_transcription.html').open('r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading web interface HTML: {e}")
        return "<html><body><h1>Error loading interface</h1></body></html>"

def get_inline_ui_html():
    """Returns the complete web interface HTML with all assets embedded in a single call."""
    try:
        with resources.files('whisperlivekit.web').joinpath('live_transcription.html').open('r', encoding='utf-8') as f:
            html_content = f.read()        
        with resources.files('whisperlivekit.web').joinpath('live_transcription.css').open('r', encoding='utf-8') as f:
            css_content = f.read()
        with resources.files('whisperlivekit.web').joinpath('live_transcription.js').open('r', encoding='utf-8') as f:
            js_content = f.read()
        
        with resources.files('whisperlivekit.web').joinpath('pcm_worklet.js').open('r', encoding='utf-8') as f:
            worklet_code = f.read()
        with resources.files('whisperlivekit.web').joinpath('recorder_worker.js').open('r', encoding='utf-8') as f:
            worker_code = f.read()
        
        js_content = js_content.replace(
            'await audioContext.audioWorklet.addModule("/web/pcm_worklet.js");',
            'const workletBlob = new Blob([`' + worklet_code + '`], { type: "application/javascript" });\n' +
            'const workletUrl = URL.createObjectURL(workletBlob);\n' +
            'await audioContext.audioWorklet.addModule(workletUrl);'
        )
        js_content = js_content.replace(
            'recorderWorker = new Worker("/web/recorder_worker.js");',
            'const workerBlob = new Blob([`' + worker_code + '`], { type: "application/javascript" });\n' +
            'const workerUrl = URL.createObjectURL(workerBlob);\n' +
            'recorderWorker = new Worker(workerUrl);'
        )
        
        # SVG files
        with resources.files('whisperlivekit.web').joinpath('src', 'system_mode.svg').open('r', encoding='utf-8') as f:
            system_svg = f.read()
            system_data_uri = f"data:image/svg+xml;base64,{base64.b64encode(system_svg.encode('utf-8')).decode('utf-8')}"
        with resources.files('whisperlivekit.web').joinpath('src', 'light_mode.svg').open('r', encoding='utf-8') as f:
            light_svg = f.read()
            light_data_uri = f"data:image/svg+xml;base64,{base64.b64encode(light_svg.encode('utf-8')).decode('utf-8')}"
        with resources.files('whisperlivekit.web').joinpath('src', 'dark_mode.svg').open('r', encoding='utf-8') as f:
            dark_svg = f.read()
            dark_data_uri = f"data:image/svg+xml;base64,{base64.b64encode(dark_svg.encode('utf-8')).decode('utf-8')}"
        with resources.files('whisperlivekit.web').joinpath('src', 'settings.svg').open('r', encoding='utf-8') as f:
            settings = f.read()
            settings_uri = f"data:image/svg+xml;base64,{base64.b64encode(settings.encode('utf-8')).decode('utf-8')}"

        # Replace external references
        html_content = html_content.replace(
            '<link rel="stylesheet" href="live_transcription.css" />',
            f'<style>\n{css_content}\n</style>'
        )
        
        html_content = html_content.replace(
            '<script src="live_transcription.js"></script>',
            f'<script>\n{js_content}\n</script>'
        )
        
        # Replace SVG references
        html_content = html_content.replace(
            '<img src="/web/src/system_mode.svg" alt="" />',
            f'<img src="{system_data_uri}" alt="" />'
        )
        
        html_content = html_content.replace(
            '<img src="/web/src/light_mode.svg" alt="" />',
            f'<img src="{light_data_uri}" alt="" />'
        )
        
        html_content = html_content.replace(
            '<img src="/web/src/dark_mode.svg" alt="" />',
            f'<img src="{dark_data_uri}" alt="" />'
        )
        
        html_content = html_content.replace(
            '<img src="web/src/settings.svg" alt="Settings" />',
            f'<img src="{settings_uri}" alt="" />'
        )
        
        return html_content
        
    except Exception as e:
        logger.error(f"Error creating embedded web interface: {e}")
        return "<html><body><h1>Error loading embedded interface</h1></body></html>"


if __name__ == '__main__':
    
    import pathlib

    import uvicorn
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    from starlette.staticfiles import StaticFiles

    import whisperlivekit.web as webpkg
    
    app = FastAPI()    
    web_dir = pathlib.Path(webpkg.__file__).parent
    app.mount("/web", StaticFiles(directory=str(web_dir)), name="web")
    
    @app.get("/")
    async def get():
        return HTMLResponse(get_inline_ui_html())

    uvicorn.run(app=app)

```
web_interface.py

/home/charlie/Projects/WhisperLiveKit/whisperlivekit/whisper/__init__.py
```python
import hashlib
import io
import json
import os
import urllib
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Union

import torch
from torch import Tensor
from tqdm import tqdm

from whisperlivekit.whisper.audio import (load_audio, log_mel_spectrogram,
                                          pad_or_trim)
from whisperlivekit.whisper.decoding import (DecodingOptions, DecodingResult,
                                             decode, detect_language)
from whisperlivekit.whisper.model import ModelDimensions, Whisper
from whisperlivekit.whisper.transcribe import transcribe
from whisperlivekit.whisper.version import __version__

_MODELS = {
    "tiny.en": "https://openaipublic.azureedge.net/main/whisper/models/d3dd57d32accea0b295c96e26691aa14d8822fac7d9d27d5dc00b4ca2826dd03/tiny.en.pt",
    "tiny": "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt",
    "base.en": "https://openaipublic.azureedge.net/main/whisper/models/25a8566e1d0c1e2231d1c762132cd20e0f96a85d16145c3a00adf5d1ac670ead/base.en.pt",
    "base": "https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt",
    "small.en": "https://openaipublic.azureedge.net/main/whisper/models/f953ad0fd29cacd07d5a9eda5624af0f6bcf2258be67c92b79389873d91e0872/small.en.pt",
    "small": "https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt",
    "medium.en": "https://openaipublic.azureedge.net/main/whisper/models/d7440d1dc186f76616474e0ff0b3b6b879abc9d1a4926b7adfa41db2d497ab4f/medium.en.pt",
    "medium": "https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt",
    "large-v1": "https://openaipublic.azureedge.net/main/whisper/models/e4b87e7e0bf463eb8e6956e646f1e277e901512310def2c24bf0e11bd3c28e9a/large-v1.pt",
    "large-v2": "https://openaipublic.azureedge.net/main/whisper/models/81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524/large-v2.pt",
    "large-v3": "https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt",
    "large": "https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt",
    "large-v3-turbo": "https://openaipublic.azureedge.net/main/whisper/models/aff26ae408abcba5fbf8813c21e62b0941638c5f6eebfb145be0c9839262a19a/large-v3-turbo.pt",
    "turbo": "https://openaipublic.azureedge.net/main/whisper/models/aff26ae408abcba5fbf8813c21e62b0941638c5f6eebfb145be0c9839262a19a/large-v3-turbo.pt",
}

# base85-encoded (n_layers, n_heads) boolean arrays indicating the cross-attention heads that are
# highly correlated to the word-level timing, i.e. the alignment between audio and text tokens.
_ALIGNMENT_HEADS = {
    "tiny.en": b"ABzY8J1N>@0{>%R00Bk>$p{7v037`oCl~+#00",
    "tiny": b"ABzY8bu8Lr0{>%RKn9Fp%m@SkK7Kt=7ytkO",
    "base.en": b"ABzY8;40c<0{>%RzzG;p*o+Vo09|#PsxSZm00",
    "base": b"ABzY8KQ!870{>%RzyTQH3`Q^yNP!>##QT-<FaQ7m",
    "small.en": b"ABzY8>?_)10{>%RpeA61k&I|OI3I$65C{;;pbCHh0B{qLQ;+}v00",
    "small": b"ABzY8DmU6=0{>%Rpa?J`kvJ6qF(V^F86#Xh7JUGMK}P<N0000",
    "medium.en": b"ABzY8usPae0{>%R7<zz_OvQ{)4kMa0BMw6u5rT}kRKX;$NfYBv00*Hl@qhsU00",
    "medium": b"ABzY8B0Jh+0{>%R7}kK1fFL7w6%<-Pf*t^=N)Qr&0RR9",
    "large-v1": b"ABzY8r9j$a0{>%R7#4sLmoOs{s)o3~84-RPdcFk!JR<kSfC2yj",
    "large-v2": b"ABzY8zd+h!0{>%R7=D0pU<_bnWW*tkYAhobTNnu$jnkEkXqp)j;w1Tzk)UH3X%SZd&fFZ2fC2yj",
    "large-v3": b"ABzY8gWO1E0{>%R7(9S+Kn!D~%ngiGaR?*L!iJG9p-nab0JQ=-{D1-g00",
    "large": b"ABzY8gWO1E0{>%R7(9S+Kn!D~%ngiGaR?*L!iJG9p-nab0JQ=-{D1-g00",
    "large-v3-turbo": b"ABzY8j^C+e0{>%RARaKHP%t(lGR*)0g!tONPyhe`",
    "turbo": b"ABzY8j^C+e0{>%RARaKHP%t(lGR*)0g!tONPyhe`",
}


def _download(url: str, root: str, in_memory: bool) -> Union[bytes, str]:
    os.makedirs(root, exist_ok=True)

    expected_sha256 = url.split("/")[-2]
    download_target = os.path.join(root, os.path.basename(url))

    if os.path.exists(download_target) and not os.path.isfile(download_target):
        raise RuntimeError(f"{download_target} exists and is not a regular file")

    if os.path.isfile(download_target):
        with open(download_target, "rb") as f:
            model_bytes = f.read()
        if hashlib.sha256(model_bytes).hexdigest() == expected_sha256:
            return model_bytes if in_memory else download_target
        else:
            warnings.warn(
                f"{download_target} exists, but the SHA256 checksum does not match; re-downloading the file"
            )

    with urllib.request.urlopen(url) as source, open(download_target, "wb") as output:
        with tqdm(
            total=int(source.info().get("Content-Length")),
            ncols=80,
            unit="iB",
            unit_scale=True,
            unit_divisor=1024,
        ) as loop:
            while True:
                buffer = source.read(8192)
                if not buffer:
                    break

                output.write(buffer)
                loop.update(len(buffer))

    model_bytes = open(download_target, "rb").read()
    if hashlib.sha256(model_bytes).hexdigest() != expected_sha256:
        raise RuntimeError(
            "Model has been downloaded but the SHA256 checksum does not not match. Please retry loading the model."
        )

    return model_bytes if in_memory else download_target


def available_models() -> List[str]:
    """Returns the names of available models"""
    return list(_MODELS.keys())


def _infer_dims_from_config(path: str) -> Optional[ModelDimensions]:
    """
    attempt to infer ModelDimensions from a HF style config.json located
    next to the given checkpoint, usefull for distilled models/MLX models.
    """
    candidates = []
    if os.path.isdir(path):
        candidates.append(os.path.join(path, "config.json"))
    else:
        candidates.append(os.path.join(os.path.dirname(path), "config.json"))

    for candidate in candidates:
        if not os.path.isfile(candidate):
            continue
        with open(candidate, "r", encoding="utf-8") as f:
            config = json.load(f)

        # native Whisper format
        native_keys = ["n_mels", "n_audio_ctx", "n_audio_state", "n_audio_head",
                       "n_audio_layer", "n_vocab", "n_text_ctx", "n_text_state",
                       "n_text_head", "n_text_layer"]
        if all(k in config for k in native_keys):
            return ModelDimensions(
                n_mels=config["n_mels"],
                n_audio_ctx=config["n_audio_ctx"],
                n_audio_state=config["n_audio_state"],
                n_audio_head=config["n_audio_head"],
                n_audio_layer=config["n_audio_layer"],
                n_vocab=config["n_vocab"],
                n_text_ctx=config["n_text_ctx"],
                n_text_state=config["n_text_state"],
                n_text_head=config["n_text_head"],
                n_text_layer=config["n_text_layer"],
            )

        # HuggingFace format
        try:
            return ModelDimensions(
                n_mels=config["num_mel_bins"],
                n_audio_ctx=config["max_source_positions"],
                n_audio_state=config["d_model"],
                n_audio_head=config["encoder_attention_heads"],
                n_audio_layer=config.get("encoder_layers")
                or config["num_hidden_layers"],
                n_vocab=config["vocab_size"],
                n_text_ctx=config["max_target_positions"],
                n_text_state=config["d_model"],
                n_text_head=config["decoder_attention_heads"],
                n_text_layer=config["decoder_layers"],
            )
        except KeyError as err:
            warnings.warn(f"Missing key {err} in HuggingFace config {candidate}")
            return None

    return None


def _convert_hf_state_dict(state_dict: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
    """
    converts a HF checkpoint state_dict into the naming convention used by
    default whisper
    """

    if not any(k.startswith("model.") for k in state_dict):
        return state_dict

    def map_block(prefix: str, target_prefix: str, remainder: str) -> Optional[str]:
        if remainder.startswith("self_attn."):
            suffix = remainder.split(".", 1)[1]
            mapping = {
                "q_proj": "attn.query",
                "k_proj": "attn.key",
                "v_proj": "attn.value",
                "out_proj": "attn.out",
            }
            stem = mapping.get(suffix.split(".")[0])
            if stem:
                rest = suffix.split(".", 1)[1] if "." in suffix else ""
                return f"{target_prefix}.{stem}" + (f".{rest}" if rest else "")
        elif remainder == "self_attn_layer_norm.weight":
            return f"{target_prefix}.attn_ln.weight"
        elif remainder == "self_attn_layer_norm.bias":
            return f"{target_prefix}.attn_ln.bias"
        elif remainder.startswith("encoder_attn."):
            suffix = remainder.split(".", 1)[1]
            mapping = {
                "q_proj": "cross_attn.query",
                "k_proj": "cross_attn.key",
                "v_proj": "cross_attn.value",
                "out_proj": "cross_attn.out",
            }
            stem = mapping.get(suffix.split(".", 1)[0])
            if stem:
                rest = suffix.split(".", 1)[1] if "." in suffix else ""
                return f"{target_prefix}.{stem}" + (f".{rest}" if rest else "")
        elif remainder == "encoder_attn_layer_norm.weight":
            return f"{target_prefix}.cross_attn_ln.weight"
        elif remainder == "encoder_attn_layer_norm.bias":
            return f"{target_prefix}.cross_attn_ln.bias"
        elif remainder.startswith("fc1."):
            return f"{target_prefix}.mlp.0.{remainder.split('.',1)[1]}"
        elif remainder.startswith("fc2."):
            return f"{target_prefix}.mlp.2.{remainder.split('.',1)[1]}"
        elif remainder == "final_layer_norm.weight":
            return f"{target_prefix}.mlp_ln.weight"
        elif remainder == "final_layer_norm.bias":
            return f"{target_prefix}.mlp_ln.bias"
        return None

    converted = {}
    for key, value in state_dict.items():
        if not key.startswith("model."):
            continue
        subkey = key[len("model.") :]

        if subkey.startswith("encoder.layers."):
            parts = subkey.split(".")
            layer_idx = parts[2]
            remainder = ".".join(parts[3:])
            mapped = map_block(subkey, f"encoder.blocks.{layer_idx}", remainder)
        elif subkey.startswith("decoder.layers."):
            parts = subkey.split(".")
            layer_idx = parts[2]
            remainder = ".".join(parts[3:])
            mapped = map_block(subkey, f"decoder.blocks.{layer_idx}", remainder)
        elif subkey.startswith("encoder.conv") or subkey.startswith("decoder.conv"):
            mapped = subkey
        elif subkey == "encoder.embed_positions.weight":
            mapped = "encoder.positional_embedding"
        elif subkey == "decoder.embed_positions.weight":
            mapped = "decoder.positional_embedding"
        elif subkey == "encoder.layer_norm.weight":
            mapped = "encoder.ln_post.weight"
        elif subkey == "encoder.layer_norm.bias":
            mapped = "encoder.ln_post.bias"
        elif subkey.startswith("decoder.embed_tokens."):
            mapped = subkey.replace("embed_tokens", "token_embedding", 1)
        elif subkey == "decoder.layer_norm.weight":
            mapped = "decoder.ln.weight"
        elif subkey == "decoder.layer_norm.bias":
            mapped = "decoder.ln.bias"
        else:
            mapped = None

        if mapped:
            converted[mapped] = value

    return converted if converted else state_dict


def _convert_mlx_state_dict(state_dict: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
    """
    Converts an mlx whisper checkpoint to a default openai whisper one
    """
    if not any("mlp1" in k or "mlp2" in k for k in state_dict):
        return state_dict

    converted = {}
    for key, value in state_dict.items():
        if key == "alignment_heads":
            continue
        
        new_key = key.replace(".mlp1.", ".mlp.0.").replace(".mlp2.", ".mlp.2.")
        converted[new_key] = value

    return converted


def _load_lora_state(lora_path: str):
    safe_path = os.path.join(lora_path, "adapter_model.safetensors")
    bin_path = os.path.join(lora_path, "adapter_model.bin")
    if os.path.isfile(safe_path):
        try:
            from safetensors.torch import load_file
        except ImportError as exc:
            raise ImportError(
                "Loading LoRA adapters stored as .safetensors requires the `safetensors` package."
            ) from exc
        return load_file(safe_path)
    if os.path.isfile(bin_path):
        return torch.load(bin_path, map_location="cpu")
    raise FileNotFoundError(
        f"No adapter weights found under {lora_path}. Expected adapter_model.safetensors or adapter_model.bin."
    )


def _collapse_hf_module_name(module: str):
    if module.startswith("base_model."):
        module = module[len("base_model.") :]
    if module.startswith("model.model."):
        module = module[len("model.") :]
    if not module.startswith("model."):
        module = f"model.{module}"
    return module


def _resolve_lora_path(lora_path: Optional[str]) -> Optional[str]:
    """
    Resolve LoRA adapter path - handles both local paths and HuggingFace repo IDs.
    
    If lora_path is a local directory containing adapter files, returns it as-is.
    If lora_path looks like a HuggingFace repo ID (contains '/'), downloads and caches it.
    """
    if not lora_path:
        return None
    
    # Check if it's already a valid local path
    if os.path.isdir(lora_path):
        config_path = os.path.join(lora_path, "adapter_config.json")
        if os.path.isfile(config_path):
            return lora_path
    
    # Try to download from HuggingFace Hub
    if "/" in lora_path:
        try:
            from huggingface_hub import snapshot_download
            local_path = snapshot_download(
                repo_id=lora_path,
                allow_patterns=["adapter_config.json", "adapter_model.*"],
            )
            return local_path
        except Exception as e:
            raise FileNotFoundError(
                f"Could not find LoRA adapter at local path or HuggingFace Hub: {lora_path}. Error: {e}"
            )
    
    raise FileNotFoundError(
        f"LoRA path '{lora_path}' is not a valid local directory or HuggingFace repo ID."
    )


def _apply_lora_adapter(state_dict: Dict[str, Tensor], lora_path: Optional[str]):
    if not lora_path:
        return
    
    # Resolve path (handles HuggingFace Hub download)
    lora_path = _resolve_lora_path(lora_path)
    if not lora_path:
        return

    config_path = os.path.join(lora_path, "adapter_config.json")
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"Missing adapter_config.json inside {lora_path}")
    with open(config_path, "r", encoding="utf-8") as handle:
        config = json.load(handle)
    if config.get("peft_type") != "LORA":
        raise ValueError("Only LoRA adapters are supported.")

    r = config.get("r")
    alpha = config.get("lora_alpha") or config.get("alpha")
    if not r or not alpha:
        raise ValueError("LoRA config must include `r` and `lora_alpha`.")
    scaling = alpha / r

    adapter_state = _load_lora_state(lora_path)
    lora_layers: Dict[str, Dict[str, Tensor]] = {}
    for key, tensor in adapter_state.items():
        if key.endswith("lora_A.weight"):
            module = key[: -len(".lora_A.weight")]
            lora_layers.setdefault(module, {})["A"] = tensor
        elif key.endswith("lora_B.weight"):
            module = key[: -len(".lora_B.weight")]
            lora_layers.setdefault(module, {})["B"] = tensor

    if not lora_layers:
        raise ValueError(f"No LoRA tensors found in {lora_path}")

    for module, parts in lora_layers.items():
        if "A" not in parts or "B" not in parts:
            raise ValueError(f"Incomplete LoRA tensors for module '{module}'")

        hf_module = _collapse_hf_module_name(module)
        hf_weight_key = f"{hf_module}.weight"

        delta = parts["B"] @ parts["A"]
        delta = delta * scaling

        converted = _convert_hf_state_dict({hf_weight_key: delta})
        if not converted:
            raise KeyError(f"Failed to map LoRA module '{module}' into Whisper state dict.")
        target_name, delta_tensor = next(iter(converted.items()))
        if target_name not in state_dict:
            raise KeyError(
                f"LoRA module '{module}' mapped to '{target_name}', but the base model has no such parameter."
            )

        state_dict[target_name] = state_dict[target_name] + delta_tensor.to(
            dtype=state_dict[target_name].dtype, device=state_dict[target_name].device
        )


def _load_checkpoint(
    file_path: Union[str, Path],
    device: str,
    in_memory: bool = False,
    checkpoint_bytes: Optional[bytes] = None,
) -> Dict[str, torch.Tensor]:
    """
    Load a checkpoint from a single file.
    
    Handles .pt, .bin, and .safetensors formats.
    """
    if checkpoint_bytes is not None:
        with io.BytesIO(checkpoint_bytes) as fp:
            return torch.load(fp, map_location=device)
    
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()
    
    if suffix == '.safetensors':
        try:
            from safetensors.torch import load_file
        except ImportError:
            raise ImportError(
                "Please install safetensors to load .safetensors model files: `pip install safetensors`"
            )
        return load_file(str(file_path), device=device)
    else:
        if in_memory:
            with open(file_path, "rb") as f:
                checkpoint_bytes = f.read()
            with io.BytesIO(checkpoint_bytes) as fp:
                return torch.load(fp, map_location=device)
        else:
            with open(file_path, "rb") as fp:
                return torch.load(fp, map_location=device)


def _load_sharded_checkpoint(
    shard_files: List[Path],
    device: str,
) -> Dict[str, torch.Tensor]:
    """
    Load a sharded checkpoint (multiple .safetensors or .bin files).
    
    Merges all shards into a single state dict.
    """
    merged_state_dict = {}
    first_suffix = shard_files[0].suffix.lower()
    
    if first_suffix == '.safetensors':
        try:
            from safetensors.torch import load_file
        except ImportError:
            raise ImportError(
                "Please install safetensors to load sharded .safetensors model: `pip install safetensors`"
            )
        for shard_path in shard_files:
            shard_dict = load_file(str(shard_path), device=device)
            merged_state_dict.update(shard_dict)
    else:
        for shard_path in shard_files:
            with open(shard_path, "rb") as fp:
                shard_dict = torch.load(fp, map_location=device)
            if isinstance(shard_dict, dict):
                merged_state_dict.update(shard_dict)
    
    return merged_state_dict


def load_model(
    name: str,
    device: Optional[Union[str, torch.device]] = None,
    download_root: str = None,
    in_memory: bool = False,
    decoder_only: bool = False,
    custom_alignment_heads: Optional[str] = None,
    lora_path: Optional[str] = None,
) -> Whisper:
    """
    Load a Whisper ASR model

    Parameters
    ----------
    name : str
        one of the official model names listed by `whisper.available_models()`, or
        path to a model checkpoint containing the model dimensions and the model state_dict.
        Can be a single file (.pt, .bin, .safetensors), a directory containing model files,
        or a sharded model directory with files like model-00001-of-00002.safetensors.
    device : Union[str, torch.device]
        the PyTorch device to put the model into
    download_root: str
        path to download the model files; by default, it uses "~/.cache/whisper"
    in_memory: bool
        whether to preload the model weights into host memory
    lora_path: str
        optional directory containing PEFT LoRA adapter weights (adapter_config + adapter_model)

    Returns
    -------
    model : Whisper
        The Whisper ASR model instance
    """
    from whisperlivekit.model_paths import detect_model_format

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if download_root is None:
        default = os.path.join(os.path.expanduser("~"), ".cache")
        download_root = os.path.join(os.getenv("XDG_CACHE_HOME", default), "whisper")
    
    checkpoint = None
    model_path_for_config = name  # Used to find config.json for dims inference
    
    if name in _MODELS:
        checkpoint_file = _download(_MODELS[name], download_root, in_memory)
        if in_memory:
            checkpoint = _load_checkpoint(None, device, checkpoint_bytes=checkpoint_file)
        else:
            checkpoint = _load_checkpoint(checkpoint_file, device)
    elif os.path.isfile(name):
        if in_memory:
            with open(name, "rb") as f:
                checkpoint_bytes = f.read()
            checkpoint = _load_checkpoint(None, device, checkpoint_bytes=checkpoint_bytes)
        else:
            checkpoint = _load_checkpoint(name, device)
        model_path_for_config = name
    elif os.path.isdir(name):
        model_info = detect_model_format(name)
        
        if not model_info.has_pytorch:
            raise RuntimeError(
                f"No PyTorch checkpoint found in directory {name}. "
                f"Expected .pt, .bin, or .safetensors file(s)."
            )
        
        if model_info.is_sharded:
            checkpoint = _load_sharded_checkpoint(model_info.pytorch_files, device)
        else:
            single_file = model_info.pytorch_files[0]
            if in_memory:
                with open(single_file, "rb") as f:
                    checkpoint_bytes = f.read()
                checkpoint = _load_checkpoint(None, device, checkpoint_bytes=checkpoint_bytes)
            else:
                checkpoint = _load_checkpoint(single_file, device)
        model_path_for_config = name
    else:
        raise RuntimeError(
            f"Model {name} not found; available models = {available_models()}"
        )
        
    alignment_heads = _ALIGNMENT_HEADS.get(name, None)
    if custom_alignment_heads:
        alignment_heads = custom_alignment_heads.encode()

    dims_cfg = checkpoint.get("dims") if isinstance(checkpoint, dict) else None
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        state_dict = checkpoint["model_state_dict"]
    else:
        state_dict = checkpoint
    
    if alignment_heads is None and "alignment_heads" in state_dict:
        alignment_heads = state_dict["alignment_heads"]
    
    state_dict = _convert_hf_state_dict(state_dict)
    state_dict = _convert_mlx_state_dict(state_dict)
    _apply_lora_adapter(state_dict, lora_path)

    if dims_cfg is not None:
        dims = ModelDimensions(**dims_cfg)
    else:
        dims = _infer_dims_from_config(model_path_for_config)
        if dims is None:
            raise RuntimeError(
                "Could not determine model dimensions. "
                "Ensure the checkpoint includes 'dims' or a HuggingFace config.json is present."
            )
        if not isinstance(state_dict, dict):
            state_dict = checkpoint

    model = Whisper(dims, decoder_only=decoder_only)
    
    if decoder_only:
        state_dict = {
            k: v for k, v in state_dict.items() 
            if 'encoder' not in k
        }

    model.load_state_dict(state_dict)

    if alignment_heads is not None:
        if isinstance(alignment_heads, bytes):
            model.set_alignment_heads(alignment_heads)
        elif isinstance(alignment_heads, torch.Tensor): #for mlx whisper
            mask = torch.zeros(dims.n_text_layer, dims.n_text_head, dtype=torch.bool)
            for layer, head in alignment_heads.tolist():
                mask[layer, head] = True
            model.register_buffer("alignment_heads", mask.to_sparse(), persistent=False)
    return model.to(device)


def convert_encoder_to_coreml(
    model_name = "base",
    output_path= "whisper_encoder.mlpackage",
    dummy_frames = 3000, #Number of time frames to use for the dummy mel input during tracing
    precision = "float16",
):
   
    import coremltools as ct
    model = load_model(model_name, device="cpu", decoder_only=False)
    encoder = model.encoder.eval().cpu()

    dummy_input = torch.randn(
        1,
        model.dims.n_mels,
        dummy_frames,
        dtype=next(encoder.parameters()).dtype,
    )

    with torch.no_grad():
        traced_encoder = torch.jit.trace(encoder, dummy_input)

    precision_map = {
        "float16": ct.precision.FLOAT16,
        "fp16": ct.precision.FLOAT16,
        "float32": ct.precision.FLOAT32,
        "fp32": ct.precision.FLOAT32,
    }
    coreml_precision = precision_map[precision.lower()]

    mlmodel = ct.convert(
        traced_encoder,
        inputs=[ct.TensorType(name="mel", shape=dummy_input.shape)],
        convert_to= "mlprogram",
        compute_precision=coreml_precision,
    )

    output_path = Path(output_path)
    mlmodel.save(str(output_path))
    return output_path

# if __name__ == "__main__":
#     convert_encoder_to_coreml(model_name="tiny", output_path="whisper_encoder.mlpackage", dummy_frames=3000, precision="float16", convert_to="mlprogram")
```
__init__.py

/home/charlie/Projects/WhisperLiveKit/whisperlivekit/whisper/audio.py
```python
import os
from functools import lru_cache
from subprocess import CalledProcessError, run
from typing import Optional, Union

import numpy as np
import torch
import torch.nn.functional as F

from .utils import exact_div

# hard-coded audio hyperparameters
SAMPLE_RATE = 16000
N_FFT = 400
HOP_LENGTH = 160
CHUNK_LENGTH = 30
N_SAMPLES = CHUNK_LENGTH * SAMPLE_RATE  # 480000 samples in a 30-second chunk
N_FRAMES = exact_div(N_SAMPLES, HOP_LENGTH)  # 3000 frames in a mel spectrogram input

N_SAMPLES_PER_TOKEN = HOP_LENGTH * 2  # the initial convolutions has stride 2
FRAMES_PER_SECOND = exact_div(SAMPLE_RATE, HOP_LENGTH)  # 10ms per audio frame
TOKENS_PER_SECOND = exact_div(SAMPLE_RATE, N_SAMPLES_PER_TOKEN)  # 20ms per audio token


def load_audio(file: str, sr: int = SAMPLE_RATE):
    """
    Open an audio file and read as mono waveform, resampling as necessary

    Parameters
    ----------
    file: str
        The audio file to open

    sr: int
        The sample rate to resample the audio if necessary

    Returns
    -------
    A NumPy array containing the audio waveform, in float32 dtype.
    """

    # This launches a subprocess to decode audio while down-mixing
    # and resampling as necessary.  Requires the ffmpeg CLI in PATH.
    # fmt: off
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-threads", "0",
        "-i", file,
        "-f", "s16le",
        "-ac", "1",
        "-acodec", "pcm_s16le",
        "-ar", str(sr),
        "-"
    ]
    # fmt: on
    try:
        out = run(cmd, capture_output=True, check=True).stdout
    except CalledProcessError as e:
        raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e

    return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0


def pad_or_trim(array, length: int = N_SAMPLES, *, axis: int = -1):
    """
    Pad or trim the audio array to N_SAMPLES, as expected by the encoder.
    """
    if torch.is_tensor(array):
        if array.shape[axis] > length:
            array = array.index_select(
                dim=axis, index=torch.arange(length, device=array.device)
            )

        if array.shape[axis] < length:
            pad_widths = [(0, 0)] * array.ndim
            pad_widths[axis] = (0, length - array.shape[axis])
            array = F.pad(array, [pad for sizes in pad_widths[::-1] for pad in sizes])
    else:
        if array.shape[axis] > length:
            array = array.take(indices=range(length), axis=axis)

        if array.shape[axis] < length:
            pad_widths = [(0, 0)] * array.ndim
            pad_widths[axis] = (0, length - array.shape[axis])
            array = np.pad(array, pad_widths)

    return array


@lru_cache(maxsize=None)
def mel_filters(device, n_mels: int) -> torch.Tensor:
    """
    load the mel filterbank matrix for projecting STFT into a Mel spectrogram.
    Allows decoupling librosa dependency; saved using:

        np.savez_compressed(
            "mel_filters.npz",
            mel_80=librosa.filters.mel(sr=16000, n_fft=400, n_mels=80),
            mel_128=librosa.filters.mel(sr=16000, n_fft=400, n_mels=128),
        )
    """
    assert n_mels in {80, 128}, f"Unsupported n_mels: {n_mels}"

    filters_path = os.path.join(os.path.dirname(__file__), "assets", "mel_filters.npz")
    with np.load(filters_path, allow_pickle=False) as f:
        return torch.from_numpy(f[f"mel_{n_mels}"]).to(device)


def log_mel_spectrogram(
    audio: Union[str, np.ndarray, torch.Tensor],
    n_mels: int = 80,
    padding: int = 0,
    device: Optional[Union[str, torch.device]] = None,
):
    """
    Compute the log-Mel spectrogram of

    Parameters
    ----------
    audio: Union[str, np.ndarray, torch.Tensor], shape = (*)
        The path to audio or either a NumPy array or Tensor containing the audio waveform in 16 kHz

    n_mels: int
        The number of Mel-frequency filters, only 80 and 128 are supported

    padding: int
        Number of zero samples to pad to the right

    device: Optional[Union[str, torch.device]]
        If given, the audio tensor is moved to this device before STFT

    Returns
    -------
    torch.Tensor, shape = (n_mels, n_frames)
        A Tensor that contains the Mel spectrogram
    """
    if not torch.is_tensor(audio):
        if isinstance(audio, str):
            audio = load_audio(audio)
        audio = torch.from_numpy(audio)

    if device is not None:
        audio = audio.to(device)
    if padding > 0:
        audio = F.pad(audio, (0, padding))
    window = torch.hann_window(N_FFT).to(audio.device)
    stft = torch.stft(audio, N_FFT, HOP_LENGTH, window=window, return_complex=True)
    magnitudes = stft[..., :-1].abs() ** 2

    filters = mel_filters(audio.device, n_mels)
    mel_spec = filters @ magnitudes

    log_spec = torch.clamp(mel_spec, min=1e-10).log10()
    log_spec = torch.maximum(log_spec, log_spec.max() - 8.0)
    log_spec = (log_spec + 4.0) / 4.0
    return log_spec

```
audio.py

/home/charlie/Projects/WhisperLiveKit/whisperlivekit/whisper/decoding.py
```python
from dataclasses import dataclass, field, replace
from typing import (TYPE_CHECKING, Dict, Iterable, List, Optional, Sequence,
                    Tuple, Union)

import numpy as np
import torch
import torch.nn.functional as F
from torch import Tensor
from torch.distributions import Categorical

from .audio import CHUNK_LENGTH
from .tokenizer import Tokenizer, get_tokenizer
from .utils import compression_ratio

if TYPE_CHECKING:
    from .model import Whisper


@torch.no_grad()
def detect_language(
    model: "Whisper", mel: Tensor, tokenizer: Tokenizer = None
) -> Tuple[Tensor, List[dict]]:
    """
    Detect the spoken language in the audio, and return them as list of strings, along with the ids
    of the most probable language tokens and the probability distribution over all language tokens.
    This is performed outside the main decode loop in order to not interfere with kv-caching.

    Returns
    -------
    language_tokens : Tensor, shape = (n_audio,)
        ids of the most probable language tokens, which appears after the startoftranscript token.
    language_probs : List[Dict[str, float]], length = n_audio
        list of dictionaries containing the probability distribution over all languages.
    """
    if tokenizer is None:
        tokenizer = get_tokenizer(
            model.is_multilingual, num_languages=model.num_languages
        )
    if (
        tokenizer.language is None
        or tokenizer.language_token not in tokenizer.sot_sequence
    ):
        raise ValueError(
            "This model doesn't have language tokens so it can't perform lang id"
        )

    single = mel.ndim == 2
    if single:
        mel = mel.unsqueeze(0)

    # skip encoder forward pass if already-encoded audio features were given
    if mel.shape[-2:] != (model.dims.n_audio_ctx, model.dims.n_audio_state):
        mel = model.encoder(mel)

    # forward pass using a single token, startoftranscript
    n_audio = mel.shape[0]
    x = torch.tensor([[tokenizer.sot]] * n_audio).to(mel.device)  # [n_audio, 1]
    logits = model.logits(x, mel)[:, 0]

    # collect detected languages; suppress all non-language tokens
    mask = torch.ones(logits.shape[-1], dtype=torch.bool)
    mask[list(tokenizer.all_language_tokens)] = False
    logits[:, mask] = -np.inf
    language_tokens = logits.argmax(dim=-1)
    language_token_probs = logits.softmax(dim=-1).cpu()
    language_probs = [
        {
            c: language_token_probs[i, j].item()
            for j, c in zip(tokenizer.all_language_tokens, tokenizer.all_language_codes)
        }
        for i in range(n_audio)
    ]

    if single:
        language_tokens = language_tokens[0]
        language_probs = language_probs[0]

    return language_tokens, language_probs


@dataclass(frozen=True)
class DecodingOptions:
    # whether to perform X->X "transcribe" or X->English "translate"
    task: str = "transcribe"

    # language that the audio is in; uses detected language if None
    language: Optional[str] = None

    # sampling-related options
    temperature: float = 0.0
    sample_len: Optional[int] = None  # maximum number of tokens to sample
    best_of: Optional[int] = None  # number of independent sample trajectories, if t > 0
    beam_size: Optional[int] = None  # number of beams in beam search, if t == 0
    patience: Optional[float] = None  # patience in beam search (arxiv:2204.05424)

    # "alpha" in Google NMT, or None for length norm, when ranking generations
    # to select which to return among the beams or best-of-N samples
    length_penalty: Optional[float] = None

    # text or tokens to feed as the prompt or the prefix; for more info:
    # https://github.com/openai/whisper/discussions/117#discussioncomment-3727051
    prompt: Optional[Union[str, List[int]]] = None  # for the previous context
    prefix: Optional[Union[str, List[int]]] = None  # to prefix the current context

    # list of tokens ids (or comma-separated token ids) to suppress
    # "-1" will suppress a set of symbols as defined in `tokenizer.non_speech_tokens()`
    suppress_tokens: Optional[Union[str, Iterable[int]]] = "-1"
    suppress_blank: bool = True  # this will suppress blank outputs

    # timestamp sampling options
    without_timestamps: bool = False  # use <|notimestamps|> to sample text tokens only
    max_initial_timestamp: Optional[float] = 1.0

    # implementation details
    fp16: bool = True  # use fp16 for most of the calculation


@dataclass(frozen=True)
class DecodingResult:
    audio_features: Tensor
    language: str
    language_probs: Optional[Dict[str, float]] = None
    tokens: List[int] = field(default_factory=list)
    text: str = ""
    avg_logprob: float = np.nan
    no_speech_prob: float = np.nan
    temperature: float = np.nan
    compression_ratio: float = np.nan


class Inference:
    def logits(self, tokens: Tensor, audio_features: Tensor) -> Tensor:
        """Perform a forward pass on the decoder and return per-token logits"""
        raise NotImplementedError

    def rearrange_kv_cache(self, source_indices) -> None:
        """Update the key-value cache according to the updated beams"""
        raise NotImplementedError

    def cleanup_caching(self) -> None:
        """Clean up any resources or hooks after decoding is finished"""
        pass


class PyTorchInference(Inference):
    def __init__(self, model: "Whisper", initial_token_length: int):
        self.model: "Whisper" = model
        self.initial_token_length = initial_token_length
        self.kv_cache = {}

        self.kv_cache_ids = []
        for block in self.model.decoder.blocks:
            self.kv_cache_ids.append(block.attn.key_cache_id)
            self.kv_cache_ids.append(block.attn.value_cache_id)

    def logits(self, tokens: Tensor, audio_features: Tensor) -> Tensor:
        if tokens.shape[-1] > self.initial_token_length:
            # only need to use the last token except in the first forward pass
            tokens = tokens[:, -1:]

        return self.model.decoder(tokens, audio_features, kv_cache=self.kv_cache)

    def cleanup_caching(self):
        self.kv_cache = {}

    def rearrange_kv_cache(self, source_indices):
        if source_indices != list(range(len(source_indices))):
            for cache_id in self.kv_cache_ids:
                if cache_id in self.kv_cache:
                    # update the key/value cache to contain the selected sequences
                    self.kv_cache[cache_id] = self.kv_cache[cache_id][source_indices].detach()


class SequenceRanker:
    def rank(
        self, tokens: List[List[Tensor]], sum_logprobs: List[List[float]]
    ) -> List[int]:
        """
        Given a list of groups of samples and their cumulative log probabilities,
        return the indices of the samples in each group to select as the final result
        """
        raise NotImplementedError


class MaximumLikelihoodRanker(SequenceRanker):
    """
    Select the sample with the highest log probabilities, penalized using either
    a simple length normalization or Google NMT paper's length penalty
    """

    def __init__(self, length_penalty: Optional[float]):
        self.length_penalty = length_penalty

    def rank(self, tokens: List[List[Tensor]], sum_logprobs: List[List[float]]):
        def scores(logprobs, lengths):
            result = []
            for logprob, length in zip(logprobs, lengths):
                if self.length_penalty is None:
                    penalty = length
                else:
                    # from the Google NMT paper
                    penalty = ((5 + length) / 6) ** self.length_penalty
                result.append(logprob / penalty)
            return result

        # get the sequence with the highest score
        lengths = [[len(t) for t in s] for s in tokens]
        return [np.argmax(scores(p, l)) for p, l in zip(sum_logprobs, lengths)]


class TokenDecoder:
    def reset(self):
        """Initialize any stateful variables for decoding a new sequence"""

    def update(
        self, tokens: Tensor, logits: Tensor, sum_logprobs: Tensor
    ) -> Tuple[Tensor, bool]:
        """Specify how to select the next token, based on the current trace and logits

        Parameters
        ----------
        tokens : Tensor, shape = (n_batch, current_sequence_length)
            all tokens in the context so far, including the prefix and sot_sequence tokens

        logits : Tensor, shape = (n_batch, vocab_size)
            per-token logits of the probability distribution at the current step

        sum_logprobs : Tensor, shape = (n_batch)
            cumulative log probabilities for each sequence

        Returns
        -------
        tokens : Tensor, shape = (n_batch, current_sequence_length + 1)
            the tokens, appended with the selected next token

        completed : bool
            True if all sequences has reached the end of text

        """
        raise NotImplementedError

    def finalize(
        self, tokens: Tensor, sum_logprobs: Tensor
    ) -> Tuple[Sequence[Sequence[Tensor]], List[List[float]]]:
        """Finalize search and return the final candidate sequences

        Parameters
        ----------
        tokens : Tensor, shape = (n_audio, n_group, current_sequence_length)
            all tokens in the context so far, including the prefix and sot_sequence

        sum_logprobs : Tensor, shape = (n_audio, n_group)
            cumulative log probabilities for each sequence

        Returns
        -------
        tokens : Sequence[Sequence[Tensor]], length = n_audio
            sequence of Tensors containing candidate token sequences, for each audio input

        sum_logprobs : List[List[float]], length = n_audio
            sequence of cumulative log probabilities corresponding to the above

        """
        raise NotImplementedError


class GreedyDecoder(TokenDecoder):
    def __init__(self, temperature: float, eot: int):
        self.temperature = temperature
        self.eot = eot

    def update(
        self, tokens: Tensor, logits: Tensor, sum_logprobs: Tensor
    ) -> Tuple[Tensor, bool]:
        if self.temperature == 0:
            next_tokens = logits.argmax(dim=-1)
        else:
            next_tokens = Categorical(logits=logits / self.temperature).sample()

        logprobs = F.log_softmax(logits.float(), dim=-1)
        current_logprobs = logprobs[torch.arange(logprobs.shape[0]), next_tokens]
        sum_logprobs += current_logprobs * (tokens[:, -1] != self.eot)

        next_tokens[tokens[:, -1] == self.eot] = self.eot
        tokens = torch.cat([tokens, next_tokens[:, None]], dim=-1)

        completed = (tokens[:, -1] == self.eot).all()
        return tokens, completed

    def finalize(self, tokens: Tensor, sum_logprobs: Tensor):
        # make sure each sequence has at least one EOT token at the end
        tokens = F.pad(tokens, (0, 1), value=self.eot)
        return tokens, sum_logprobs.tolist()


class BeamSearchDecoder(TokenDecoder):
    def __init__(
        self,
        beam_size: int,
        eot: int,
        inference: Inference,
        patience: Optional[float] = None,
    ):
        self.beam_size = beam_size
        self.eot = eot
        self.inference = inference
        self.patience = patience or 1.0
        self.max_candidates: int = round(beam_size * self.patience)
        self.finished_sequences = None

        assert (
            self.max_candidates > 0
        ), f"Invalid beam size ({beam_size}) or patience ({patience})"

    def reset(self):
        self.finished_sequences = None

    def update(
        self, tokens: Tensor, logits: Tensor, sum_logprobs: Tensor
    ) -> Tuple[Tensor, bool]:
        if tokens.shape[0] % self.beam_size != 0:
            raise ValueError(f"{tokens.shape}[0] % {self.beam_size} != 0")

        n_audio = tokens.shape[0] // self.beam_size
        if self.finished_sequences is None:  # for the first update
            self.finished_sequences = [{} for _ in range(n_audio)]

        logprobs = F.log_softmax(logits.float(), dim=-1)
        next_tokens, source_indices, finished_sequences = [], [], []
        for i in range(n_audio):
            scores, sources, finished = {}, {}, {}

            # STEP 1: calculate the cumulative log probabilities for possible candidates
            for j in range(self.beam_size):
                idx = i * self.beam_size + j
                prefix = tokens[idx].tolist()
                for logprob, token in zip(*logprobs[idx].topk(self.beam_size + 1)):
                    new_logprob = (sum_logprobs[idx] + logprob).item()
                    sequence = tuple(prefix + [token.item()])
                    scores[sequence] = new_logprob
                    sources[sequence] = idx

            # STEP 2: rank the candidates and keep the top beam_size sequences for each audio
            saved = 0
            for sequence in sorted(scores, key=scores.get, reverse=True):
                if sequence[-1] == self.eot:
                    finished[sequence] = scores[sequence]
                else:
                    sum_logprobs[len(next_tokens)] = scores[sequence]
                    next_tokens.append(sequence)
                    source_indices.append(sources[sequence])

                    saved += 1
                    if saved == self.beam_size:
                        break

            finished_sequences.append(finished)

        tokens = torch.tensor(next_tokens, device=tokens.device)
        self.inference.rearrange_kv_cache(source_indices)

        # add newly finished sequences to self.finished_sequences
        assert len(self.finished_sequences) == len(finished_sequences)
        for previously_finished, newly_finished in zip(
            self.finished_sequences, finished_sequences
        ):
            for seq in sorted(newly_finished, key=newly_finished.get, reverse=True):
                if len(previously_finished) >= self.max_candidates:
                    break  # the candidate list is full
                previously_finished[seq] = newly_finished[seq]

        # mark as completed if all audio has enough number of samples
        completed = all(
            len(sequences) >= self.max_candidates
            for sequences in self.finished_sequences
        )
        return tokens, completed

    def finalize(self, preceding_tokens: Tensor, sum_logprobs: Tensor):
        # collect all finished sequences, including patience, and add unfinished ones if not enough
        sum_logprobs = sum_logprobs.cpu()
        for i, sequences in enumerate(self.finished_sequences):
            if (
                len(sequences) < self.beam_size
            ):  # when not enough sequences are finished
                for j in list(np.argsort(sum_logprobs[i]))[::-1]:
                    sequence = preceding_tokens[i, j].tolist() + [self.eot]
                    sequences[tuple(sequence)] = sum_logprobs[i][j].item()
                    if len(sequences) >= self.beam_size:
                        break

        tokens: List[List[Tensor]] = [
            [torch.tensor(seq) for seq in sequences.keys()]
            for sequences in self.finished_sequences
        ]
        sum_logprobs: List[List[float]] = [
            list(sequences.values()) for sequences in self.finished_sequences
        ]
        return tokens, sum_logprobs


class LogitFilter:
    def apply(self, logits: Tensor, tokens: Tensor) -> None:
        """Apply any filtering or masking to logits in-place

        Parameters
        ----------
        logits : Tensor, shape = (n_batch, vocab_size)
            per-token logits of the probability distribution at the current step

        tokens : Tensor, shape = (n_batch, current_sequence_length)
            all tokens in the context so far, including the prefix and sot_sequence tokens

        """
        raise NotImplementedError


class SuppressBlank(LogitFilter):
    def __init__(self, tokenizer: Tokenizer, sample_begin: int):
        self.tokenizer = tokenizer
        self.sample_begin = sample_begin

    def apply(self, logits: Tensor, tokens: Tensor):
        if tokens.shape[1] == self.sample_begin:
            logits[:, self.tokenizer.encode(" ") + [self.tokenizer.eot]] = -np.inf


class SuppressTokens(LogitFilter):
    def __init__(self, suppress_tokens: Sequence[int]):
        self.suppress_tokens = list(suppress_tokens)

    def apply(self, logits: Tensor, tokens: Tensor):
        logits[:, self.suppress_tokens] = -np.inf


class ApplyTimestampRules(LogitFilter):
    def __init__(
        self,
        tokenizer: Tokenizer,
        sample_begin: int,
        max_initial_timestamp_index: Optional[int],
    ):
        self.tokenizer = tokenizer
        self.sample_begin = sample_begin
        self.max_initial_timestamp_index = max_initial_timestamp_index

    def apply(self, logits: Tensor, tokens: Tensor):
        # suppress <|notimestamps|> which is handled by without_timestamps
        if self.tokenizer.no_timestamps is not None:
            logits[:, self.tokenizer.no_timestamps] = -np.inf

        # timestamps have to appear in pairs, except directly before EOT; mask logits accordingly
        for k in range(tokens.shape[0]):
            sampled_tokens = tokens[k, self.sample_begin :]
            seq = [t for t in sampled_tokens.tolist()]
            last_was_timestamp = (
                len(seq) >= 1 and seq[-1] >= self.tokenizer.timestamp_begin
            )
            penultimate_was_timestamp = (
                len(seq) < 2 or seq[-2] >= self.tokenizer.timestamp_begin
            )

            if last_was_timestamp:
                if penultimate_was_timestamp:  # has to be non-timestamp
                    logits[k, self.tokenizer.timestamp_begin :] = -np.inf
                else:  # cannot be normal text tokens
                    logits[k, : self.tokenizer.eot] = -np.inf

            timestamps = sampled_tokens[
                sampled_tokens.ge(self.tokenizer.timestamp_begin)
            ]
            if timestamps.numel() > 0:
                # timestamps shouldn't decrease; forbid timestamp tokens smaller than the last
                # also force each segment to have a nonzero length, to prevent infinite looping
                if last_was_timestamp and not penultimate_was_timestamp:
                    timestamp_last = timestamps[-1]
                else:
                    timestamp_last = timestamps[-1] + 1
                logits[k, self.tokenizer.timestamp_begin : timestamp_last] = -np.inf

        if tokens.shape[1] == self.sample_begin:
            # suppress generating non-timestamp tokens at the beginning
            logits[:, : self.tokenizer.timestamp_begin] = -np.inf

            # apply the `max_initial_timestamp` option
            if self.max_initial_timestamp_index is not None:
                last_allowed = (
                    self.tokenizer.timestamp_begin + self.max_initial_timestamp_index
                )
                logits[:, last_allowed + 1 :] = -np.inf

        # if sum of probability over timestamps is above any other token, sample timestamp
        logprobs = F.log_softmax(logits.float(), dim=-1)
        for k in range(tokens.shape[0]):
            timestamp_logprob = logprobs[k, self.tokenizer.timestamp_begin :].logsumexp(
                dim=-1
            )
            max_text_token_logprob = logprobs[k, : self.tokenizer.timestamp_begin].max()
            if timestamp_logprob > max_text_token_logprob:
                logits[k, : self.tokenizer.timestamp_begin] = -np.inf


class DecodingTask:
    inference: Inference
    sequence_ranker: SequenceRanker
    decoder: TokenDecoder
    logit_filters: List[LogitFilter]

    def __init__(self, model: "Whisper", options: DecodingOptions):
        self.model = model

        language = options.language or "en"
        tokenizer = get_tokenizer(
            model.is_multilingual,
            num_languages=model.num_languages,
            language=language,
            task=options.task,
        )
        self.tokenizer: Tokenizer = tokenizer
        self.options: DecodingOptions = self._verify_options(options)

        self.n_group: int = options.beam_size or options.best_of or 1
        self.n_ctx: int = model.dims.n_text_ctx
        self.sample_len: int = options.sample_len or model.dims.n_text_ctx // 2

        self.sot_sequence: Tuple[int] = tokenizer.sot_sequence
        if self.options.without_timestamps:
            self.sot_sequence = tokenizer.sot_sequence_including_notimestamps

        self.initial_tokens: Tuple[int] = self._get_initial_tokens()
        self.sample_begin: int = len(self.initial_tokens)
        self.sot_index: int = self.initial_tokens.index(tokenizer.sot)

        # inference: implements the forward pass through the decoder, including kv caching
        self.inference = PyTorchInference(model, len(self.initial_tokens))

        # sequence ranker: implements how to rank a group of sampled sequences
        self.sequence_ranker = MaximumLikelihoodRanker(options.length_penalty)

        # decoder: implements how to select the next tokens, given the autoregressive distribution
        if options.beam_size is not None:
            self.decoder = BeamSearchDecoder(
                options.beam_size, tokenizer.eot, self.inference, options.patience
            )
        else:
            self.decoder = GreedyDecoder(options.temperature, tokenizer.eot)

        # logit filters: applies various rules to suppress or penalize certain tokens
        self.logit_filters = []
        if self.options.suppress_blank:
            self.logit_filters.append(SuppressBlank(self.tokenizer, self.sample_begin))
        if self.options.suppress_tokens:
            self.logit_filters.append(SuppressTokens(self._get_suppress_tokens()))
        if not options.without_timestamps:
            precision = CHUNK_LENGTH / model.dims.n_audio_ctx  # usually 0.02 seconds
            max_initial_timestamp_index = None
            if options.max_initial_timestamp:
                max_initial_timestamp_index = round(
                    self.options.max_initial_timestamp / precision
                )
            self.logit_filters.append(
                ApplyTimestampRules(
                    tokenizer, self.sample_begin, max_initial_timestamp_index
                )
            )

    def _verify_options(self, options: DecodingOptions) -> DecodingOptions:
        if options.beam_size is not None and options.best_of is not None:
            raise ValueError("beam_size and best_of can't be given together")
        if options.temperature == 0:
            if options.best_of is not None:
                raise ValueError("best_of with greedy sampling (T=0) is not compatible")
        if options.patience is not None and options.beam_size is None:
            raise ValueError("patience requires beam_size to be given")
        if options.length_penalty is not None and not (
            0 <= options.length_penalty <= 1
        ):
            raise ValueError("length_penalty (alpha) should be a value between 0 and 1")

        return options

    def _get_initial_tokens(self) -> Tuple[int]:
        tokens = list(self.sot_sequence)

        if prefix := self.options.prefix:
            prefix_tokens = (
                self.tokenizer.encode(" " + prefix.strip())
                if isinstance(prefix, str)
                else prefix
            )
            if self.sample_len is not None:
                max_prefix_len = self.n_ctx // 2 - self.sample_len
                prefix_tokens = prefix_tokens[-max_prefix_len:]
            tokens = tokens + prefix_tokens

        if prompt := self.options.prompt:
            prompt_tokens = (
                self.tokenizer.encode(" " + prompt.strip())
                if isinstance(prompt, str)
                else prompt
            )
            tokens = (
                [self.tokenizer.sot_prev]
                + prompt_tokens[-(self.n_ctx // 2 - 1) :]
                + tokens
            )

        return tuple(tokens)

    def _get_suppress_tokens(self) -> Tuple[int]:
        suppress_tokens = self.options.suppress_tokens

        if isinstance(suppress_tokens, str):
            suppress_tokens = [int(t) for t in suppress_tokens.split(",")]

        if -1 in suppress_tokens:
            suppress_tokens = [t for t in suppress_tokens if t >= 0]
            suppress_tokens.extend(self.tokenizer.non_speech_tokens)
        elif suppress_tokens is None or len(suppress_tokens) == 0:
            suppress_tokens = []  # interpret empty string as an empty list
        else:
            assert isinstance(suppress_tokens, list), "suppress_tokens must be a list"

        suppress_tokens.extend(
            [
                self.tokenizer.transcribe,
                self.tokenizer.translate,
                self.tokenizer.sot,
                self.tokenizer.sot_prev,
                self.tokenizer.sot_lm,
            ]
        )
        if self.tokenizer.no_speech is not None:
            # no-speech probability is collected separately
            suppress_tokens.append(self.tokenizer.no_speech)

        return tuple(sorted(set(suppress_tokens)))

    def _get_audio_features(self, mel: Tensor):
        if self.options.fp16:
            mel = mel.half()

        if mel.shape[-2:] == (
            self.model.dims.n_audio_ctx,
            self.model.dims.n_audio_state,
        ):
            # encoded audio features are given; skip audio encoding
            audio_features = mel
        else:
            audio_features = self.model.encoder(mel)

        if audio_features.dtype != (
            torch.float16 if self.options.fp16 else torch.float32
        ):
            return TypeError(
                f"audio_features has an incorrect dtype: {audio_features.dtype}"
            )

        return audio_features

    def _detect_language(self, audio_features: Tensor, tokens: Tensor):
        languages = [self.options.language] * audio_features.shape[0]
        lang_probs = None

        if self.options.language is None or self.options.task == "lang_id":
            lang_tokens, lang_probs = self.model.detect_language(
                audio_features, self.tokenizer
            )
            languages = [max(probs, key=probs.get) for probs in lang_probs]
            if self.options.language is None:
                tokens[:, self.sot_index + 1] = lang_tokens  # write language tokens

        return languages, lang_probs

    def _main_loop(self, audio_features: Tensor, tokens: Tensor):
        n_batch = tokens.shape[0]
        sum_logprobs: Tensor = torch.zeros(n_batch, device=audio_features.device)
        no_speech_probs = [np.nan] * n_batch

        try:
            for i in range(self.sample_len):
                logits = self.inference.logits(tokens, audio_features)

                if (
                    i == 0 and self.tokenizer.no_speech is not None
                ):  # save no_speech_probs
                    probs_at_sot = logits[:, self.sot_index].float().softmax(dim=-1)
                    no_speech_probs = probs_at_sot[:, self.tokenizer.no_speech].tolist()

                # now we need to consider the logits at the last token only
                logits = logits[:, -1]

                # apply the logit filters, e.g. for suppressing or applying penalty to
                for logit_filter in self.logit_filters:
                    logit_filter.apply(logits, tokens)

                # expand the tokens tensor with the selected next tokens
                tokens, completed = self.decoder.update(tokens, logits, sum_logprobs)

                if completed or tokens.shape[-1] > self.n_ctx:
                    break
        finally:
            self.inference.cleanup_caching()

        return tokens, sum_logprobs, no_speech_probs

    @torch.no_grad()
    def run(self, mel: Tensor) -> List[DecodingResult]:
        self.decoder.reset()
        tokenizer: Tokenizer = self.tokenizer
        n_audio: int = mel.shape[0]

        audio_features: Tensor = self._get_audio_features(mel)  # encoder forward pass
        tokens: Tensor = torch.tensor([self.initial_tokens]).repeat(n_audio, 1)

        # detect language if requested, overwriting the language token
        languages, language_probs = self._detect_language(audio_features, tokens)
        if self.options.task == "lang_id":
            return [
                DecodingResult(
                    audio_features=features, language=language, language_probs=probs
                )
                for features, language, probs in zip(
                    audio_features, languages, language_probs
                )
            ]

        # repeat text tensors by the group size, for beam search or best-of-n sampling
        tokens = tokens.repeat_interleave(self.n_group, dim=0).to(audio_features.device)

        # call the main sampling loop
        tokens, sum_logprobs, no_speech_probs = self._main_loop(audio_features, tokens)

        # reshape the tensors to have (n_audio, n_group) as the first two dimensions
        audio_features = audio_features[:: self.n_group]
        no_speech_probs = no_speech_probs[:: self.n_group]
        assert audio_features.shape[0] == len(no_speech_probs) == n_audio

        tokens = tokens.reshape(n_audio, self.n_group, -1)
        sum_logprobs = sum_logprobs.reshape(n_audio, self.n_group)

        # get the final candidates for each group, and slice between the first sampled token and EOT
        tokens, sum_logprobs = self.decoder.finalize(tokens, sum_logprobs)
        tokens: List[List[Tensor]] = [
            [t[self.sample_begin : (t == tokenizer.eot).nonzero()[0, 0]] for t in s]
            for s in tokens
        ]

        # select the top-ranked sample in each group
        selected = self.sequence_ranker.rank(tokens, sum_logprobs)
        tokens: List[List[int]] = [t[i].tolist() for i, t in zip(selected, tokens)]
        texts: List[str] = [tokenizer.decode(t).strip() for t in tokens]

        sum_logprobs: List[float] = [lp[i] for i, lp in zip(selected, sum_logprobs)]
        avg_logprobs: List[float] = [
            lp / (len(t) + 1) for t, lp in zip(tokens, sum_logprobs)
        ]

        fields = (
            texts,
            languages,
            tokens,
            audio_features,
            avg_logprobs,
            no_speech_probs,
        )
        if len(set(map(len, fields))) != 1:
            raise RuntimeError(f"inconsistent result lengths: {list(map(len, fields))}")

        return [
            DecodingResult(
                audio_features=features,
                language=language,
                tokens=tokens,
                text=text,
                avg_logprob=avg_logprob,
                no_speech_prob=no_speech_prob,
                temperature=self.options.temperature,
                compression_ratio=compression_ratio(text),
            )
            for text, language, tokens, features, avg_logprob, no_speech_prob in zip(
                *fields
            )
        ]


@torch.no_grad()
def decode(
    model: "Whisper",
    mel: Tensor,
    options: DecodingOptions = DecodingOptions(),
    **kwargs,
) -> Union[DecodingResult, List[DecodingResult]]:
    """
    Performs decoding of 30-second audio segment(s), provided as Mel spectrogram(s).

    Parameters
    ----------
    model: Whisper
        the Whisper model instance

    mel: torch.Tensor, shape = (80, 3000) or (*, 80, 3000)
        A tensor containing the Mel spectrogram(s)

    options: DecodingOptions
        A dataclass that contains all necessary options for decoding 30-second segments

    Returns
    -------
    result: Union[DecodingResult, List[DecodingResult]]
        The result(s) of decoding contained in `DecodingResult` dataclass instance(s)
    """
    if single := mel.ndim == 2:
        mel = mel.unsqueeze(0)

    if kwargs:
        options = replace(options, **kwargs)

    result = DecodingTask(model, options).run(mel)

    return result[0] if single else result

```
decoding.py

/home/charlie/Projects/WhisperLiveKit/whisperlivekit/whisper/model.py
```python
import base64
import gzip
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from torch import Tensor, nn

from .decoding import decode as decode_function
from .decoding import detect_language as detect_language_function
from .transcribe import transcribe as transcribe_function

try:
    from torch.nn.functional import scaled_dot_product_attention

    SDPA_AVAILABLE = True
except (ImportError, RuntimeError, OSError):
    scaled_dot_product_attention = None
    SDPA_AVAILABLE = False


@dataclass
class ModelDimensions:
    n_mels: int
    n_audio_ctx: int
    n_audio_state: int
    n_audio_head: int
    n_audio_layer: int
    n_vocab: int
    n_text_ctx: int
    n_text_state: int
    n_text_head: int
    n_text_layer: int


class LayerNorm(nn.LayerNorm):
    def forward(self, x: Tensor) -> Tensor:
        return super().forward(x.float()).type(x.dtype)


class Linear(nn.Linear):
    def forward(self, x: Tensor) -> Tensor:
        return F.linear(
            x,
            self.weight.to(x.dtype),
            None if self.bias is None else self.bias.to(x.dtype),
        )


class Conv1d(nn.Conv1d):
    def _conv_forward(
        self, x: Tensor, weight: Tensor, bias: Optional[Tensor]
    ) -> Tensor:
        return super()._conv_forward(
            x, weight.to(x.dtype), None if bias is None else bias.to(x.dtype)
        )


def sinusoids(length, channels, max_timescale=10000):
    """Returns sinusoids for positional embedding"""
    assert channels % 2 == 0
    log_timescale_increment = np.log(max_timescale) / (channels // 2 - 1)
    inv_timescales = torch.exp(-log_timescale_increment * torch.arange(channels // 2))
    scaled_time = torch.arange(length)[:, np.newaxis] * inv_timescales[np.newaxis, :]
    return torch.cat([torch.sin(scaled_time), torch.cos(scaled_time)], dim=1)


@contextmanager
def disable_sdpa():
    prev_state = MultiHeadAttention.use_sdpa
    try:
        MultiHeadAttention.use_sdpa = False
        yield
    finally:
        MultiHeadAttention.use_sdpa = prev_state


class MultiHeadAttention(nn.Module):
    use_sdpa = False  # Disable SDPA to ensure qk is always computed when needed

    def __init__(self, n_state: int, n_head: int, cache_id: str = "", n_text_ctx: int = 448):
        super().__init__()
        self.n_head = n_head
        self.n_text_ctx = n_text_ctx
        self.query = Linear(n_state, n_state)
        self.key = Linear(n_state, n_state, bias=False)
        self.value = Linear(n_state, n_state)
        self.out = Linear(n_state, n_state)
        self.cache_id = cache_id
        # Cache IDs for key and value (used with dict-based kv_cache)
        self.key_cache_id = f"{cache_id}_key"
        self.value_cache_id = f"{cache_id}_value"
        # Keep these for backward compatibility with hook-based caching
        self.key.cache_id = self.key_cache_id
        self.value.cache_id = self.value_cache_id

    def forward(
        self,
        x: Tensor,
        xa: Optional[Tensor] = None,
        mask: Optional[Tensor] = None,
        kv_cache: Optional[dict] = None,
    ):
        q = self.query(x)

        if xa is None:
            # Self-attention
            k = self.key(x)
            v = self.value(x)
            if kv_cache is not None:
                k, v = self._update_self_attn_cache(k, v, kv_cache)
        else:
            # Cross-attention: compute once and cache, or reuse from cache
            if kv_cache is not None and self.key_cache_id in kv_cache:
                k = kv_cache[self.key_cache_id]
                v = kv_cache[self.value_cache_id]
            else:
                k = self.key(xa)
                v = self.value(xa)
                if kv_cache is not None:
                    kv_cache[self.key_cache_id] = k
                    kv_cache[self.value_cache_id] = v

        wv, qk = self.qkv_attention(q, k, v, mask)
        return self.out(wv), qk

    def _update_self_attn_cache(
        self, k: Tensor, v: Tensor, kv_cache: dict
    ) -> Tuple[Tensor, Tensor]:
        """Update self-attention kv cache by concatenating new k,v with cached values."""
        if self.key_cache_id not in kv_cache or k.shape[1] > self.n_text_ctx:
            # First token or context overflow: save as-is
            kv_cache[self.key_cache_id] = k.detach()
            kv_cache[self.value_cache_id] = v.detach()
        else:
            # Concatenate with existing cache
            cached_k = kv_cache[self.key_cache_id]
            cached_v = kv_cache[self.value_cache_id]
            k = torch.cat([cached_k, k], dim=1).detach()
            v = torch.cat([cached_v, v], dim=1).detach()
            kv_cache[self.key_cache_id] = k
            kv_cache[self.value_cache_id] = v
        return k, v

    def qkv_attention(
        self, q: Tensor, k: Tensor, v: Tensor, mask: Optional[Tensor] = None
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        n_batch, n_ctx, n_state = q.shape
        scale = (n_state // self.n_head) ** -0.25
        q = q.view(*q.shape[:2], self.n_head, -1).permute(0, 2, 1, 3)
        k = k.view(*k.shape[:2], self.n_head, -1).permute(0, 2, 1, 3)
        v = v.view(*v.shape[:2], self.n_head, -1).permute(0, 2, 1, 3)

        if SDPA_AVAILABLE and MultiHeadAttention.use_sdpa:
            a = scaled_dot_product_attention(
                q, k, v, is_causal=mask is not None and n_ctx > 1
            )
            out = a.permute(0, 2, 1, 3).flatten(start_dim=2)
            qk = None
        else:
            qk = (q * scale) @ (k * scale).transpose(-1, -2)
            if mask is not None:
                qk = qk + mask[:n_ctx, :n_ctx]
            qk = qk.float()

            w = F.softmax(qk, dim=-1).to(q.dtype)
            out = (w @ v).permute(0, 2, 1, 3).flatten(start_dim=2)
            qk = qk.detach()

        return out, qk


class ResidualAttentionBlock(nn.Module):
    def __init__(
        self, n_state: int, n_head: int, cross_attention: bool = False, 
        cache_id: str = "", n_text_ctx: int = 448
    ):
        super().__init__()

        self.attn = MultiHeadAttention(
            n_state, n_head, cache_id=f"{cache_id}_self_attn", n_text_ctx=n_text_ctx
        )
        self.attn_ln = LayerNorm(n_state)

        self.cross_attn = (
            MultiHeadAttention(
                n_state, n_head, cache_id=f"{cache_id}_cross_attn", n_text_ctx=n_text_ctx
            ) if cross_attention else None
        )
        self.cross_attn_ln = LayerNorm(n_state) if cross_attention else None

        n_mlp = n_state * 4
        self.mlp = nn.Sequential(
            Linear(n_state, n_mlp), nn.GELU(), Linear(n_mlp, n_state)
        )
        self.mlp_ln = LayerNorm(n_state)

    def forward(
        self,
        x: Tensor,
        xa: Optional[Tensor] = None,
        mask: Optional[Tensor] = None,
        kv_cache: Optional[dict] = None,
    ) -> Tuple[Tensor, Optional[Tensor]]:
        """
        Returns:
            x: The output tensor
            cross_attn_qk: Cross-attention weights (if cross_attn exists), else None
        """
        x = x + self.attn(self.attn_ln(x), mask=mask, kv_cache=kv_cache)[0]
        cross_attn_qk = None
        if self.cross_attn:
            cross_out, cross_attn_qk = self.cross_attn(
                self.cross_attn_ln(x), xa, kv_cache=kv_cache
            )
            x = x + cross_out
        x = x + self.mlp(self.mlp_ln(x))
        return x, cross_attn_qk


class AudioEncoder(nn.Module):
    def __init__(
        self, n_mels: int, n_ctx: int, n_state: int, n_head: int, n_layer: int
    ):
        super().__init__()
        self.conv1 = Conv1d(n_mels, n_state, kernel_size=3, padding=1)
        self.conv2 = Conv1d(n_state, n_state, kernel_size=3, stride=2, padding=1)
        self.register_buffer("positional_embedding", sinusoids(n_ctx, n_state))

        self.blocks: Iterable[ResidualAttentionBlock] = nn.ModuleList(
            [ResidualAttentionBlock(n_state, n_head, cache_id=f"enc_layer{i}") for i in range(n_layer)]
        )
        self.ln_post = LayerNorm(n_state)

    def forward(self, x: Tensor):
        """
        x : torch.Tensor, shape = (batch_size, n_mels, n_ctx)
            the mel spectrogram of the audio
        """
        x = F.gelu(self.conv1(x))
        x = F.gelu(self.conv2(x))
        x = x.permute(0, 2, 1)

        assert x.shape[1:] == self.positional_embedding.shape, "incorrect audio shape"
        x = (x + self.positional_embedding).to(x.dtype)

        for block in self.blocks:
            x, _ = block(x)  # Encoder blocks don't have cross-attention

        x = self.ln_post(x)
        return x


class TextDecoder(nn.Module):
    def __init__(
        self, n_vocab: int, n_ctx: int, n_state: int, n_head: int, n_layer: int
    ):
        super().__init__()
        self.n_ctx = n_ctx

        self.token_embedding = nn.Embedding(n_vocab, n_state)
        self.positional_embedding = nn.Parameter(torch.empty(n_ctx, n_state))

        self.blocks: Iterable[ResidualAttentionBlock] = nn.ModuleList(
            [
                ResidualAttentionBlock(
                    n_state, n_head, cross_attention=True, 
                    cache_id=f"dec_layer{i}", n_text_ctx=n_ctx
                )
                for i in range(n_layer)
            ]
        )
        self.ln = LayerNorm(n_state)

        mask = torch.empty(n_ctx, n_ctx).fill_(-np.inf).triu_(1)
        self.register_buffer("mask", mask, persistent=False)

    def forward(
        self, 
        x: Tensor, 
        xa: Tensor, 
        kv_cache: Optional[dict] = None,
        return_cross_attn: bool = False,
    ):
        """
        x : torch.LongTensor, shape = (batch_size, <= n_ctx)
            the text tokens
        xa : torch.Tensor, shape = (batch_size, n_audio_ctx, n_audio_state)
            the encoded audio features to be attended on
        kv_cache : Optional[dict]
            Dictionary to store/retrieve key-value cache for efficient decoding
        return_cross_attn : bool
            If True, return cross-attention weights from all decoder layers
            
        Returns
        -------
        logits : Tensor
            The output logits
        cross_attns : Optional[List[Tensor]]
            List of cross-attention weights per layer (only if return_cross_attn=True)
        """
        # Calculate offset from self-attention cache (not cross-attention which has audio length)
        offset = 0
        if kv_cache:
            # Use the first decoder block's self-attention key cache to get token position
            first_self_attn_key = self.blocks[0].attn.key_cache_id
            if first_self_attn_key in kv_cache:
                offset = kv_cache[first_self_attn_key].shape[1]
        
        x = (
            self.token_embedding(x)
            + self.positional_embedding[offset : offset + x.shape[-1]]
        )
        x = x.to(xa.dtype)

        cross_attns = [] if return_cross_attn else None
        for block in self.blocks:
            x, cross_attn_qk = block(x, xa, mask=self.mask, kv_cache=kv_cache)
            if return_cross_attn and cross_attn_qk is not None:
                cross_attns.append(cross_attn_qk)

        x = self.ln(x)
        logits = (
            x @ torch.transpose(self.token_embedding.weight.to(x.dtype), 0, 1)
        ).float()

        if return_cross_attn:
            return logits, cross_attns
        return logits


class Whisper(nn.Module):
    def __init__(self, dims: ModelDimensions, decoder_only: bool = False):
        super().__init__()
        self.dims = dims
        
        if not decoder_only:
            self.encoder = AudioEncoder(
                self.dims.n_mels,
                self.dims.n_audio_ctx,
                self.dims.n_audio_state,
                self.dims.n_audio_head,
                self.dims.n_audio_layer,
            )
        self.decoder = TextDecoder(
            self.dims.n_vocab,
            self.dims.n_text_ctx,
            self.dims.n_text_state,
            self.dims.n_text_head,
            self.dims.n_text_layer,
        )
        # use the last half among the decoder layers for time alignment by default;
        # to use a specific set of heads, see `set_alignment_heads()` below.
        all_heads = torch.zeros(
            self.dims.n_text_layer, self.dims.n_text_head, dtype=torch.bool
        )
        all_heads[self.dims.n_text_layer // 2 :] = True
        self.register_buffer("alignment_heads", all_heads.to_sparse(), persistent=False)

    def set_alignment_heads(self, dump: bytes):
        array = np.frombuffer(
            gzip.decompress(base64.b85decode(dump)), dtype=bool
        ).copy()
        mask = torch.from_numpy(array).reshape(
            self.dims.n_text_layer, self.dims.n_text_head
        )
        self.register_buffer("alignment_heads", mask.to_sparse(), persistent=False)

    def embed_audio(self, mel: torch.Tensor):
        return self.encoder(mel)

    def logits(
        self, 
        tokens: torch.Tensor, 
        audio_features: torch.Tensor,
        kv_cache: Optional[dict] = None,
        return_cross_attn: bool = False,
    ):
        return self.decoder(
            tokens, audio_features, 
            kv_cache=kv_cache, 
            return_cross_attn=return_cross_attn
        )

    def forward(
        self, mel: torch.Tensor, tokens: torch.Tensor
    ) -> Dict[str, torch.Tensor]:
        return self.decoder(tokens, self.encoder(mel))

    @property
    def device(self):
        return next(self.parameters()).device

    @property
    def is_multilingual(self):
        return self.dims.n_vocab >= 51865

    @property
    def num_languages(self):
        return self.dims.n_vocab - 51765 - int(self.is_multilingual)

    detect_language = detect_language_function
    transcribe = transcribe_function
    decode = decode_function

```
model.py

/home/charlie/Projects/WhisperLiveKit/whisperlivekit/whisper/transcribe.py
```python
import argparse
import os
import traceback
import warnings
from typing import TYPE_CHECKING, List, Optional, Tuple, Union

import numpy as np
import torch
import tqdm

from .audio import (FRAMES_PER_SECOND, HOP_LENGTH, N_FRAMES, N_SAMPLES,
                    SAMPLE_RATE, log_mel_spectrogram, pad_or_trim)
from .decoding import DecodingOptions, DecodingResult
from .timing import add_word_timestamps
from .tokenizer import LANGUAGES, TO_LANGUAGE_CODE, get_tokenizer
from .utils import (exact_div, format_timestamp, get_end, get_writer,
                    make_safe, optional_float, optional_int, str2bool)

if TYPE_CHECKING:
    from .model import Whisper


def transcribe(
    model: "Whisper",
    audio: Union[str, np.ndarray, torch.Tensor],
    *,
    verbose: Optional[bool] = None,
    temperature: Union[float, Tuple[float, ...]] = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
    compression_ratio_threshold: Optional[float] = 2.4,
    logprob_threshold: Optional[float] = -1.0,
    no_speech_threshold: Optional[float] = 0.6,
    condition_on_previous_text: bool = True,
    initial_prompt: Optional[str] = None,
    carry_initial_prompt: bool = False,
    word_timestamps: bool = False,
    prepend_punctuations: str = "\"'“¿([{-",
    append_punctuations: str = "\"'.。,，!！?？:：”)]}、",
    clip_timestamps: Union[str, List[float]] = "0",
    hallucination_silence_threshold: Optional[float] = None,
    **decode_options,
):
    """
    Transcribe an audio file using Whisper

    Parameters
    ----------
    model: Whisper
        The Whisper model instance

    audio: Union[str, np.ndarray, torch.Tensor]
        The path to the audio file to open, or the audio waveform

    verbose: bool
        Whether to display the text being decoded to the console. If True, displays all the details,
        If False, displays minimal details. If None, does not display anything

    temperature: Union[float, Tuple[float, ...]]
        Temperature for sampling. It can be a tuple of temperatures, which will be successively used
        upon failures according to either `compression_ratio_threshold` or `logprob_threshold`.

    compression_ratio_threshold: float
        If the gzip compression ratio is above this value, treat as failed

    logprob_threshold: float
        If the average log probability over sampled tokens is below this value, treat as failed

    no_speech_threshold: float
        If the no_speech probability is higher than this value AND the average log probability
        over sampled tokens is below `logprob_threshold`, consider the segment as silent

    condition_on_previous_text: bool
        if True, the previous output of the model is provided as a prompt for the next window;
        disabling may make the text inconsistent across windows, but the model becomes less prone to
        getting stuck in a failure loop, such as repetition looping or timestamps going out of sync.

    word_timestamps: bool
        Extract word-level timestamps using the cross-attention pattern and dynamic time warping,
        and include the timestamps for each word in each segment.

    prepend_punctuations: str
        If word_timestamps is True, merge these punctuation symbols with the next word

    append_punctuations: str
        If word_timestamps is True, merge these punctuation symbols with the previous word

    initial_prompt: Optional[str]
        Optional text to provide as a prompt for the first window. This can be used to provide, or
        "prompt-engineer" a context for transcription, e.g. custom vocabularies or proper nouns
        to make it more likely to predict those word correctly.

    carry_initial_prompt: bool
        If carry_initial_prompt is True, `initial_prompt` is prepended to the prompt of each internal
        `decode()` call. If there is not enough context space at the start of the prompt, it is
        left-sliced to make space.

    decode_options: dict
        Keyword arguments to construct `DecodingOptions` instances

    clip_timestamps: Union[str, List[float]]
        Comma-separated list start,end,start,end,... timestamps (in seconds) of clips to process.
        The last end timestamp defaults to the end of the file.

    hallucination_silence_threshold: Optional[float]
        When word_timestamps is True, skip silent periods longer than this threshold (in seconds)
        when a possible hallucination is detected

    Returns
    -------
    A dictionary containing the resulting text ("text") and segment-level details ("segments"), and
    the spoken language ("language"), which is detected when `decode_options["language"]` is None.
    """
    dtype = torch.float16 if decode_options.get("fp16", True) else torch.float32
    if model.device == torch.device("cpu"):
        if torch.cuda.is_available():
            warnings.warn("Performing inference on CPU when CUDA is available")
        if dtype == torch.float16:
            warnings.warn("FP16 is not supported on CPU; using FP32 instead")
            dtype = torch.float32

    if dtype == torch.float32:
        decode_options["fp16"] = False

    # Pad 30-seconds of silence to the input audio, for slicing
    mel = log_mel_spectrogram(audio, model.dims.n_mels, padding=N_SAMPLES)
    content_frames = mel.shape[-1] - N_FRAMES
    content_duration = float(content_frames * HOP_LENGTH / SAMPLE_RATE)

    if decode_options.get("language", None) is None:
        if not model.is_multilingual:
            decode_options["language"] = "en"
        else:
            if verbose:
                print(
                    "Detecting language using up to the first 30 seconds. Use `--language` to specify the language"
                )
            mel_segment = pad_or_trim(mel, N_FRAMES).to(model.device).to(dtype)
            _, probs = model.detect_language(mel_segment)
            decode_options["language"] = max(probs, key=probs.get)
            if verbose is not None:
                print(
                    f"Detected language: {LANGUAGES[decode_options['language']].title()}"
                )

    language: str = decode_options["language"]
    task: str = decode_options.get("task", "transcribe")
    tokenizer = get_tokenizer(
        model.is_multilingual,
        num_languages=model.num_languages,
        language=language,
        task=task,
    )

    if isinstance(clip_timestamps, str):
        clip_timestamps = [
            float(ts) for ts in (clip_timestamps.split(",") if clip_timestamps else [])
        ]
    seek_points: List[int] = [round(ts * FRAMES_PER_SECOND) for ts in clip_timestamps]
    if len(seek_points) == 0:
        seek_points.append(0)
    if len(seek_points) % 2 == 1:
        seek_points.append(content_frames)
    seek_clips: List[Tuple[int, int]] = list(zip(seek_points[::2], seek_points[1::2]))

    punctuation = "\"'“¿([{-\"'.。,，!！?？:：”)]}、"

    if word_timestamps and task == "translate":
        warnings.warn("Word-level timestamps on translations may not be reliable.")

    def decode_with_fallback(segment: torch.Tensor) -> DecodingResult:
        temperatures = (
            [temperature] if isinstance(temperature, (int, float)) else temperature
        )
        decode_result = None

        for t in temperatures:
            kwargs = {**decode_options}
            if t > 0:
                # disable beam_size and patience when t > 0
                kwargs.pop("beam_size", None)
                kwargs.pop("patience", None)
            else:
                # disable best_of when t == 0
                kwargs.pop("best_of", None)

            options = DecodingOptions(**kwargs, temperature=t)
            decode_result = model.decode(segment, options)

            needs_fallback = False
            if (
                compression_ratio_threshold is not None
                and decode_result.compression_ratio > compression_ratio_threshold
            ):
                needs_fallback = True  # too repetitive
            if (
                logprob_threshold is not None
                and decode_result.avg_logprob < logprob_threshold
            ):
                needs_fallback = True  # average log probability is too low
            if (
                no_speech_threshold is not None
                and decode_result.no_speech_prob > no_speech_threshold
                and logprob_threshold is not None
                and decode_result.avg_logprob < logprob_threshold
            ):
                needs_fallback = False  # silence
            if not needs_fallback:
                break

        return decode_result

    clip_idx = 0
    seek = seek_clips[clip_idx][0]
    input_stride = exact_div(
        N_FRAMES, model.dims.n_audio_ctx
    )  # mel frames per output token: 2
    time_precision = (
        input_stride * HOP_LENGTH / SAMPLE_RATE
    )  # time per output token: 0.02 (seconds)
    all_tokens = []
    all_segments = []
    prompt_reset_since = 0

    remaining_prompt_length = model.dims.n_text_ctx // 2 - 1
    if initial_prompt is not None:
        initial_prompt_tokens = tokenizer.encode(" " + initial_prompt.strip())
        all_tokens.extend(initial_prompt_tokens)
        remaining_prompt_length -= len(initial_prompt_tokens)
    else:
        initial_prompt_tokens = []

    def new_segment(
        *, start: float, end: float, tokens: torch.Tensor, result: DecodingResult
    ):
        tokens = tokens.tolist()
        text_tokens = [token for token in tokens if token < tokenizer.eot]
        return {
            "seek": seek,
            "start": start,
            "end": end,
            "text": tokenizer.decode(text_tokens),
            "tokens": tokens,
            "temperature": result.temperature,
            "avg_logprob": result.avg_logprob,
            "compression_ratio": result.compression_ratio,
            "no_speech_prob": result.no_speech_prob,
        }

    # show the progress bar when verbose is False (if True, transcribed text will be printed)
    with tqdm.tqdm(
        total=content_frames, unit="frames", disable=verbose is not False
    ) as pbar:
        last_speech_timestamp = 0.0
        # NOTE: This loop is obscurely flattened to make the diff readable.
        # A later commit should turn this into a simpler nested loop.
        # for seek_clip_start, seek_clip_end in seek_clips:
        #     while seek < seek_clip_end
        while clip_idx < len(seek_clips):
            seek_clip_start, seek_clip_end = seek_clips[clip_idx]
            if seek < seek_clip_start:
                seek = seek_clip_start
            if seek >= seek_clip_end:
                clip_idx += 1
                if clip_idx < len(seek_clips):
                    seek = seek_clips[clip_idx][0]
                continue
            time_offset = float(seek * HOP_LENGTH / SAMPLE_RATE)
            window_end_time = float((seek + N_FRAMES) * HOP_LENGTH / SAMPLE_RATE)
            segment_size = min(N_FRAMES, content_frames - seek, seek_clip_end - seek)
            mel_segment = mel[:, seek : seek + segment_size]
            segment_duration = segment_size * HOP_LENGTH / SAMPLE_RATE
            mel_segment = pad_or_trim(mel_segment, N_FRAMES).to(model.device).to(dtype)

            if carry_initial_prompt:
                nignored = max(len(initial_prompt_tokens), prompt_reset_since)
                remaining_prompt = all_tokens[nignored:][-remaining_prompt_length:]
                decode_options["prompt"] = initial_prompt_tokens + remaining_prompt
            else:
                decode_options["prompt"] = all_tokens[prompt_reset_since:]

            result: DecodingResult = decode_with_fallback(mel_segment)
            tokens = torch.tensor(result.tokens)

            if no_speech_threshold is not None:
                # no voice activity check
                should_skip = result.no_speech_prob > no_speech_threshold
                if (
                    logprob_threshold is not None
                    and result.avg_logprob > logprob_threshold
                ):
                    # don't skip if the logprob is high enough, despite the no_speech_prob
                    should_skip = False

                if should_skip:
                    seek += segment_size  # fast-forward to the next segment boundary
                    continue

            previous_seek = seek
            current_segments = []

            # anomalous words are very long/short/improbable
            def word_anomaly_score(word: dict) -> float:
                probability = word.get("probability", 0.0)
                duration = word["end"] - word["start"]
                score = 0.0
                if probability < 0.15:
                    score += 1.0
                if duration < 0.133:
                    score += (0.133 - duration) * 15
                if duration > 2.0:
                    score += duration - 2.0
                return score

            def is_segment_anomaly(segment: Optional[dict]) -> bool:
                if segment is None or not segment["words"]:
                    return False
                words = [w for w in segment["words"] if w["word"] not in punctuation]
                words = words[:8]
                score = sum(word_anomaly_score(w) for w in words)
                return score >= 3 or score + 0.01 >= len(words)

            def next_words_segment(segments: List[dict]) -> Optional[dict]:
                return next((s for s in segments if s["words"]), None)

            timestamp_tokens: torch.Tensor = tokens.ge(tokenizer.timestamp_begin)
            single_timestamp_ending = timestamp_tokens[-2:].tolist() == [False, True]

            consecutive = torch.where(timestamp_tokens[:-1] & timestamp_tokens[1:])[0]
            consecutive.add_(1)
            if len(consecutive) > 0:
                # if the output contains two consecutive timestamp tokens
                slices = consecutive.tolist()
                if single_timestamp_ending:
                    slices.append(len(tokens))

                last_slice = 0
                for current_slice in slices:
                    sliced_tokens = tokens[last_slice:current_slice]
                    start_timestamp_pos = (
                        sliced_tokens[0].item() - tokenizer.timestamp_begin
                    )
                    end_timestamp_pos = (
                        sliced_tokens[-1].item() - tokenizer.timestamp_begin
                    )
                    current_segments.append(
                        new_segment(
                            start=time_offset + start_timestamp_pos * time_precision,
                            end=time_offset + end_timestamp_pos * time_precision,
                            tokens=sliced_tokens,
                            result=result,
                        )
                    )
                    last_slice = current_slice

                if single_timestamp_ending:
                    # single timestamp at the end means no speech after the last timestamp.
                    seek += segment_size
                else:
                    # otherwise, ignore the unfinished segment and seek to the last timestamp
                    last_timestamp_pos = (
                        tokens[last_slice - 1].item() - tokenizer.timestamp_begin
                    )
                    seek += last_timestamp_pos * input_stride
            else:
                duration = segment_duration
                timestamps = tokens[timestamp_tokens.nonzero().flatten()]
                if (
                    len(timestamps) > 0
                    and timestamps[-1].item() != tokenizer.timestamp_begin
                ):
                    # no consecutive timestamps but it has a timestamp; use the last one.
                    last_timestamp_pos = (
                        timestamps[-1].item() - tokenizer.timestamp_begin
                    )
                    duration = last_timestamp_pos * time_precision

                current_segments.append(
                    new_segment(
                        start=time_offset,
                        end=time_offset + duration,
                        tokens=tokens,
                        result=result,
                    )
                )
                seek += segment_size

            if word_timestamps:
                add_word_timestamps(
                    segments=current_segments,
                    model=model,
                    tokenizer=tokenizer,
                    mel=mel_segment,
                    num_frames=segment_size,
                    prepend_punctuations=prepend_punctuations,
                    append_punctuations=append_punctuations,
                    last_speech_timestamp=last_speech_timestamp,
                )

                if not single_timestamp_ending:
                    last_word_end = get_end(current_segments)
                    if last_word_end is not None and last_word_end > time_offset:
                        seek = round(last_word_end * FRAMES_PER_SECOND)

                # skip silence before possible hallucinations
                if hallucination_silence_threshold is not None:
                    threshold = hallucination_silence_threshold
                    if not single_timestamp_ending:
                        last_word_end = get_end(current_segments)
                        if last_word_end is not None and last_word_end > time_offset:
                            remaining_duration = window_end_time - last_word_end
                            if remaining_duration > threshold:
                                seek = round(last_word_end * FRAMES_PER_SECOND)
                            else:
                                seek = previous_seek + segment_size

                    # if first segment might be a hallucination, skip leading silence
                    first_segment = next_words_segment(current_segments)
                    if first_segment is not None and is_segment_anomaly(first_segment):
                        gap = first_segment["start"] - time_offset
                        if gap > threshold:
                            seek = previous_seek + round(gap * FRAMES_PER_SECOND)
                            continue

                    # skip silence before any possible hallucination that is surrounded
                    # by silence or more hallucinations
                    hal_last_end = last_speech_timestamp
                    for si in range(len(current_segments)):
                        segment = current_segments[si]
                        if not segment["words"]:
                            continue
                        if is_segment_anomaly(segment):
                            next_segment = next_words_segment(
                                current_segments[si + 1 :]
                            )
                            if next_segment is not None:
                                hal_next_start = next_segment["words"][0]["start"]
                            else:
                                hal_next_start = time_offset + segment_duration
                            silence_before = (
                                segment["start"] - hal_last_end > threshold
                                or segment["start"] < threshold
                                or segment["start"] - time_offset < 2.0
                            )
                            silence_after = (
                                hal_next_start - segment["end"] > threshold
                                or is_segment_anomaly(next_segment)
                                or window_end_time - segment["end"] < 2.0
                            )
                            if silence_before and silence_after:
                                seek = round(
                                    max(time_offset + 1, segment["start"])
                                    * FRAMES_PER_SECOND
                                )
                                if content_duration - segment["end"] < threshold:
                                    seek = content_frames
                                current_segments[si:] = []
                                break
                        hal_last_end = segment["end"]

                last_word_end = get_end(current_segments)
                if last_word_end is not None:
                    last_speech_timestamp = last_word_end

            if verbose:
                for segment in current_segments:
                    start, end, text = segment["start"], segment["end"], segment["text"]
                    line = f"[{format_timestamp(start)} --> {format_timestamp(end)}] {text}"
                    print(make_safe(line))

            # if a segment is instantaneous or does not contain text, clear it
            for i, segment in enumerate(current_segments):
                if segment["start"] == segment["end"] or segment["text"].strip() == "":
                    segment["text"] = ""
                    segment["tokens"] = []
                    segment["words"] = []

            all_segments.extend(
                [
                    {"id": i, **segment}
                    for i, segment in enumerate(
                        current_segments, start=len(all_segments)
                    )
                ]
            )
            all_tokens.extend(
                [token for segment in current_segments for token in segment["tokens"]]
            )

            if not condition_on_previous_text or result.temperature > 0.5:
                # do not feed the prompt tokens if a high temperature was used
                prompt_reset_since = len(all_tokens)

            # update progress bar
            pbar.update(min(content_frames, seek) - previous_seek)

    return dict(
        text=tokenizer.decode(all_tokens[len(initial_prompt_tokens) :]),
        segments=all_segments,
        language=language,
    )


def cli():
    from . import available_models

    def valid_model_name(name):
        if name in available_models() or os.path.exists(name):
            return name
        raise ValueError(
            f"model should be one of {available_models()} or path to a model checkpoint"
        )

    # fmt: off
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("audio", nargs="+", type=str, help="audio file(s) to transcribe")
    parser.add_argument("--model", default="turbo", type=valid_model_name, help="name of the Whisper model to use")
    parser.add_argument("--model_dir", type=str, default=None, help="the path to save model files; uses ~/.cache/whisper by default")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu", help="device to use for PyTorch inference")
    parser.add_argument("--output_dir", "-o", type=str, default=".", help="directory to save the outputs")
    parser.add_argument("--output_format", "-f", type=str, default="all", choices=["txt", "vtt", "srt", "tsv", "json", "all"], help="format of the output file; if not specified, all available formats will be produced")
    parser.add_argument("--verbose", type=str2bool, default=True, help="whether to print out the progress and debug messages")

    parser.add_argument("--task", type=str, default="transcribe", choices=["transcribe", "translate"], help="whether to perform X->X speech recognition ('transcribe') or X->English translation ('translate')")
    parser.add_argument("--language", type=str, default=None, choices=sorted(LANGUAGES.keys()) + sorted([k.title() for k in TO_LANGUAGE_CODE.keys()]), help="language spoken in the audio, specify None to perform language detection")

    parser.add_argument("--temperature", type=float, default=0, help="temperature to use for sampling")
    parser.add_argument("--best_of", type=optional_int, default=5, help="number of candidates when sampling with non-zero temperature")
    parser.add_argument("--beam_size", type=optional_int, default=5, help="number of beams in beam search, only applicable when temperature is zero")
    parser.add_argument("--patience", type=float, default=None, help="optional patience value to use in beam decoding, as in https://arxiv.org/abs/2204.05424, the default (1.0) is equivalent to conventional beam search")
    parser.add_argument("--length_penalty", type=float, default=None, help="optional token length penalty coefficient (alpha) as in https://arxiv.org/abs/1609.08144, uses simple length normalization by default")

    parser.add_argument("--suppress_tokens", type=str, default="-1", help="comma-separated list of token ids to suppress during sampling; '-1' will suppress most special characters except common punctuations")
    parser.add_argument("--initial_prompt", type=str, default=None, help="optional text to provide as a prompt for the first window.")
    parser.add_argument("--carry_initial_prompt", type=str2bool, default=False, help="if True, prepend initial_prompt to every internal decode() call. May reduce the effectiveness of condition_on_previous_text")

    parser.add_argument("--condition_on_previous_text", type=str2bool, default=True, help="if True, provide the previous output of the model as a prompt for the next window; disabling may make the text inconsistent across windows, but the model becomes less prone to getting stuck in a failure loop")
    parser.add_argument("--fp16", type=str2bool, default=True, help="whether to perform inference in fp16; True by default")

    parser.add_argument("--temperature_increment_on_fallback", type=optional_float, default=0.2, help="temperature to increase when falling back when the decoding fails to meet either of the thresholds below")
    parser.add_argument("--compression_ratio_threshold", type=optional_float, default=2.4, help="if the gzip compression ratio is higher than this value, treat the decoding as failed")
    parser.add_argument("--logprob_threshold", type=optional_float, default=-1.0, help="if the average log probability is lower than this value, treat the decoding as failed")
    parser.add_argument("--no_speech_threshold", type=optional_float, default=0.6, help="if the probability of the <|nospeech|> token is higher than this value AND the decoding has failed due to `logprob_threshold`, consider the segment as silence")
    parser.add_argument("--word_timestamps", type=str2bool, default=False, help="(experimental) extract word-level timestamps and refine the results based on them")
    parser.add_argument("--prepend_punctuations", type=str, default="\"\'“¿([{-", help="if word_timestamps is True, merge these punctuation symbols with the next word")
    parser.add_argument("--append_punctuations", type=str, default="\"\'.。,，!！?？:：”)]}、", help="if word_timestamps is True, merge these punctuation symbols with the previous word")
    parser.add_argument("--highlight_words", type=str2bool, default=False, help="(requires --word_timestamps True) underline each word as it is spoken in srt and vtt")
    parser.add_argument("--max_line_width", type=optional_int, default=None, help="(requires --word_timestamps True) the maximum number of characters in a line before breaking the line")
    parser.add_argument("--max_line_count", type=optional_int, default=None, help="(requires --word_timestamps True) the maximum number of lines in a segment")
    parser.add_argument("--max_words_per_line", type=optional_int, default=None, help="(requires --word_timestamps True, no effect with --max_line_width) the maximum number of words in a segment")
    parser.add_argument("--threads", type=optional_int, default=0, help="number of threads used by torch for CPU inference; supercedes MKL_NUM_THREADS/OMP_NUM_THREADS")
    parser.add_argument("--clip_timestamps", type=str, default="0", help="comma-separated list start,end,start,end,... timestamps (in seconds) of clips to process, where the last end timestamp defaults to the end of the file")
    parser.add_argument("--hallucination_silence_threshold", type=optional_float, help="(requires --word_timestamps True) skip silent periods longer than this threshold (in seconds) when a possible hallucination is detected")
    # fmt: on

    args = parser.parse_args().__dict__
    model_name: str = args.pop("model")
    model_dir: str = args.pop("model_dir")
    output_dir: str = args.pop("output_dir")
    output_format: str = args.pop("output_format")
    device: str = args.pop("device")
    os.makedirs(output_dir, exist_ok=True)

    if model_name.endswith(".en") and args["language"] not in {"en", "English"}:
        if args["language"] is not None:
            warnings.warn(
                f"{model_name} is an English-only model but receipted '{args['language']}'; using English instead."
            )
        args["language"] = "en"

    temperature = args.pop("temperature")
    if (increment := args.pop("temperature_increment_on_fallback")) is not None:
        temperature = tuple(np.arange(temperature, 1.0 + 1e-6, increment))
    else:
        temperature = [temperature]

    if (threads := args.pop("threads")) > 0:
        torch.set_num_threads(threads)

    from . import load_model

    model = load_model(model_name, device=device, download_root=model_dir)

    writer = get_writer(output_format, output_dir)
    word_options = [
        "highlight_words",
        "max_line_count",
        "max_line_width",
        "max_words_per_line",
    ]
    if not args["word_timestamps"]:
        for option in word_options:
            if args[option]:
                parser.error(f"--{option} requires --word_timestamps True")
    if args["max_line_count"] and not args["max_line_width"]:
        warnings.warn("--max_line_count has no effect without --max_line_width")
    if args["max_words_per_line"] and args["max_line_width"]:
        warnings.warn("--max_words_per_line has no effect with --max_line_width")
    writer_args = {arg: args.pop(arg) for arg in word_options}
    for audio_path in args.pop("audio"):
        try:
            result = transcribe(model, audio_path, temperature=temperature, **args)
            writer(result, audio_path, **writer_args)
        except Exception as e:
            traceback.print_exc()
            print(f"Skipping {audio_path} due to {type(e).__name__}: {str(e)}")


if __name__ == "__main__":
    cli()

```
transcribe.py
