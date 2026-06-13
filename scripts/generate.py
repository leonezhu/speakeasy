#!/usr/bin/env python3
"""
SpeakEasy Lesson Generator

Reads curriculum.yaml, calls BearEcho /api/tts/raw for TTS audio,
generates self-contained HTML lessons with local audio files.

All audio saved to speakeasy/audio/ — decoupled from BearEcho storage.

Usage:
    python scripts/generate.py --dry-run                      # Plan without generating
    python scripts/generate.py --lang en --level beginner      # Generate all beginner English
    python scripts/generate.py --lang en --unit 1             # Generate specific unit
    python scripts/generate.py --list                          # List all available lessons
"""

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from datetime import datetime

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("ERROR: requests required. Install with: pip install requests")
    sys.exit(1)

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    print("ERROR: Jinja2 required. Install with: pip install jinja2")
    sys.exit(1)

# ========== CONFIGURATION ==========
BEARECHO_API = os.environ.get("BEARECHO_API", "http://localhost:8000")
PROJECT_ROOT = Path(__file__).parent.parent
CURRICULUM_PATH = PROJECT_ROOT / "data" / "curriculum.yaml"
TEMPLATE_PATH = PROJECT_ROOT / "templates" / "lesson.html"
OUTPUT_LESSONS_DIR = PROJECT_ROOT / "lessons"
OUTPUT_AUDIO_DIR = PROJECT_ROOT / "audio"
PROGRESS_FILE = PROJECT_ROOT / "data" / ".progress.json"


def wav_to_mp3_bytes(wav_bytes: bytes) -> bytes:
    """Convert WAV bytes to MP3 bytes using ffmpeg (10x smaller)."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_f:
        wav_f.write(wav_bytes)
        wav_path = wav_f.name
    mp3_path = wav_path.replace(".wav", ".mp3")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, "-b:a", "64k", "-f", "mp3", mp3_path],
            capture_output=True, timeout=30,
        )
        with open(mp3_path, "rb") as f:
            return f.read()
    finally:
        os.unlink(wav_path)
        if os.path.exists(mp3_path):
            os.unlink(mp3_path)


# ========== HELPERS ==========

def load_curriculum():
    """Load and parse the curriculum YAML."""
    if not CURRICULUM_PATH.exists():
        print(f"ERROR: Curriculum not found at {CURRICULUM_PATH}")
        sys.exit(1)
    with open(CURRICULUM_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_progress():
    """Load generation progress tracker."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"generated": [], "last_run": None}


def save_progress(progress):
    """Save generation progress."""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def lesson_key(lang, level, unit):
    return f"{lang}:{level}:{unit}"


def is_generated(progress, key):
    return key in progress.get("generated", [])


def mark_generated(progress, key):
    if key not in progress.get("generated", []):
        progress["generated"].append(key)
    progress["last_run"] = datetime.now().isoformat()
    save_progress(progress)


# ========== BEARECHO RAW TTS CLIENT ==========

class BearEchoTTS:
    """Client for BearEcho /api/tts/raw — no auth, returns audio binary."""

    def __init__(self, base_url=BEARECHO_API):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def health_check(self):
        try:
            r = self.session.get(f"{self.base_url}/health", timeout=5)
            return r.status_code == 200
        except requests.ConnectionError:
            return False

    def generate(self, text: str, lang: str, voice: str = None,
                 output_path: Path = None) -> dict:
        """
        Generate TTS audio via /api/tts/raw.

        Args:
            text: Text to synthesize
            lang: Language code (en, yue, sicuan)
            voice: Optional voice_id override
            output_path: If provided, save audio to this path

        Returns:
            {"success": True/False, "path": str|None, "size": int, "error": str|None}
        """
        payload = {"text": text, "lang": lang}
        if voice:
            payload["voice"] = voice

        try:
            if output_path:
                # Use /file endpoint — saves server-side, but we want local
                # Instead, use / endpoint and save ourselves
                r = self.session.post(
                    f"{self.base_url}/api/tts/raw/",
                    json=payload,
                    timeout=60,
                )
                if r.status_code != 200:
                    return {
                        "success": False,
                        "error": f"HTTP {r.status_code}: {r.text[:200]}",
                    }

                # Save audio to local path
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(r.content)
                size = len(r.content)
                return {"success": True, "path": str(output_path), "size": size}
            else:
                r = self.session.post(
                    f"{self.base_url}/api/tts/raw/",
                    json=payload,
                    timeout=60,
                )
                if r.status_code == 200:
                    return {"success": True, "size": len(r.content), "data": r.content}
                return {
                    "success": False,
                    "error": f"HTTP {r.status_code}: {r.text[:200]}",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_batch(self, items: list[dict]) -> list[dict]:
        """
        Batch TTS via /api/tts/raw/batch.

        Args:
            items: [{"text": ..., "lang": ..., "voice": ...}, ...]

        Returns:
            [{"success": True/False, "audio_bytes": bytes|None, "error": str|None}, ...]
        """
        payload = {"items": items}
        try:
            r = self.session.post(
                f"{self.base_url}/api/tts/raw/batch",
                json=payload,
                timeout=120,
            )
            if r.status_code != 200:
                return [{"success": False, "error": f"HTTP {r.status_code}"}]

            data = r.json()
            results = []
            for item in data.get("results", []):
                if item.get("success") and item.get("audio_base64"):
                    audio_bytes = base64.b64decode(item["audio_base64"])
                    results.append({
                        "success": True,
                        "audio_bytes": audio_bytes,
                        "duration": item.get("duration", 0),
                    })
                else:
                    results.append({
                        "success": False,
                        "error": item.get("error", "unknown"),
                    })
            return results
        except Exception as e:
            return [{"success": False, "error": str(e)} for _ in items]


# ========== LESSON GENERATOR ==========

class LessonGenerator:
    """Generates HTML lessons from curriculum data using BearEcho /api/tts/raw."""

    def __init__(self, curriculum, client=None, dry_run=False):
        self.curriculum = curriculum
        self.client = client or BearEchoTTS()
        self.dry_run = dry_run
        self.progress = load_progress()

        template_dir = str(TEMPLATE_PATH.parent)
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=False,
        )

    def get_language_config(self, lang_code):
        for lang in self.curriculum["languages"]:
            if lang["code"] == lang_code:
                return lang
        return None

    def get_lessons_for_lang_level(self, lang_code, level_id):
        lang_curriculum = self.curriculum.get("curriculum", {}).get(lang_code, {})
        level_units = lang_curriculum.get(level_id, [])
        return [u for u in level_units if not u.get("placeholder", False)]

    def generate_lesson(self, lang_code, level_id, unit_data, force=False):
        """
        Generate a single lesson unit:
        1. Generate TTS audio for each dialogue line → save to audio/<lang>/
        2. Generate TTS for each vocabulary word → save to audio/<lang>/
        3. Render HTML from template → save to lessons/<lang>/
        """
        lang_config = self.get_language_config(lang_code)
        if not lang_config:
            print(f"  ⚠ Unknown language: {lang_code}")
            return False

        unit_num = unit_data["unit"]
        unit_id = unit_data["id"]
        title = unit_data["title"]
        key = lesson_key(lang_code, level_id, unit_num)

        # Theme info
        theme_info = {"name": "General", "icon": "📖"}
        for theme in self.curriculum.get("themes", []):
            if theme["id"] == unit_data.get("theme"):
                theme_info = theme
                break

        # Level info
        level_info = {"name": level_id}
        for level in self.curriculum.get("levels", []):
            if level["id"] == level_id:
                level_info = level
                break

        lang_dir = lang_config["base_dir"]
        output_dir = OUTPUT_LESSONS_DIR / lang_dir
        audio_dir = OUTPUT_AUDIO_DIR / lang_dir
        output_file = output_dir / f"unit-{unit_num:02d}-{unit_id}.html"
        audio_prefix = unit_id

        # Skip check
        if is_generated(self.progress, key) and not force and not self.dry_run:
            print(f"  ⏭ Already generated: {output_file.name}")
            return True

        print(f"\n{'='*60}")
        print(f"📖 Generating: {title}")
        print(f"   Language: {lang_config['name']} | Level: {level_info['name']} | Unit: {unit_num}")
        print(f"   Theme: {theme_info['icon']} {theme_info['name']}")
        print(f"{'='*60}")

        dialogue = unit_data.get("dialogue", [])
        vocabulary = unit_data.get("vocabulary", [])
        cultural_notes = unit_data.get("cultural_notes", [])

        voice = lang_config.get("voice")

        # === Generate dialogue audio (as base64 data URIs for self-contained HTML) ===
        processed_dialogue = []
        audio_data_uris = {}  # line index → data:audio/wav;base64,...

        for i, line in enumerate(dialogue, 1):
            source = line["source"]
            target = line.get("target", "")

            processed_dialogue.append({
                "index": i,
                "speaker": line.get("speaker", "A"),
                "source": source,
                "target": target,
                "note": line.get("note", ""),
            })

            if self.dry_run:
                continue

            # Generate TTS → get raw audio bytes → compress to MP3 → embed as data URI
            result = self.client.generate(source, lang=lang_code, voice=voice)
            if result["success"] and result.get("data"):
                mp3_bytes = wav_to_mp3_bytes(result["data"])
                b64 = base64.b64encode(mp3_bytes).decode("ascii")
                audio_data_uris[i] = f"data:audio/mpeg;base64,{b64}"
                print(f"  🔊 Line {i}: {source[:40]}... ✅ (WAV {result['size']} → MP3 {len(mp3_bytes)})")
            else:
                print(f"  ❌ Line {i}: {result.get('error', 'unknown')[:60]}")
            time.sleep(0.2)  # Rate limiting

        # === Generate vocabulary audio (same data URI approach) ===
        processed_vocab = []
        vocab_data_uris = {}

        for i, vocab in enumerate(vocabulary, 1):
            processed_vocab.append({
                "index": i,
                "word": vocab["word"],
                "definition": vocab["definition"],
                "example": vocab.get("example", ""),
            })

            if self.dry_run:
                continue

            result = self.client.generate(vocab["word"], lang=lang_code, voice=voice)
            if result["success"] and result.get("data"):
                mp3_bytes = wav_to_mp3_bytes(result["data"])
                b64 = base64.b64encode(mp3_bytes).decode("ascii")
                vocab_data_uris[i] = f"data:audio/mpeg;base64,{b64}"
                print(f"  🔊 Vocab {i}: {vocab['word']} ✅ (MP3 {len(mp3_bytes)})")
            else:
                print(f"  ❌ Vocab {i}: {result.get('error', 'unknown')[:60]}")
            time.sleep(0.2)

        if self.dry_run:
            print(f"\n  📋 DRY RUN — would generate:")
            print(f"     HTML:  {output_file}")
            print(f"     Audio: {len(dialogue) + len(vocabulary)} TTS calls to BearEcho /api/tts/raw")
            return True

        # === Render HTML ===
        html_content = self._render_html(
            title=title,
            unit_num=unit_num,
            unit_id=unit_id,
            lang_name=lang_config["name"],
            lang_code=lang_code,
            level_name=level_info["name"],
            theme_name=theme_info["name"],
            theme_icon=theme_info["icon"],
            scenario=unit_data.get("scenario", ""),
            dialogue=processed_dialogue,
            vocabulary=processed_vocab,
            cultural_notes=cultural_notes,
            audio_files=audio_data_uris,
            vocab_audio_files=vocab_data_uris,
            generation_date=datetime.now().strftime("%Y-%m-%d"),
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"\n  ✅ Lesson saved: {output_file}")

        mark_generated(self.progress, key)
        return True

    def _render_html(self, **kwargs):
        """Render HTML from template."""
        template = self.jinja_env.get_template(TEMPLATE_PATH.name)
        return template.render(**kwargs)

    def generate_batch(self, lang_code, level_id, units=None, force=False):
        all_units = self.get_lessons_for_lang_level(lang_code, level_id)

        if units:
            unit_nums = [int(u.strip()) for u in units.split(",")]
            all_units = [u for u in all_units if u["unit"] in unit_nums]

        if not all_units:
            print(f"No units found for {lang_code}/{level_id}")
            return

        print(f"\n🚀 Generating {len(all_units)} lesson(s) for {lang_code}/{level_id}")
        print(f"   Dry run: {self.dry_run}")

        if not self.dry_run:
            if not self.client.health_check():
                print("⚠ WARNING: BearEcho API not reachable at", BEARECHO_API)
                print("  Proceeding anyway — audio generation will fail.")

        success = 0
        for unit_data in all_units:
            if self.generate_lesson(lang_code, level_id, unit_data, force=force):
                success += 1

        print(f"\n🎉 Done: {success}/{len(all_units)} lessons generated")


# ========== CLI ==========

def list_lessons(curriculum):
    print("\n📚 Available Lessons in Curriculum")
    print("=" * 70)

    for lang in curriculum["languages"]:
        print(f"\n  🌐 {lang['name']} ({lang['code']})")
        lang_curriculum = curriculum.get("curriculum", {}).get(lang["code"], {})

        for level in curriculum["levels"]:
            units = lang_curriculum.get(level["id"], [])
            active_units = [u for u in units if not u.get("placeholder", False)]
            if active_units:
                print(f"\n    {level['name'].upper()}")
                for u in active_units:
                    key = lesson_key(lang["code"], level["id"], u["unit"])
                    progress = load_progress()
                    status = " ✅" if is_generated(progress, key) else ""
                    print(f"      Unit {u['unit']:02d}: {u['title']}{status}")


def main():
    parser = argparse.ArgumentParser(
        description="SpeakEasy Lesson Generator — Generate HTML lessons with local TTS audio"
    )
    parser.add_argument("--lang", "-l", choices=["en", "yue", "sicuan"],
                        help="Language to generate")
    parser.add_argument("--level", choices=["beginner", "intermediate", "advanced"],
                        help="Level to generate")
    parser.add_argument("--unit", "-u",
                        help="Specific unit number(s), comma-separated")
    parser.add_argument("--dry-run", action="store_true",
                        help="Plan what would be generated without API calls")
    parser.add_argument("--list", action="store_true",
                        help="List all available lessons")
    parser.add_argument("--all", action="store_true",
                        help="Generate all lessons for all languages")
    parser.add_argument("--force", action="store_true",
                        help="Force regeneration of existing lessons")

    args = parser.parse_args()
    curriculum = load_curriculum()

    if args.list:
        list_lessons(curriculum)
        return

    if not args.all and not args.lang:
        parser.error("--lang or --all is required (or use --list to browse)")

    if args.lang and not args.level:
        parser.error("--level is required when --lang is specified")

    generator = LessonGenerator(
        curriculum,
        client=BearEchoTTS(),
        dry_run=args.dry_run,
    )

    if args.all:
        for lang in curriculum["languages"]:
            for level in curriculum["levels"]:
                units = curriculum.get("curriculum", {}).get(lang["code"], {}).get(level["id"], [])
                active = [u for u in units if not u.get("placeholder", False)]
                if active:
                    generator.generate_batch(lang["code"], level["id"], force=args.force)
    else:
        generator.generate_batch(
            args.lang, args.level,
            units=args.unit, force=args.force
        )


if __name__ == "__main__":
    main()
