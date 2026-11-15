# Moopa 🫶

**A wristband that helps grandparents use their phone just by talking, and calls family if they fall.**

> "My grandfather fainted alone at home in June and none of us knew."
> That's why we built Moopa.

Let's make ageing more independent.

---

## What is Moopa? (the short version)

Phones are hard when your eyes are tired and your fingers shake.
So Moopa lets a grandparent **skip the screen completely**.

1. They **tap their wristband twice**.
2. They **say what they want**, like *"Call my grandson."*
3. Moopa **uses the phone for them**: it opens the app, finds the button and taps it, just like a helpful grandchild would.

While Moopa is working, the phone glows with a soft rainbow border (we call it **the halo**), so you can see it's busy.

---

## What can it do?

| You say… | Moopa does… |
|---|---|
| 📞 "Call my grandson." | Opens WhatsApp and starts a video call with him. |
| 🧘 "Order yoga mats for me, please." | Opens Amazon, finds a yoga mat, puts it in the cart, tells you the name and price, then **asks "Shall I go to checkout?"** It never buys anything without a spoken **yes**, and it never presses "Place order" by itself. |
| ❤️ "How am I doing today?" | Tells you your heart rate and blood oxygen (from the ring) and your steps (from the band). |
| 🆘 *(nothing, because you fell)* | The band feels the fall. Moopa asks **"Are you okay? Are you all right?"** If you say you're fine, it relaxes. If you ask for help, or say nothing for 10 seconds, it **calls your family** and the family's screen turns **red**. |

---

## The pieces

- **The band (Vexo Open band)**: goes on your wrist. It has a microphone (to hear you) and a motion sensor (to feel a fall).
- **The ring (COLMI R02)**: goes on your finger. It measures heart rate and blood oxygen.
- **The phone (Android)**: Moopa controls it over Wi-Fi. No cables!
- **The laptop**: runs Moopa's brain.
- **Two screens**:
  - **Grandpa screen**: a cute pixel helper called **Moo** who shows what's happening ("I'm listening…", "Calling Grandson…", "Are you okay?").
  - **Family screen**: shows heart rate, steps, everything Moopa heard and did, and turns red if there's an emergency.

---

## How does it work? (like you're 10)

Think of Moopa as a team of helpers passing a note along:

1. **The ears 👂**: [Deepgram](https://deepgram.com) turns your voice into words (inside [Pipecat](https://github.com/pipecat-ai/pipecat), which keeps the conversation flowing in real time).
2. **The brain 🧠**: [OpenAI](https://openai.com) reads the words and decides what to do: call, shop, check vitals, or get help.
3. **The eyes 👀**: [Gemini](https://deepmind.google/technologies/gemini/) (on Google Vertex AI) looks at the phone screen and picks **one safe tap at a time**.
4. **The hands ✋**: Phone Harness taps the phone over Wi-Fi, like a finger would.
5. **The double-checker ✅**: [TypeSafe System One](https://typesafe.ai) checks "Was that *really* a yes?" before going to checkout. Gemini judges "Did they say they're okay?" after a fall.
6. **The voice 🔊**: Deepgram reads Moopa's answer out loud from the phone's own speaker.

**No Bixby. No Siri.** Moopa doesn't need any special app support. It reads the screen and taps, just like you do.

---

## How does it know someone fell?

The band's motion sensor checks for three things in a row:

1. **Falling**: for a moment it feels almost weightless (under 0.4 g).
2. **Bump**: then a big hit (over 2.5 g).
3. **Stillness**: then no movement for 3 seconds.

If all three happen, Gemini double-checks the numbers (about 1 second). Then Moopa asks "Are you okay?"
If the answer isn't clear, it asks once more: "Are you hurt? Say yes or no."
**Double-tapping the band means "I'm fine."**

---

## What's real and what's pretend? (being honest)

| Thing | Real or pretend? |
|---|---|
| Voice → phone call on WhatsApp | ✅ Real (in the demo video, uncut, just sped up) |
| Voice → Amazon yoga mat in the cart → "Shall I go to checkout?" | ✅ Real |
| The halo glow on the phone | ✅ Real (our own little Android app) |
| Fall detection from the band | ✅ Real code, tested with a pretend band and real Gemini |
| The fall person in the video | ⚠️ **AI-generated** with Google Veo, and labelled that way on screen |
| Heart rate in the video | ⚠️ **Simulated**, and labelled SIMULATED. Moopa tries the real ring first and says "SIMULATED" everywhere if it can't reach it. |
| 8 sign-ups, 4 would pay $10, 21 care agencies emailed | ✅ Real numbers from our Google Form and outreach on 14 Nov 2026 |

Moopa is a **wellness and safety helper, not a medical device**. It never diagnoses anything.

---

## Run it yourself

You need: a Mac, an Android phone with Wireless debugging on, Python 3.12, and API keys.

```bash
# 1. Get the code
git clone https://github.com/adarshbaburaj/yc_moopa.git
cd yc_moopa

# 2. Make a Python home for it and install the parts
python3 -m venv .venv
.venv/bin/pip install pipecat-ai deepgram-sdk openai google-genai fastapi uvicorn sounddevice python-dotenv colmi-r02-client

# 3. Add your keys (copy the example, then fill it in; never share this file)
cp .env.example .env

# 4. Start Moopa
.venv/bin/python run.py --band real --ring real --no-camera
```

When you see **👍 READY FOR ACTION**, double-tap the band and talk.

Open the two screens in a browser:
- Grandpa screen: http://127.0.0.1:8765/?view=grandpa
- Family screen: http://127.0.0.1:8765/?view=family

**No band or phone yet?** Try `.venv/bin/python run.py --band sim --no-phone` and press **SPACE** to talk, or **f** to pretend to fall.

Useful switches: `--band real|sim|off`, `--ring real|sim|off`, `--mic band|mac`, `--voice phone|mac`, `--no-phone`, `--no-camera`, `--verbose`.

---

## What's in this folder?

```
run.py               starts everything
moopa/
  agent.py           the voice helper (ears, brain, voice)
  phone.py           taps the phone, finds buttons, never presses "Place order"
  band.py            talks to the wristband
  motion.py          spots falls from the motion sensor
  fall.py            "Are you okay?" and calling family
  ring.py            heart rate from the ring (or SIMULATED)
  server.py          feeds the two screens
dashboard/           the Grandpa screen (with Moo) and the Family screen
halo-app/            the tiny Android app that makes the phone glow and talk
video/               our demo film (made with HyperFrames)
```

---

## Privacy

- The microphone only listens **after a double-tap**. It's never always on.
- Motion data is checked **on the laptop**. Only a short summary of numbers goes to Gemini when a fall is suspected.
- Keys live in `.env`, which is **never** uploaded to GitHub.

---

## Built at a Y Combinator hackathon, 14 Nov 2026

With: **Vexo Open band**, **Deepgram + Pipecat**, **OpenAI**, **Google Gemini + Veo (Vertex AI)**, **TypeSafe System One**, **Phone Harness**, **ElevenLabs** (music in the film).

**What's next:** a real live heart-rate stream from the ring on stage, more apps (doctor appointments, groceries, taxis), and a pilot with the home-care agencies who signed up.
