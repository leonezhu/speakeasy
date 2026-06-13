# Contributing to SpeakEasy

Thanks for your interest in contributing! This guide covers the basics.

## Ways to Contribute

### Curriculum Content
The most impactful contribution: write new lesson dialogues, vocabulary, and cultural notes.
1. Edit `data/curriculum.yaml`
2. Follow the existing unit format
3. Ensure dialogues are natural and conversational
4. Add cultural context notes

### New Languages/Dialects
Want to add a new language? You need:
1. A TTS engine (add to BearEcho backend)
2. A translation engine (or use LLM-based translation)
3. Add language config to `curriculum.yaml`
4. Write beginner curriculum units

### Bug Fixes & Features
1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Test with `python scripts/generate.py --dry-run`
5. Submit a pull request

## Curriculum Writing Guidelines

- **Be conversational**: Write how people actually speak, not how textbooks teach
- **Be specific**: "Order at a cha chaan teng" > "Order food at a restaurant"
- **Be progressive**: Each level builds on the previous one
- **Be cultural**: Include notes that explain *why*, not just *what*
- **Be concise**: 8-12 dialogue lines per unit, 5-8 vocabulary items
- **Be authentic**: Use native slang, idioms, and expressions

## Code of Conduct

- Be respectful and inclusive
- Assume good intent
- Focus on the work, not the person
- Welcome newcomers
