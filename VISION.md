# SpeakEasy — Vision Document

## The Problem

Most language learning apps are built around **reading and typing**. Duolingo asks you to match words. Anki asks you to recall characters. Grammar books ask you to fill in blanks.

But real language fluency starts with **speaking**. You don't become fluent in Cantonese by multiple-choice quizzes about tones — you become fluent by saying "你好嗎" a hundred times at the market until it feels natural.

## The Vision

SpeakEasy is a toolkit for **oral-first language learning**. It generates interactive audio lessons from real-life scenarios, powered by AI translation and synthesis.

The key insight: **you don't need an app**. A self-contained HTML file with inline audio, opened in any browser, on any device, is the most portable and accessible lesson format possible. No app stores, no subscriptions, no internet after download.

## Design Principles

### 1. Speak First
Every lesson centers on speaking. Audio is the primary content, text is secondary. The default interaction is "listen → repeat → check", not "read → answer".

### 2. Daily Life Scenarios
Lessons are organized around situations you'll actually encounter — ordering food, greeting colleagues, asking directions, making small talk. Not textbook sentences about "the cat is on the table."

### 3. Dialect Respect
Cantonese and Sichuanese aren't "bad Mandarin" — they're rich languages in their own right. Lessons use authentic vocabulary, slang, and cultural context. The LLM translation pipeline uses dialect-aware prompts to produce natural, native-sounding translations.

### 4. Shadow Practice
The shadowing technique (listen → immediately repeat) is the fastest way to build speaking muscle memory. Every sentence has a loop mode specifically designed for shadowing.

### 5. Progressive Difficulty
Start with simple greetings, build to complex conversations. Each level assumes mastery of the previous one. The curriculum is carefully sequenced — not random topic dumps.

### 6. Zero Friction
Single HTML files. No build step. No account required. No server after generation. Click and learn.

## The Learning Philosophy

### English: Your Bridge Language
English isn't just a language — it's a thinking tool. Learning English in Cantonese/Sichuanese context means you're building the neural pathways for bilingual switching, which makes learning additional languages faster.

### Cantonese: Living Language
Cantonese is the language of Hong Kong cinema, Cantonese pop, dim sum culture, and 80+ million speakers. It's tonal, expressive, and shockingly different from Mandarin in everyday speech. Learning Cantonese unlocks a cultural world that Mandarin alone can't reach.

### Sichuanese: Heritage Preservation
Sichuanese (四川话) is a dialect on the UNESCO endangered list. Once spoken by hundreds of millions across Southwest China, it's rapidly being replaced by standardized Mandarin among younger generations. Learning it is an act of cultural preservation and personal connection.

## Technology Choices

| Choice | Why |
|---|---|
| HTML lessons | Universal, offline-capable, no build step |
| YAML curriculum | Human-readable, easy to edit, git-friendly |
| BearEcho API | Proven multi-dialect TTS + LLM translation |
| Python pipeline | Simple, no heavy framework needed |
| Single-file output | Maximum portability |

## What Success Looks Like

- **3 months in**: You can have basic conversations in English, greet people in Cantonese, and order food in Sichuanese
- **6 months in**: You can navigate Hong Kong in Cantonese, understand Sichuan TV shows, and hold English meetings
- **1 year in**: You think bilingually, switch languages naturally, and feel genuinely fluent in daily interactions

## Open Source Goals

1. **Transparency**: Anyone can see and improve the curriculum
2. **Community**: Native speakers can contribute authentic content
3. **Extensibility**: The framework supports any language with a TTS engine
4. **Education**: Free, high-quality oral language learning for everyone
5. **Preservation**: A platform for endangered dialects to find new speakers

---

*This is a living document. As SpeakEasy evolves, so will this vision.*
