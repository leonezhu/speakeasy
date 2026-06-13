# SpeakEasy — Hermes Agent Skill

## Overview

This skill enables Hermes Agent to manage the SpeakEasy oral language learning project: generate lessons, manage curriculum content, and produce TTS audio via the BearEcho backend.

**Repository**: `~/Documents/GitHub/notes/speakeasy/`
**BearEcho API**: `http://localhost:8000`

---

## Trigger Patterns

Hermes should activate this skill when the user says things like:
- "generate a lesson about..."
- "create a new English/Cantonese/Sichuanese lesson"
- "add a lesson to the curriculum"
- "make a lesson about [topic]"
- "练习一下 [language]" (practice)
- "生成课程" (generate curriculum)

---

## Capabilities

### 1. Generate New Lessons

When the user wants a new lesson, follow this pipeline:

```
1. Determine: language (en/yue/sicuan), level, theme, topic
2. Create/update curriculum.yaml with the new unit
3. Run generate.py to produce HTML + audio
4. Open the result in browser
```

**Example interaction:**
> User: "Generate an English lesson about ordering coffee"
>
> Agent actions:
> 1. Add unit to `data/curriculum.yaml` under `en.beginner`
> 2. Write dialogue sentences (8-12 lines, realistic scenario)
> 3. Add vocabulary (5-8 key words)
> 4. Add cultural notes (2-3 notes)
> 5. Run: `cd ~/Documents/GitHub/notes/speakeasy && python scripts/generate.py --lang en --level beginner --unit N`
> 6. Report: "Lesson generated at lessons/english/unit-XX.html"

### 2. Generate Audio via BearEcho API

Direct TTS generation without the full pipeline:

```bash
# Single sentence TTS
curl -X POST http://localhost:8000/api/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好，我想叫一杯咖啡",
    "targetLangs": ["yue"],
    "sourceLang": "yue",
    "voices": {"yue": "WingNeuro"}
  }' \
  --output audio.cantonese.mp3

# Multi-language TTS (generate same text in multiple languages)
curl -X POST http://localhost:8000/api/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Good morning, how are you?",
    "targetLangs": ["en", "yue", "sicuan"],
    "sourceLang": "en",
    "voices": {
      "en": "en-US-ChristopherNeural",
      "yue": "WingNeuro"
    }
  }'
```

### 3. Add New Curriculum Units

To add a lesson to the curriculum:

1. Edit `data/curriculum.yaml`
2. Add unit under the appropriate `curriculum.<lang>.<level>` section
3. Required fields:
   ```yaml
   - unit: N
     id: unique-slug
     title: "Lesson Title"
     theme: work|daily|social|travel|tech|food|expressions
     scenario: "Context description for the learner"
     cultural_notes:
       - "Note about cultural context"
     vocabulary:
       - word: "Key phrase"
         definition: "What it means"
         example: "Example usage"
     dialogue:
       - speaker: A
         source: "Source language sentence"
         target: "Target language translation"
         note: "Grammar/usage tip"
   ```

### 4. Curriculum Management Commands

| Command | Action |
|---|---|
| List lessons | `python scripts/generate.py --list` |
| Generate all | `python scripts/generate.py --all` |
| Dry run | `python scripts/generate.py --lang en --level beginner --dry-run` |
| Force regenerate | `python scripts/generate.py --lang en --level beginner --force` |
| Specific unit | `python scripts/generate.py --lang en --level beginner --unit 1` |
| Multiple units | `python scripts/generate.py --lang en --level beginner --unit 1,3,5` |

### 5. Notes Vault Integration

Lessons can be linked to the broader knowledge base:

- **Add links**: Each lesson HTML can reference related notes in the vault
- **Daily review**: Generate a "today's review" lesson from recent notes
- **Vocabulary mining**: Extract key vocabulary from user's notes and create mini-lessons
- **Cultural context**: Pull cultural notes from notes/vault and include in lessons

**Example workflow:**
> User: "I learned some new phrases at dim sum today. Make it a lesson."
>
> Agent:
> 1. Review recent notes for food/dining phrases
> 2. Create Cantonese lesson unit with those phrases
> 3. Generate audio and HTML
> 4. Link the lesson back to the original note

---

## Language Reference

| Code | Language | TTS Engine | Voice | Translation |
|---|---|---|---|---|
| `en` | English | edge-tts | en-US-ChristopherNeural | qwen-mt-turbo |
| `yue` | Cantonese | qwen-tts | WingNeuro | GLM-4-flash (dialect-aware) |
| `sicuan` | Sichuanese | dui-tts | default | GLM-4-flash (dialect-aware) |

## File Structure Reference

```
speakeasy/
├── data/curriculum.yaml     ← Lesson content (edit this to add lessons)
├── scripts/generate.py      ← Generation pipeline (run this to build)
├── templates/lesson.html    ← HTML template (Jinja2)
├── lessons/english/         ← Generated English lessons
├── lessons/cantonese/       ← Generated Cantonese lessons
├── lessons/sichuanese/      ← Generated Sichuanese lessons
├── audio/english/           ← Generated English audio
├── audio/cantonese/         ← Generated Cantonese audio
└── audio/sichuanese/        ← Generated Sichuanese audio
```

## Prerequisites Checklist

Before generating lessons, verify:
1. ✅ BearEcho running: `curl http://localhost:8000/health`
2. ✅ Python deps: `pip install pyyaml requests jinja2`
3. ✅ Curriculum data: `data/curriculum.yaml` exists with content

## Best Practices

1. **Always dry-run first** — Check what will be generated before making API calls
2. **Real dialogues** — Write natural, conversational sentences, not textbook examples
3. **Cultural context** — Include cultural notes that explain *why* something is said
4. **Progressive difficulty** — Each unit should build on vocabulary from previous units
5. **Keep units focused** — One clear scenario per unit, don't try to cover too much
6. **Audio quality check** — After generating, open the HTML and verify audio plays correctly
