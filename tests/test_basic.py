# -*- coding: utf-8 -*-
"""
CFA 备考工具 - 基础测试
作者：CodeBuddy AI Assistant
用途：对核心模块进行基础功能测试，确保各模块可正常初始化和运行。
"""

import sys
import os
from pathlib import Path

# 将项目根目录加入路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.knowledge_base import KnowledgeBase
from src.mistake_analyzer import MistakeAnalyzer
from src.progress_tracker import ProgressTracker
from src.flashcard_generator import FlashcardGenerator
from src.ips_builder import IPSBuilder
from src.quiz_engine import QuizEngine
from src.utils import (
    get_project_root,
    get_data_dir,
    fuzzy_match,
    extract_context,
    today_str,
    load_settings,
    save_settings,
)


def test_project_root():
    """测试项目根目录是否正确"""
    root = get_project_root()
    assert root.exists(), "项目根目录不存在"
    assert (root / "src").exists(), "src 目录不存在"
    print(f"  ✅ 项目根目录: {root}")


def test_data_dirs():
    """测试数据目录创建"""
    dirs = ["kb", "mistakes", "progress", "flashcards", "templates"]
    for d in dirs:
        p = get_data_dir(d)
        assert p.exists(), f"{d} 目录创建失败"
    print(f"  ✅ 所有数据目录正常")


def test_fuzzy_match():
    """测试模糊匹配"""
    assert fuzzy_match("FCFE", "Free Cash Flow to Equity") == True
    assert fuzzy_match("xyz", "Free Cash Flow to Equity") == False
    assert fuzzy_match("fcfe", "FCFE") == True
    print(f"  ✅ 模糊匹配正常")


def test_extract_context():
    """测试上下文提取"""
    text = "The Free Cash Flow to Equity (FCFE) model values a company based on cash available to shareholders."
    snippet = extract_context(text, "FCFE")
    assert "FCFE" in snippet
    print(f"  ✅ 上下文提取正常")


def test_knowledge_base():
    """测试知识库初始化"""
    kb = KnowledgeBase()
    stats = kb.get_stats()
    assert "total_files" in stats
    assert "total_pages" in stats
    print(f"  ✅ 知识库模块正常 (文件数: {stats['total_files']})")


def test_mistake_analyzer():
    """测试错题分析器"""
    analyzer = MistakeAnalyzer()
    stats = analyzer.get_mistake_stats()
    assert "total" in stats
    print(f"  ✅ 错题分析器正常 (错题数: {stats['total']})")


def test_progress_tracker():
    """测试进度追踪器"""
    tracker = ProgressTracker()
    content = tracker.load()
    assert "# CFA 备考进度" in content
    print(f"  ✅ 进度追踪器正常")


def test_ips_builder():
    """测试 IPS 构建器"""
    builder = IPSBuilder()
    # 测试个人 IPS 生成
    path = builder.generate("personal")
    assert Path(path).exists()
    content = open(path, "r", encoding="utf-8").read()
    assert "个人投资政策声明" in content
    print(f"  ✅ IPS 构建器正常 (个人)")

    # 测试机构 IPS 生成
    path = builder.generate("institutional")
    assert Path(path).exists()
    content = open(path, "r", encoding="utf-8").read()
    assert "机构投资政策声明" in content
    print(f"  ✅ IPS 构建器正常 (机构)")


def test_quiz_engine():
    """测试刷题引擎"""
    engine = QuizEngine()
    topics = engine._generate_l1_quiz()
    assert len(topics) <= 10
    print(f"  ✅ 刷题引擎正常 (L1 题目数: {len(topics)})")


def test_flashcard_generator():
    """测试闪卡生成器"""
    generator = FlashcardGenerator()
    # 测试概念提取（用模拟文本）
    sample_text = """
    FCFE（Free Cash Flow to Equity）是指公司可分配给股东的现金流。
    DDM 即股利折现模型，是一种股票估值方法。
    FCFF = EBIT(1-T) + Depreciation - CapEx - ΔWC
    """
    concepts = generator.extract_concepts(sample_text)
    assert len(concepts) > 0
    print(f"  ✅ 闪卡生成器正常 (提取概念数: {len(concepts)})")


def test_settings():
    """测试配置读写"""
    settings = load_settings()
    assert "level" in settings
    assert "version" in settings
    print(f"  ✅ 配置读写正常 (级别: {settings['level']})")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("  🧪 CFA Prep Tool - 基础测试")
    print("=" * 60 + "\n")

    tests = [
        ("项目根目录", test_project_root),
        ("数据目录", test_data_dirs),
        ("模糊匹配", test_fuzzy_match),
        ("上下文提取", test_extract_context),
        ("知识库", test_knowledge_base),
        ("错题分析器", test_mistake_analyzer),
        ("进度追踪器", test_progress_tracker),
        ("IPS 构建器", test_ips_builder),
        ("刷题引擎", test_quiz_engine),
        ("闪卡生成器", test_flashcard_generator),
        ("配置读写", test_settings),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"  测试结果: {passed} 通过 / {failed} 失败 / {len(tests)} 总计")
    print(f"{'=' * 60}\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
