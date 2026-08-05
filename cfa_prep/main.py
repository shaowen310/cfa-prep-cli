# -*- coding: utf-8 -*-
"""
CFA Prep CLI - Main entry point (CLI)
Author: CodeBuddy AI Assistant
Purpose: Provide a command-line interface that orchestrates all submodule functionality.
         Supports the search / quiz / add-mistake / recap / flashcard / ips / init commands.
"""

import os
import argparse

from .knowledge_base import KnowledgeBase
from .quiz_engine import QuizEngine
from .mistake_analyzer import MistakeAnalyzer
from .progress_tracker import ProgressTracker
from .flashcard_generator import FlashcardGenerator
from .ips_builder import IPSBuilder
from .utils import (
    get_data_root,
    get_data_dir,
    save_settings,
    print_header,
    print_section,
    today_iso,
)


def cmd_init(args) -> None:
    """
    Initialize the project: create all necessary directories and default config files
    under the resolved data root (~/.cfa-prep by default, or CFA_PREP_HOME / --home).
    """
    print_header("🚀 CFA Prep CLI - Project Initialization")

    root = get_data_root()
    print(f"  📁 Data root: {root}")

    # Create the directory structure under the data root
    dirs = [
        "kb",
        "mistakes",
        "progress",
        "flashcards",
        "templates",
        "config",
    ]
    for d in dirs:
        p = get_data_dir(d)
        p.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ Created directory: {d}")

    # Create the default settings.json (remember the data_root so future runs resolve the same folder)
    settings = {
        "level": "L1",
        "version": "1.0",
        "data_root": str(root),
        "kb_dir": "kb",
        "mistakes_dir": "mistakes",
        "progress_dir": "progress",
        "flashcards_dir": "flashcards",
        "templates_dir": "templates",
    }
    save_settings(settings)
    print(f"  ✅ Created config: config/settings.json")

    # Create the initial progress file
    tracker = ProgressTracker()
    _ = tracker.load()
    print(f"  ✅ Created progress file: progress/progress.md")

    # Generate IPS templates
    builder = IPSBuilder()
    today = today_iso()
    _ = builder.generate("personal", today)
    _ = builder.generate("institutional", today)
    print(f"  ✅ Generated IPS templates: templates/")

    print("\n" + "=" * 60)
    print("  🎉 Initialization complete!")
    print("=" * 60)
    print("\n📋 Next steps:")
    print("  1. Place knowledge files (.txt) into the kb/ directory under the data root")
    print("     File name format: l1_vol1_p1-60.txt")
    print("     Mark pages inside files with ===== PAGE N =====")
    print()
    print("  2. Start using:")
    print("     cfa-prep search \"FCFE\"        # Search the knowledge base")
    print("     cfa-prep quiz --level L1       # Start quizzing")
    print("     cfa-prep recap                 # View progress")
    print()


def cmd_search(args) -> None:
    """
    Search the knowledge base: search for keywords across all files under data/kb/.
    """
    if not args.keyword:
        print("❌ Please provide a search keyword")
        print("Usage: python main.py search <keyword>")
        return

    print_header(f"🔍 Search: {args.keyword}")

    kb = KnowledgeBase()

    # Show the knowledge base status
    stats = kb.get_stats()
    print(f"Knowledge base: {stats['total_files']} files, {stats['total_pages']} pages\n")

    results = kb.search(
        keyword=args.keyword,
        use_regex=args.regex,
        use_fuzzy=not args.no_fuzzy,
        max_results=args.max_results,
    )

    if not results:
        print(f"❌ No content matching「{args.keyword}」was found.")
        print("💡 Tips:")
        print("  - Check whether the data/kb/ directory contains .txt files")
        print("  - Try a shorter keyword")
        print("  - Use --regex to enable regex search")
        print("  - Use --no-fuzzy to disable fuzzy matching for higher precision")
        return

    print(f"Found {len(results)} result(s):\n")
    for i, r in enumerate(results, 1):
        print(f"{'─' * 60}")
        print(f"  📄 [{i}] {r['file']} - page {r['page']}")
        print(f"{'─' * 60}")
        print(f"  {r['snippet']}")
        print()


def cmd_quiz(args) -> None:
    """
    Start the quiz mode.
    """
    level = args.level.upper() if args.level else "L1"
    engine = QuizEngine()
    engine.start_quiz(level=level)


def cmd_add_mistake(_args) -> None:
    """
    Interactively log a mistake.
    """
    analyzer = MistakeAnalyzer()
    analyzer.add_mistake_interactive()


def cmd_recap(args) -> None:
    """
    View and update study progress.
    """
    tracker = ProgressTracker()
    analyzer = MistakeAnalyzer()

    if args.update:
        # Interactive update
        stats = analyzer.get_mistake_stats()
        tracker.interactive_update(mistake_stats=stats)
    else:
        # Display only
        print_header("📊 Study Progress Overview")
        tracker.show()

        print_section("Mistake Statistics")
        stats = analyzer.get_mistake_stats()
        total_value = stats.get("total")
        total = total_value if isinstance(total_value, int) else 0
        print(f"  Total mistakes: {total}")
        if total > 0:
            print(f"\n  Category distribution:")
            categories_value = stats.get("categories")
            categories: dict[str, float] = {
                str(k): float(v)
                for k, v in (categories_value.items() if isinstance(categories_value, dict) else {}.items())
            }
            for cat, pct in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                bar = "█" * int(pct / 5)
                print(f"    {cat}: {pct}% {bar}")
            print(f"\n  Subject distribution:")
            subjects_value = stats.get("subjects")
            subjects: dict[str, int] = {
                str(k): int(v)
                for k, v in (subjects_value.items() if isinstance(subjects_value, dict) else {}.items())
            }
            for subj, count in sorted(subjects.items(), key=lambda x: x[1], reverse=True):
                print(f"    {subj}: {count} questions")

        print(f"\n💡 Use 'python main.py recap --update' to update progress")


def cmd_flashcard(args) -> None:
    """
    Generate flashcards.
    """
    generator = FlashcardGenerator()

    if args.interactive:
        generator.interactive_generate()
    else:
        subject = args.subject or ""
        print_header(f"🃏 Generate Flashcards{' - ' + subject if subject else ''}")

        md_path = generator.generate_by_subject(subject)
        if md_path:
            print(f"✅ Markdown flashcards: {md_path}")

        if args.anki:
            csv_path = generator.export_anki_csv(subject)
            if csv_path:
                print(f"✅ Anki CSV: {csv_path}")

        if not md_path:
            print("⚠️ Knowledge base is empty. Please place your materials into the data/kb/ directory first.")


def cmd_ips(args) -> None:
    """
    Generate IPS templates.
    """
    ips_type = args.type.lower() if args.type else "personal"
    if ips_type not in ("personal", "p", "institutional", "inst", "i"):
        print(f"❌ Unsupported IPS type: {ips_type}")
        print("Please use: personal or institutional/inst")
        return

    builder = IPSBuilder()
    today = today_iso()

    if args.show:
        builder.show_template(ips_type, today)
    else:
        filepath = builder.generate(ips_type, today)
        type_name = "Personal" if ips_type in ("personal", "p") else "Institutional"
        print_header(f"📄 Generate {type_name} IPS Template")
        print(f"✅ Generated: {filepath}")
        print(f"\n💡 Use 'python main.py ips {ips_type} --show' to view the template content")


def main():
    """Main entry function, parses command-line arguments and dispatches to the corresponding subcommand."""
    parser = argparse.ArgumentParser(
        description="CFA Prep CLI - knowledge base search, quizzing, mistake analysis, progress tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cfa-prep init                          Initialize the project
  cfa-prep search "FCFE"                 Search the knowledge base
  cfa-prep search "FCFE" --regex         Use regex search
  cfa-prep quiz --level L1               Start L1 quizzing
  cfa-prep quiz --level L2               Start L2 quizzing
  cfa-prep add-mistake                   Log a mistake
  cfa-prep recap                         View progress
  cfa-prep recap --update                Update progress
  cfa-prep flashcard --subject FRA       Generate FRA flashcards
  cfa-prep flashcard --anki              Export Anki CSV
  cfa-prep ips personal                  Generate a personal IPS template
  cfa-prep ips inst                      Generate an institutional IPS template

Data root (default ~/.cfa-prep) can be set via:
  --home /path/to/data, or the CFA_PREP_HOME environment variable.
        """,
    )
    _ = parser.add_argument("--home", metavar="PATH", help="override the data root directory (also honored via CFA_PREP_HOME env var)")

    subparsers = parser.add_subparsers(dest="command", help="available commands")

    # init command
    _ = subparsers.add_parser("init", help="Initialize the data root directories and config")

    # add-mistake command
    _ = subparsers.add_parser("add-mistake", help="Interactively log a mistake")

    # search command
    p_search = subparsers.add_parser("search", help="Search the knowledge base")
    _ = p_search.add_argument("keyword", nargs="?", help="search keyword")
    _ = p_search.add_argument("--regex", action="store_true", help="search using regular expressions")
    _ = p_search.add_argument("--no-fuzzy", action="store_true", help="disable fuzzy matching")
    _ = p_search.add_argument("--max-results", type=int, default=10, help="maximum number of results (default 10)")

    # quiz command
    p_quiz = subparsers.add_parser("quiz", help="Start quizzing")
    _ = p_quiz.add_argument("--level", choices=["L1", "L2", "L3", "l1", "l2", "l3"],
                        default="L1", help="exam level (default L1)")

    # recap command
    p_recap = subparsers.add_parser("recap", help="View/update study progress")
    _ = p_recap.add_argument("--update", action="store_true", help="interactively update progress")

    # flashcard command
    p_flash = subparsers.add_parser("flashcard", help="Generate flashcards")
    _ = p_flash.add_argument("--subject", help="subject filter (e.g., FRA, Equity)")
    _ = p_flash.add_argument("--anki", action="store_true", help="also export in Anki CSV format")
    _ = p_flash.add_argument("--interactive", "-i", action="store_true", help="interactive generation")

    # ips command
    p_ips = subparsers.add_parser("ips", help="Generate IPS templates")
    _ = p_ips.add_argument("type", nargs="?", default="personal",
                       help="IPS type: personal or inst/institutional")
    _ = p_ips.add_argument("--show", action="store_true", help="display the template content in the terminal")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Apply --home override before dispatching so all modules resolve the data root consistently
    if getattr(args, "home", None):
        os.environ["CFA_PREP_HOME"] = args.home

    # Dispatch commands
    commands = {
        "init": cmd_init,
        "search": cmd_search,
        "quiz": cmd_quiz,
        "add-mistake": cmd_add_mistake,
        "recap": cmd_recap,
        "flashcard": cmd_flashcard,
        "ips": cmd_ips,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
