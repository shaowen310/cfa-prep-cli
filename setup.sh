#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# CFA Prep CLI - 一键初始化脚本
# 作者：CodeBuddy AI Assistant
# 用途：创建所有必要目录、生成默认配置文件、打印使用指引。
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "============================================================"
echo "  🚀 CFA Prep CLI - 一键初始化"
echo "============================================================"
echo ""

# 1. 创建目录结构
echo "📁 创建目录结构..."
mkdir -p data/kb
mkdir -p data/mistakes
mkdir -p data/progress
mkdir -p data/flashcards
mkdir -p data/templates
mkdir -p config
mkdir -p tests
echo "  ✅ 目录创建完成"

# 2. 生成默认配置文件
echo ""
echo "⚙️  生成默认配置..."
cat > config/settings.json << 'JSONEOF'
{
  "level": "L1",
  "version": "1.0",
  "kb_dir": "data/kb",
  "mistakes_dir": "data/mistakes",
  "progress_dir": "data/progress",
  "flashcards_dir": "data/flashcards",
  "templates_dir": "data/templates"
}
JSONEOF
echo "  ✅ config/settings.json"

# 3. 生成初始进度文件
echo ""
echo "📊 生成进度文件..."
cat > data/progress/progress.md << 'MDEOF'
# CFA 备考进度

> 进度总览（更新于 $(date +%Y-%m-%d)）

## 已掌握

（暂无记录）

## 仍模糊

（暂无记录）

## 错因分布

（暂无数据）

## 明日唯一任务

（暂无计划）
MDEOF
echo "  ✅ data/progress/progress.md"

# 4. 生成 IPS 模板
echo ""
echo "📄 生成 IPS 模板..."
echo "  ✅ data/templates/ (使用 python main.py ips 命令生成)"

# 5. 检查 Python 环境
echo ""
echo "🐍 检查 Python 环境..."
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "  ⚠️  未找到 Python，请安装 Python 3.10+"
    PYTHON=""
fi

if [ -n "$PYTHON" ]; then
    PY_VERSION=$($PYTHON --version 2>&1)
    echo "  ✅ $PY_VERSION"

    # 初始化项目（运行 Python 初始化）
    echo ""
    echo "🔧 运行 Python 初始化..."
    $PYTHON -m src.main init 2>/dev/null || $PYTHON src/main.py init 2>/dev/null || echo "  ⚠️  请手动运行: python main.py init"
fi

# 6. 打印完成信息
echo ""
echo "============================================================"
echo "  🎉 初始化完成！"
echo "============================================================"
echo ""
echo "📋 下一步:"
echo "  1. 将知识文件（.txt）放入 data/kb/ 目录"
echo "     文件名格式：l1_vol1_p1-60.txt"
echo "     文件内用 ===== PAGE N ===== 标记页码"
echo ""
echo "  2. 开始使用:"
echo "     python main.py search \"FCFE\"        # 搜索知识库"
echo "     python main.py quiz --level L1       # 开始刷题"
echo "     python main.py recap                 # 查看进度"
echo "     python main.py flashcard --subject FRA  # 生成闪卡"
echo "     python main.py ips personal          # 生成 IPS 模板"
echo ""
echo "  📖 更多信息请查看 README.md"
echo ""
