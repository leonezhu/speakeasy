# 🗣️ SpeakEasy

> **Speak first, think later.** An open-source oral language learning toolkit that turns daily life into immersive speaking practice — powered by real TTS voices and LLM translation.

## What is SpeakEasy?

SpeakEasy generates **self-contained HTML lessons with inline audio** for oral language learning. Instead of typing drills or grammar quizzes, it focuses on what matters most for real communication: **listening, repeating, and speaking**.

Each lesson is a mini podcast you can interact with — play sentences, shadow the speaker, hide translations, and quiz yourself. Lessons work offline on any device, no app store needed.

## The Learning Path

SpeakEasy teaches three languages in a deliberate progression:

```
🇺🇸 English (Foundation)  →  🇭🇰 Cantonese (Dialect 1)  →  🔥 Sichuanese (Dialect 2)
       Global language            Practical for HK/GD           Cultural roots
```

**Why this order?**
- **English first**: The most broadly useful second language. Builds a foundation for bilingual thinking.
- **Cantonese**: A living dialect with rich slang, essential for life in Hong Kong/Guangdong. Different enough from Mandarin to be a genuine second Chinese language.
- **Sichuanese**: Personal connection, vibrant culture, and preservation of a declining dialect.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    SpeakEasy Pipeline                     │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  curriculum.yaml                                          │
│  (lesson content, dialogues, vocabulary)                  │
│         │                                                │
│         ▼                                                │
│  ┌─────────────┐    API calls    ┌───────────────────┐  │
│  │ generate.py  │ ──────────────► │  BearEcho Backend  │  │
│  │ (pipeline)   │                │  localhost:8000    │  │
│  │              │◄────────────── │                    │  │
│  │              │  audio files  │  ┌──────────────┐  │  │
│  └──────┬───────┘  + metadata   │  │ edge-tts     │  │  │
│         │                        │  │ (English)   │  │  │
│         ▼                        │  ├──────────────┤  │  │
│  ┌─────────────┐                │  │ qwen-tts     │  │  │
│  │ lesson.html  │                │  │ (Cantonese) │  │  │
│  │ (template)   │                │  ├──────────────┤  │  │
│  │              │                │  │ dui-tts     │  │  │
│  └──────┬───────┘                │  │ (Sichuanese)│  │  │
│         │                        │  ├──────────────┤  │  │
│         ▼                        │  │ kokoro-tts  │  │  │
│  ┌─────────────┐                │  │ (Alt voices)│  │  │
│  │ lessons/     │                │  ├──────────────┤  │  │
│  │ audio/       │                │  │ Translation  │  │  │
│  │ (offline)    │                │  │ qwen-mt /    │  │  │
│  └─────────────┘                │  │ GLM-4-flash  │  │  │
│                                  │  └──────────────┘  │  │
│                                  └───────────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## How It Works

1. **Define** lessons in `curriculum.yaml` — dialogues, vocabulary, cultural notes
2. **Generate** with `python scripts/generate.py` — calls BearEcho for translation + TTS audio
3. **Learn** with `lessons/english/unit-01-greeting.html` — self-contained HTML, works anywhere
4. **Repeat** daily — add new units, regenerate, practice

### BearEcho Integration

[BearEcho](https://github.com/yourusername/bearecho) provides the AI backbone:

| Capability | Engine | Languages |
|---|---|---|
| TTS | edge-tts | English, Chinese, multilingual |
| TTS | qwen-tts | Cantonese (yue) |
| TTS | dui-tts | Sichuanese (sicuan) |
| Translation | qwen-mt-turbo | Standard languages |
| Translation | GLM-4-flash LLM | Cantonese, Sichuanese (dialect-aware) |

SpeakEasy calls the REST API:
```
POST /api/tts
{
  "text": "你好嗎？",
  "targetLangs": ["yue"],
  "sourceLang": "yue",
  "voices": {"yue": "WingNeuro"}
}
→ Returns audio file path(s)
```

## Features

- 🎧 **Per-sentence audio** — click any sentence to hear it
- 🔁 **Shadow mode** — loop sentences for repetition practice
- 🙈 **Progressive reveal** — hide translations, test yourself
- 📱 **Mobile-first** — clean UI that works on any screen
- 📦 **Self-contained** — single HTML file, no build step, no server needed
- 🌍 **Multi-language** — English, Cantonese, Sichuanese with more to come
- 🤖 **AI-powered** — LLM translation handles dialects that traditional MT can't
- 🔓 **Open source** — MIT licensed, contributions welcome

## Quick Start

### Prerequisites
- Python 3.10+
- BearEcho backend running on `localhost:8000`
- Dependencies: `pyyaml`, `requests`, `jinja2`

```bash
# Clone the repo
git clone https://github.com/yourusername/speakeasy.git
cd speakeasy

# Install dependencies
pip install -r requirements.txt

# (Optional) Dry run to see what would be generated
python scripts/generate.py --dry-run

# Generate all Level 1 English lessons
python scripts/generate.py --lang en --level beginner

# Generate a specific lesson
python scripts/generate.py --lang en --level beginner --unit 1

# Open in browser
open lessons/english/unit-01-greeting.html
```

## Curriculum Structure

```
Beginner           Intermediate        Advanced
─────────          ───────────         ─────────
01 Greeting        01 Meetings         01 Storytelling
02 Introductions   02 Negotiation      02 Debates
03 Numbers         03 Presentations    03 Slang deep dive
04 Shopping        04 Travel planning  04 Cultural humor
05 Food ordering   05 Tech support     05 Free conversation
06 Directions      ...                  ...
```

Each unit contains:
- **Scenario**: Real-world context (e.g., "Ordering at a cha chaan teng")
- **Dialogue**: 8-12 sentences with source + target language
- **Vocabulary**: Key words with pronunciation notes
- **Cultural Notes**: Why this matters, usage tips
- **Practice**: Shadow mode + quiz prompts

## Project Goals

### v1.0 — Foundation
- [x] Curriculum design (English Level 1)
- [x] Generation pipeline with BearEcho integration
- [x] HTML lesson template with audio playback
- [x] Shadow practice mode

### v1.5 — Expansion
- [ ] Cantonese curriculum (Beginner → Advanced)
- [ ] Sichuanese curriculum (Beginner → Advanced)
- [ ] Spaced repetition tracking
- [ ] Lesson difficulty scoring

### v2.0 — Intelligence
- [ ] AI-generated lessons from any topic
- [ ] Pronunciation scoring (via Whisper)
- [ ] Personalized review scheduling
- [ ] Community lesson sharing

### v3.0 — Ecosystem
- [ ] More dialects (Hakka, Teochew, Minnan)
- [ ] Language exchange pairing
- [ ] Voice cloning for custom lesson voices

## Contributing

We welcome contributions! Areas where help is especially appreciated:

1. **Curriculum content** — Write dialogues for new scenarios
2. **Translations** — Add or improve Cantonese/Sichuanese content
3. **Templates** — Improve the lesson UI/UX
4. **Languages** — Add support for new languages/dialects
5. **Testing** — Try the lessons and report issues

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for details.

## License

MIT License — use freely, modify freely, share freely.

---

*"Language is the road map of a culture. It tells you where its people come from and where they are going."* — Rita Mae Brown
