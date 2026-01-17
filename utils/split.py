"""
Markdown splitter utility for splitting a file into chapters.

Splits a single markdown file into multiple files based on heading patterns.
Each output file gets YAML frontmatter with section metadata.

Usage:
    uv run lib/split.py input.md [--out DIR] [--pattern PATTERN] [--fm key:value ...]

Examples:
    # Split on ## headings (default)
    uv run lib/split.py book.md

    # Split on ### headings with custom output directory
    uv run lib/split.py book.md --pattern "###" --out ./chapters/

    # Add custom frontmatter fields to all chapters
    uv run lib/split.py book.md --fm title:"My Book" --fm author:"Jane Doe" --fm url:"https://example.com"

Output:
    Creates numbered markdown files (01_chapter_name.md, 02_chapter_name.md, etc.)
    with frontmatter containing section_number, section_title, and any custom fields.
"""

import argparse
import re
import shutil
import sys
from pathlib import Path


def generate_frontmatter(fields: dict) -> str:
    """
    Generate YAML frontmatter from a dictionary of fields.

    Args:
        fields: Dictionary of field names to values

    Returns:
        Frontmatter string including --- delimiters
    """
    if not fields:
        return ""

    lines = ["---"]
    for key, value in fields.items():
        # Quote strings that contain special characters
        if isinstance(value, str) and any(c in value for c in ":#{}[]&*!|>'\"%@`"):
            value = f'"{value}"'
        lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")  # Empty line after frontmatter

    return "\n".join(lines)


def parse_fm_field(field_str: str) -> tuple[str, str]:
    """
    Parse a frontmatter field argument like 'title:"Some Title"' or 'author:Name'.

    Args:
        field_str: String in format 'key:value' or 'key:"quoted value"'

    Returns:
        Tuple of (key, value)

    Raises:
        ValueError: If the format is invalid
    """
    # Match key:value or key:"quoted value"
    match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*):(.+)$', field_str)
    if not match:
        raise ValueError(f"Invalid frontmatter field format: {field_str}")

    key = match.group(1)
    value = match.group(2).strip()

    # Remove surrounding quotes if present
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]

    return key, value


def make_folder_safe_name(name: str) -> str:
    """
    Convert a string to a folder-safe name.

    Args:
        name: The string to convert

    Returns:
        A lowercase string with spaces/special chars replaced by underscores
    """
    # Remove file extension if present
    name = Path(name).stem
    # Convert to lowercase and replace non-alphanumeric chars with underscores
    safe_name = re.sub(r"[^a-z0-9]+", "_", name.lower())
    # Remove leading/trailing underscores
    safe_name = safe_name.strip("_")
    return safe_name or "output"


def make_chapter_filename(title: str, index: int) -> str:
    """
    Create a filename from a chapter title.

    Args:
        title: The chapter heading text
        index: The chapter index (for ordering)

    Returns:
        A numbered, folder-safe filename with .md extension
    """
    # Clean the title for use as filename
    safe_title = re.sub(r"[^a-z0-9]+", "_", title.lower())
    safe_title = safe_title.strip("_")
    if not safe_title:
        safe_title = "chapter"
    return f"{index:02d}_{safe_title}.md"


def split_markdown(
    content: str,
    heading_pattern: str = "##",
) -> list[tuple[str, str]]:
    """
    Split markdown content into chapters based on heading pattern.

    Args:
        content: The markdown content to split
        heading_pattern: The heading marker to split on (default: "##")

    Returns:
        List of tuples: (chapter_title, chapter_content)
    """
    # Build regex pattern to match headings at start of line
    # Escape the pattern in case it contains special regex chars
    escaped_pattern = re.escape(heading_pattern)
    # Match heading pattern followed by space and capture the title
    pattern = rf"^({escaped_pattern})\s+(.+?)$"

    chapters = []
    current_title = None
    current_content = []
    preamble_content = []

    lines = content.split("\n")

    for line in lines:
        match = re.match(pattern, line)
        if match:
            # Found a chapter heading
            if current_title is not None:
                # Save previous chapter
                chapters.append((current_title, "\n".join(current_content).strip()))
            elif current_content:
                # Content before first heading goes to preamble
                preamble_content = current_content

            current_title = match.group(2).strip()
            current_content = [line]  # Include the heading in content
        else:
            current_content.append(line)

    # Don't forget the last chapter
    if current_title is not None:
        chapters.append((current_title, "\n".join(current_content).strip()))
    elif current_content:
        # File has no headings matching the pattern
        preamble_content = current_content

    # If there's preamble content and we have chapters, prepend it to first chapter
    # If no chapters, create one from preamble
    if preamble_content:
        preamble_text = "\n".join(preamble_content).strip()
        if chapters and preamble_text:
            # Prepend preamble to first chapter
            title, content = chapters[0]
            chapters[0] = (title, preamble_text + "\n\n" + content)
        elif preamble_text:
            # No chapters found, entire file is one "chapter"
            chapters.append(("preamble", preamble_text))

    return chapters


def split_file(
    input_path: str | Path,
    output_dir: str | Path | None = None,
    heading_pattern: str = "##",
    frontmatter_fields: dict | None = None,
) -> dict:
    """
    Split a markdown file into separate chapter files.

    Args:
        input_path: Path to the input markdown file
        output_dir: Output directory (default: ./data/{folder_safe_name}/)
        heading_pattern: The heading marker to split on (default: "##")
        frontmatter_fields: Additional frontmatter fields to add to each chapter

    Returns:
        Dictionary with split statistics
    """
    frontmatter_fields = frontmatter_fields or {}
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if not input_path.suffix.lower() == ".md":
        print(f"Warning: Input file does not have .md extension: {input_path}")

    # Determine output directory
    if output_dir is None:
        folder_name = make_folder_safe_name(input_path.name)
        output_dir = Path("./data") / folder_name
    else:
        output_dir = Path(output_dir)

    # Read input file
    content = input_path.read_text(encoding="utf-8")

    # Split into chapters
    chapters = split_markdown(content, heading_pattern)

    if not chapters:
        print(f"No chapters found in {input_path}")
        return {"chapters_created": 0, "output_dir": str(output_dir)}

    # Remove output directory if it exists, then create fresh
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Splitting {input_path.name} into {len(chapters)} chapter(s)")
    print(f"Output directory: {output_dir}")
    print(f"Heading pattern: {heading_pattern}")
    print()

    # Write chapter files
    for i, (title, content) in enumerate(chapters, start=1):
        filename = make_chapter_filename(title, i)
        output_path = output_dir / filename

        # Build frontmatter for this chapter
        chapter_frontmatter = {
            "section_number": i,
            "section_title": title,
            **frontmatter_fields,
        }
        frontmatter_str = generate_frontmatter(chapter_frontmatter)

        # Combine frontmatter with content
        full_content = frontmatter_str + content

        output_path.write_text(full_content, encoding="utf-8")
        print(f"  Created: {filename} ({len(full_content)} chars)")

    print(f"\nSplit complete! Created {len(chapters)} file(s)")

    return {
        "chapters_created": len(chapters),
        "output_dir": str(output_dir),
        "files": [make_chapter_filename(title, i) for i, (title, _) in enumerate(chapters, start=1)],
    }


def main():
    """CLI entry point for markdown splitting."""
    parser = argparse.ArgumentParser(
        description="Split a markdown file into separate chapter files"
    )
    parser.add_argument(
        "input",
        help="Path to the input markdown file",
    )
    parser.add_argument(
        "--out",
        dest="output_dir",
        default=None,
        help="Output directory (default: ./data/{folder_safe_name}/)",
    )
    parser.add_argument(
        "--pattern",
        default="##",
        help="Heading pattern to split on (default: ##)",
    )
    parser.add_argument(
        "--fm",
        action="append",
        dest="fm_fields",
        metavar='key:"value"',
        help='Add frontmatter field (e.g., --fm title:"My Book" --fm author:"Jane Doe")',
    )

    args = parser.parse_args()

    # Parse frontmatter fields
    frontmatter_fields = {}
    if args.fm_fields:
        for field in args.fm_fields:
            try:
                key, value = parse_fm_field(field)
                frontmatter_fields[key] = value
            except ValueError as e:
                print(f"Error: {e}")
                sys.exit(1)

    try:
        split_file(
            args.input,
            output_dir=args.output_dir,
            heading_pattern=args.pattern,
            frontmatter_fields=frontmatter_fields,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
