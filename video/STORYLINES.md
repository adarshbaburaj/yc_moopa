# Moopa demo film: three storylines

Facts every storyline uses (all from the code, nothing invented):

- **Band (Vexo Open):** listens on a double-tap; the accelerometer streams at 50 Hz. A fall is a free-fall, then an impact, then stillness.
- **Ring (COLMI R02):** heart rate and SpO2. Shown as LIVE only if `--ring real` connected during filming, otherwise labelled SIMULATED.
- **Ears:** Deepgram Nova-3 speech-to-text, in a Pipecat real-time pipeline.
- **Brain:** OpenAI (gpt-6-sol) understands the request and picks the tool: call, shop, vitals, alert.
- **Eyes on the phone:** Gemini on Vertex AI reads the screen and picks one safe tap at a time.
- **Hands:** Phone Harness over wireless adb operates the Android phone.
- **Judgment:** TypeSafe System One (Jev) decides whether "are you okay?" got an okay, and whether "go ahead" really means yes.
- **Voice:** Deepgram Aura-2, played from the phone's own speaker; the Moopa Halo glows while the agent works.
- **No Bixby, no Siri, no Google Assistant.** Moopa uses the apps the way a person would, tap by tap. It never taps "Place order" and never diagnoses.

---

## A. One day with Grandpa (recommended: a stranger follows a person, not a diagram)

**Device / form:** a moment in someone's day, as an object-to-object chain. Each scene ends on the thing that opens the next.
The viewer spends one day with an elder who never touches a screen. Each time of day brings one need, and the hardware steps out of the footage the first time it acts. The film ends by opening the machine to show who did the work.

- **First 2 s:** real close-up of a wrist double-tapping the band, a "9:12 AM" time stamp, and the phone behind it waking up and dialling "Grandson in NYC".
- **Beats:** hook (call dials) → the band lifts out of the footage, "It listens" → 11:40 AM "Get me a yoga mat": Amazon on the phone under the halo, "Shall I go to checkout?", a spoken yes → 4:05 PM "How am I doing today?": the ring lifts out, "It feels", heart rate lands → 7:30 PM the fall: "Are you okay?", 10 s of silence counting down, the family page turns red, the phone calls → the brain: the sentence "Call my grandson" travels band → Deepgram → OpenAI → Gemini → phone, each part named → "No Bixby. No Siri." → real sign-ups → end card.
- **Look:** your real footage full-bleed; between scenes, a warm daylight ground (#F4F1EC) with the halo's own violet/blue/pink sweep as the only accent, carried as a ring that opens each scene.
- **Sound:** a warm piano-and-pulse bed at ~96 bpm, almost silent during the fall countdown, opening up on the brain section. A pop when each device lands, one riser into the end card.

## B. The sentence that travels

**Device / form:** one object across apps, as one continuous take.
A spoken sentence becomes a waveform that leaves the band and flies through Moopa's stack to land as a tap on the phone. The camera follows it four times, once per demo. The "what's the brain" part *is* the film, not a section.

- **First 2 s:** the words "Call my grandson" leave the band as a waveform and the camera chases them.
- **Beats:** waveform leaves the band → Deepgram turns it into text → OpenAI picks "call" → Gemini finds the button → the phone dials (clip) → the same route for the yoga mat, vitals and fall, each faster → "No Bixby. No Siri." → sign-ups → end card.
- **Look:** a large cut-away of the system on the daylight ground; clips play inside the phone at the end of the route.
- **Sound:** a driving pulse at ~120 bpm; a whoosh per hop, rotating three takes.

## C. Hands that don't work anymore (the bold one)

**Device / form:** life before and after, as split screen to one.
Shaky hands fight a tiny screen on the left; on the right, one sentence does the same job. The tap count on the left climbs while the right finishes, then the left pane collapses.

- **First 2 s:** an extreme close-up of an old thumb missing a tiny "Video call" button. A tap counter reads 1… 2… 3.
- **Beats:** the struggle → double-tap → split: the taps it takes vs. one sentence, for the call, then the yoga mat (the tap count from Moopa's own action log) → the ring and the fall, full-frame → who did the tapping: the brain → "No Bixby. No Siri." → sign-ups → end card.
- **Look:** harsh cool light on the struggle side, warm daylight on Moopa's side.
- **Sound:** near silence and clicks on the struggle side; music arrives with the double-tap.
- **Needs one extra clip:** someone struggling with the phone by hand.

---

All three: 1920×1080, 30 fps, about 90–120 s. Your clips carry the real voices (no narrator). Music comes from the HyperFrames catalog if your HeyGen sign-in allows it; otherwise the film is silent apart from the clip audio, and you can drop any track into `clips/music.mp3`.
