# SPEC: Moopa, one day with Grandpa (storyline A)

GOAL:    A judge watches one elder's day handled by voice alone, sees what the band, the ring and each AI part does,
         and leaves remembering "it runs the phone for them: no Bixby, no Siri".
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps.
TIME:    105 s x 30 = 3150 frames. Music bed ~96 bpm (18.75 frames/beat) once a track is chosen.

LOOK:    ground #F4F1EC (the family view's own background), ink #1D1B18, muted #6D665C, line #E4DED4.
         Accent: the Moopa Halo sweep from the phone app (violet #7C4DFF, blue #2F80ED, pink #E0559B), only on
         the halo ring, one word per title, and the end card. Alert red #C62828 only in the fall scene.
         Display: Inter 900, titles 120 px (11% of height), tracking -0.03em. Time stamps Inter 900 200 px.
         Body lines Inter 700 46 px; quiet lines Inter 400 34 px. Never under 30 px.
         Medium: real footage full-bleed and the real phone screen at full frame height; product cutouts on the ground
         with a contact shadow 0 30px 60px rgba(29,27,24,0.22). No grain, no vignette, no glow.
OBJECTS: the Vexo band and the COLMI ring (from Adarsh's photos, cut out), the Samsung phone (real footage + scrcpy
         recording), the family view page (real screen recording), the halo (the app's own sweep gradient as a ring),
         the band's accelerometer trace (free-fall < 0.45 g, impact >= 1.6 g, still 4 s: the thresholds in motion.py).
MOTION:  arrivals expo.out 0.7 s; camera/route moves power2.inOut 0.8 s; exits power3.in 0.3 s;
         titles per word blur 6px -> 0 + opacity, 0.13 s each, 0.067 s apart, no translate;
         cutouts spring in back.out(1.4) on scale and y, never on opacity.
SHOTS:
  s1 hook   0-9     Clip 01-call full-bleed from frame 0. "9:12 AM" lands; the elder's words "Call my grandson." per word;
                    the phone dials. Ends on the wrist -> the band lifts out.
  s2 band   9-15    Band cutout springs up to 60% height. "The band listens." Waveform leaves the band and turns into
                    the next sentence.
  s3 yoga   15-35   "11:40 AM" + "Get me a yoga mat." The phone screen recording rises to full height in the centre
                    (halo visible); the real action log ticks in beside it; "Shall I go to checkout?" -> "Yes" ->
                    "Stopped before Place order. Family presses it."
  s4 ring   35-46   "4:05 PM" + "How am I doing today?" Ring cutout springs in. "The ring feels." Heart rate lands,
                    tagged LIVE or SIMULATED (whatever the ring really was). The pulse line flattens into the fall trace.
  s5 fall   46-64   "7:30 PM". Accelerometer trace draws free-fall -> impact -> still. Clip 04-fall. "Are you okay?"
                    10 -> 0 countdown in near silence. Colour flood to red: the family view goes red; the phone calls family.
  s6 brain  64-87   "Who did all that?" The sentence "Call my grandson" travels a route, one stop per part, the camera
                    flying stop to stop: hears (Vexo band mic) -> words (Deepgram Nova-3 in Pipecat) -> decides (OpenAI)
                    -> sees the screen (Gemini on Vertex AI) -> taps (Phone Harness, wireless adb) -> double-checks
                    (TypeSafe System One) -> speaks (Deepgram Aura-2 on the phone speaker).
  s7 nosiri 87-93   Colour flood to ink. "No Bixby." "No Siri." "No app integrations." -> "Moopa reads the screen and taps, like you."
  s8 proof  93-99   Real outreach and sign-up numbers from the tracker and the Google Form, counting up.
  s9 end    99-105  The halo ring draws itself; "Moopa" wipes in; the repo link holds 3 s.
BANNED:  dark void ground; glow, particles, lens flares; purple/blue gradients except the halo's own ring; glass cards;
         cream + serif + mono-label look; pills and chips; three cards in a row; logo grids (the stack is a route);
         corner labels and HUD; everything fading up; titles that drift after landing; the logo docked in a corner;
         any vital sign shown without its LIVE/SIMULATED tag; any sign-up number not from the real sheet or form.
QA:      t=0.2 (thumbnail = real footage), 10 (band), 22 (phone + log), 38 (ring + tag), 52 (trace), 60 (red), 70/78 (route),
         89 (No Siri), 96 (numbers), 103 (end card).
