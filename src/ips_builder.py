# -*- coding: utf-8 -*-
"""
CFA 备考工具 - IPS 构建器模块
作者：CodeBuddy AI Assistant
用途：生成 CFA L3 级别的个人和机构 Investment Policy Statement (IPS) 模板，
      输出 Markdown 到 data/templates/ 目录。
"""

from pathlib import Path
from typing import Optional

from .utils import (
    get_data_dir,
    write_file_text,
    read_file_text,
    today_iso,
)


# 个人 IPS 模板内容
IPS_PERSONAL_TEMPLATE = """# 个人投资政策声明 (Individual IPS)

> 生成日期: {date}
> CFA Level III 备考工具

---

## 1. 客户概况 (Client Profile)

- **姓名**: （填写）
- **年龄**: （填写）
- **职业**: （填写）
- **家庭状况**: （填写）
- **投资经验**: （填写）

---

## 2. 收益要求 (Return Requirement)

| 类别 | 描述 |
|------|------|
| **目标收益** | （填写具体数值或范围） |
| **收益来源** | 资本增值 / 当前收入 / 总回报 |
| **约束条件** | 通货膨胀调整 / 税后收益要求 |

**分析**: （填写详细分析）

---

## 3. 风险承受能力 (Risk Tolerance)

| 因素 | 评估 |
|------|------|
| **客观能力** | 高 / 中 / 低（基于资产规模、收入稳定性等） |
| **主观意愿** | 高 / 中 / 低（基于客户访谈和问卷） |
| **综合结论** | 高于平均 / 平均 / 低于平均 |

**关键考量**:
- （列出影响风险承受能力的关键因素）
- （如投资期限、流动性需求等）

---

## 4. 时间期限 (Time Horizon)

| 阶段 | 时间段 | 特点 |
|------|--------|------|
| **第一阶段** | （如退休前 15 年） | 积累期 |
| **第二阶段** | （如退休后 20 年） | 分配期 |

**多阶段分析**: （填写）

---

## 5. 流动性需求 (Liquidity Requirements)

| 需求类型 | 金额/比例 | 时间 |
|----------|-----------|------|
| **紧急备用金** | | |
| **大额支出** | | |
| **持续现金流需求** | | |

**分析**: （填写）

---

## 6. 法律与监管 (Legal & Regulatory)

| 项目 | 说明 |
|------|------|
| **税务考虑** | 所得税 / 资本利得税 / 遗产税 |
| **法律限制** | （如信托条款、法律实体限制） |
| **监管要求** | （如 SEC 注册要求） |

---

## 7. 独特情况 (Unique Circumstances)

- （如 ESG/社会责任投资偏好）
- （如特定行业股票限制）
- （如家族企业股份处理）
- （其他个性化需求）

---

## 8. 资产配置建议 (Asset Allocation)

| 资产类别 | 目标权重 | 范围 |
|----------|----------|------|
| 权益类 | | |
| 固定收益 | | |
| 另类投资 | | |
| 现金 | | |

**再平衡策略**: （填写）

---

## 9. 业绩基准 (Benchmark)

- **综合基准**: （如 60% S&P 500 + 40% Bloomberg Agg）
- **各资产类别基准**: （列表）

---

## 10. 监控与审查 (Monitoring & Review)

- **审查频率**: 季度 / 半年 / 年度
- **触发条件**: （偏离目标权重 > X% / 客户情况重大变化）
- **报告内容**: （填写）

---

*此模板由 CFA Prep CLI 自动生成*
"""

# 机构 IPS 模板内容
IPS_INSTITUTIONAL_TEMPLATE = """# 机构投资政策声明 (Institutional IPS)

> 生成日期: {date}
> CFA Level III 备考工具

---

## 1. 机构概况 (Institution Profile)

- **机构类型**: 养老基金 / 基金会 / 捐赠基金 / 保险公司 / 银行 / 其他
- **机构名称**: （填写）
- **使命/目的**: （填写）
- **资产规模**: （填写）

---

## 2. 收益要求 (Return Requirement)

| 类别 | 描述 |
|------|------|
| **精算假设收益率** | （如 DB 养老金计划的折现率） |
| **支出率 (Spending Rate)** | （如 捐赠基金 4-5%） |
| **通胀调整** | （是否需保护购买力） |
| **净收益要求** | （扣除费用后的目标） |

**分析**: （填写详细分析）

---

## 3. 风险承受能力 (Risk Tolerance)

| 因素 | 评估 |
|------|------|
| **资金充足率 (Funded Status)** | 超额 / 充足 / 不足 |
| **缴费灵活性** | 高 / 中 / 低 |
| **监管约束** | （如有） |
| **综合风险承受力** | 高于平均 / 平均 / 低于平均 |

**关键考量**:
- （盈余/赤字对风险承受力的影响）
- （缴费人/受益人的风险偏好）

---

## 4. 时间期限 (Time Horizon)

| 因素 | 描述 |
|------|------|
| **负债期限结构** | （如养老金计划的 duration） |
| **永续经营假设** | 是 / 否 |
| **阶段性目标** | （列表） |

---

## 5. 流动性需求 (Liquidity Requirements)

| 需求类型 | 金额/比例 | 时间 |
|----------|-----------|------|
| **养老金支付** | | |
| **运营费用** | | |
| **资本调用 (Capital Calls)** | | |
| **其他承诺** | | |

**分析**: （填写）

---

## 6. 法律与监管 (Legal & Regulatory)

| 项目 | 说明 |
|------|------|
| **ERISA / 相关法规** | （适用法律） |
| **UPMIFA / 审慎投资人规则** | （适用规则） |
| **税务地位** | 免税 / 应税 |
| **报告要求** | （监管报告义务） |

---

## 7. 支出政策 (Spending Policy)

| 参数 | 数值 |
|------|------|
| **支出率** | （如资产市值的 4-5%） |
| **计算方式** | 移动平均 / 滞后市值 / 混合法 |
| **平滑机制** | （如 Yale 公式、3 年平均） |
| **保本条款** | （是否保留本金购买力） |

**分析**: （填写）

---

## 8. 董事会/投资委员会监督 (Board Oversight)

| 职责 | 描述 |
|------|------|
| **IPS 审批** | 董事会 / 投资委员会 |
| **投资经理选择** | 内部 / 外部 / 混合 |
| **业绩审查频率** | 季度 / 年度 |
| **合规监督** | （填写） |

---

## 9. 独特情况 (Unique Circumstances)

- （如社会/环境影响投资要求）
- （如集中持股限制）
- （如捐赠者限制条款）
- （其他个性化需求）

---

## 10. 资产配置建议 (Asset Allocation)

| 资产类别 | 目标权重 | 允许范围 |
|----------|----------|----------|
| 全球权益 | | |
| 固定收益 | | |
| 另类投资 | | |
| 实物资产 | | |
| 现金 | | |

**再平衡策略**: （填写）

---

## 11. 业绩基准 (Benchmark)

- **综合基准**: （如 Policy Portfolio Benchmark）
- **各资产类别基准**: （列表）
- **相对基准评估**: （填写）

---

## 12. 监控与审查 (Monitoring & Review)

- **审查频率**: 年度（至少）
- **触发条件**: 市场剧烈波动 / 法规变化 / 机构目标变化
- **IPS 修订流程**: （填写）

---

*此模板由 CFA Prep CLI 自动生成*
"""


class IPSBuilder:
    """
    IPS 构建器。
    生成 CFA Level III 个人和机构 IPS 模板。
    """

    def __init__(self):
        self.templates_dir = get_data_dir("templates")

    def generate(self, ips_type: str) -> str:
        """
        生成 IPS 模板。

        参数：
            ips_type: "personal" 或 "institutional"（支持简写 personal/inst）

        返回：
            生成的文件路径
        """
        ips_type = ips_type.lower()
        if ips_type in ("personal", "p"):
            template = IPS_PERSONAL_TEMPLATE
            filename = "ips_personal.md"
        elif ips_type in ("institutional", "inst", "i"):
            template = IPS_INSTITUTIONAL_TEMPLATE
            filename = "ips_institutional.md"
        else:
            raise ValueError(f"不支持的 IPS 类型: {ips_type}，请使用 personal 或 institutional")

        content = template.format(date=today_iso())
        filepath = self.templates_dir / filename
        write_file_text(filepath, content)

        return str(filepath)

    def show_template(self, ips_type: str) -> None:
        """在终端显示 IPS 模板内容"""
        ips_type = ips_type.lower()
        if ips_type in ("personal", "p"):
            print(IPS_PERSONAL_TEMPLATE.format(date=today_iso()))
        elif ips_type in ("institutional", "inst", "i"):
            print(IPS_INSTITUTIONAL_TEMPLATE.format(date=today_iso()))
        else:
            print(f"❌ 不支持的 IPS 类型: {ips_type}")
