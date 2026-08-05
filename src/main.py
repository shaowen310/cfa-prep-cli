# -*- coding: utf-8 -*-
"""
CFA 备考工具 - 主入口 (CLI)
作者：CodeBuddy AI Assistant
用途：提供命令行交互界面，统一调度所有子模块功能。
      支持 search / quiz / add-mistake / recap / flashcard / ips / init 命令。
"""

import sys
import os
import argparse
from pathlib import Path

# 将项目根目录加入路径，方便直接运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.knowledge_base import KnowledgeBase
from src.quiz_engine import QuizEngine
from src.mistake_analyzer import MistakeAnalyzer
from src.progress_tracker import ProgressTracker
from src.flashcard_generator import FlashcardGenerator
from src.ips_builder import IPSBuilder
from src.utils import (
    get_project_root,
    get_data_dir,
    get_config_dir,
    load_settings,
    save_settings,
    print_header,
    print_section,
)


def cmd_init(args) -> None:
    """
    初始化项目：创建所有必要的目录和默认配置文件。
    """
    print_header("🚀 CFA Prep CLI - 项目初始化")

    root = get_project_root()

    # 创建目录结构
    dirs = [
        "data/kb",
        "data/mistakes",
        "data/progress",
        "data/flashcards",
        "data/templates",
        "config",
        "tests",
    ]
    for d in dirs:
        p = root / d
        p.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ 创建目录: {d}")

    # 创建默认 settings.json
    settings = {
        "level": "L1",
        "version": "1.0",
        "kb_dir": "data/kb",
        "mistakes_dir": "data/mistakes",
        "progress_dir": "data/progress",
        "flashcards_dir": "data/flashcards",
        "templates_dir": "data/templates",
    }
    save_settings(settings)
    print(f"  ✅ 创建配置: config/settings.json")

    # 创建初始进度文件
    tracker = ProgressTracker()
    tracker.load()
    print(f"  ✅ 创建进度文件: data/progress/progress.md")

    # 生成 IPS 模板
    builder = IPSBuilder()
    builder.generate("personal")
    builder.generate("institutional")
    print(f"  ✅ 生成 IPS 模板: data/templates/")

    print("\n" + "=" * 60)
    print("  🎉 初始化完成！")
    print("=" * 60)
    print("\n📋 下一步:")
    print("  1. 将知识文件（.txt）放入 data/kb/ 目录")
    print("     文件名格式：l1_vol1_p1-60.txt")
    print("     文件内用 ===== PAGE N ===== 标记页码")
    print()
    print("  2. 开始使用:")
    print("     python main.py search \"FCFE\"        # 搜索知识库")
    print("     python main.py quiz --level L1       # 开始刷题")
    print("     python main.py recap                 # 查看进度")
    print()


def cmd_search(args) -> None:
    """
    搜索知识库：在 data/kb/ 下的所有文件中搜索关键词。
    """
    if not args.keyword:
        print("❌ 请提供搜索关键词")
        print("用法: python main.py search <关键词>")
        return

    print_header(f"🔍 搜索: {args.keyword}")

    kb = KnowledgeBase()

    # 显示知识库状态
    stats = kb.get_stats()
    print(f"知识库: {stats['total_files']} 个文件, {stats['total_pages']} 页\n")

    results = kb.search(
        keyword=args.keyword,
        use_regex=args.regex,
        use_fuzzy=not args.no_fuzzy,
        max_results=args.max_results,
    )

    if not results:
        print(f"❌ 未找到与「{args.keyword}」相关的内容。")
        print("💡 提示:")
        print("  - 检查 data/kb/ 目录是否有 .txt 文件")
        print("  - 尝试使用更简短的关键词")
        print("  - 使用 --regex 启用正则搜索")
        print("  - 使用 --no-fuzzy 关闭模糊匹配以提高精确度")
        return

    print(f"找到 {len(results)} 条结果:\n")
    for i, r in enumerate(results, 1):
        print(f"{'─' * 60}")
        print(f"  📄 [{i}] {r['file']} - 第 {r['page']} 页")
        print(f"{'─' * 60}")
        print(f"  {r['snippet']}")
        print()


def cmd_quiz(args) -> None:
    """
    启动刷题模式。
    """
    level = args.level.upper() if args.level else "L1"
    engine = QuizEngine()
    engine.start_quiz(level=level)


def cmd_add_mistake(args) -> None:
    """
    交互式录入错题。
    """
    analyzer = MistakeAnalyzer()
    analyzer.add_mistake_interactive()


def cmd_recap(args) -> None:
    """
    查看和更新学习进度。
    """
    tracker = ProgressTracker()
    analyzer = MistakeAnalyzer()

    if args.update:
        # 交互式更新
        stats = analyzer.get_mistake_stats()
        tracker.interactive_update(mistake_stats=stats)
    else:
        # 仅显示
        print_header("📊 学习进度总览")
        tracker.show()

        print_section("错题统计")
        stats = analyzer.get_mistake_stats()
        print(f"  总错题数: {stats['total']}")
        if stats["total"] > 0:
            print(f"\n  错因分布:")
            for cat, pct in sorted(stats["categories"].items(), key=lambda x: x[1], reverse=True):
                bar = "█" * int(pct / 5)
                print(f"    {cat}: {pct}% {bar}")
            print(f"\n  科目分布:")
            for subj, count in sorted(stats["subjects"].items(), key=lambda x: x[1], reverse=True):
                print(f"    {subj}: {count} 题")

        print(f"\n💡 使用 'python main.py recap --update' 更新进度")


def cmd_flashcard(args) -> None:
    """
    生成闪卡。
    """
    generator = FlashcardGenerator()

    if args.interactive:
        generator.interactive_generate()
    else:
        subject = args.subject or ""
        print_header(f"🃏 生成闪卡{' - ' + subject if subject else ''}")

        md_path = generator.generate_by_subject(subject)
        if md_path:
            print(f"✅ Markdown 闪卡: {md_path}")

        if args.anki:
            csv_path = generator.export_anki_csv(subject)
            if csv_path:
                print(f"✅ Anki CSV: {csv_path}")

        if not md_path:
            print("⚠️ 知识库为空，请先将资料放入 data/kb/ 目录。")


def cmd_ips(args) -> None:
    """
    生成 IPS 模板。
    """
    ips_type = args.type.lower() if args.type else "personal"
    if ips_type not in ("personal", "p", "institutional", "inst", "i"):
        print(f"❌ 不支持的 IPS 类型: {ips_type}")
        print("请使用: personal (个人) 或 institutional/inst (机构)")
        return

    builder = IPSBuilder()

    if args.show:
        builder.show_template(ips_type)
    else:
        filepath = builder.generate(ips_type)
        type_name = "个人" if ips_type in ("personal", "p") else "机构"
        print_header(f"📄 生成 {type_name} IPS 模板")
        print(f"✅ 已生成: {filepath}")
        print(f"\n💡 使用 'python main.py ips {ips_type} --show' 查看模板内容")


def main():
    """主入口函数，解析命令行参数并分发到对应子命令。"""
    parser = argparse.ArgumentParser(
        description="CFA 备考工具 - 知识库检索、刷题、错题分析、进度追踪",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py init                    初始化项目
  python main.py search "FCFE"           搜索知识库
  python main.py search "FCFE" --regex   使用正则搜索
  python main.py quiz --level L1         开始 L1 刷题
  python main.py quiz --level L2         开始 L2 刷题
  python main.py add-mistake             录入错题
  python main.py recap                   查看进度
  python main.py recap --update          更新进度
  python main.py flashcard --subject FRA 生成 FRA 闪卡
  python main.py flashcard --anki        导出 Anki CSV
  python main.py ips personal            生成个人 IPS 模板
  python main.py ips inst                生成机构 IPS 模板
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # init 命令
    p_init = subparsers.add_parser("init", help="初始化项目目录和配置")

    # search 命令
    p_search = subparsers.add_parser("search", help="搜索知识库")
    p_search.add_argument("keyword", nargs="?", help="搜索关键词")
    p_search.add_argument("--regex", action="store_true", help="使用正则表达式搜索")
    p_search.add_argument("--no-fuzzy", action="store_true", help="禁用模糊匹配")
    p_search.add_argument("--max-results", type=int, default=10, help="最大结果数（默认 10）")

    # quiz 命令
    p_quiz = subparsers.add_parser("quiz", help="开始刷题")
    p_quiz.add_argument("--level", choices=["L1", "L2", "L3", "l1", "l2", "l3"],
                        default="L1", help="考试级别（默认 L1）")

    # add-mistake 命令
    p_mistake = subparsers.add_parser("add-mistake", help="录入错题")

    # recap 命令
    p_recap = subparsers.add_parser("recap", help="查看/更新学习进度")
    p_recap.add_argument("--update", action="store_true", help="交互式更新进度")

    # flashcard 命令
    p_flash = subparsers.add_parser("flashcard", help="生成闪卡")
    p_flash.add_argument("--subject", help="科目筛选（如 FRA, Equity）")
    p_flash.add_argument("--anki", action="store_true", help="同时导出 Anki CSV 格式")
    p_flash.add_argument("--interactive", "-i", action="store_true", help="交互式生成")

    # ips 命令
    p_ips = subparsers.add_parser("ips", help="生成 IPS 模板")
    p_ips.add_argument("type", nargs="?", default="personal",
                       help="IPS 类型: personal (个人) 或 inst/institutional (机构)")
    p_ips.add_argument("--show", action="store_true", help="在终端显示模板内容")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 分发命令
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
