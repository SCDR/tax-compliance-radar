"""生成用于演示 / 联调的示例合同 PDF。

用法：
    uv run python scripts/gen_sample_contract.py [--out PATH]

按真实跨境电商综合服务合同的排版重构：
- 封面（合同编号、双方主体、签署地、签署日期、有效期）
- 鉴于 / 序言
- 目录
- 第一条 … 第十八条：定义、合作范围、四国业务附表（表格）、服务范围、
  服务费与结算、发票与税务、知识产权、保密、数据合规、违约、
  不可抗力、争议解决、通知、其他
- 附件 A（4 国字段汇总表格）· 附件 B（服务费费率表）· 附件 C（SLA 表）
- 签署页（双方盖章 / 授权代表签字栏）

合同覆盖 countries.yaml 定义的 TH / VN / MY / ID 全部字段，同时塞入大量
真实合同的噪声条款（不可抗力、赔偿上限、仲裁、语言优先级等），用于测试
`/api/v1/uploads/contract-extract` 的抗干扰能力。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

CN_FONT = "STSong-Light"  # reportlab 内置 CID 中文字体

DEFAULT_OUT = (
    Path(__file__).resolve().parents[1] / "data" / "samples" / "sample_contract_TH_VN.pdf"
)


# ---------- 字体 ----------

def _register_font() -> str:
    try:
        pdfmetrics.registerFont(UnicodeCIDFont(CN_FONT))
        return CN_FONT
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] 注册 {CN_FONT} 失败：{exc}，回退 Helvetica")
        return "Helvetica"


# ---------- 页眉页脚 ----------

CONTRACT_NO = "STAR-SEA-2026-Q3-0817"


def _on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont(CN_FONT, 8)
    canvas.setFillColor(colors.grey)
    # 页眉：合同名称 + 编号
    canvas.drawString(
        20 * mm,
        A4[1] - 12 * mm,
        f"东南亚跨境电商综合服务合作合同 · Contract No. {CONTRACT_NO}",
    )
    canvas.line(20 * mm, A4[1] - 13.5 * mm, A4[0] - 20 * mm, A4[1] - 13.5 * mm)
    # 页脚：机密 + 页码
    canvas.drawString(20 * mm, 10 * mm, "机密 · CONFIDENTIAL")
    canvas.drawRightString(A4[0] - 20 * mm, 10 * mm, f"第 {doc.page} 页")
    canvas.restoreState()


# ---------- 内容构建 ----------

def _styles(font: str) -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "cn_title", parent=base["Title"], fontName=font,
            fontSize=20, leading=28, alignment=TA_CENTER, spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "cn_sub", parent=base["Normal"], fontName=font,
            fontSize=12, leading=18, alignment=TA_CENTER, textColor=colors.HexColor("#555555"),
            spaceAfter=24,
        ),
        "cover_meta": ParagraphStyle(
            "cn_cover_meta", parent=base["Normal"], fontName=font,
            fontSize=11, leading=20, alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "cn_h1", parent=base["Heading1"], fontName=font,
            fontSize=14, leading=22, spaceBefore=14, spaceAfter=8,
            textColor=colors.HexColor("#0f172a"),
        ),
        "h2": ParagraphStyle(
            "cn_h2", parent=base["Heading2"], fontName=font,
            fontSize=12, leading=20, spaceBefore=8, spaceAfter=4,
            textColor=colors.HexColor("#1f2937"),
        ),
        "body": ParagraphStyle(
            "cn_body", parent=base["BodyText"], fontName=font,
            fontSize=10.5, leading=18, alignment=TA_JUSTIFY, firstLineIndent=0,
        ),
        "quote": ParagraphStyle(
            "cn_quote", parent=base["BodyText"], fontName=font,
            fontSize=10.5, leading=18, leftIndent=14, textColor=colors.HexColor("#374151"),
        ),
        "right": ParagraphStyle(
            "cn_right", parent=base["Normal"], fontName=font,
            fontSize=10.5, leading=20, alignment=TA_RIGHT,
        ),
        "small": ParagraphStyle(
            "cn_small", parent=base["Normal"], fontName=font,
            fontSize=9, leading=14, textColor=colors.HexColor("#4b5563"),
        ),
    }


def _table(data, col_widths, font, header=True):
    tbl = Table(data, colWidths=col_widths, hAlign="LEFT", repeatRows=1 if header else 0)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
        ]
    tbl.setStyle(TableStyle(style))
    return tbl


def build_story(font: str) -> list:
    s = _styles(font)
    story: list = []

    # ---------- 封面 ----------
    story += [
        Spacer(1, 40 * mm),
        Paragraph("东南亚跨境电商综合服务合作合同", s["title"]),
        Paragraph(
            "Southeast Asia Cross-Border E-Commerce<br/>Comprehensive Services Agreement",
            s["subtitle"],
        ),
        Spacer(1, 20 * mm),
    ]

    cover_tbl = _table(
        [
            ["合同编号 / Contract No.", CONTRACT_NO],
            ["甲方 / Party A", "星海跨境电商（深圳）有限公司"],
            ["", "Star Sea Cross-Border E-Commerce (Shenzhen) Co., Ltd."],
            ["乙方 / Party B", "Ocean Trade Southeast Asia Holdings Pte. Ltd."],
            ["签署地点 / Place", "中国 · 深圳前海自贸区"],
            ["签署日期 / Date", "2026 年 7 月 1 日"],
            ["合同期限 / Term", "2026-07-01 至 2029-06-30（36 个月）"],
        ],
        col_widths=[55 * mm, 100 * mm],
        font=font,
        header=False,
    )
    story += [cover_tbl, PageBreak()]

    # ---------- 鉴于 / 序言 ----------
    story += [
        Paragraph("鉴于", s["h1"]),
        Paragraph(
            "1. 甲方系依据中华人民共和国法律合法设立、有效存续的有限责任公司，"
            "统一社会信用代码 91440300MA5FXXXXX，注册地址位于深圳市南山区科技园，"
            "专业从事跨境电商零售业务，拥有稳定的供应链体系与自主品牌矩阵。",
            s["body"],
        ),
        Paragraph(
            "2. 乙方系依据新加坡法律合法设立并有效存续的私人有限公司，"
            "UEN 编号 202612345K，在泰国、越南、马来西亚、印度尼西亚等东南亚国家"
            "分别设有本地关联公司，具备海外仓配、清关代理、税务申报与合规咨询能力。",
            s["body"],
        ),
        Paragraph(
            "3. 双方本着平等自愿、诚实信用、互利共赢之原则，经友好协商，"
            "就甲方委托乙方在东南亚市场提供综合服务事宜，达成如下协议，供双方共同遵守：",
            s["body"],
        ),
        Spacer(1, 6),
    ]

    # ---------- 目录 ----------
    toc_rows = [
        ["条款", "标题"],
        ["第一条", "定义与解释"],
        ["第二条", "合作范围与业务模式"],
        ["第三条", "泰国（TH）市场业务安排"],
        ["第四条", "越南（VN）市场业务安排"],
        ["第五条", "马来西亚（MY）市场业务安排"],
        ["第六条", "印度尼西亚（ID）市场业务安排"],
        ["第七条", "服务范围（Scope of Services）"],
        ["第八条", "服务费与结算"],
        ["第九条", "发票与税务合规"],
        ["第十条", "知识产权"],
        ["第十一条", "保密条款"],
        ["第十二条", "数据合规与个人信息保护"],
        ["第十三条", "违约责任"],
        ["第十四条", "不可抗力"],
        ["第十五条", "合同变更与解除"],
        ["第十六条", "争议解决"],
        ["第十七条", "通知"],
        ["第十八条", "其他"],
        ["附件 A", "四国业务字段汇总表"],
        ["附件 B", "服务费费率表"],
        ["附件 C", "SLA 指标"],
    ]
    story += [
        Paragraph("目录 · Table of Contents", s["h1"]),
        _table(toc_rows, col_widths=[35 * mm, 120 * mm], font=font),
        PageBreak(),
    ]

    # ---------- 第一条 定义 ----------
    story += [
        Paragraph("第一条　定义与解释", s["h1"]),
        Paragraph(
            "除本合同另有明确约定外，下列术语具有以下含义：",
            s["body"],
        ),
        Paragraph(
            "1.1 <b>目标市场</b>：指本合同附件 A 所列 4 个东南亚国家，即 "
            "<b>泰国、越南、马来西亚、印度尼西亚</b>。",
            s["quote"],
        ),
        Paragraph(
            "1.2 <b>业务类型</b>：本合同项下双方合作的业务类型明确为 "
            "<b>跨境电商零售</b>；如未来拓展至品牌出海直营或外贸综合服务模式，双方另签补充协议。",
            s["quote"],
        ),
        Paragraph(
            "1.3 <b>GMV</b>：指订单成交总额（Gross Merchandise Volume），"
            "含商品价、平台补贴与运费，不含退款金额。",
            s["quote"],
        ),
        Paragraph(
            "1.4 <b>合同货币</b>：以美元（USD）为核算币种，各国本币金额按合同"
            "签署日中国银行现汇卖出中间价折算，仅用于合并汇报，不改变各国实际本币结算义务。",
            s["quote"],
        ),
        Paragraph(
            "1.5 <b>Merchant of Record（MoR）</b>：指在东道国充当"
            "记录商户以承担平台结算、发票开具、税务申报义务的一方，"
            "本合同项下各国 MoR 由乙方或其关联公司担任。",
            s["quote"],
        ),
        Paragraph(
            "1.6 <b>关联公司</b>：指直接或间接控制、被控制、或与一方处于共同控制之下的任何实体，"
            "控制系指持有 50% 以上表决权或有权决定管理层任免。",
            s["quote"],
        ),
    ]

    # ---------- 第二条 合作概述 ----------
    story += [
        Paragraph("第二条　合作范围与业务模式", s["h1"]),
        Paragraph(
            "2.1 甲方委托乙方在目标市场开展跨境电商零售业务，业务类型为 <b>跨境电商零售</b>，"
            "主营 SKU 覆盖 3C 电子、快时尚服饰、大众美妆、家居日用及地方特色食品五大品类。",
            s["body"],
        ),
        Paragraph(
            "2.2 首年（2026-07 至 2027-06）GMV 目标：不低于 <b>USD 15,000,000</b>；"
            "三年累计 GMV 目标：<b>USD 60,000,000</b>。若首年实际 GMV 达成率低于 70%，"
            "双方应于每年 8 月复盘并调整年度目标，调整后目标以书面备忘录形式确认。",
            s["body"],
        ),
        Paragraph(
            "2.3 甲方承诺：（1）提供不少于 12,000 个可售 SKU；"
            "（2）每月备货预算不少于 <b>USD 4,000,000</b>；"
            "（3）保证商品符合各国进口规范、认证及标签要求。",
            s["body"],
        ),
        Paragraph(
            "2.4 乙方承诺：（1）在合同期限内独家为甲方在目标市场提供本合同项下服务，"
            "未经甲方书面同意，不得为甲方直接竞争对手（甲方另行提供竞对清单）提供相同服务；"
            "（2）配备不少于 1 名 KA 项目经理与 15 人本地运营团队。",
            s["body"],
        ),
    ]

    # ---------- 第三 ~ 第六条 各国安排 ----------
    story += _country_section(
        s, font,
        title="第三条　泰国（TH）市场业务安排",
        prose=[
            "3.1 甲方在泰国市场的<b>年度销售额预计约 1,200 万泰铢</b>"
            "（THB 12,000,000，约合 USD 340,000），首年月度爬坡曲线附后。",
            "3.2 入驻平台：<b>Shopee、Lazada、TikTok Shop</b> 三大平台官方旗舰店；"
            "如后续开放 Line Shopping、Central Online 等新兴渠道，需以补充协议形式确认。",
            "3.3 主营商品类目：<b>电子产品、服饰、美妆</b>；"
            "不含酒精饮品、药品、保健品、食品等需要泰国 FDA 单独许可的类目。",
            "3.4 月均订单量预估 <b>35,000 单</b>，客单价约 THB 350，"
            "月度退货率控制在 8% 以内，超出部分甲方另行支付 THB 30/单的退货处理费。",
            "3.5 仓储模式：采用 <b>海外仓</b> 模式，租用乙方位于曼谷 Bang Na 的"
            " 4,500㎡ B 级仓库，SKU 提前 45 天备货入仓，仓储费按 THB 12/立方米·天计收。",
            "3.6 本地公司主体：暂时 <b>否</b>；甲方通过乙方之泰国关联公司 "
            "Ocean Trade Thailand Co., Ltd.（税号 0105562098XXX）作为进口商与 VAT 纳税人。",
            "3.7 税务事项：泰国 VAT 税率 7%，注册门槛为年营业额 THB 1,800,000；"
            "乙方负责按月申报 PP.30 并按年出具审计报告；如年内发生 e-Tax Invoice 强制上线，"
            "乙方无条件配合系统对接。",
        ],
    )
    story += _country_section(
        s, font,
        title="第四条　越南（VN）市场业务安排",
        prose=[
            "4.1 甲方在越南市场的<b>年度销售额预计约 80 亿越南盾</b>"
            "（VND 8,000,000,000，约合 USD 320,000）。",
            "4.2 入驻平台：<b>Shopee、TikTok Shop、Sendo</b> 三家；"
            "Lazada 越南站因流量下滑本期不入驻。",
            "4.3 主营商品类目：<b>服饰、家居</b> 为主，占比 70%；"
            "美妆类目试点上架但不作为主推。",
            "4.4 月均订单量预估 <b>20,000 单</b>，客单价约 VND 400,000。",
            "4.5 仓储模式：采用 <b>本地仓</b> 模式，租用胡志明市第七郡（District 7）"
            "保税仓 2,200㎡，仓储服务由 Sagawa Vietnam 分包提供。",
            "4.6 税务事项：越南 VAT 标准税率 10%，跨境电商适用条件按 78 号法令"
            "（Decree 78/2026/ND-CP）执行；乙方承担电子发票（HĐĐT）开具与 GTGT 月度申报义务。",
        ],
    )
    story += _country_section(
        s, font,
        title="第五条　马来西亚（MY）市场业务安排",
        prose=[
            "5.1 甲方在马来西亚市场的<b>年度销售额预计约 350 万林吉特</b>"
            "（MYR 3,500,000，约合 USD 780,000）。",
            "5.2 入驻平台：<b>Shopee、Lazada、TikTok Shop</b>。",
            "5.3 主营商品类目：<b>电子产品、服饰、美妆</b>。",
            "5.4 仓储模式：采用 <b>直邮</b> 模式，货物从深圳前海保税仓直发终端消费者，"
            "运输方式以航空小包为主，海运整柜为辅，暂不建海外仓。",
            "5.5 本地公司主体：<b>是</b>；甲方已于 2026 年 3 月注册 "
            "Star Sea Malaysia Sdn. Bhd.，SSM 编号 202601045678，注册资本 MYR 500,000；"
            "乙方将协助完成 SST 登记与年度 CP204 预缴。",
            "5.6 税务事项：马来西亚 SST（服务税 6% + 销售税 5%~10%）并行，"
            "注册门槛 MYR 500,000；2027 年预算案计划扩围至跨境低值商品（LVG），"
            "如生效，乙方在 30 日内完成税档升级。",
        ],
    )
    story += _country_section(
        s, font,
        title="第六条　印度尼西亚（ID）市场业务安排",
        prose=[
            "6.1 甲方在印度尼西亚市场的<b>年度销售额预计约 800 亿印尼盾</b>"
            "（IDR 80,000,000,000，约合 USD 5,100,000）。",
            "6.2 入驻平台：<b>Shopee、Tokopedia、Lazada</b>；"
            "因印尼禁止 TikTok Shop 直接交易，仅通过 TikTok 引流至 Tokopedia 完成成交。",
            "6.3 本地合作方类型：<b>本地公司</b>；由乙方持有 "
            "PT Ocean Trade Indonesia（PT PMA 结构）承接本地运营，"
            "股比 100%，注册资本 IDR 10,000,000,000。",
            "6.4 进口许可证类型：<b>API</b>（Angka Pengenal Importir Umum，一般进口商识别码），"
            "持证方为 PT Ocean Trade Indonesia，证书编号 API-U-01.02.1.XX.12345。",
            "6.5 仓库位置：仓储节点覆盖 <b>雅加达、泗水</b> 两地，其中雅加达 Cakung 仓 6,000㎡ "
            "为主仓，泗水 Rungkut 仓 2,500㎡ 为南部转运节点。",
            "6.6 是否有税号 NPWP：<b>是</b>，PT Ocean Trade Indonesia 已取得 "
            "NPWP 01.234.567.8-901.000，同时完成 PKP（应税企业）确认。",
            "6.7 税务事项：适用 PPh 22 预扣所得税 0.5%、PPN（增值税）11%；"
            "PMK-131/2026 已于 2026 年 7 月生效，乙方按 SE-33/PJ/2026 履行代扣代缴义务；"
            "本地税务局要求电子发票（e-Faktur）实时上传，乙方承担系统对接与月度调节。",
        ],
    )

    # ---------- 第七条 服务范围 ----------
    story += [
        Paragraph("第七条　服务范围（Scope of Services）", s["h1"]),
        Paragraph(
            "乙方在本合同项下向甲方提供的服务范围包括但不限于以下五大类：",
            s["body"],
        ),
        Paragraph(
            "7.1 <b>平台运营</b>：店铺装修、商品上下架、促销活动排期、直播代播、"
            "客服（中文 + 英文 + 当地语言，7×12h 覆盖）、评价维护与差评处理。",
            s["quote"],
        ),
        Paragraph(
            "7.2 <b>物流仓配</b>：头程海运/空运、清关代理、入仓上架、拣货打包、"
            "末端派送（COD + 非 COD）、退换货、废弃物合规处置。",
            s["quote"],
        ),
        Paragraph(
            "7.3 <b>支付结算</b>：由乙方本地关联公司作为 Merchant of Record"
            "与平台结算，扣除平台费、税费及乙方服务费后按周汇款至甲方指定境外账户；"
            "外汇管制严格国家（如印尼、越南）按当地央行规定办理售付汇。",
            s["quote"],
        ),
        Paragraph(
            "7.4 <b>税务合规</b>：VAT/SST/PPh/PPN 等各税种登记、申报、缴纳与稽查应对；"
            "协助配合 DAC7 / OECD 平台经济信息申报；关联交易转让定价文档准备。",
            s["quote"],
        ),
        Paragraph(
            "7.5 <b>数据分析</b>：提供 SKU 级利润看板、客群画像、竞品监控周报、"
            "月度经营分析会（线上）与季度经营分析会（线下 · 深圳或上海）。",
            s["quote"],
        ),
    ]

    # ---------- 第八条 服务费 ----------
    story += [
        Paragraph("第八条　服务费与结算", s["h1"]),
        Paragraph(
            "8.1 <b>平台运营服务费</b>：按各国实际 GMV 的 4.5% 计收；"
            "如年度 GMV 达成率低于 60%，服务费下限按 USD 8,000/国/月保底。",
            s["body"],
        ),
        Paragraph(
            "8.2 <b>仓配服务费</b>：按包裹数量计收，具体费率见 <b>附件 B</b>。"
            "偏远地区（东部群岛、边远府）按标准费率的 130% 计收。",
            s["body"],
        ),
        Paragraph(
            "8.3 <b>税务代理服务费</b>：每国每月固定 <b>USD 800</b>，含月度申报与常规咨询；"
            "年度审计、税务稽查、争议应对等按实际工作量另行报价。",
            s["body"],
        ),
        Paragraph(
            "8.4 <b>结算周期</b>：T+7 日回款；若平台冻结货款超过 30 日，"
            "乙方向甲方书面通知后可顺延，但顺延期最长不超过 60 日。",
            s["body"],
        ),
        Paragraph(
            "8.5 <b>违约金</b>：任一方逾期支付超过 15 日的，按逾期金额的 0.05%/日计收违约金，"
            "累计不超过逾期金额的 20%；逾期超过 60 日的，守约方有权解除本合同并追究损失。",
            s["body"],
        ),
    ]

    # ---------- 第九条 发票税务 ----------
    story += [
        Paragraph("第九条　发票与税务合规", s["h1"]),
        Paragraph(
            "9.1 乙方应就其向甲方提供的服务开具符合中华人民共和国税法要求的"
            "增值税专用发票或商业发票（视双方所在税收管辖区确定）。",
            s["body"],
        ),
        Paragraph(
            "9.2 各国本地税负（含 VAT/SST/PPh/PPN/PDPD 等）由乙方在东道国代为申报缴纳，"
            "税负经济负担由甲方最终承担，乙方按月提供税负清单与完税凭证扫描件。",
            s["body"],
        ),
        Paragraph(
            "9.3 如东道国税制变更（税率调整、门槛调整、代扣代缴规则变更等），"
            "双方按变更后生效日起分担变更影响，任一方无权因此单方主张损失赔偿。",
            s["body"],
        ),
    ]

    # ---------- 第十 ~ 第十二条 知识产权 / 保密 / 数据 ----------
    story += [
        Paragraph("第十条　知识产权", s["h1"]),
        Paragraph(
            "10.1 甲方品牌、商标、专利、软件著作权归甲方所有；"
            "乙方在合作期内享有为履行本合同必需的、免费、非排他的许可使用权，"
            "许可地域限于目标市场，合同终止即自动失效。",
            s["body"],
        ),
        Paragraph(
            "10.2 合作过程中共同产生的运营数据、消费者画像归甲方所有；"
            "乙方可对数据做脱敏、聚合处理后用于内部服务改进和行业报告发布。",
            s["body"],
        ),
        Paragraph(
            "10.3 未经对方书面授权，任一方不得以任何形式复制、翻译、"
            "改编、许可、转让对方的知识产权。",
            s["body"],
        ),

        Paragraph("第十一条　保密条款", s["h1"]),
        Paragraph(
            "11.1 保密信息包括但不限于：财务数据、SKU 成本、供应商名单、"
            "客户名单、消费者画像、算法与流量投放策略、商业计划。",
            s["body"],
        ),
        Paragraph(
            "11.2 保密期限自本合同签署之日起至合同终止后 <b>5 年</b> 内持续有效；"
            "对于构成商业秘密的信息，保密义务无期限限制。",
            s["body"],
        ),
        Paragraph(
            "11.3 违反保密义务的一方须向守约方支付不低于 <b>USD 200,000</b> 的违约金，"
            "并赔偿因此造成的实际损失（包含但不限于律师费、公证费、调查费）。",
            s["body"],
        ),

        Paragraph("第十二条　数据合规与个人信息保护", s["h1"]),
        Paragraph(
            "12.1 双方按以下法规履行数据保护义务：欧盟 GDPR、"
            "Thailand PDPA（B.E. 2562 / 2019）、Vietnam PDPD 13/2023/ND-CP、"
            "Malaysia PDPA 2010、Indonesia UU PDP 27/2022、"
            "中华人民共和国《个人信息保护法》。",
            s["body"],
        ),
        Paragraph(
            "12.2 涉及跨境个人信息传输时，双方签署"
            "《标准合同条款》（Standard Contractual Clauses, SCC），"
            "完成必要的安全评估、备案、数据处理影响评估（DPIA）。",
            s["body"],
        ),
        Paragraph(
            "12.3 发生数据泄露事件的一方应在 <b>72 小时</b> 内书面通知对方，"
            "并按东道国监管要求向相关部门报告；因一方过错导致的行政罚款、"
            "民事赔偿由过错方全额承担。",
            s["body"],
        ),
    ]

    # ---------- 第十三 ~ 第十八条 ----------
    story += [
        Paragraph("第十三条　违约责任", s["h1"]),
        Paragraph(
            "13.1 除本合同另有约定外，一方违约给对方造成损失的，应予以全额赔偿，"
            "赔偿范围包括直接损失与可预见的间接损失。",
            s["body"],
        ),
        Paragraph(
            "13.2 <b>累计赔偿上限</b>：本合同项下累计赔偿不超过过去 12 个月已支付"
            "服务费的 <b>200%</b>；因故意或重大过失、违反保密义务、"
            "侵犯知识产权、发生数据泄露事件的除外，不受本上限约束。",
            s["body"],
        ),

        Paragraph("第十四条　不可抗力", s["h1"]),
        Paragraph(
            "14.1 因不可抗力（战争、疫情、政府征收、汇率单日波动 &gt; 5%、"
            "港口罢工、关键平台单方封店超过 15 日等）导致的违约，"
            "免于承担违约责任，但应在 5 个工作日内通知对方并采取减损措施。",
            s["body"],
        ),
        Paragraph(
            "14.2 不可抗力持续超过 90 日的，任一方有权提前 30 日书面通知解除本合同，"
            "解除时已发生但未结算的费用按实际工作量按比例结算。",
            s["body"],
        ),

        Paragraph("第十五条　合同变更与解除", s["h1"]),
        Paragraph(
            "15.1 本合同任何变更须以双方授权代表签署的书面补充协议为准，"
            "口头约定不产生效力。",
            s["body"],
        ),
        Paragraph(
            "15.2 任一方提前 90 日书面通知对方可解除本合同；"
            "解除时已发生的服务费按比例结算，已备货 SKU 由乙方按成本价 + 10% 回购或代甲方处置。",
            s["body"],
        ),

        Paragraph("第十六条　争议解决", s["h1"]),
        Paragraph(
            "16.1 本合同适用中华人民共和国香港特别行政区法律，"
            "不适用《联合国国际货物销售合同公约》。",
            s["body"],
        ),
        Paragraph(
            "16.2 因本合同引起或与之相关的任何争议，双方应先友好协商；"
            "协商不成的，提交香港国际仲裁中心（HKIAC）按其现行仲裁规则在"
            "香港以英文进行仲裁，仲裁员为 3 人，仲裁裁决为终局裁决。",
            s["body"],
        ),

        Paragraph("第十七条　通知", s["h1"]),
        Paragraph(
            "17.1 甲方联系人：陈磊 · 商务副总裁 · +86 138-0000-1234 · lei.chen@starsea.com",
            s["body"],
        ),
        Paragraph(
            "17.2 乙方联系人：Lim Wei Jian · SEA Director · +65 9123-4567 · weijian.lim@oceantrade.sg",
            s["body"],
        ),
        Paragraph(
            "17.3 通知方式：书面（含 PDF 邮件）为准，"
            "自对方书面回执或邮件送达服务器返回成功之日起视为送达。",
            s["body"],
        ),

        Paragraph("第十八条　其他", s["h1"]),
        Paragraph(
            "18.1 本合同一式六份，中英文各三份，具有同等法律效力；"
            "如中英文表述冲突，以 <b>中文文本</b> 为准。",
            s["body"],
        ),
        Paragraph(
            "18.2 本合同附件 A（四国业务字段汇总）、附件 B（服务费费率）、"
            "附件 C（SLA 指标）为本合同不可分割的组成部分，与正文具有同等效力。",
            s["body"],
        ),
        Paragraph(
            "18.3 本合同未尽事宜，由双方另行协商并以书面补充协议为准；"
            "如任一条款被认定无效，不影响其他条款的效力。",
            s["body"],
        ),
    ]

    # ---------- 签署页 ----------
    story += [PageBreak(), *_signature_block(s, font)]

    # ---------- 附件 A ----------
    story += [PageBreak(), Paragraph("附件 A · 四国业务字段汇总表", s["h1"])]
    story += [
        _table(
            [
                ["国家", "业务类型", "年销售额（本币）", "主平台", "主营类目", "仓储模式", "本地主体 / 特殊字段"],
                ["🇹🇭 泰国 TH", "跨境电商零售", "THB 12,000,000", "Shopee / Lazada / TikTok Shop", "电子产品 / 服饰 / 美妆", "海外仓", "无本地主体（借用乙方 MoR）"],
                ["🇻🇳 越南 VN", "跨境电商零售", "VND 8,000,000,000", "Shopee / TikTok Shop / Sendo", "服饰 / 家居", "本地仓", "—"],
                ["🇲🇾 马来 MY", "跨境电商零售", "MYR 3,500,000", "Shopee / Lazada / TikTok Shop", "电子产品 / 服饰 / 美妆", "直邮", "有本地主体（SSM 编号 202601045678）"],
                ["🇮🇩 印尼 ID", "跨境电商零售", "IDR 80,000,000,000", "Shopee / Tokopedia / Lazada", "—", "—", "本地合作方=本地公司 / API 许可证 / 仓：雅加达+泗水 / 有 NPWP"],
            ],
            col_widths=[22 * mm, 22 * mm, 30 * mm, 34 * mm, 26 * mm, 18 * mm, 40 * mm],
            font=font,
        ),
    ]

    # ---------- 附件 B ----------
    story += [Spacer(1, 10), Paragraph("附件 B · 服务费费率表", s["h1"])]
    story += [
        _table(
            [
                ["项目", "泰国 TH", "越南 VN", "马来 MY", "印尼 ID"],
                ["平台运营（% GMV）", "4.5%", "4.5%", "4.5%", "4.5%"],
                ["仓配（每单）", "THB 25", "VND 18,000", "MYR 3.2", "IDR 12,000"],
                ["税务代理（USD/月）", "800", "800", "800", "800"],
                ["最低服务费保底（USD/月）", "8,000", "8,000", "8,000", "12,000"],
            ],
            col_widths=[45 * mm, 28 * mm, 32 * mm, 28 * mm, 32 * mm],
            font=font,
        ),
    ]

    # ---------- 附件 C ----------
    story += [Spacer(1, 10), Paragraph("附件 C · SLA 指标", s["h1"])]
    story += [
        _table(
            [
                ["指标", "承诺值", "考核方式", "未达成后果"],
                ["订单发货时效（入仓 SKU）", "24 小时内出库", "平台后台数据", "赔付订单金额 5%"],
                ["订单发货时效（直邮 SKU）", "48 小时内交运", "物流轨迹回传", "赔付订单金额 5%"],
                ["客服首响", "在线咨询 60s / 工单 4h", "平台数据 + 抽检", "服务费扣减 2%"],
                ["系统可用率", "≥ 99.5%（不含平台侧）", "月度可用率报告", "按停机时长退费"],
                ["财务对账", "每周五 18:00 前", "邮件送达时间戳", "按迟延日次序警"],
            ],
            col_widths=[42 * mm, 38 * mm, 42 * mm, 42 * mm],
            font=font,
        ),
    ]

    story += [
        Spacer(1, 12),
        Paragraph("（本合同正文及附件共 XX 页，以下无正文）", s["small"]),
    ]

    return story


def _country_section(styles: dict, font: str, *, title: str, prose: list[str]) -> list:
    story: list = [Paragraph(title, styles["h1"])]
    for line in prose:
        story.append(Paragraph(line, styles["body"]))
    return [KeepTogether(story)] if len(prose) <= 4 else story


def _signature_block(s: dict, font: str) -> list:
    sig_tbl = _table(
        [
            ["甲方（盖章）", "乙方（盖章）"],
            ["星海跨境电商（深圳）有限公司", "Ocean Trade Southeast Asia Holdings Pte. Ltd."],
            ["", ""],
            ["授权代表签字：__________________", "Authorized Signatory: __________________"],
            ["姓名：陈磊　　职务：商务副总裁", "Name: Lim Wei Jian    Title: SEA Director"],
            ["日期：2026 年 7 月 1 日", "Date: 1 July 2026"],
        ],
        col_widths=[85 * mm, 85 * mm],
        font=font,
        header=False,
    )
    return [
        Paragraph("签　署　页 · Signature Page", s["h1"]),
        Paragraph(
            "双方确认已充分阅读、理解本合同及全部附件的每一条款，"
            "并授权下列代表签字盖章。本页为签署页，无正文。",
            s["body"],
        ),
        Spacer(1, 20),
        sig_tbl,
    ]


def build_pdf(out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    font = _register_font()

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title="东南亚跨境电商综合服务合作合同",
        author="Star Sea Cross-Border E-Commerce (Shenzhen) Co., Ltd.",
    )
    doc.build(build_story(font), onFirstPage=_on_page, onLaterPages=_on_page)


def main() -> None:
    parser = argparse.ArgumentParser(description="生成示例合同 PDF")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="输出路径")
    args = parser.parse_args()

    build_pdf(args.out)
    print(f"✅ 已生成示例合同：{args.out}")


if __name__ == "__main__":
    main()
