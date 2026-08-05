# CFA Prep CLI

> CFA 备考辅助工具 — 知识库检索 · 智能刷题 · 错题分析 · 进度追踪 · 闪卡生成 · IPS 模板

## 项目简介

CFA Prep CLI 是一个纯 Python 实现的命令行 CFA 备考助手，覆盖 Level I / II / III 的全部备考需求。无需任何第三方依赖，开箱即用。

### 核心功能

| 功能         | 说明                                     |
| ---------- | -------------------------------------- |
| **知识库检索**  | 在教材/Notes 切片中搜索关键词，支持正则和模糊匹配           |
| **智能刷题**   | L1 混合选题 / L2 vignette / L3 情景分析，错题优先出题 |
| **错题分析**   | 自动归类错因（概念不清/计算错误/审题失误），生成复习建议          |
| **进度追踪**   | 维护学习进度文件，追踪已掌握和模糊的知识点                  |
| **闪卡生成**   | 从知识库自动提取 Q&A，支持导出 Anki CSV             |
| **IPS 模板** | L3 个人和机构 IPS 模板，含完整框架                  |

## 快速开始

```bash
# 1. 初始化项目
python main.py init

# 2. 将知识文件放入 data/kb/ 目录
#    文件名格式：l1_vol1_p1-60.txt
#    文件内用 ===== PAGE N ===== 标记页码

# 3. 开始使用
python main.py search "FCFE"
```

## 命令列表

| 命令                        | 说明              | 示例                                        |
| ------------------------- | --------------- | ----------------------------------------- |
| `init`                    | 初始化项目目录和配置      | `python main.py init`                     |
| `search <关键词>`            | 搜索知识库           | `python main.py search "FCFE"`            |
| `search --regex`          | 正则表达式搜索         | `python main.py search "FCF[EF]" --regex` |
| `quiz --level L1`         | L1 刷题（10 题混合）   | `python main.py quiz --level L1`          |
| `quiz --level L2`         | L2 刷题（vignette） | `python main.py quiz --level L2`          |
| `quiz --level L3`         | L3 刷题（IPS 情景）   | `python main.py quiz --level L3`          |
| `add-mistake`             | 交互式录入错题         | `python main.py add-mistake`              |
| `recap`                   | 查看学习进度          | `python main.py recap`                    |
| `recap --update`          | 更新学习进度          | `python main.py recap --update`           |
| `flashcard --subject FRA` | 生成科目闪卡          | `python main.py flashcard --subject FRA`  |
| `flashcard --anki`        | 导出 Anki CSV     | `python main.py flashcard --anki`         |
| `ips personal`            | 生成个人 IPS 模板     | `python main.py ips personal`             |
| `ips inst`                | 生成机构 IPS 模板     | `python main.py ips inst`                 |

## 目录结构

```
cfa-prep-tool/
├── README.md                    # 本文件
├── setup.sh                     # 一键初始化脚本 (Linux/macOS)
├── .gitignore
├── src/
│   ├── main.py                  # CLI 主入口
│   ├── knowledge_base.py        # 知识库管理
│   ├── quiz_engine.py           # 刷题引擎
│   ├── mistake_analyzer.py      # 错题分析器
│   ├── progress_tracker.py      # 进度追踪
│   ├── flashcard_generator.py   # 闪卡生成
│   ├── ips_builder.py           # IPS 模板构建
│   └── utils.py                 # 通用工具函数
├── data/
│   ├── kb/                      # 知识文件 (.txt)
│   ├── mistakes/                # 错题本（自动生成）
│   ├── progress/                # 进度文件（自动生成）
│   ├── flashcards/              # 闪卡（自动生成）
│   └── templates/               # IPS 模板
├── config/
│   └── settings.json            # 配置文件
└── tests/
    └── test_basic.py            # 基础测试
```

## 知识文件格式

放入 `data/kb/` 的 `.txt` 文件需要遵循以下格式：

- **文件名**：`l1_vol1_p1-60.txt`（级别_卷号_页码范围）
- **页码标记**：使用 `===== PAGE N =====` 标记每页开始

示例：

```
===== PAGE 1 =====
这里是第 1 页的内容...

===== PAGE 2 =====
这里是第 2 页的内容...
```

## 运行测试

```bash
python -m tests.test_basic
```

## 技术栈

- **语言**: Python 3.10+
- **依赖**: 零外部依赖，仅使用 Python 标准库
- **编码**: UTF-8
- **兼容性**: Windows / macOS / Linux

# 

---

Built with CodeBuddy · CFA Prep CLI v1.0