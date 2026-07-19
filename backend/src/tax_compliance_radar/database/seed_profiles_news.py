"""预置模拟用户画像和新闻/政策数据。启动时 idempotent 插入。

标签统一使用中文自然短语，与 tag_extractor 输出一致。
新闻正文尽可能接近真实报道口吻，包含数字、条款、生效日期与影响面，便于演示。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tax_compliance_radar.services.db import (
    get_connection,
    insert_audit_history,
    insert_news_item,
    insert_qa_history,
    news_count,
    profile_count,  # noqa: F401 - 保留以便外部调试
    upsert_profile,
    upsert_profile_tags,
)


def _iso(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def _iso_h(days_ago: int, hours_ago: int = 0) -> str:
    """带小时精度的 ISO，用于把种子记录打散到一天中不同时段，让看板活跃热力图更真实。"""
    return (datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_ago)).isoformat()


SEED_PROFILES: list[dict] = [
    {
        "profile_id": "default",
        "display_name": "默认访客",
        "business_type": None,
        "description": "未指定身份的访客（前端未生成 profile_id 时的兜底）",
        "base_tags": {},
    },
    {
        "profile_id": "ecom_th",
        "display_name": "跨境电商-泰国老王",
        "business_type": "跨境电商零售",
        "description": "泰国 Shopee 独立小卖家，年销售额约 200 万 THB",
        "base_tags": {
            "泰国": 4.0,
            "增值税": 3.5,
            "跨境电商": 3.0,
            "Shopee": 2.0,
            "已达注册门槛": 2.0,
            "注册门槛": 2.0,
            "申报": 1.5,
        },
    },
    {
        "profile_id": "brand_id_vn",
        "display_name": "品牌出海-Anna",
        "business_type": "品牌出海直营",
        "description": "同时运营印尼、越南两个 DTC 独立站，主打个护小家电",
        "base_tags": {
            "印尼": 3.0,
            "越南": 3.0,
            "增值税": 2.5,
            "品牌出海": 3.0,
            "独立站": 2.0,
            "电子发票": 1.5,
            "跨境": 1.5,
        },
    },
    {
        "profile_id": "trade_multi",
        "display_name": "外贸综合-老李",
        "business_type": "外贸综合服务",
        "description": "代多家工厂做出口清关与退税，覆盖泰国/马来西亚/新加坡/菲律宾",
        "base_tags": {
            "泰国": 2.0,
            "马来西亚": 2.5,
            "新加坡": 2.0,
            "菲律宾": 1.5,
            "增值税": 2.0,
            "关税": 2.0,
            "外贸综合服务": 3.0,
            "申报": 1.5,
            "退税": 1.5,
        },
    },
    {
        "profile_id": "newbie_blank",
        "display_name": "新用户-空白画像",
        "business_type": None,
        "description": "刚注册尚未产生任何行为，用于验证冷启动。",
        "base_tags": {},
    },
]


SEED_NEWS: list[dict] = [
    {
        "title": "泰国税务局重申跨境电商 VAT 注册门槛维持 180 万泰铢",
        "summary": (
            "泰国税务局 6 月最新答复企业咨询函明确：2026 年度跨境电商年销售额超过 180 万泰铢仍须完成 VAT 注册，"
            "并按月提交 PP.30 申报表。近期已对 Shopee、Lazada 平台商户开展抽查。"
        ),
        "body": (
            "泰国税务局（Revenue Department）在 2026 年 7 月 3 日发布的第 Por.62/2569 号答复函中重申，"
            "跨境电商经营者（包括通过 Shopee、Lazada、TikTok Shop 等平台向泰国消费者销售商品或服务的境外主体），"
            "年度累计销售额超过 180 万泰铢即达到 VAT 注册门槛，须在 30 日内向税务局提交 P.P.01 表格完成注册，"
            "并自次月起按月提交 P.P.30 申报表。\n\n"
            "泰国税务局跨境电商专责组透露，2026 年二季度共对 217 家境外卖家发起询证函，其中 41 家因未按时注册 VAT 被追缴"
            "税款并处以 1.5%/月的滞纳金和最多 2 倍未缴税额的罚款。税务局建议尚未注册的卖家尽快自查历史销售数据，"
            "对已达门槛但未注册的年度补办登记，可依据自愿申报政策争取减免 50% 罚款。"
        ),
        "source": "泰国税务局",
        "publish_time": _iso(5),
        "tags": ["编辑精选", "泰国", "增值税", "跨境电商", "注册门槛", "Shopee", "Lazada"],
        "original_link": "https://www.rd.go.th/english/",
    },
    {
        "title": "泰国 VAT 月度申报截止日调整为每月 17 日",
        "summary": (
            "泰国税务局公告：自 2026 年 8 月起，VAT 月度申报（P.P.30）截止日由每月 15 日推迟至 17 日；"
            "电子申报（e-Filing）可再延后至当月 23 日。逾期罚金标准同步公布。"
        ),
        "body": (
            "根据泰国税务局 2026 年 6 月 28 日发布的第 3/2569 号部长命令，P.P.30 增值税月度申报截止日由每月 15 日"
            "统一延后至 17 日；通过 e-Filing 系统提交的纳税人在此基础上可再延后 8 个自然日，即当月 23 日。\n\n"
            "对逾期未申报或未足额缴纳税款的纳税人，税务局将按以下标准处罚：\n"
            "  · 未按时申报：每张申报表 500 泰铢固定罚金；\n"
            "  · 未足额缴纳：按未缴税额 1.5%/月计算滞纳金，上不封顶；\n"
            "  · 情节严重且经稽查确认逃税的：处应缴税额 1–2 倍罚款。\n\n"
            "税务局同步提醒跨境电商卖家关注国庆假期（10 月）与申报期的时间冲突，建议提前提交避免系统拥堵。"
        ),
        "source": "泰国税务局",
        "publish_time": _iso(12),
        "tags": ["泰国", "增值税", "申报", "处罚"],
        "original_link": "https://www.rd.go.th/english/",
    },
    {
        "title": "印尼取消 3 美元以下跨境包裹免税待遇，全面征收 11% 增值税",
        "summary": (
            "印尼财政部第 PMK-131/2026 号条例落地：自 2026 年 7 月 1 日起，所有跨境电商入境包裹不再享受 3 美元"
            "以下低值免税待遇，由平台统一代扣代缴 11% VAT；独立站须完成 PPN 号注册。"
        ),
        "body": (
            "印尼财政部（Kementerian Keuangan）签发第 PMK-131/2026 号部长条例，取消此前对 3 美元以下跨境包裹的增值税豁免。"
            "自 2026 年 7 月 1 日起，所有进入印尼的跨境电商包裹一律按 11% 征收 VAT（PPN），由持牌电商平台代扣代缴。\n\n"
            "对未通过持牌平台成交、直接由境外独立站发货的品牌方，需自行申请印尼税务身份号（NPWP）并注册 PPN 号，"
            "并按月提交 SPT Masa PPN 申报表。海关与税务总局联合执法，未合规包裹将被扣押并处以货值 50–100% 罚款。\n\n"
            "此次调整预计影响印尼跨境电商年 GMV 约 45 亿美元；DTC 独立站品牌方需评估其定价策略，避免 11% 税负全部"
            "由消费者承担导致转化率下滑。"
        ),
        "source": "印尼财政部（PMK-131/2026）",
        "publish_time": _iso(9),
        "tags": ["编辑精选", "印尼", "增值税", "跨境", "代扣代缴", "跨境电商", "品牌出海", "低值免税政策", "独立站"],
        "original_link": "https://www.pajak.go.id/",
    },
    {
        "title": "越南税务总局：2026 Q3 起面向个人消费者的跨境电商强制使用电子发票",
        "summary": (
            "越南税务总局第 78/2026/TT-BTC 号通知：自 2026 年 9 月 1 日起，所有面向越南个人消费者的境内外电商卖家"
            "均须开具电子发票（e-invoice），违规按 40,000–80,000 越南盾/张处罚。"
        ),
        "body": (
            "越南财政部与税务总局联合发布 78/2026/TT-BTC 号通知，将电子发票强制适用范围扩展至跨境电商 B2C 场景。\n\n"
            "关键要点：\n"
            "  1. 覆盖对象：在越南境内销售商品/服务的境外卖家（含 DTC 独立站、Shopee/Lazada/TikTok Shop 越南站等）；\n"
            "  2. 生效时间：2026 年 9 月 1 日；\n"
            "  3. 认证服务商：Viettel、VNPT、FPT 等 8 家；\n"
            "  4. 处罚：漏开或伪造电子发票，每张按 400,000–800,000 越南盾（约 16–32 美元）处罚，"
            "     年内累计超过 100 张即列入税务黑名单。\n\n"
            "对于此前使用纸质发票或不出具发票的品牌方，建议尽快与本地财税服务商对接完成系统接入，"
            "并测试与自有 ERP/独立站订单系统的对接稳定性。"
        ),
        "source": "越南税务总局",
        "publish_time": _iso(20),
        "tags": ["编辑精选", "越南", "增值税", "电子发票", "发票", "品牌出海", "跨境电商"],
        "original_link": "https://www.gdt.gov.vn/",
    },
    {
        "title": "马来西亚拟将 SST 注册门槛由 50 万令吉下调至 30 万令吉",
        "summary": (
            "马来西亚财政部发布 2027 年度预算公开咨询稿，拟将销售与服务税（SST）注册门槛由 50 万令吉下调至 30 万令吉，"
            "预计新增约 3 万家中小外贸综合服务商纳入征收范围。"
        ),
        "body": (
            "马来西亚财政部（Kementerian Kewangan）于 2026 年 7 月 12 日发布《2027 年度预算公开咨询稿》，"
            "其中最受关注的一项调整是：拟将 SST 中的服务税注册门槛由现行的 50 万令吉/年下调至 30 万令吉/年，"
            "生效日期暂定为 2027 年 1 月 1 日。\n\n"
            "若草案通过，主要影响以下三类企业：\n"
            "  · 提供跨境物流、报关代理服务的外贸综合服务商；\n"
            "  · 面向马来商户的 SaaS、数字营销服务提供商；\n"
            "  · 年营业额介于 30–50 万令吉之间的中型专业服务企业。\n\n"
            "咨询期截至 8 月 30 日，建议受影响企业通过行业协会提交反馈，同时准备好登记、开票、申报流程的过渡方案。"
        ),
        "source": "马来西亚财政部",
        "publish_time": _iso(3),
        "tags": ["马来西亚", "销售与服务税", "注册门槛", "外贸综合服务", "SaaS"],
        "original_link": "https://www.mof.gov.my/",
    },
    {
        "title": "新加坡 GST 维持 9% 不再上调，OVR 门槛延续现行标准",
        "summary": (
            "新加坡财政部长在国会答复中确认，商品与服务税（GST）短期内维持 9%；海外供应商注册（OVR）门槛"
            "同步保持全球营收 100 万新元 + 新加坡销售 10 万新元。"
        ),
        "body": (
            "新加坡副总理兼财政部长在 2026 年 7 月 1 日国会答复中确认，鉴于居民消费信心尚未完全恢复，"
            "GST 税率维持 9%，2027 年预算中亦不再考虑上调。海外供应商注册（Overseas Vendor Registration, OVR）"
            "门槛延续现行标准：\n"
            "  · 全球年度营收 ≥ 100 万新元；\n"
            "  · 且面向新加坡消费者销售 ≥ 10 万新元。\n\n"
            "适用于向新加坡个人消费者销售数字服务（SaaS、流媒体、在线教育等）以及低值商品的境外供应商。"
            "新加坡 IRAS 提供 30 分钟在线快速注册通道，注册后须按季度提交 GST F5 表。"
        ),
        "source": "新加坡财政部 / IRAS",
        "publish_time": _iso(15),
        "tags": ["新加坡", "商品与服务税", "注册门槛", "SaaS", "数字服务"],
        "original_link": "https://www.iras.gov.sg/",
    },
    {
        "title": "菲律宾数字服务税立法生效，境外 SaaS/流媒体须注册并按月申报",
        "summary": (
            "菲律宾《数字服务税法》（RA 11976 修正案）于 2026 年 6 月正式生效，境外提供数字服务的供应商"
            "年菲律宾营收超过 300 万比索即须注册 VAT，税率 12%。"
        ),
        "body": (
            "菲律宾国税局（BIR）依据 RA 11976 修正案发布 RR 3-2026 号实施细则，对境外数字服务供应商征收 12% VAT，"
            "生效日为 2026 年 6 月 15 日。适用范围包括：\n"
            "  · SaaS 与云计算服务；\n"
            "  · 在线广告投放服务；\n"
            "  · 视频/音频流媒体订阅；\n"
            "  · 在线教育、电子书、游戏点卡等数字商品；\n\n"
            "达到年菲律宾营收 300 万比索门槛的境外供应商，须在 60 日内完成简易注册（Simplified Registration），"
            "并按月通过 BIR 电子申报系统提交 VAT 申报表。未合规者除追缴税款外，将被处以 25%–50% 罚款。"
        ),
        "source": "菲律宾国税局（BIR）",
        "publish_time": _iso(25),
        "tags": ["菲律宾", "增值税", "数字服务税", "数字服务", "SaaS", "注册门槛"],
        "original_link": "https://www.bir.gov.ph/",
    },
    {
        "title": "亚马逊东南亚站扩大代扣代缴销售税适用品类",
        "summary": (
            "亚马逊 SEA 官方公告：自 2026 年 8 月 5 日起，亚马逊将对家居、玩具、消费电子等 6 大品类"
            "订单默认代扣代缴销售税，卖家须核对店铺 Tax Settings 避免重复申报。"
        ),
        "body": (
            "亚马逊东南亚业务在 2026 年 7 月 10 日发布卖家公告，将代扣代缴销售税（Marketplace Facilitator Tax）"
            "范围扩大至以下品类：\n"
            "  · 家居用品与厨具（Home & Kitchen）；\n"
            "  · 玩具与游戏（Toys & Games）；\n"
            "  · 消费电子（Consumer Electronics）；\n"
            "  · 运动户外（Sports & Outdoors）；\n"
            "  · 美妆个护（Beauty & Personal Care）；\n"
            "  · 服装鞋帽（Clothing & Shoes）。\n\n"
            "上述品类订单，亚马逊将在结算环节直接代扣代缴销售税，卖家不再在自有申报表中重复计入。"
            "建议卖家登录 Seller Central > Tax Settings 页面核对生效日期，并据此更新自有 ERP 的税额计算逻辑。"
        ),
        "source": "亚马逊卖家中心",
        "publish_time": _iso(2),
        "tags": ["编辑精选", "跨境电商", "亚马逊", "代扣代缴", "增值税"],
        "original_link": "https://sellercentral.amazon.com/",
    },
    {
        "title": "海关总署优化综合外贸服务企业出口退税审核周期至 5 个工作日",
        "summary": (
            "海关总署与国家税务总局联合印发《关于进一步支持综合外贸服务企业出口退税便利化的通知》，"
            "对备案的综合外贸服务企业将退税审核周期由 15 日压缩至 5 个工作日。"
        ),
        "body": (
            "海关总署与国家税务总局在 2026 年 7 月 8 日联合印发文件（署税发〔2026〕41 号），要点如下：\n"
            "  1. 适用对象：在海关备案的一类、二类综合外贸服务企业；\n"
            "  2. 退税审核周期：由 15 个工作日压缩至 5 个工作日；\n"
            "  3. 电子底账系统对接：优化与外贸综合服务企业 ERP 的直连接口，减少人工核对；\n"
            "  4. 抽查机制：加强对涉税异常样本的抽查，重点关注虚开发票、虚假报关；\n\n"
            "该政策既缩短了综合外贸服务企业的现金流回款周期，也进一步压实合规责任，"
            "建议受益企业主动完善内控与凭证留存。"
        ),
        "source": "海关总署 / 国家税务总局",
        "publish_time": _iso(7),
        "tags": ["外贸综合服务", "退税", "关税", "申报"],
        "original_link": "http://www.customs.gov.cn/",
    },
    {
        "title": "泰国 e-Tax Invoice 全面推广：小型商户 2026 年底前必须接入",
        "summary": (
            "泰国税务局公告：面向所有 VAT 登记纳税人推广 e-Tax Invoice 与 e-Receipt 系统；"
            "小型商户（年销售额 3000 万泰铢以下）须在 2026 年 12 月 31 日前完成对接。"
        ),
        "body": (
            "泰国税务局在 2026 年 6 月发布 e-Tax Invoice 系统 2.0 版，要求所有 VAT 登记的纳税人在下列节点前完成接入：\n"
            "  · 大型企业（年销售额 ≥ 5 亿泰铢）：2026 年 3 月 31 日（已完成）；\n"
            "  · 中型企业（3000 万–5 亿泰铢）：2026 年 9 月 30 日；\n"
            "  · 小型企业（3000 万泰铢以下）：2026 年 12 月 31 日。\n\n"
            "跨境电商卖家如已完成 VAT 注册，可优先接入税务局提供的 PEPPOL 兼容 API，"
            "或选用 GENSA、Netbay 等本地服务商。逾期未接入的纳税人，"
            "税务局将暂停其新版 P.P.30 表格的电子申报权限。"
        ),
        "source": "泰国税务局",
        "publish_time": _iso(35),
        "tags": ["泰国", "增值税", "电子发票", "发票"],
        "original_link": "https://etax.rd.go.th/",
    },
    {
        "title": "印尼 PPh 22 进口预扣税：跨境卖家申报口径最新说明",
        "summary": (
            "印尼税务总局澄清 PPh 22 对跨境电商进口环节的计算基准与税率适用："
            "以 CIF + 关税 + VAT 为计税基数，持 API 号税率 2.5%、无 API 号税率 7.5%。"
        ),
        "body": (
            "印尼税务总局（DJP）在 2026 年 5 月发布 SE-33/PJ/2026 号通函，"
            "对 PPh 22（Pajak Penghasilan Pasal 22）进口预扣税针对跨境电商场景做出如下澄清：\n\n"
            "1. 计税基数 = CIF + 关税 + 已代扣 VAT（PPN）；\n"
            "2. 税率：\n"
            "   · 持有 Angka Pengenal Impor（API 进口识别号）的卖家：2.5%；\n"
            "   · 未持 API 的卖家：7.5%；\n"
            "3. 缴纳时点：清关放行前一并缴纳，由海关代收；\n"
            "4. 抵扣：所缴 PPh 22 可作为企业所得税年度汇算清缴的预付税款抵扣。\n\n"
            "建议 DTC 独立站品牌方评估是否申请 API 号以适用更低费率，同时理顺关税、VAT、PPh 22 三税的现金流管理。"
        ),
        "source": "印尼税务总局",
        "publish_time": _iso(45),
        "tags": ["印尼", "预扣税", "跨境", "跨境电商", "关税"],
        "original_link": "https://www.pajak.go.id/",
    },
    {
        "title": "TikTok Shop 泰国站强制绑定 VAT ID，未合规订单将限流",
        "summary": (
            "TikTok Shop 泰国站官方通知：自 2026 年 6 月 15 日起，卖家须在店铺后台绑定泰国 VAT ID，"
            "未合规店铺的商品将被限制出现在推荐流。"
        ),
        "body": (
            "TikTok Shop 泰国站（seller-th.tiktok.com）在 2026 年 5 月 20 日发布卖家公告，"
            "为响应泰国税务局关于跨境电商 VAT 合规的要求，平台将在 2026 年 6 月 15 日起启用如下措施：\n"
            "  1. 强制绑定：卖家须在店铺后台上传泰国 VAT 注册证书并填写 VAT ID；\n"
            "  2. 电子发票：达到 VAT 注册标准的卖家须开具 e-Tax Invoice 给消费者；\n"
            "  3. 未合规处理：未按期绑定 VAT ID 的店铺，其商品在 For You 页与 LIVE 场景推荐权重下调 80%，严重情况下暂停开播；\n"
            "  4. 稽核：平台每周向税务局同步一次 VAT 绑定状态。\n\n"
            "已完成 VAT 注册但未绑定的卖家，请在 6 月 15 日前在 seller center Tax Settings 中完成绑定，避免流量损失。"
        ),
        "source": "TikTok Shop 卖家中心",
        "publish_time": _iso(11),
        "tags": ["泰国", "TikTok Shop", "增值税", "跨境电商", "电子发票"],
        "original_link": "https://seller-th.tiktok.com/",
    },
    {
        "title": "越南跨境退税门槛提升至 500 美元，小额包裹处理简化",
        "summary": (
            "越南税务总局第 65/2026/QD-BTC 号决定：将跨境退税门槛由 300 美元提升至 500 美元，"
            "500 美元以下包裹的进口关税与 VAT 一律通过平台简易通道核销。"
        ),
        "body": (
            "越南税务总局 2026 年 4 月发布 65/2026/QD-BTC 号决定，简化 500 美元以下小额包裹的税务处理：\n"
            "  · 平台代扣代缴：由持牌电商平台在下单时代扣代缴 10% VAT；\n"
            "  · 免于逐票审核：500 美元以下包裹不再要求逐票提供发票原件；\n"
            "  · 退货退税：允许通过平台简易通道核销，最长处理周期 15 个工作日。\n\n"
            "利好使用越南本地履约的品牌方，可减少财务对账工作量。仍有约 12% 的高单价 SKU（超过 500 美元）"
            "需继续按原流程处理，建议品牌方按 SKU 分档规划仓储与开票策略。"
        ),
        "source": "越南税务总局",
        "publish_time": _iso(60),
        "tags": ["越南", "退税", "跨境", "品牌出海"],
        "original_link": "https://www.gdt.gov.vn/",
    },
    {
        "title": "新加坡 IRAS 推出 OVR 快速注册通道，30 分钟完成海外供应商注册",
        "summary": (
            "新加坡税务局（IRAS）升级 myTax Portal，向海外数字服务供应商开放 30 分钟"
            "在线 OVR 注册通道，材料齐全者当日完成登记并生成 GST 号。"
        ),
        "body": (
            "新加坡税务局（IRAS）于 2026 年 5 月正式上线 OVR 简化注册流程 2.0。相较旧流程，主要变化包括：\n"
            "  1. 全流程线上：无需邮寄纸质材料；\n"
            "  2. 材料清单精简：仅需公司注册证书、法定代表护照、业务模式说明与银行账户凭证；\n"
            "  3. 审核时长：材料齐全者 30 分钟内完成审核并生成 GST 号；\n"
            "  4. 双语支持：中文界面与在线客服。\n\n"
            "适用于 SaaS、流媒体、在线教育、跨境电商等业态。IRAS 特别提示："
            "OVR 注册后须按季度提交 GST F5 表，即使当期无销售也须提交零申报。"
        ),
        "source": "新加坡税务局（IRAS）",
        "publish_time": _iso(50),
        "tags": ["新加坡", "商品与服务税", "SaaS", "数字服务", "注册门槛"],
        "original_link": "https://www.iras.gov.sg/",
    },
    {
        "title": "警示案例：菲律宾一跨境电商未注册 VAT 被追缴 3 年税款+50% 罚款",
        "summary": (
            "菲律宾 BIR 近期对一家运营 3 年、年销售约 1.2 亿比索的境外跨境电商开出税单："
            "追缴 3 年 VAT 共计 3900 万比索，另加 50% 罚款与利息。"
        ),
        "body": (
            "菲律宾国税局（BIR）在 2026 年 7 月对某境外跨境电商（未披露品牌名）开出裁定书，主要事实与结论如下：\n"
            "  · 违规事实：该卖家自 2023 年起通过 Shopee 与自有独立站向菲律宾消费者销售，"
            "    3 年累计销售 1.2 亿比索，但从未在菲律宾办理 VAT 注册；\n"
            "  · 追缴金额：VAT 本金 3900 万比索（约合 68 万美元），"
            "    加 50% 罚款、25% 年利息，合计约 7200 万比索；\n"
            "  · 强制措施：BIR 已请求 Shopee 冻结其店铺资金并请求菲律宾央行协助追偿。\n\n"
            "该案例是 RA 11976 数字服务税修正案生效后首例大宗追偿，警示所有向菲律宾消费者销售的跨境卖家："
            "只要销售可归属当地，即便未在当地设实体，也承担 VAT 注册与申报义务。"
        ),
        "source": "菲律宾国税局（BIR） / 行业媒体综合",
        "publish_time": _iso(4),
        "tags": ["编辑精选", "菲律宾", "增值税", "处罚", "跨境电商", "Shopee"],
        "original_link": "https://www.bir.gov.ph/",
    },
]


# ------------------------------------------------------------------ #
# 模拟检索历史与审核记录（按 profile 分组）
# ------------------------------------------------------------------ #


def _qa_answer(
    regulation_base: str,
    core_rules: str,
    suggestion: str = "",
    warning: str = "",
    guide: str = "",
    link: str = "",
    **kwargs,
) -> dict:
    """构造 QAAnswer 兼容的 dict。允许用命名参数 operation_guide/compliance_suggestion/risk_warning。

    与在线流式回答保持一致：将 regulation_base 以 `**引用来源：**` 标记追加到 core_rules 末尾，
    这样 QaHistoryModal 的 renderAnswerWithSourceLinks 才会解析出可点击的来源 tag。
    """
    marker = "**引用来源：**"
    reg = kwargs.get("regulation_base", regulation_base)
    body = core_rules or ""
    if reg and marker not in body:
        body = f"{body}\n\n{marker}\n{reg}"
    return {
        "regulation_base": reg,
        "core_rules": body,
        "compliance_suggestion": kwargs.get("compliance_suggestion", suggestion),
        "risk_warning": kwargs.get("risk_warning", warning),
        "operation_guide": kwargs.get("operation_guide", guide),
        "original_link": kwargs.get("original_link", link),
    }


SEED_QA_HISTORY: dict[str, list[dict]] = {
    "ecom_th": [
        {
            "query_text": "泰国 VAT 注册门槛是多少？我在 Shopee 上一年做 200 万泰铢，需要注册吗？",
            "answer_text": _qa_answer(
                regulation_base="泰国VAT注册门槛；泰国税务局 Por.62/2569 号答复函",
                core_rules="泰国 VAT 注册门槛为年销售额 180 万泰铢。跨境电商年销售额超过门槛的境外主体，需在 30 日内提交 P.P.01 表格完成 VAT 注册，并按月申报 P.P.30。",
                suggestion="200 万泰铢已超过门槛，建议尽快办理 VAT 注册，同时补做月度申报。可利用自愿申报政策减免 50% 滞纳金。",
                warning="逾期注册会被追缴税款并处以 1.5%/月滞纳金，情节严重者罚款可达未缴税额 2 倍。",
                operation_guide="1) 准备公司注册证书、法定代表护照、银行账户；2) 通过 e-Registration 系统提交 P.P.01；3) 30 日内完成后按月提交 P.P.30。",
                link="https://www.rd.go.th/english/",
            ),
            "recall_doc_ids": ["泰国VAT注册门槛"],
            "create_time": _iso(38),
        },
        {
            "query_text": "在 Shopee 泰国店铺开电子发票（e-Tax Invoice）应该怎么做？",
            "answer_text": _qa_answer(
                regulation_base="泰国电子发票e-TaxInvoice；泰国税务局 e-Tax Invoice 2.0 系统指引",
                core_rules="所有 VAT 登记纳税人须在 2026 年 12 月 31 日前完成 e-Tax Invoice 接入。可选 PEPPOL 兼容 API，或通过 GENSA、Netbay 等本地服务商接入。",
                suggestion="建议使用 PEPPOL 兼容接口，方便未来在东南亚多国复用；同时将 e-Tax Invoice 与自有 ERP/店铺后台对接以自动开票。",
                warning="逾期未接入的纳税人，税务局将暂停其新版 P.P.30 表格的电子申报权限。",
                operation_guide="1) 在税务局 e-Tax portal 注册；2) 选择服务商接入；3) 完成 UAT 测试；4) 与 Shopee 后台开票逻辑联调。",
                link="https://etax.rd.go.th/",
            ),
            "recall_doc_ids": ["泰国电子发票e-TaxInvoice"],
            "create_time": _iso(21),
        },
        {
            "query_text": "TikTok Shop 泰国站要绑定 VAT ID 吗？不绑定会怎样？",
            "answer_text": _qa_answer(
                regulation_base="TikTokShop泰国站合规；TikTok Shop 泰国站卖家公告 2026-05-20",
                core_rules="自 2026 年 6 月 15 日起，卖家须在店铺后台绑定泰国 VAT 注册证书与 VAT ID。达到 VAT 门槛的卖家须开具 e-Tax Invoice 给消费者。",
                suggestion="尽快完成 VAT 注册并在店铺后台 Tax Settings 页面上传证书，避免流量损失。",
                warning="未绑定 VAT ID 的店铺，商品在 For You 页与 LIVE 场景的推荐权重下调 80%，严重情况暂停开播权限。",
                operation_guide="Seller Center → Business Center → Tax Settings → 上传 VAT 证书 → 填写 VAT ID → 提交审核。",
                link="https://seller-th.tiktok.com/",
            ),
            "recall_doc_ids": ["TikTokShop泰国站合规"],
            "create_time": _iso(9),
        },
        {
            "query_text": "泰国 VAT 每月申报截止日是几号？逾期会怎么处罚？",
            "answer_text": _qa_answer(
                regulation_base="泰国VAT月度申报；泰国税务局第 3/2569 号部长命令",
                core_rules="自 2026 年 8 月起，P.P.30 申报截止日为每月 17 日；e-Filing 电子申报可再延后 8 个自然日至当月 25 日。",
                suggestion="建议提前 3 天提交并避开每月月中系统高峰。国庆假期期间提前计划。",
                warning="未按时申报每张表 500 泰铢固定罚金；未足额缴纳按 1.5%/月计息，情节严重者应缴税额 1–2 倍罚款。",
                operation_guide="e-Filing 系统 → 上传 P.P.30 → 核对进销项 → 完成扣款。",
                link="https://efiling.rd.go.th/",
            ),
            "recall_doc_ids": ["泰国VAT月度申报"],
            "create_time": _iso(3),
        },
        {
            "query_text": "Shopee 泰国站的进项税抵扣有哪些条件？",
            "answer_text": _qa_answer(
                regulation_base="泰国VAT注册门槛；泰国税法典第 82/3 条",
                core_rules="VAT 登记纳税人可就采购商品或服务的进项税进行抵扣，前提是：1) 已开具符合泰国税法规定的 e-Tax Invoice；2) 用途与经营业务相关；3) 于开票次月内申报抵扣。",
                suggestion="建议 ERP/店铺后台按月归集全部进项发票，避免逾期未抵扣。",
                warning="逾期 6 个月以上的进项税发票不再允许抵扣。",
                operation_guide="P.P.30 表格填报进项部分 → 附上 e-Tax Invoice 号 → 系统自动校验。",
                link="https://etax.rd.go.th/",
            ),
            "recall_doc_ids": ["泰国VAT月度申报"],
            "create_time": _iso_h(1, 5),
        },
        {
            "query_text": "泰国 TikTok Shop 直播主，个人所得税怎么算？",
            "answer_text": _qa_answer(
                regulation_base="TikTokShop泰国站合规；泰国税法典第 40 条第 8 项",
                core_rules="直播主收入按劳务报酬计征个人所得税，累进税率 0–35%。年综合所得 ≥ 15 万 THB 起 5% 起征；平台在结算时按 3% 预扣，年终多退少补。",
                suggestion="建议直播主保留结算流水、平台预扣凭证；如年度所得较低可申请退税。",
                warning="未申报的直播主收入被稽核后按缺税额 1–2 倍罚款。",
                operation_guide="次年 3 月底前通过 e-Filing 提交 P.N.D.90/91 → 附平台预扣凭证 → 完成汇算。",
                link="https://www.rd.go.th/",
            ),
            "recall_doc_ids": ["TikTokShop泰国站合规"],
            "create_time": _iso_h(0, 6),
        },
    ],
    "brand_id_vn": [
        {
            "query_text": "印尼取消 3 美元以下免税后，DTC 独立站怎么合规？",
            "answer_text": _qa_answer(
                regulation_base="印尼PMK-131跨境电商；印尼财政部 PMK-131/2026 号部长条例",
                core_rules="所有跨境电商包裹按 11% 征收 VAT（PPN），持牌平台代扣代缴。独立站品牌方须在印尼注册 NPWP 与 PPN 号，并按月提交 SPT Masa PPN。",
                suggestion="尽快通过印尼本地财税服务商完成 NPWP + PPN 注册；同时评估定价策略避免 11% 税负打压转化。",
                warning="未合规包裹将被扣押并处货值 50–100% 罚款。品牌若无本地实体亦承担义务。",
                operation_guide="1) 选定本地代理机构；2) 准备公司注册文件；3) 提交 NPWP + PPN 申请；4) 部署月度申报流程。",
                link="https://www.pajak.go.id/",
            ),
            "recall_doc_ids": ["印尼PMK-131跨境电商"],
            "create_time": _iso(30),
        },
        {
            "query_text": "越南 2026 Q3 电子发票新规覆盖 DTC 品牌吗？",
            "answer_text": _qa_answer(
                regulation_base="越南电子发票新规；越南 78/2026/TT-BTC 号通知",
                core_rules="自 2026 年 9 月 1 日起，所有面向越南个人消费者的境内外 B2C 电商（含独立站）均须开具电子发票。认证服务商为 Viettel、VNPT、FPT 等 8 家。",
                suggestion="尽早与本地财税服务商对接完成系统接入，测试与自有 ERP/独立站订单系统的稳定性。",
                warning="漏开或伪造电子发票，每张按 400,000–800,000 越南盾罚款；年内累计超 100 张列入税务黑名单。",
                operation_guide="1) 选择服务商（Viettel 推荐）；2) 提交注册资料；3) 完成 API 对接；4) 联调订单开票。",
                link="https://www.gdt.gov.vn/",
            ),
            "recall_doc_ids": ["越南电子发票新规"],
            "create_time": _iso(17),
        },
        {
            "query_text": "越南跨境退税门槛从 300 提高到 500 美元，具体如何操作？",
            "answer_text": _qa_answer(
                regulation_base="越南跨境退税调整；越南 65/2026/QD-BTC 号决定",
                core_rules="500 美元以下小额包裹由平台代扣代缴 10% VAT，免逐票发票原件；退货退税走平台简易通道，最长 15 个工作日处理。",
                suggestion="按 SKU 分档规划：500 美元以下走平台通道；500 美元以上按原流程处理。",
                warning="需与平台确认代扣税率与结算周期，避免财务对账时出现税额差异。",
                operation_guide="1) 与平台确认代扣覆盖；2) 建立 SKU 分档规则；3) 更新独立站开票与退款流程。",
                link="https://www.gdt.gov.vn/",
            ),
            "recall_doc_ids": ["越南跨境退税调整"],
            "create_time": _iso(11),
        },
        {
            "query_text": "印尼进口环节 PPh 22 预扣税怎么算？有 API 号能省多少？",
            "answer_text": _qa_answer(
                regulation_base="印尼PPh22预扣税；印尼税务总局 SE-33/PJ/2026 号通函",
                core_rules="计税基数 = CIF + 关税 + 已代扣 VAT；持 API 号税率 2.5%，未持 API 税率 7.5%。清关时由海关代收；可作为企业所得税汇算时预付税款抵扣。",
                suggestion="建议尽早申请 API 号，节省 5 个百分点税负；同时理顺关税、VAT、PPh 22 的现金流管理。",
                warning="未持 API 长期以 7.5% 缴纳，1000 万美元规模每年多缴约 50 万美元。",
                operation_guide="1) 通过 OSS 平台申请 API 号；2) 提交贸易资料与担保；3) 完成审批后在海关系统备案。",
                link="https://www.pajak.go.id/",
            ),
            "recall_doc_ids": ["印尼PPh22预扣税"],
            "create_time": _iso(5),
        },
        {
            "query_text": "越南本地 DTC 独立站怎么开发票给企业客户？",
            "answer_text": _qa_answer(
                regulation_base="越南电子发票新规；78/2026/TT-BTC",
                core_rules="B2B 电子发票需包含买方增值税号（MST）、双方公司信息与商品明细；开票后 T+1 上传至越南税务总局系统备案。",
                suggestion="使用 Viettel/VNPT 服务商 API 与独立站订单系统对接，自动生成合规发票。",
                warning="漏开或伪造电子发票，每张按 400,000–800,000 VND 罚款；累计超 100 张列入税务黑名单。",
                operation_guide="独立站订单完成 → 触发开票 API → 服务商生成 e-Invoice → T+1 上传备案。",
                link="https://www.gdt.gov.vn/",
            ),
            "recall_doc_ids": ["越南电子发票新规"],
            "create_time": _iso(2),
        },
        {
            "query_text": "印尼 PMK-131 生效后小卖家能用平台代扣代缴解决吗？",
            "answer_text": _qa_answer(
                regulation_base="印尼PMK-131跨境电商；PMK-131/2026",
                core_rules="持牌跨境平台（Tokopedia、Shopee ID、TikTok Shop ID）已实现平台代扣代缴。独立站或未持牌平台仍需卖家自行注册 NPWP + PPN 号并按月申报。",
                suggestion="小卖家优先使用持牌平台；独立站品牌方尽快完成本地注册避免包裹扣押。",
                warning="非平台内订单仍属卖家自行合规范围，被稽核时不能以'平台代扣'免责。",
                operation_guide="通过 OSS 一体化系统申请 NPWP → PPN → 月度 SPT Masa PPN 申报。",
                link="https://www.pajak.go.id/",
            ),
            "recall_doc_ids": ["印尼PMK-131跨境电商"],
            "create_time": _iso_h(0, 8),
        },
    ],
    "trade_multi": [
        {
            "query_text": "海关总署综合外贸服务企业出口退税周期 5 天新政怎么申请？",
            "answer_text": _qa_answer(
                regulation_base="综合外贸退税加速；署税发〔2026〕41 号",
                core_rules="适用于备案的一类、二类综合外贸服务企业，退税审核周期由 15 个工作日压缩至 5 个工作日。加强对涉税异常样本的抽查。",
                suggestion="加快电子底账与自有 ERP 的直连接口对接；同时完善内控与凭证留存以应对抽查。",
                warning="虚开发票、虚假报关将被重点稽查。",
                operation_guide="1) 完成海关企业分类备案；2) 对接电子底账 API；3) 定期自查异常样本。",
                link="http://www.customs.gov.cn/",
            ),
            "recall_doc_ids": ["综合外贸退税加速"],
            "create_time": _iso(28),
        },
        {
            "query_text": "马来西亚 SST 门槛拟下调至 30 万令吉，影响外贸综合服务哪些业务？",
            "answer_text": _qa_answer(
                regulation_base="马来SST门槛下调；马来西亚财政部 2027 年度预算公开咨询稿",
                core_rules="拟将 SST 服务税注册门槛由 50 万令吉/年下调至 30 万令吉/年，2027 年 1 月 1 日起生效。",
                suggestion="立即评估营收介于 30–50 万令吉的马来主体，提前准备登记、开票、申报流程过渡方案。",
                warning="草案通过后未注册者将面临补缴税款+罚款。行业协会建议在咨询期反馈。",
                operation_guide="1) 梳理马来主体近 12 个月营收；2) 判断是否达标；3) 联系本地代理准备 SST-02 登记。",
                link="https://www.mof.gov.my/",
            ),
            "recall_doc_ids": ["马来SST门槛下调"],
            "create_time": _iso(14),
        },
        {
            "query_text": "新加坡 GST 会再涨吗？OVR 门槛还是 100 万新元吗？",
            "answer_text": _qa_answer(
                regulation_base="新加坡GST维持9%；新加坡财政部长 2026 年 7 月国会答复",
                core_rules="GST 维持 9%，2027 年不再上调。OVR 门槛为全球营收 ≥ 100 万新元 且 新加坡销售 ≥ 10 万新元。",
                suggestion="通过 IRAS 简化通道 30 分钟完成 OVR 注册；即使当期无销售也须按季度提交 GST F5 零申报。",
                warning="未注册者一旦被 IRAS 稽核，将追缴税款+罚款，最高可达应缴税额 2 倍。",
                operation_guide="myTax Portal → OVR 简化注册 → 提交公司证书、护照、业务说明 → 生成 GST 号。",
                link="https://www.iras.gov.sg/",
            ),
            "recall_doc_ids": ["新加坡GST维持9%"],
            "create_time": _iso(6),
        },
        {
            "query_text": "菲律宾数字服务税生效后代理外贸的企业还能免税吗？",
            "answer_text": _qa_answer(
                regulation_base="菲律宾数字服务税；RA 11976 修正案 / RR 3-2026",
                core_rules="RA 11976 后境外数字服务提供商年菲律宾销售 ≥ 300 万比索须注册 VAT（12%）。外贸综合服务企业若仅提供物流/清关而不涉及数字化交付，暂不属于征收范围。",
                suggestion="梳理服务产品结构，区分'数字化交付'与'传统外贸物流'，前者需评估注册义务。",
                warning="服务边界模糊被稽核时按数字服务补缴 12% VAT + 25–50% 罚款。",
                operation_guide="1) 服务产品分类清单；2) 与菲当地代理确认属地判定；3) 达门槛后通过 BIR portal 注册。",
                link="https://www.bir.gov.ph/",
            ),
            "recall_doc_ids": ["菲律宾数字服务税"],
            "create_time": _iso(4),
        },
        {
            "query_text": "东南亚多国转让定价文档同步准备的最佳实践？",
            "answer_text": _qa_answer(
                regulation_base="OECD BEPS Action 13；泰国 TP-Disclosure Form；越南 132/2020/ND-CP",
                core_rules="东南亚主要国家（TH/VN/ID/MY/SG/PH）均要求年营收 ≥ 2 亿本币的关联交易主体准备 TP 三层文档（主文档 Master File / 本地文档 Local File / 国别报告 CbCR）。",
                suggestion="集团层面统一编写 Master File；各主体 Local File 按当地要求本地化；使用统一比对基准数据库如 TP Catalyst。",
                warning="不合规的 TP 文档可能触发反避税调整，追溯 5–7 年。",
                operation_guide="1) Master File 集团编写；2) 各国 Local File 本地化；3) 年度 CbCR 集团总部报送。",
                link="https://www.oecd.org/tax/beps/",
            ),
            "recall_doc_ids": ["综合外贸退税加速"],
            "create_time": _iso_h(0, 4),
        },
    ],
    "newbie_blank": [
        {
            "query_text": "刚开始做跨境电商，需要先注册哪些税号？流程是什么？",
            "answer_text": _qa_answer(
                regulation_base="跨境电商合规入门；海关总署 2018 年第 194 号公告",
                core_rules="跨境电商出口新手至少完成三项登记：1) 海关企业注册（获取 10 位注册代码）；2) 电子口岸 IC 卡办理；3) 外汇管理局名录登记（境内主体）。目标市场若为泰国、越南、印尼等，还需按当地门槛注册 VAT/PPN。",
                suggestion="建议先跑通国内出口环节，再按目标国销售规模决定当地注册顺序（TH > VN > ID > MY 优先级）。",
                warning="未完成海关注册出口报关将被拒；未办理外汇登记则收汇困难。",
                operation_guide="1) 单一窗口 → 企业注册 → 提交营业执照；2) 电子口岸办理 IC 卡；3) 外管局名录登记。",
                link="https://www.singlewindow.cn/",
            ),
            "recall_doc_ids": ["综合外贸退税加速"],
            "create_time": _iso_h(2, 4),
        },
        {
            "query_text": "月销售 10 万，泰国和越南哪个更划算？",
            "answer_text": _qa_answer(
                regulation_base="泰国VAT注册门槛；越南电子发票新规",
                core_rules="月销 10 万人民币约合泰铢 50 万或越南盾 3.5 亿。泰国 VAT 门槛年 180 万 THB，月均 15 万 THB，暂不触发注册；越南 78/2026 电子发票起点更低，B2C 从 2026-09-01 起须开票。",
                suggestion="按合规成本排序：泰国 <= 越南。建议从泰国先试水，跑通订单再扩越南。",
                warning="即使未达门槛，Shopee/TikTok 平台可能仍要求上传税号，评估平台侧规则。",
                operation_guide="1) 优先申请泰国 Shopee/Lazada 店铺；2) 达门槛后 30 日内办理 VAT；3) 扩越南时提前部署电子发票。",
                link="https://seller-th.tiktok.com/",
            ),
            "recall_doc_ids": ["泰国VAT注册门槛"],
            "create_time": _iso_h(0, 3),
        },
    ],
    "default": [
        {
            "query_text": "跨境电商代扣代缴是什么意思？平台会替我交税吗？",
            "answer_text": _qa_answer(
                regulation_base="TikTokShop泰国站合规；印尼PMK-131跨境电商",
                core_rules="代扣代缴（Withholding）指电商平台在结算给卖家前直接扣留应缴税款并代交税务机关。目前泰国 TikTok Shop、印尼各持牌跨境平台均已实施该机制。",
                suggestion="卖家仍须完成本国 VAT 注册获取税号并上传平台，否则可能被暂停结算或降权。",
                warning="平台代扣代缴不等于卖家自身合规义务免除，仍须按月申报。",
                operation_guide="Seller Center → Tax Settings 上传税号 → 平台扣税后开出正规凭证 → 月度申报时抵扣。",
                link="https://etax.rd.go.th/",
            ),
            "recall_doc_ids": ["TikTokShop泰国站合规"],
            "create_time": _iso_h(4, 6),
        },
        {
            "query_text": "东南亚各国 VAT/GST 税率一览？",
            "answer_text": _qa_answer(
                regulation_base="泰国VAT注册门槛；新加坡GST维持9%；印尼PMK-131跨境电商",
                core_rules="截至 2026 年主要东南亚税率：泰国 VAT 7%（延续至 2027-09-30）；越南 VAT 10%；印尼 PPN 11%；马来 SST 6%（服务）/10%（销售）；新加坡 GST 9%；菲律宾 VAT 12%。",
                suggestion="做多国经营时按税率排序：SG(9) < TH(7) < MY(6-10) < VN(10) < ID(11) < PH(12)，可用于定价策略参考。",
                warning="部分国家有低价值商品豁免（越南 500 USD、印尼 3 USD 已取消），需实时跟踪政策。",
                operation_guide="按月监控目标市场政策变化；使用推送订阅本工具实时政策更新。",
                link="",
            ),
            "recall_doc_ids": ["新加坡GST维持9%", "印尼PMK-131跨境电商"],
            "create_time": _iso_h(1, 2),
        },
    ],
}


SEED_AUDIT_HISTORY: dict[str, list[dict]] = {
    "ecom_th": [
        {
            "create_time": _iso(20),
            "business_info": {
                "business_type": "跨境电商零售",
                "selected_countries": ["TH"],
                "target_market": "泰国",
                "annual_sales": 2_000_000,
                "platforms": ["Shopee", "TikTok Shop"],
            },
            "audit_report": {
                "overall_summary": "泰国站销售已达 200 万 THB，超过 180 万 VAT 注册门槛，须尽快完成注册并按月申报。",
                "all_risks": [
                    {
                        "risk_level": "高风险",
                        "risk_desc": "已超过 VAT 注册门槛但尚未注册",
                        "description": "年销售额 200 万泰铢已达门槛，未办理 VAT 注册",
                        "risk_point": "泰国 VAT 注册",
                        "trigger_condition": "年销售额 > 180 万 THB",
                        "regulation_base": "泰国VAT注册门槛；泰国税法典第 82/1 条",
                        "violation_consequence": "追缴税款 + 1.5%/月滞纳金 + 最高 2 倍罚款",
                    },
                    {
                        "risk_level": "中风险",
                        "risk_desc": "未接入 e-Tax Invoice",
                        "description": "小型商户须在 2026 年 12 月 31 日前完成电子发票对接",
                        "risk_point": "电子发票",
                        "trigger_condition": "VAT 登记纳税人",
                        "regulation_base": "泰国电子发票e-TaxInvoice；泰国税务局 e-Tax Invoice 2.0 指引",
                        "violation_consequence": "暂停 P.P.30 电子申报权限",
                    },
                ],
                "all_suggestions": [
                    {"content": "30 日内提交 P.P.01 完成 VAT 注册", "source_info": {"country_code": "TH"}},
                    {"content": "选定 PEPPOL 兼容 e-Tax Invoice 服务商", "source_info": {"country_code": "TH"}},
                ],
            },
        },
        {
            "create_time": _iso(7),
            "business_info": {
                "business_type": "跨境电商零售",
                "selected_countries": ["TH"],
                "target_market": "泰国",
                "annual_sales": 2_400_000,
                "platforms": ["Shopee", "TikTok Shop", "Lazada"],
            },
            "audit_report": {
                "overall_summary": "多平台运营扩大后续风险面。已完成 VAT 注册，须优化申报与直播主个税代扣流程。",
                "all_risks": [
                    {
                        "risk_level": "中风险",
                        "risk_desc": "直播主个税代扣未落地",
                        "description": "3 名合作主播月度分成合计 15 万 THB，未按 3% 预扣",
                        "risk_point": "泰国个人所得税",
                        "trigger_condition": "合作主播月收入 > 1.5 万 THB",
                        "regulation_base": "TikTokShop泰国站合规；泰国税法典第 40 条",
                        "violation_consequence": "被稽核后按缺税额 1–2 倍罚款",
                    },
                    {
                        "risk_level": "低风险",
                        "risk_desc": "进项税抵扣归集不完整",
                        "description": "部分小额采购未上传 e-Tax Invoice",
                        "risk_point": "进项税抵扣",
                        "trigger_condition": "有 VAT 登记且发生进项",
                        "regulation_base": "泰国VAT月度申报",
                        "violation_consequence": "多缴 VAT，逾期 6 个月不可抵扣",
                    },
                ],
                "all_suggestions": [
                    {"content": "为合作主播部署 3% 预扣代缴流程", "source_info": {"country_code": "TH"}},
                    {"content": "月度归集全部进项 e-Tax Invoice 用于抵扣", "source_info": {"country_code": "TH"}},
                ],
            },
        },
        {
            "create_time": _iso_h(0, 5),
            "business_info": {
                "business_type": "跨境电商零售",
                "selected_countries": ["TH"],
                "target_market": "泰国",
                "annual_sales": 2_600_000,
                "platforms": ["TikTok Shop"],
            },
            "audit_report": {
                "overall_summary": "TikTok Shop 单平台深耕，重点关注 6-15 后平台绑定 VAT 及 e-Tax Invoice 义务落地。",
                "all_risks": [
                    {
                        "risk_level": "高风险",
                        "risk_desc": "平台 VAT 绑定截止日临近",
                        "description": "6-15 后未绑定，For You 曝光下调 80%",
                        "risk_point": "TikTok Shop VAT 绑定",
                        "trigger_condition": "TikTok Shop 泰国站销售",
                        "regulation_base": "TikTokShop泰国站合规；TikTok Shop 卖家公告 2026-05-20",
                        "violation_consequence": "流量下调 + 严重时暂停开播",
                    },
                ],
                "all_suggestions": [
                    {"content": "本周内在 Seller Center → Tax Settings 上传 VAT 证书", "source_info": {"country_code": "TH"}},
                    {"content": "选定 e-Tax Invoice 服务商完成对接", "source_info": {"country_code": "TH"}},
                ],
            },
        },
    ],
    "brand_id_vn": [
        {
            "create_time": _iso(25),
            "business_info": {
                "business_type": "品牌出海直营",
                "selected_countries": ["ID", "VN"],
                "target_market": "印尼 + 越南",
                "annual_sales": 3_500_000,
                "platforms": ["独立站"],
            },
            "audit_report": {
                "overall_summary": "印尼、越南两地 DTC 独立站均已达 VAT/PPN 门槛，且需应对印尼 PMK-131 与越南电子发票新规。",
                "all_risks": [
                    {
                        "risk_level": "高风险",
                        "risk_desc": "印尼未注册 PPN 号",
                        "description": "PMK-131 生效后，独立站须持有印尼 PPN 号方可清关",
                        "risk_point": "印尼 PPN 注册",
                        "trigger_condition": "跨境电商包裹入印尼",
                        "regulation_base": "印尼PMK-131跨境电商；PMK-131/2026",
                        "violation_consequence": "包裹扣押 + 货值 50–100% 罚款",
                    },
                    {
                        "risk_level": "中风险",
                        "risk_desc": "越南电子发票尚未部署",
                        "description": "2026-09-01 起 B2C 强制电子发票",
                        "risk_point": "越南电子发票",
                        "trigger_condition": "面向越南个人消费者销售",
                        "regulation_base": "越南电子发票新规；78/2026/TT-BTC",
                        "violation_consequence": "每张 40 万–80 万越南盾罚款",
                    },
                ],
                "all_suggestions": [
                    {"content": "启动印尼 NPWP + PPN 注册流程", "source_info": {"country_code": "ID"}},
                    {"content": "与 Viettel 或 VNPT 对接电子发票 API", "source_info": {"country_code": "VN"}},
                ],
            },
        },
        {
            "create_time": _iso(8),
            "business_info": {
                "business_type": "品牌出海直营",
                "selected_countries": ["VN"],
                "target_market": "越南",
                "annual_sales": 1_800_000,
                "platforms": ["独立站", "TikTok Shop"],
            },
            "audit_report": {
                "overall_summary": "越南主体重点关注跨境退税门槛提升至 500 美元后的 SKU 分档策略。",
                "all_risks": [
                    {
                        "risk_level": "低风险",
                        "risk_desc": "退税 SKU 分档策略缺失",
                        "description": "高单价 SKU 仍按逐票原流程处理",
                        "risk_point": "退税",
                        "trigger_condition": "SKU 单价 > 500 USD",
                        "regulation_base": "越南跨境退税调整；65/2026/QD-BTC",
                        "violation_consequence": "现金流回款延后",
                    },
                ],
                "all_suggestions": [
                    {"content": "按 SKU 分档更新开票与退款流程", "source_info": {"country_code": "VN"}},
                ],
            },
        },
        {
            "create_time": _iso(3),
            "business_info": {
                "business_type": "品牌出海直营",
                "selected_countries": ["ID"],
                "target_market": "印尼",
                "annual_sales": 2_100_000,
                "platforms": ["独立站"],
            },
            "audit_report": {
                "overall_summary": "印尼独立站已完成 NPWP + PPN 注册。API 号申请是本期主要合规优化项。",
                "all_risks": [
                    {
                        "risk_level": "中风险",
                        "risk_desc": "未持 API 号导致 PPh 22 税率偏高",
                        "description": "当前按 7.5% 缴纳，持 API 后降至 2.5%",
                        "risk_point": "印尼 PPh 22 预扣税",
                        "trigger_condition": "进口清关",
                        "regulation_base": "印尼PPh22预扣税；SE-33/PJ/2026",
                        "violation_consequence": "长期多缴 5 个百分点，现金流承压",
                    },
                ],
                "all_suggestions": [
                    {"content": "通过 OSS 平台申请 API 号，预计 2 个月内下证", "source_info": {"country_code": "ID"}},
                    {"content": "同步梳理 CIF/关税/PPN/PPh 22 现金流管理", "source_info": {"country_code": "ID"}},
                ],
            },
        },
    ],
    "trade_multi": [
        {
            "create_time": _iso(30),
            "business_info": {
                "business_type": "外贸综合服务",
                "selected_countries": ["TH", "MY", "SG", "PH"],
                "target_market": "东南亚多国",
                "annual_sales": 12_000_000,
                "platforms": [],
            },
            "audit_report": {
                "overall_summary": "多国代理业务，重点关注马来 SST 门槛下调、菲律宾 DST 生效与新加坡 GST 稳定。",
                "all_risks": [
                    {
                        "risk_level": "中风险",
                        "risk_desc": "马来主体可能被纳入 SST 征收范围",
                        "description": "现营收 40 万令吉，处于新门槛 30 万临界线上",
                        "risk_point": "马来 SST",
                        "trigger_condition": "年营收 ≥ 30 万令吉（拟）",
                        "regulation_base": "马来SST门槛下调；马来财政部 2027 预算稿",
                        "violation_consequence": "补缴税款 + 罚款",
                    },
                    {
                        "risk_level": "中风险",
                        "risk_desc": "菲律宾 DST 生效后未评估合规义务",
                        "description": "如果向菲提供数字化外贸服务，可能触发 12% VAT 义务",
                        "risk_point": "菲律宾 DST",
                        "trigger_condition": "年菲律宾营收 ≥ 300 万比索",
                        "regulation_base": "菲律宾数字服务税；RA 11976 修正案 / RR 3-2026",
                        "violation_consequence": "追缴 + 25–50% 罚款",
                    },
                ],
                "all_suggestions": [
                    {"content": "梳理马来主体近 12 个月营收，评估 SST 登记必要性", "source_info": {"country_code": "MY"}},
                    {"content": "对菲律宾数字化服务收入做属地判定", "source_info": {"country_code": "PH"}},
                    {"content": "复用海关总署综合外贸企业退税加速通道", "source_info": {"country_code": "CN"}},
                ],
            },
        },
        {
            "create_time": _iso(12),
            "business_info": {
                "business_type": "外贸综合服务",
                "selected_countries": ["SG"],
                "target_market": "新加坡",
                "annual_sales": 900_000,
                "platforms": [],
            },
            "audit_report": {
                "overall_summary": "新加坡主体年销售 90 万新元，OVR 门槛 100 万新元，暂无强制注册义务但接近门槛。",
                "all_risks": [
                    {
                        "risk_level": "低风险",
                        "risk_desc": "接近 OVR 门槛未部署监控",
                        "description": "年销售距 100 万新元 OVR 门槛仅差 10 万",
                        "risk_point": "新加坡 GST OVR",
                        "trigger_condition": "全球营收 ≥ 100 万新元 且 SG 销售 ≥ 10 万",
                        "regulation_base": "新加坡GST维持9%；新加坡 GST 法 OVR 条款",
                        "violation_consequence": "触发门槛未及时注册将被追缴",
                    },
                ],
                "all_suggestions": [
                    {"content": "月度监控 SG 销售数据，接近门槛时提前启动 OVR 注册", "source_info": {"country_code": "SG"}},
                ],
            },
        },
        {
            "create_time": _iso(4),
            "business_info": {
                "business_type": "外贸综合服务",
                "selected_countries": ["CN", "MY", "TH"],
                "target_market": "中国 + 马来 + 泰国",
                "annual_sales": 8_500_000,
                "platforms": [],
            },
            "audit_report": {
                "overall_summary": "综合外贸出口业务，重点关注 5 天退税加速政策申报流程与马来 SST 门槛下调影响。",
                "all_risks": [
                    {
                        "risk_level": "高风险",
                        "risk_desc": "电子底账未与 ERP 直连",
                        "description": "现仍手工录入，无法用满 5 天退税加速通道",
                        "risk_point": "综合外贸退税",
                        "trigger_condition": "备案为二类以上综合外贸企业",
                        "regulation_base": "综合外贸退税加速；署税发〔2026〕41 号",
                        "violation_consequence": "退税周期延后至 15 个工作日；现金流拉长",
                    },
                    {
                        "risk_level": "低风险",
                        "risk_desc": "马来 SST 门槛变化跟踪",
                        "description": "马来主体临近 30 万令吉新门槛",
                        "risk_point": "马来 SST 门槛",
                        "trigger_condition": "年营收 ≥ 30 万令吉（拟）",
                        "regulation_base": "马来SST门槛下调",
                        "violation_consequence": "达门槛后未登记 → 补缴 + 罚款",
                    },
                ],
                "all_suggestions": [
                    {"content": "启动电子底账 API 直连改造项目", "source_info": {"country_code": "CN"}},
                    {"content": "预备马来 SST-02 登记材料", "source_info": {"country_code": "MY"}},
                ],
            },
        },
    ],
    "newbie_blank": [
        {
            "create_time": _iso(1),
            "business_info": {
                "business_type": "跨境电商零售",
                "selected_countries": ["TH"],
                "target_market": "泰国试水",
                "annual_sales": 600_000,
                "platforms": ["Shopee"],
            },
            "audit_report": {
                "overall_summary": "新手泰国试水，年销售 60 万 THB 尚未达 VAT 门槛，重点关注平台侧税务合规。",
                "all_risks": [
                    {
                        "risk_level": "低风险",
                        "risk_desc": "尚未达 VAT 注册门槛",
                        "description": "距离 180 万 THB 门槛仍有 120 万空间",
                        "risk_point": "泰国 VAT 门槛监控",
                        "trigger_condition": "年销售额 > 180 万 THB",
                        "regulation_base": "泰国VAT注册门槛",
                        "violation_consequence": "达门槛未注册 → 追缴 + 罚款",
                    },
                ],
                "all_suggestions": [
                    {"content": "月度监控销售数据，达 150 万 THB 时启动 VAT 注册准备", "source_info": {"country_code": "TH"}},
                    {"content": "在 Shopee 后台预留税号上传入口", "source_info": {"country_code": "TH"}},
                ],
            },
        },
    ],
    "default": [
        {
            "create_time": _iso(2),
            "business_info": {
                "business_type": "跨境电商零售",
                "selected_countries": ["TH", "VN"],
                "target_market": "东南亚双市场",
                "annual_sales": 1_500_000,
                "platforms": ["TikTok Shop", "Shopee"],
            },
            "audit_report": {
                "overall_summary": "泰国 + 越南双市场，均接近或已达 VAT 门槛，须尽快启动合规注册。",
                "all_risks": [
                    {
                        "risk_level": "中风险",
                        "risk_desc": "越南 B2C 电子发票尚未接入",
                        "description": "2026-09-01 起须开电子发票",
                        "risk_point": "越南电子发票",
                        "trigger_condition": "面向越南 C 端销售",
                        "regulation_base": "越南电子发票新规",
                        "violation_consequence": "每张 40 万–80 万 VND 罚款",
                    },
                    {
                        "risk_level": "低风险",
                        "risk_desc": "泰国接近 VAT 门槛",
                        "description": "泰国主体年销售约 90 万 THB，距门槛 50%",
                        "risk_point": "泰国 VAT 门槛",
                        "trigger_condition": "年销售额 > 180 万 THB",
                        "regulation_base": "泰国VAT注册门槛",
                        "violation_consequence": "达门槛未注册的处罚",
                    },
                ],
                "all_suggestions": [
                    {"content": "与 Viettel 对接电子发票 API", "source_info": {"country_code": "VN"}},
                    {"content": "月度监控泰国销售数据", "source_info": {"country_code": "TH"}},
                ],
            },
        },
    ],
}


def seed_profiles_and_news(force: bool = False) -> None:
    """
    - profile：若 profile 当前没有任何 profile_tags 记录，则写入 base_tags；否则保留用户历史累积。
    - news：仅在新闻表为空时插入。
    - qa/audit 历史：仅在对应 profile 名下无任何历史时插入。
    """
    from tax_compliance_radar.services.db import list_profile_tags

    for p in SEED_PROFILES:
        upsert_profile(
            profile_id=p["profile_id"],
            display_name=p["display_name"],
            business_type=p["business_type"],
            description=p["description"],
            base_tags=list((p.get("base_tags") or {}).keys()),
        )
        base_tags = p.get("base_tags") or {}
        if base_tags and len(list_profile_tags(p["profile_id"])) == 0:
            upsert_profile_tags(p["profile_id"], base_tags, source="seed")

    if force or news_count() == 0:
        for n in SEED_NEWS:
            insert_news_item(
                title=n["title"],
                summary=n["summary"],
                body=n["body"],
                source=n["source"],
                publish_time=n["publish_time"],
                tags=n["tags"],
                original_link=n.get("original_link"),
            )

    _seed_qa_and_audit_history(force=force)


def _seed_qa_and_audit_history(force: bool = False) -> None:
    """为每个模拟画像插入检索与审核历史。若该 profile 已有历史则跳过；
    force=True 时先删除该 profile 的种子历史再重播，避免重复叠加。"""
    for profile_id, items in SEED_QA_HISTORY.items():
        if _profile_has_qa_history(profile_id):
            if not force:
                continue
            # force 模式：清空该 profile 现有 QA 历史，再重播种子
            with get_connection() as connection:
                connection.execute("DELETE FROM qa_history WHERE profile_id = ?", (profile_id,))
                connection.commit()
        for item in items:
            insert_qa_history(
                query_text=item["query_text"],
                answer_text=item["answer_text"],
                recall_doc_ids=item.get("recall_doc_ids") or [],
                recall_snippets=item.get("recall_snippets") or {},
                profile_id=profile_id,
                create_time=item.get("create_time"),
            )

    for profile_id, items in SEED_AUDIT_HISTORY.items():
        if _profile_has_audit_history(profile_id):
            if not force:
                continue
            with get_connection() as connection:
                connection.execute("DELETE FROM audit_history WHERE profile_id = ?", (profile_id,))
                connection.commit()
        for item in items:
            insert_audit_history(
                business_info=item["business_info"],
                audit_report=item["audit_report"],
                profile_id=profile_id,
                create_time=item.get("create_time"),
            )


def _profile_has_qa_history(profile_id: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM qa_history WHERE profile_id = ? LIMIT 1",
            (profile_id,),
        ).fetchone()
    return row is not None


def _profile_has_audit_history(profile_id: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM audit_history WHERE profile_id = ? LIMIT 1",
            (profile_id,),
        ).fetchone()
    return row is not None
