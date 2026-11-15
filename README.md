# Moopa

### Let's make ageing more independent.

**Moopa is a wristband that lets older people use their phone just by talking. And when they fall, it checks on them and calls family, without being asked.**

---

## The problem

> "My grandfather fainted alone at home in June, and none of us knew."

Our parents and grandparents increasingly live alone, often far from their children. Their phone is their lifeline to family, shopping and help, but it was built for young eyes and steady fingers. Tiny buttons, menus and passwords quietly lock them out.

Today's answers don't fit:
- **Voice assistants** (Siri, Bixby, Google Assistant) only do what each app allows them to. They can't really *use* the phone for you.
- **Fall alarms** are separate gadgets with a panic button that you have to press, and you can't press it if you're on the floor and confused.
- **Families** end up either worrying all day or phoning every hour.

## The solution

**Moopa is the bridge between older people and technology.**

A soft band on the wrist and a ring on the finger, with an AI agent that operates the phone the way a patient grandchild would.

1. **Tap the band twice.**
2. **Say what you want.**
3. **Moopa does it on the phone**: it opens the app, reads the screen, and taps the right buttons. A glowing halo on the screen shows it's working.

No new apps to learn. No screens to read. Just talking.

## What Moopa does today

| They say… | Moopa… |
|---|---|
| **"Call my grandson."** | opens WhatsApp and starts the video call. *(Demo: one real take, about 20 seconds from double-tap to his face.)* |
| **"Order yoga mats for me, please."** | finds a mat on Amazon, adds it to the cart, reads back the name and price, and asks **"Shall I go to checkout?"** **Nothing is bought without a spoken yes**, and Moopa never presses "Place order" itself. |
| **"How am I doing today?"** | answers from the ring (heart rate, blood oxygen) and the band (steps, activity). |
| *(nothing, because they've fallen)* | The band feels the fall. Moopa asks **"Are you okay? Are you all right?"** If they're fine, it stands down. If they ask for help, or don't answer for 10 seconds, it **calls family**, and the family dashboard turns **red**. |

The family gets a live dashboard showing vitals, activity, and everything Moopa heard and did. The grandparent gets a calm screen with **Moo**, a friendly pixel character that shows what's happening in big, simple words.

## Why now

- AI models can now **see a phone screen and decide what to tap**, reliably enough to do real tasks in ordinary apps, with no special integrations.
- Real-time speech is now fast and accurate enough for a natural back-and-forth with an older voice.
- Wearables like the Vexo band and the COLMI ring are cheap, comfortable and open to developers.

## How it works

| Job | What we use |
|---|---|
| Hear the request | Vexo band microphone (on only after a double-tap) → **Deepgram** speech-to-text in a **Pipecat** real-time pipeline |
| Understand and decide | **OpenAI** picks the right action: call, shop, vitals, or alert |
| Use the phone | **Gemini** (Vertex AI) reads the screen and picks one safe tap at a time; **Phone Harness** taps the Android phone over Wi-Fi |
| Double-check | **TypeSafe System One** checks that a "yes" really means yes before checkout |
| Speak back | **Deepgram** voice, played from the phone's own speaker |
| Spot a fall | the band's motion sensor: weightless (< 0.4 g) → impact (> 2.5 g) → still for 3 s, then a ~1 s **Gemini** check, then the spoken check-in |
| Vitals | **COLMI R02** ring: heart rate and blood oxygen |

**Safety rules built into the code:** Moopa never taps "Buy now", "Place order" or "Pay". It treats anything on the screen as information, never as instructions. It is a wellness and safety helper, **not a medical device**, and never diagnoses.

## Traction (built and tested in one day)

All numbers are real, from our Google Form and outreach on 14 Nov 2026:

- **8 people signed up** for Moopa. Not just friends: they include my professor and a stranger I met on a flight.
- **4 of the 8 said they would pay $10 (refundable) to reserve one.**
- **21 home-care agencies and contacts** reached by email.
- What they want most: **a fall alert that calls family** and **heart-rate trends** (3 of 8 each).
- Who it's for: a grandparent (3), both parents (2), a mother (2), a father (1).

## Business model

- **Families** buy the band and ring kit and pay a small monthly subscription for the agent and the family dashboard.
- **Home-care agencies** use Moopa across their clients, with one dashboard for all of them.
- We're starting with **$10 refundable reservations** to measure real demand.

## What's next

- Live heart-rate streaming from the ring during demos, plus long-term wellness trends for families.
- More everyday tasks: doctor appointments, groceries, taxis, paying bills (always with a spoken yes).
- A pilot with the care agencies who replied.
- An even simpler band: speaker and mic on the wrist, so the phone can stay in another room.

## Honest notes on the demo

| | |
|---|---|
| Voice → WhatsApp video call | ✅ Real, one uncut take (sped up in the video, and labelled) |
| Voice → Amazon cart → "Shall I go to checkout?" | ✅ Real |
| Halo glow on the phone | ✅ Real (our own small Android app) |
| Fall detection + "Are you okay?" check-in | ✅ Real code, tested end to end with a simulated band fall and live Gemini |
| The person falling in the video | ⚠️ AI-generated with Google Veo, labelled on screen |
| Heart-rate numbers in the video | ⚠️ Simulated, labelled SIMULATED (the app tries the real ring first) |

---

<details>
<summary><b>Run it yourself</b></summary>

You need a Mac, an Android phone with Wireless debugging on, Python 3.12, and API keys (Deepgram, OpenAI, Google Vertex AI, TypeSafe).

```bash
git clone https://github.com/adarshbaburaj/yc_moopa.git && cd yc_moopa
python3 -m venv .venv
.venv/bin/pip install pipecat-ai deepgram-sdk openai google-genai fastapi uvicorn sounddevice python-dotenv colmi-r02-client
cp .env.example .env        # add your keys; never commit this file
.venv/bin/python run.py --band real --ring real --no-camera
```

When it says **READY FOR ACTION**, double-tap the band and speak.
- Grandparent screen: http://127.0.0.1:8765/?view=grandpa
- Family screen: http://127.0.0.1:8765/?view=family

No hardware? `.venv/bin/python run.py --band sim --no-phone`, then press SPACE to talk or **f** to pretend to fall.

```
run.py          starts everything
moopa/          agent (voice), phone (taps), band, motion + fall, ring, server
dashboard/      grandparent screen (Moo) + family screen
halo-app/       Android app: the halo glow + Moopa's voice on the phone speaker
video/          the demo film (HyperFrames)
```
</details>

**Built solo in one day at VexoHacks, a Y Combinator hackathon in SF, 14 Nov 2026**, with the Vexo Open band, Deepgram + Pipecat, OpenAI, Google Gemini and Veo, TypeSafe System One, Phone Harness and ElevenLabs.
