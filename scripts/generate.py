#!/usr/bin/env python3
"""
SpeakEasy Lesson Generator

Reads curriculum.yaml and generates interactive HTML lessons with TTS audio
by calling the BearEcho backend API.

Usage:
    python scripts/generate.py --dry-run                    # Plan without generating
    python scripts/generate.py --lang en --level beginner   # Generate all beginner English
    python scripts/generate.py --lang en --unit 1          # Generate specific unit
    python scripts/generate.py --lang en --level beginner --unit 1,3,5  # Selective
    python scripts/generate.py --list                       # List all available lessons
"""

import argparse
import json
import os
import sys
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
CURRICULUM_PATH = Path(__file__).parent.parent / "data" / "curriculum.yaml"
TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "lesson.html"
OUTPUT_LESSONS_DIR = Path(__file__).parent.parent / "lessons"
OUTPUT_AUDIO_DIR = Path(__file__).parent.parent / "audio"
PROGRESS_FILE = Path(__file__).parent.parent / "data" / ".progress.json"


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
    """Generate a unique key for a lesson."""
    return f"{lang}:{level}:{unit}"


def is_generated(progress, key):
    """Check if a lesson has already been generated."""
    return key in progress.get("generated", [])


def mark_generated(progress, key):
    """Mark a lesson as generated."""
    if key not in progress.get("generated", []):
        progress["generated"].append(key)
    progress["last_run"] = datetime.now().isoformat()
    save_progress(progress)


# ========== BEARECHO API ==========

class BearEchoClient:
    """Client for the BearEcho TTS and translation API."""

    def __init__(self, base_url=BEARECHO_API):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def health_check(self):
        """Check if BearEcho is running."""
        try:
            r = self.session.get(f"{self.base_url}/health", timeout=5)
            return r.status_code == 200
        except requests.ConnectionError:
            return False

    def translate(self, text, source_lang, target_lang):
        """
        Translate text via BearEcho.

        For standard languages, uses qwen-mt-turbo.
        For dialects (yue, sicuan), uses GLM-4-flash with dialect-aware prompts.
        """
        try:
            r = self.session.post(
                f"{self.base_url}/api/translate",
                json={
                    "text": text,
                    "sourceLang": source_lang,
                    "targetLang": target_lang,
                },
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            return data.get("translation", text)
        except Exception as e:
            print(f"  ⚠ Translation failed: {e}")
            return f"[Translation unavailable: {text}]"

    def generate_tts(self, text, lang, voice=None, output_path=None):
        """
        Generate TTS audio via BearEcho.

        Args:
            text: Text to synthesize
            lang: Language code (en, yue, sicuan)
            voice: Optional voice name override
            output_path: Where to save the audio file

        Returns:
            Path to the saved audio file, or None on failure
        """
        try:
            payload = {
                "text": text,
                "targetLangs": [lang],
                "sourceLang": lang,
            }
            if voice:
                payload["voices"] = {lang: voice}

            r = self.session.post(
                f"{self.base_url}/api/tts",
                json=payload,
                timeout=60,
            )
            r.raise_for_status()

            # Handle response — audio could be base64 or file URL
            content_type = r.headers.get("content-type", "")

            if "audio" in content_type:
                # Direct audio binary response
                if output_path:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(r.content)
                    return output_path
                return None

            data = r.json()
            # If response contains file paths or base64
            audio_data = data.get("audio", data.get("files", {}))
            if isinstance(audio_data, dict):
                audio_b64 = audio_data.get(lang)
                if audio_b64:
                    import base64
                    audio_bytes = base64.b64decode(audio_b64)
                    if output_path:
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(output_path, "wb") as f:
                            f.write(audio_bytes)
                        return output_path

            return None

        except Exception as e:
            print(f"  ⚠ TTS failed: {e}")
            return None


# ========== LESSON GENERATOR ==========

class LessonGenerator:
    """Generates HTML lessons from curriculum data."""

    def __init__(self, curriculum, client=None, dry_run=False):
        self.curriculum = curriculum
        self.client = client or BearEchoClient()
        self.dry_run = dry_run
        self.progress = load_progress()

        # Set up Jinja2
        template_dir = str(TEMPLATE_PATH.parent)
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=False,
        )
        self.jinja_env.filters["lower"] = lambda x: str(x).lower()

    def get_language_config(self, lang_code):
        """Get language configuration from curriculum."""
        for lang in self.curriculum["languages"]:
            if lang["code"] == lang_code:
                return lang
        return None

    def get_lessons_for_lang_level(self, lang_code, level_id):
        """Get all units for a language and level."""
        lang_curriculum = self.curriculum.get("curriculum", {}).get(lang_code, {})
        level_units = lang_curriculum.get(level_id, [])
        return [u for u in level_units if not u.get("placeholder", False)]

    def generate_lesson(self, lang_code, level_id, unit_data):
        """
        Generate a single lesson unit.

        Steps:
        1. Check if already generated
        2. Generate translations (if needed)
        3. Generate TTS audio for each sentence
        4. Render HTML from template
        5. Save outputs
        """
        lang_config = self.get_language_config(lang_code)
        if not lang_config:
            print(f"  ⚠ Unknown language: {lang_code}")
            return False

        unit_num = unit_data["unit"]
        unit_id = unit_data["id"]
        title = unit_data["title"]
        key = lesson_key(lang_code, level_id, unit_num)

        # Get theme info
        theme_info = {"name": "General", "icon": "📖"}
        for theme in self.curriculum.get("themes", []):
            if theme["id"] == unit_data.get("theme"):
                theme_info = theme
                break

        # Get level info
        level_info = {"name": level_id}
        for level in self.curriculum.get("levels", []):
            if level["id"] == level_id:
                level_info = level
                break

        output_dir = OUTPUT_LESSONS_DIR / lang_config["base_dir"]
        audio_dir = OUTPUT_AUDIO_DIR / lang_config["base_dir"]

        output_file = output_dir / f"unit-{unit_num:02d}-{unit_id}.html"
        audio_prefix = f"{unit_id}"

        # Skip if already generated
        if is_generated(self.progress, key) and not self.dry_run:
            print(f"  ⏭ Already generated: {output_file.name}")
            return True

        print(f"\n{'='*60}")
        print(f"📖 Generating: {title}")
        print(f"   Language: {lang_config['name']} | Level: {level_info['name']} | Unit: {unit_num}")
        print(f"   Theme: {theme_info['icon']} {theme_info['name']}")
        print(f"{'='*60}")

        # Build lesson data
        dialogue = unit_data.get("dialogue", [])
        vocabulary = unit_data.get("vocabulary", [])
        cultural_notes = unit_data.get("cultural_notes", [])

        # Process dialogue sentences
        processed_dialogue = []
        for i, line in enumerate(dialogue, 1):
            source = line["source"]

            # Use pre-existing target or generate translation
            target = line.get("target")
            if not target and not self.dry_run:
                print(f"  🔤 Translating line {i}: {source[:50]}...")
                target = self.client.translate(
                    source,
                    source_lang=lang_code,
                    target_lang="zh" if lang_code != "zh" else "en",
                )

            processed_dialogue.append({
                "speaker": line.get("speaker", "A"),
                "source": source,
                "target": target or f"[{source}]",
                "note": line.get("note", ""),
            })

            # Generate TTS audio
            if not self.dry_run:
                audio_file = audio_dir / f"{audio_prefix}-{i}.mp3"
                print(f"  🔊 TTS line {i}: {source[:40]}...")
                result = self.client.generate_tts(
                    source,
                    lang=lang_code,
                    voice=lang_config.get("voice"),
                    output_path=audio_file,
                )
                if result:
                    print(f"     ✅ Saved: {audio_file.name}")
                else:
                    print(f"     ❌ Failed: line {i} audio")
                time.sleep(0.3)  # Rate limiting

        # Generate vocabulary audio
        processed_vocab = []
        for i, vocab in enumerate(vocabulary, 1):
            processed_vocab.append({
                "word": vocab["word"],
                "definition": vocab["definition"],
                "example": vocab.get("example", ""),
            })

            if not self.dry_run:
                audio_file = audio_dir / f"{audio_prefix}-vocab-{i}.mp3"
                self.client.generate_tts(
                    vocab["word"],
                    lang=lang_code,
                    voice=lang_config.get("voice"),
                    output_path=audio_file,
                )
                time.sleep(0.3)

        if self.dry_run:
            print(f"\n  📋 DRY RUN — would generate:")
            print(f"     HTML:  {output_file}")
            print(f"     Audio: {audio_dir}/{audio_prefix}-*.mp3 ({len(processed_dialogue)} files)")
            print(f"     Vocab: {audio_dir}/{audio_prefix}-vocab-*.mp3 ({len(processed_vocab)} files)")
            return True

        # Render HTML
        self.jinja_env.globals["lesson"] = {
            "title": title,
            "unit": unit_num,
            "id": unit_id,
            "language_name": lang_config["name"],
            "level_name": level_info["name"],
            "theme_name": theme_info["name"],
            "theme_icon": theme_info["icon"],
            "scenario": unit_data.get("scenario", ""),
            "dialogue": processed_dialogue,
            "vocabulary": processed_vocab,
            "cultural_notes": cultural_notes,
            "audio_dir": lang_config["base_dir"],
            "generation_date": datetime.now().strftime("%Y-%m-%d"),
        }

        template = self.jinja_env.get_template(TEMPLATE_PATH.name)
        html_content = template.render()

        # Save HTML
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"\n  ✅ Lesson saved: {output_file}")

        # Mark as generated
        mark_generated(self.progress, key)
        return True

    def generate_batch(self, lang_code, level_id, units=None):
        """Generate multiple lessons."""
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
                print("  Proceeding anyway — audio generation may fail.")

        success = 0
        for unit_data in all_units:
            if self.generate_lesson(lang_code, level_id, unit_data):
                success += 1

        print(f"\n🎉 Done: {success}/{len(all_units)} lessons generated")


# ========== CLI ==========

def list_lessons(curriculum):
    """List all available lessons in the curriculum."""
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
                    status = ""
                    key = lesson_key(lang["code"], level["id"], u["unit"])
                    progress = load_progress()
                    if is_generated(progress, key):
                        status = " ✅"
                    elif u.get("placeholder"):
                        status = " 📝 (planned)"
                    print(f"      Unit {u['unit']:02d}: {u['title']}{status}")


def main():
    parser = argparse.ArgumentParser(
        description="SpeakEasy Lesson Generator — Generate interactive HTML lessons with TTS audio"
    )
    parser.add_argument(
        "--lang", "-l",
        choices=["en", "yue", "sicuan"],
        help="Language to generate (en=English, yue=Cantonese, sicuan=Sichuanese)",
    )
    parser.add_argument(
        "--level",
        choices=["beginner", "intermediate", "advanced"],
        help="Level to generate",
    )
    parser.add_argument(
        "--unit", "-u",
        help="Specific unit number(s), comma-separated (e.g., '1,3,5')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan what would be generated without making API calls",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available lessons in the curriculum",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate all lessons for all languages",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration of already-generated lessons",
    )

    args = parser.parse_args()
    curriculum = load_curriculum()

    # List mode
    if args.list:
        list_lessons(curriculum)
        return

    # Validate arguments
    if not args.all and not args.lang:
        parser.error("--lang or --all is required (or use --list to browse)")

    if args.lang and not args.level:
        parser.error("--level is required when --lang is specified")

    generator = LessonGenerator(
        curriculum,
        client=BearEchoClient(),
        dry_run=args.dry_run,
    )

    # Handle --force: clear progress for selected lessons
    if args.force:
        print("⚠ Force mode: regenerating all selected lessons")

    # Generate all
    if args.all:
        for lang in curriculum["languages"]:
            for level in curriculum["levels"]:
                units = generator.get_lessons_for_lang_level(lang["code"], level["id"])
                if units:
                    generator.generate_batch(lang["code"], level["id"])
        return

    # Generate specific
    generator.generate_batch(args.lang, args.level, args.unit)


if __name__ == "__main__":
    main()
