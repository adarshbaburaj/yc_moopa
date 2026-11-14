# clips/: drop the demo footage here

The video (`video/`) picks these files up by name. Video files are git-ignored (too big for git).
Any format works (.mp4, .mov). Landscape is best for the wide shots; the phone-screen recordings are portrait and that's fine.

| File | What to film | How |
|---|---|---|
| `band.jpg` | The Vexo band on your wrist, close-up, plain background, good light | Phone camera |
| `ring.jpg` | The COLMI ring on your finger, close-up, same background | Phone camera |
| `01-call.mp4` | Double-tap the band → "Call my grandson" → the phone dials WhatsApp video | A second phone filming your wrist + the Samsung together |
| `01-call-screen.mp4` | The Samsung's screen during the same take | `scrcpy --record` (below) |
| `02-yoga.mp4` | "Get me a yoga mat" → Amazon opens, searches, adds to cart → "Shall I go to checkout?" → "Yes" → stops at the final screen | Same two cameras |
| `02-yoga-screen.mp4` | The Samsung's screen during that take | `scrcpy --record` |
| `03-how-am-i.mp4` | "How am I doing today?" → Moopa answers with heart rate, SpO2 and steps | Wrist + phone, or wrist + Mac dashboard |
| `04-fall.mp4` | A safe, staged fall (onto a sofa or mat) → "Are you okay?" → stay silent → the phone calls family | Wide shot |
| `04-dashboard.mov` | The family page at http://127.0.0.1:8765 turning red during the fall | QuickTime → File → New Screen Recording |
| `signups.png` | The Google Form's Responses tab (or the sign-ups page at http://127.0.0.1:8765/signups) | Screenshot |

Record the phone screen without a cable (wireless adb is already set up):

```
ADB=tools/platform-tools/adb tools/scrcpy-macos-aarch64-v5.0.1/scrcpy --record clips/01-call-screen.mp4 --audio-dup
```

`--audio-dup` keeps Moopa's voice playing on the phone while scrcpy records it. Press Ctrl+C in that terminal to stop the recording.

Tips:
- Start each clip 2 s before the double-tap and stop it 2 s after the result. The video trims the rest.
- Put the Mac's mic, or the band, close to your mouth, and keep the room quiet.
- For the "How am I doing" take, run with `--ring real` so the numbers come from the ring. If it falls back, the dashboard and the video both say SIMULATED.
