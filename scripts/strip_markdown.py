#!/usr/bin/env python3
"""
strip_markdown.py — strip markdown formatting for prose analysis.
Reads from file or stdin. Writes plain text to stdout.
"""

import re
import sys


def strip_markdown(text: str) -> str:
    """Strip markdown formatting, leaving plain prose."""
    # Remove image links
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # Remove links, keep text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove headings
    text = re.sub(r'^#{1,6}\s+.+$', lambda m: m.group().split('#')[-1].strip(), text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    # Remove code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    # Remove inline code
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Remove horizontal rules
    text = re.sub(r'^-{3,}$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\*{3,}$', '', text, flags=re.MULTILINE)
    # Remove HTML-like comments
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    return text


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()
    print(strip_markdown(text))


if __name__ == "__main__":
    main()
