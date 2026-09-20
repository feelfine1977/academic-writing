# Speak my idea on iPad

The native app has a **Reading & notes → Speak my idea** sheet. It saves spoken planning alongside an existing paper and section in the connected Obsidian vault. This is a native capture and notes interface; it does not duplicate the desktop section editor.

## Use it

1. Open Obsidian on the iPad and let Sync finish. In Writing Lab, connect the vault root, then open **Speak my idea**.
2. Choose an existing paper and section, and give the idea a readable title. The chooser reads the paper root outline and section/subsection cards in `06_Academic_Writing_Lab/Papers`.
3. Tap **Record my idea**. Pause/resume if useful, then **Stop & save**. Each recording is limited to 60 seconds. You can also import M4A, WAV, MP3, AIFF or CAF audio up to 40 MB.
4. Play the saved audio back. Choose the spoken language, then **Transcribe on this iPad**. The app saves audio to its private recovery folder first and to the chosen vault paper before requesting transcription.
5. Check names, citations, technical terms and missing words in **My corrected spoken notes**. The first successful raw transcription remains read only. Use **Ideas I chose to develop** for the points you want to write yourself.
6. Leave Obsidian open long enough to sync before switching devices. Enable audio/attachment sync in Obsidian as needed. The desktop Writing Lab reads these same notes under the corresponding paper and section.

The app never inserts a transcript into manuscript prose automatically. On iPad you can select and copy words deliberately; the desktop section-writing interface provides the fuller draft workflow.

## Merge or remove recordings

Expand **Saved voice notes for this section** and choose **Merge recordings**. Add 2–10 different clips, use **Up** and **Down** to set their playback order, name the result, then create it. The merge produces a new M4A and a new note with ordered links to its source notes. Audio is joined without generating prose. Original audio, transcripts and corrected notes remain available. The new clip needs its own transcription. Total length is limited to ten minutes and the result to 40 MB; clips longer than 60 seconds can be transcribed on the desktop.

Use **Move to Trash** beside a saved note to remove it from the active list. **Trash · recoverable → Restore** brings it back. This changes note metadata; it does not permanently delete audio, transcripts or notes. Finish or cancel a local recording/transcription before moving its note. Stale recovery drafts cannot silently restore a trashed note. Trash and restoration travel through Obsidian Sync.

## Local recognition and limits

The adapter uses Apple's `SFSpeechURLRecognitionRequest`. It first checks `SFSpeechRecognizer.supportsOnDeviceRecognition`, then sets `requiresOnDeviceRecognition = true` for every recognition request. It does not fall back to a server recognizer. Apple documents that the request property is honoured only when on-device recognition is supported, so both checks matter. See [on-device recognition support](https://developer.apple.com/documentation/speech/sfspeechrecognizer/supportsondevicerecognition) and [requiring on-device recognition](https://developer.apple.com/documentation/speech/sfspeechrecognitionrequest/requiresondevicerecognition).

Language and device support vary. If the recognizer is unavailable, its language resources are missing, or permission is denied, the sheet explains the problem and keeps the recording. There is no separate app-managed model download. Longer imported recordings remain playable and editable as notes, but use the desktop's local transcription adapter for clips over 60 seconds. A transcription request has a two-minute timeout and can be cancelled.

Desktop recordings may use WebM, Ogg or FLAC. Their notes remain editable on iPad and the original audio is preserved, but native playback, merging or transcription may not support that format. Use the desktop for those audio operations if the iPad reports it cannot decode a clip.

Microphone permission is requested only after **Record my idea**; speech permission only after **Transcribe on this iPad**. Permissions can be changed in iPad Settings → Privacy & Security. The app uses [`AVAudioApplication.requestRecordPermission`](https://developer.apple.com/documentation/avfaudio/avaudioapplication/requestrecordpermission(completionhandler:)) and [`AVAudioRecorder`](https://developer.apple.com/documentation/avfaudio/avaudiorecorder) for file recording, pause, resume and stop.

## Portable files and recovery

Inside the selected paper:

```text
Section writing/Voice notes/
  2026-09-20 103000 - Introduction - My idea - 8char-id.md
  Audio/<same readable name>.m4a
  Transcripts/<note-id>-<run-id>.json
```

Markdown uses `awl_kind: voice_note`, paper/section identifiers, relative audio and transcript links, an audio SHA-256, and the same four named sections as the desktop: **Original transcription**, **My corrected spoken notes**, **Ideas I chose to develop**, and **Transcription history**. Raw transcript JSON stores text and timestamped segments. Another successful transcription adds a separate JSON record; it does not replace the first raw transcript or an author's corrected notes.

Merged notes additionally contain `merged_from` in playback order and a **Merged recordings** list. Soft deletion uses `trashed` and `trashed_at`. Native edits preserve desktop request identifiers and additional note sections.

The native app keeps an app-local recovery copy of audio and edits. **Recordings kept on this iPad** reopens those copies. A vault note changed on another device is not overwritten silently: the save is refused and the local recovery remains. Reload the synced note after resolving which version to retain. Declared transcript files must finish syncing before a note can be reopened; unrelated/orphan transcript files are ignored.

## Development checks

Portable storage tests are in `ipad/Tests/VoiceTests.swift`. They cover native/desktop YAML and JSON metadata, human-readable section IDs, audio and first-transcript preservation, corrected notes, stale writes, missing synced assets, orphan exclusion and path checks. They use synthetic bytes to test storage, not speech accuracy.

`ipad/Tests/VoiceMergeTests.swift` generates two distinct WAV tones, exports forward and reverse M4A merges, and measures frequency in each part to verify playback order. It also checks duration, original-file preservation and refusal to overwrite an existing output. These generated audio tests do not use a microphone or private recordings.

Build the native app with Xcode using the `AcademicWritingLab` scheme. A simulator build checks API/type integration; it does not prove microphone capture or language availability on a physical iPad. Test recording, interruption, playback, supported and unsupported languages, permission denial and Obsidian Sync on the actual iPad before relying on it for irreplaceable audio. The feature is not automatically installed on a connected device by a source-code update.
