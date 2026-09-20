# Speak an idea, then write

Open **Papers**, choose your paper and open **Section writing**. Choose **Speak my idea** beside the writing controls.

1. Choose English, German, Polish or automatic language detection. Select **Record** and allow the microphone when your browser asks. Explain one idea in your own words; one to three minutes is a useful starting point. Pause when needed, then stop. You can also import an existing audio recording.
2. Save the recording. The app keeps the audio in your paper folder before starting transcription. You can continue writing while the local speech model works. Reopen **Speak my idea** in the same section to find your saved recordings and their status.
3. Read **My corrected spoken notes** and check technical words, names, numbers and negations. Play the audio to check uncertain passages. The original machine transcript remains separate.
4. Keep these notes beside your draft and write from them. To use the wording itself, select the part you want and explicitly insert it into your draft. Insertion uses the editor's usual save and recovery path; Undo removes that insertion when it can do so without discarding later edits.

Recording does not change your manuscript, ask the tutor to rewrite it or complete a learning activity. Transcription preserves the spoken language; it does not translate. An audio file is your working material, not a literature source.

## Organise recordings

In **Speak my idea**, use the recording management controls to select clips from this section and put them in the order you want. **Merge recordings** creates a separate combined recording. Transcribe it to get one continuous transcript, then correct its spoken notes. The original recordings and their corrected notes remain available; merging does not edit your manuscript or combine earlier tutor feedback.

Choose between two and ten clips, with a combined duration of at most ten minutes. If the intended order is different from the recording dates, use the move controls before merging. A merged note records which clips were used and in which order.

**Move to trash** removes a saved recording from the active list. Open **Trash** to restore it. This is recoverable: audio, transcript and corrected notes remain in the private vault, with the note marked as trashed. There is no permanent-erasure action in this interface. Trashing an original after a merge does not delete the combined recording.

## Desktop setup

Voice setup is optional. In the installed app folder, run **Set up voice on Mac.command** or **Set up voice on Windows.cmd** once. It downloads the multilingual Whisper small model, approximately 488 MB, and configures a local speech engine and audio decoder. Mac setup uses an existing Homebrew installation; Windows x64 setup uses the official whisper.cpp package and a packaged FFmpeg executable. An Internet connection is needed for this setup. Subsequent transcription runs on this computer.

Ollama still provides writing feedback. It is separate from the speech engine. Model files and executable paths stay in the computer's local application data and must be configured independently on another computer. To target a non-default instance, run its Python environment with `setup_voice.py --data PATH-TO-APP-DATA`.

If you installed or upgraded FFmpeg while the recorder was open, choose **Local transcription setup → Check setup again**. The app checks installed executables again and can recover from stale version-specific paths. Homebrew's stable command paths are kept in the local configuration so normal package updates do not require another model download.

Recordings are limited to 10 minutes and 40 MB. Shorter recordings are easier to check and work with. Supported imports include WAV, M4A, MP3, WebM, Ogg, FLAC, AAC and CAF. If microphone access is unavailable in an embedded browser, open the same local app address in Safari, Chrome or Edge, or import a recording. Recording requires an explicit permission and Record action.

## Obsidian and another computer

The private paper folder contains:

```text
Section writing/
  Voice notes/
    Date - Section - Spoken idea.md
    Audio/
    Transcripts/
    Recovered files/
```

The readable Markdown note links to its section and recording. It separates **Original transcription**, **My corrected spoken notes** and **Ideas I chose to develop**. Retranscription retains earlier transcripts and leaves edited notes intact. Conflicting note saves ask you to compare versions.

Enable the corresponding audio and JSON attachment types in Obsidian Sync and check your plan's attachment size limit. Wait for Sync on both devices before switching. The app confirms local saves, but cannot verify remote Sync delivery. Browser recovery is an emergency local copy; it is not a synced backup. Save the recording to the vault before closing the browser or changing computers.

## Native iPad

The native iPad client has a separate **Speak my idea** screen under **Reading & notes**, with a synced paper and section chooser. It uses Apple's on-device speech recognition where the selected language and device support it. It does not silently fall back to cloud recognition. Audio can still be retained if recognition is unavailable. See [the native voice guide](native-voice-notes.md).

Installing the desktop update does not install a new iPad binary. The iPad app must also be rebuilt and installed through the existing Xcode workflow.
