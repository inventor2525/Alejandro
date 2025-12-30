# Guide for New Claude Sessions - Alejandro WhisperLiveKit Development

## The Branch Problem & Solution

### TL;DR
**You can only push to branches matching your session ID.** The user works on one branch, but you may be spawned with a different session ID. The solution: merge their branch into yours and push to your branch.

### Background
Claude Code web UI spawns each session with a unique session ID (e.g., `rlz6k`, `iKKKo`). This ID is embedded in the branch name pattern `claude/*-{SESSION_ID}`. You can ONLY push to branches ending with YOUR session ID.

**This causes a problem:**
- User continues work on branch: `claude/add-wlk-word-stream-iKKKo`
- New Claude session spawned with different ID: `rlz6k`
- You can ONLY push to: `claude/fix-whisper-livekit-stream-rlz6k`
- Attempting to push to the user's branch results in: `HTTP 403 error`

### How to Change Your Branch (Unknown)
As of this writing, we don't know how to change the assigned branch in Claude Code web UI. If you figure it out, UPDATE THIS SECTION!

---

## Step-by-Step: Picking Up Where We Left Off

### 1. Identify the Situation
User will tell you something like:
> "We were working on branch `claude/add-wlk-word-stream-iKKKo`, can you continue from there?"

### 2. Check What Branch You Can Push To
```bash
# Check all branches
git branch -a

# Try to push to any branch to see the error
git push origin HEAD:test-branch-name

# You'll get 403 unless the branch ends with your session ID
```

Your pushable branch will match the pattern in the system prompt under "Git Development Branch Requirements".

### 3. Merge Their Branch Into Your Pushable Branch
```bash
# Switch to your pushable branch
git checkout claude/fix-whisper-livekit-stream-rlz6k  # (or whatever your session ID is)

# Fetch the latest from their branch
git fetch origin claude/add-wlk-word-stream-iKKKo

# Merge their branch into yours
git merge claude/add-wlk-word-stream-iKKKo --no-edit

# Push to your branch
git push -u origin claude/fix-whisper-livekit-stream-rlz6k
```

### 4. Update Installation References
**CRITICAL:** After merging, update these files to point to YOUR branch:

**README.md** (line ~17):
```bash
wget -O - https://raw.githubusercontent.com/inventor2525/Alejandro/claude%2F{YOUR-BRANCH-NAME}/installer.sh | bash
```

**installer.sh** (line ~25):
```bash
git checkout {YOUR-BRANCH-NAME}
```

Then commit and push:
```bash
git add README.md installer.sh
git commit -m "Update installation to use claude/{YOUR-BRANCH-NAME} branch"
git push origin claude/{YOUR-BRANCH-NAME}
```

---

## Important Files for WhisperLiveKit Work

### Core Implementation
1. **`Alejandro/Core/WhisperLiveKitWordStream.py`** - Main implementation
   - Audio processing with async/threading
   - Integration with WhisperLiveKit AudioProcessor
   - Race condition fix: `is_recording = True` BEFORE `_init_audio_processor()`

### Configuration Files
2. **`setup.py`** - Dependencies including `whisperlivekit`
3. **`installer.sh`** - Install script (MUST update branch reference)
4. **`README.md`** - Install instructions (MUST update branch reference)

### Reference Documentation
5. **`dear_claude.md`** - Contains WhisperLiveKit source code and API documentation
   - **CRITICAL:** You cannot `pip install whisperlivekit` to inspect it - the source is in this file
   - Contains full WhisperLiveKit implementation from the upstream project
   - Example usage from official WLK docs
   - **Technical Integration Guide (line ~1381):** Key integration patterns:
     - Create global TranscriptionEngine (expensive - reuse it)
     - Instantiate AudioProcessor per connection
     - Call create_tasks() for async generator, process_audio() for bytes
   - Shows proper async pattern:
     ```python
     audio_processor = AudioProcessor(transcription_engine=engine)
     results_generator = await audio_processor.create_tasks()
     results_task = asyncio.create_task(handle_results(results_generator))
     # Then keep calling: await audio_processor.process_audio(bytes)
     ```

### Web Interface
6. **`Alejandro/web/app.py`** - Flask app initialization
7. **`Alejandro/web/static/js/streaming_transcribe.js`** - Client-side audio capture

---

## The WhisperLiveKit Race Condition Bug (FIXED)

### The Problem
The async processing thread was dying immediately after initialization:
```
[WLK] AudioProcessor initialized
[WLK] _run_async_processor: Thread exiting  # ← Died immediately!
[WLK] Not processing: processing thread died
```

### Root Cause
In `_start_listening()`:
```python
# OLD CODE (BROKEN):
self._init_audio_processor()  # Started thread
self.is_recording = True       # Set flag AFTER

# Thread's main loop saw is_recording=False and exited:
while self.is_recording or not self.audio_chunk_queue.empty():
    # Evaluated to False → loop exits → thread dies
```

### The Fix (WhisperLiveKitWordStream.py:350-357)
```python
# NEW CODE (FIXED):
self.is_recording = True              # Set flag FIRST
self._init_audio_processor()          # Then start thread

# Now the loop sees is_recording=True and stays alive
```

**File:** `Alejandro/Core/WhisperLiveKitWordStream.py` lines 350-357

---

## Testing the Fix

1. Run the Flask app:
```bash
python Alejandro/web/app.py
```

2. Navigate to: `http://localhost:5000/recorder?session=test-session-id`

3. Click "Start Recording" and speak

4. Look for these log messages (success indicators):
```
[WLK] AudioProcessor initialized, processing audio chunks...
[WLK] Initial state: is_recording=True, queue_size=0
[WLK] Queued 32509 bytes for processing (queue size: 1)
[WLK] Processing 32509 bytes...
[WLK] Received transcription result: {...}
```

5. If you see `[WLK] Not processing: processing thread died` → race condition bug is back!

---

## Common Issues

### HTTP 403 on Push
**Symptom:** `error: RPC failed; HTTP 403`
**Cause:** Branch name doesn't end with your session ID
**Solution:** Push to a branch that matches your session ID pattern

### Processing Thread Dies Immediately
**Symptom:** `[WLK] _run_async_processor: Thread exiting` right after init
**Cause:** `is_recording = True` set AFTER thread started
**Solution:** Verify the fix is applied (see "The Fix" section above)

### WhisperLiveKit Not Available
**Symptom:** `[WLK] WhisperLiveKit not available`
**Cause:** Package not installed
**Solution:** `pip install whisperlivekit`

---

## Quick Start Checklist for New Sessions

- [ ] User tells me what branch they were working on
- [ ] Check what branch I can push to (`git branch -a`)
- [ ] Merge their branch into my pushable branch
- [ ] Update `README.md` with my branch name
- [ ] Update `installer.sh` with my branch name
- [ ] Commit and push these changes
- [ ] Read `dear_claude.md` for WLK API reference if needed
- [ ] Verify the race condition fix is present in `WhisperLiveKitWordStream.py:350-357`
- [ ] Ready to continue development!

---

## Notes for Future Development

### WhisperLiveKit API Pattern
The correct async pattern (from `dear_claude.md`):
```python
# 1. Create AudioProcessor (heavy - reuse TranscriptionEngine)
audio_processor = AudioProcessor(transcription_engine=shared_engine)

# 2. Create tasks - returns async generator
results_generator = await audio_processor.create_tasks()

# 3. Start task to consume results
async def handle_results(generator):
    async for result in generator:
        process_result(result)
results_task = asyncio.create_task(handle_results(results_generator))

# 4. Feed audio continuously
while recording:
    await audio_processor.process_audio(audio_bytes)
```

### Key Insights
- `TranscriptionEngine` is HEAVY - create once, share across sessions
- `AudioProcessor` is per-session - one per connection
- `create_tasks()` returns a long-running generator, not a one-shot result
- Audio processing is continuous via `process_audio(bytes)`
- Results come through the async generator

---

*Last updated: 2025-12-30*
*If you're reading this in a new session: Good luck, and may your branches merge cleanly!*
