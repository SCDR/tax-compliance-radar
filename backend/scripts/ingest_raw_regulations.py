#!/usr/bin/env python3
"""
ingest_raw_regulations.py — 将原始 PDF/HTML 税务文档整理为知识库 markdown 文件。

自动发现 `东南亚税务政策来源/` 下的所有 PDF/HTML 文件：
  1. 提取文本（pypdf / HTML 解析）
  2. 通过火山引擎 LLM 生成中文合规摘要（含 YAML frontmatter）
  3. 写入 `_generated/` 目录（人工复核后移入主目录）

用法：
  cd backend && uv run python scripts/ingest_raw_regulations.py

筛选参数（可选）：
  --country th,id      只处理指定国家（目录名逗号分隔）
  --min-chars 2000     只处理文本长度 >= 2000 字符的文件
  --max-chars 30000    截断超长文本到该字符数
  --limit 3            只处理前 N 个文件（测试用）
"""

import argparse
import os
import re
import sys
from pathlib import Path

import dotenv
from openai import OpenAI

# 加载 .env 配置
dotenv.load_dotenv()

# 路径配置
BACKEND_DIR = Path(__file__).resolve().parent.parent
REGULATIONS_DIR = BACKEND_DIR / "data" / "regulations"
OUTPUT_DIR = REGULATIONS_DIR / "_generated"
SOURCE_DIR = REGULATIONS_DIR / "东南亚税务政策来源"

# LLM 配置
LLM_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-flash-260425")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))

# ---------- 文件名 → 元数据 映射规则 ----------

# 国家代码映射
COUNTRY_CODE = {
    "thailand": "th",
    "indonesia": "id",
    "vietnam": "vn",
    "malaysia": "my",
    "international": "intl",
}

# 文件名关键词 → category
CATEGORY_KEYWORDS = {
    "vat": "vat",
    "ppn": "vat",
    "value_added": "vat",
    "e_service": "vat",
    "pph": "withholding",
    "withholding": "withholding",
    "article23": "withholding",
    "article26": "withholding",
    "fct": "withholding",
    "circular103": "withholding",
    "cit": "corporate_tax",
    "corporate_income": "corporate_tax",
    "income_tax": "corporate_tax",
    "revenue": "vat",
    "pmk81": "vat",
    "pmk37": "withholding",
    "pmk51": "customs",
    "pmk172": "tp",
    "transfer_pricing": "tp",
    "tp_": "tp",
    "transfer": "tp",
    "registration": "registration",
    "reg": "registration",
    "dgt": "withholding",
    "einvoice": "einvoice",
    "einvoice": "einvoice",
    "invoice": "einvoice",
    "customs": "customs",
    "dta": "dta",
    "treaty": "dta",
    "tax_treaty": "dta",
    "permanent_establishment": "pe",
    "pe_": "pe",
    "digital": "vat",
    "marketplace": "withholding",
    "platform": "withholding",
    "foreign_company": "corporate_tax",
    "foreign_business": "registration",
    "foreign_trade": "customs",
    "taxpayer_status": "general",
    "corporate_index": "general",
    "spln": "general",
    "spdn": "general",
    "apa": "tp",
    "coretax": "general",
    "faq": "registration",
    "budget": "registration",
    "sst": "registration",
    "companies_act": "registration",
    "guide": "registration",
}

# 国家 → 发布机构
COUNTRY_ORG = {
    "thailand": "泰国税务局",
    "indonesia": "印尼财政部",
    "vietnam": "越南财政部",
    "malaysia": "马来西亚财政部",
    "international": "国际组织",
}

# 国家 → 官方链接前缀
COUNTRY_LINK = {
    "thailand": "https://www.rd.go.th/english/",
    "indonesia": "https://www.pajak.go.id/",
    "vietnam": "https://www.gdt.gov.vn/",
    "malaysia": "https://www.mof.gov.my/",
    "international": "",
}

# 国家 → 语言
COUNTRY_LANG = {
    "thailand": "en",
    "indonesia": "id",
    "vietnam": "en",
    "malaysia": "en",
    "international": "en",
}

# ---------- 文件发现 ----------


def discover_sources() -> list[dict]:
    """扫描源目录，返回所有待处理的文件信息。"""
    if not SOURCE_DIR.exists():
        print(f"❌ 源目录不存在: {SOURCE_DIR}")
        return []

    sources = []
    for country_dir in sorted(SOURCE_DIR.iterdir()):
        if not country_dir.is_dir() or country_dir.name.startswith("."):
            continue
        cc = COUNTRY_CODE.get(country_dir.name, "xx")
        for f in sorted(country_dir.iterdir()):
            if f.suffix.lower() not in (".pdf", ".html") or f.name.startswith("."):
                continue
            sources.append(_infer_metadata(f, country_dir.name, cc))
    return sources


def _infer_metadata(f: Path, country_name: str, cc: str) -> dict:
    """从文件名和目录名推断 metadata。"""
    stem = f.stem.replace(".en", "").replace("_mplaw", "")
    # 转成大写 doc_id
    doc_id = stem.upper().replace("-", "_").replace(" ", "_").replace(".", "_")
    # 去掉多余的下划线
    doc_id = re.sub(r"_+", "_", doc_id).strip("_")
    # 给 doc_id 加国家前缀（如果还没加）
    if not doc_id.startswith(cc.upper() + "_"):
        doc_id = f"{cc.upper()}_{doc_id}"

    # 判断 category
    category = "general"
    stem_lower = stem.lower()
    for kw, cat in CATEGORY_KEYWORDS.items():
        if kw in stem_lower:
            category = cat
            break

    # 输出文件名：序号在 main 循环中按批次顺序分配，此处用占位符
    slug = _make_slug(stem, cc)
    out_name = f"XX_{cc}_{slug}.md"

    return {
        "path": f,
        "country": country_name,
        "cc": cc,
        "doc_id": doc_id,
        "doc_name": "",
        "category": category,
        "publish_org": COUNTRY_ORG.get(country_name, "待补充"),
        "original_link": COUNTRY_LINK.get(country_name, "待补充"),
        "lang": COUNTRY_LANG.get(country_name, "en"),
        "out_name": out_name,
    }


def _next_seq_number() -> int:
    """计算 regulations 目录里下一个可用序号 + _generated 目录里已有的序号。"""
    existing = set()
    for d in [REGULATIONS_DIR, OUTPUT_DIR]:
        if d.exists():
            for m in d.glob("*.md"):
                m2 = m.name
                if re.match(r"^\d{2}_", m2):
                    existing.add(int(m2[:2]))
    # 也考虑 _generated 里的
    n = 29  # 当前已有 01-28
    while n in existing:
        n += 1
    return n


def _make_slug(stem: str, cc: str) -> str:
    """从文件名 stem 生成 slug。"""
    slug = stem.lower()
    # 去掉已知前缀
    for prefix in ["id_", "th_", "vn_", "my_", "sg_", "ph_", "cn_", "intl_",
                    "en_", "en-"]:
        if slug.startswith(prefix):
            slug = slug[len(prefix):]
            break
    # 替换非字母数字字符
    slug = re.sub(r"[^a-z0-9_]+", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:50]


# ---------- PDF / HTML 文本提取 ----------


def extract_text(f: Path) -> str:
    """从 PDF 或 HTML 文件提取文本。"""
    if f.suffix.lower() == ".pdf":
        return _extract_pdf(f)
    elif f.suffix.lower() == ".html":
        return _extract_html(f)
    return ""


def _extract_pdf(f: Path) -> str:
    """用 pypdf 提取文本。"""
    from pypdf import PdfReader
    reader = PdfReader(str(f))
    parts = []
    for page in reader.pages:
        t = page.extract_text() or ""
        if t.strip():
            parts.append(t)
    return "\n\n".join(parts)


def _extract_html(f: Path) -> str:
    """从 HTML 提取正文（去脚本/样式/导航）。"""
    content = f.read_text(encoding="utf-8", errors="replace")
    # 移除 script / style
    content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL)
    content = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.DOTALL)
    # 去标签
    text = re.sub(r"<[^>]+>", "\n", content)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 解码 HTML 实体
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    # 去空行
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    return "\n\n".join(lines)


# ---------- LLM 生成 ----------


def truncate_text(text: str, max_chars: int = 25000) -> str:
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_para = truncated.rfind("\n\n")
    if last_para > max_chars * 0.8:
        truncated = truncated[:last_para]
    return truncated + "\n\n[原文后续内容已截断]"


def build_prompt(raw_text: str, src_lang: str) -> str:
    raw_text = truncate_text(raw_text, max_chars=25000)
    return f"""你是一位专业的税务合规翻译与整理专家。请将以下{src_lang.upper()}税务原文整理成中文合规摘要。

## 输出要求

### 1. 输出结构
直接输出 markdown 文档，**不要**用 ```markdown 代码块包裹。输出内容必须包含以下两部分：

#### YAML frontmatter（文件头，用 --- 包裹）
```yaml
---
doc_id: <根据内容生成的唯一ID>
doc_name: <简明中文标题>
category: <vat / registration / withholding / corporate_tax / customs / tp / einvoice / cross_border / dta / general>
effective_date: <根据原文推断，格式 YYYY-MM-DD，不确定写 "待补充">
original_link: <官方来源链接，不确定写 "待补充">
publish_org: <发布机构名称，不确定写 "待补充">
---
```

#### 正文中文 Markdown（用 ## 分段）
- 一级标题 `# 中文标题 —— 英文标题`
- 引用来源：`> 来源：原文出处`

正文结构按以下分段组织：
- **一、适用范围**：适用主体、豁免情形
- **二、关键门槛与税率**：具体数字、税率、计算方式
- **三、申报时限与流程**：注册/申报时间线、所需表格
- **四、罚则与违规后果**：罚款金额、滞纳金比例、刑事责任
- **五、常见问答**：3-5 个高频问题与回答

### 2. 重要规则
- 保留所有原文中的数字、日期、法规编号、条款号
- 表格用 markdown 表格格式
- 每个段落用空行隔开
- 严禁编造原文中不存在的内容
- 如果某些信息原文未提供（如罚则），注明"原文未明确提供"而非编造

## 原文内容
```
{raw_text}
```
"""


def call_llm(prompt: str) -> str:
    client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=LLM_TEMPERATURE,
        max_tokens=4096,
    )
    return response.choices[0].message.content.strip()


# ---------- 输出解析 ----------


def parse_llm_output(content: str, meta: dict) -> str:
    """从 LLM 输出解析出最终 markdown，用预设 metadata 覆盖。"""
    # 去代码块包裹
    content = content.strip()
    for prefix in ["```markdown", "```yaml", "```"]:
        if content.startswith(prefix):
            content = content[len(prefix):].strip()
    if content.endswith("```"):
        content = content[:-3].strip()

    # 提取 YAML frontmatter
    fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    yaml_block = fm_match.group(1) if fm_match else ""
    content_without_fm = content[fm_match.end():].strip() if fm_match else content

    # 提取正文
    body_match = re.search(r"# .+", content_without_fm)
    body = content_without_fm[body_match.start():].strip() if body_match else content_without_fm.strip()

    # 从 LLM 的 frontmatter 提取有用信息
    doc_name = meta["doc_name"]
    effective_date = "待补充"
    category = meta["category"]

    if yaml_block:
        for line in yaml_block.splitlines():
            line = line.strip()
            if line.startswith("doc_name:"):
                v = line.split(":", 1)[1].strip().strip('"').strip("'")
                if v and v != "待补充":
                    doc_name = v
            elif line.startswith("effective_date:"):
                v = line.split(":", 1)[1].strip()
                if v and v != "待补充" and v != "N/A":
                    effective_date = v
            elif line.startswith("category:"):
                v = line.split(":", 1)[1].strip()
                if v and v != "待补充":
                    category = v

    # 用预设覆盖
    fm = f"""---
doc_id: {meta["doc_id"]}
doc_name: {doc_name}
category: {meta["category"]}
effective_date: {effective_date}
original_link: {meta["original_link"]}
publish_org: {meta["publish_org"]}
---"""

    return fm + "\n\n" + body


# ---------- 处理流程 ----------


def process_source(meta: dict) -> str | None:
    """处理单个源文件。"""
    src = meta["path"]
    out_name = meta["out_name"]
    print(f"\n{'='*60}")
    print(f"📄 {src.parent.name}/{src.name}")
    print(f"   → {out_name}  |  doc_id: {meta['doc_id']}")

    # 提取文本
    raw_text = extract_text(src).strip()
    if not raw_text:
        print(f"   ⚠️  文本提取为空，跳过")
        return None
    if len(raw_text) < 200:
        print(f"   ⚠️  文本太少 ({len(raw_text)} 字符)，可能是扫描件，跳过")
        return None

    print(f"   原文: {len(raw_text)} 字符")

    # LLM 生成
    print(f"   🧠 调用 LLM 生成摘要...")
    prompt = build_prompt(raw_text, meta["lang"])
    try:
        llm_output = call_llm(prompt)
    except Exception as e:
        print(f"   ❌ LLM 调用失败: {e}")
        return None

    print(f"   LLM 输出: {len(llm_output)} 字符")

    # 解析 + 写入
    final = parse_llm_output(llm_output, meta)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / out_name
    out_path.write_text(final, encoding="utf-8")
    print(f"   ✅ 已写入: {out_path}")
    return out_name


def main():
    parser = argparse.ArgumentParser(description="税务法规知识库导入工具")
    parser.add_argument("--country", help="只处理指定国家，逗号分隔（目录名: thailand,indonesia,...）")
    parser.add_argument("--min-chars", type=int, default=200, help="最少文本字符数（默认200）")
    parser.add_argument("--max-chars", type=int, default=25000, help="截断超长文本（默认25000）")
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 个文件（测试用，0=全部）")
    args = parser.parse_args()

    print("=" * 60)
    print("📚 税务法规知识库导入工具")
    print(f"   源目录: {SOURCE_DIR}")
    print(f"   输出目录: {OUTPUT_DIR}")
    print(f"   LLM: {LLM_MODEL} @ {LLM_BASE_URL}")
    print("=" * 60)

    # 发现所有源文件
    all_sources = discover_sources()
    print(f"\n🔍 发现 {len(all_sources)} 个源文件")

    # 按国家筛选
    if args.country:
        allowed = set(args.country.split(","))
        all_sources = [s for s in all_sources if s["cc"] in allowed]
        print(f"   --country={args.country}: 剩余 {len(all_sources)} 个")

    # 按 limit 截断
    if args.limit and args.limit > 0:
        all_sources = all_sources[:args.limit]
        print(f"   --limit={args.limit}: 只处理前 {len(all_sources)} 个")

    if not all_sources:
        print("⚠️  没有需要处理的文件")
        return

    # 按批次分配序号
    base_seq = _next_seq_number()
    results: list[tuple[str, str | None]] = []
    existing_out: set[str] = set()
    for i, meta in enumerate(all_sources):
        # 分配序号
        seq = base_seq + i
        meta["out_name"] = meta["out_name"].replace("XX", f"{seq:02d}")
        # 避免文件名冲突（同一批次内）
        while meta["out_name"] in existing_out:
            seq += 1
            meta["out_name"] = meta["out_name"].replace(f"{seq-1:02d}", f"{seq:02d}")
        existing_out.add(meta["out_name"])

        result = process_source(meta)
        results.append((meta["out_name"], result))
        print(f"   [{i+1}/{len(all_sources)}]")

    # 汇总
    print("\n" + "=" * 60)
    print("📋 处理汇总")
    print("=" * 60)
    success = 0
    for out_name, result in results:
        status = "✅" if result else "❌"
        print(f"  {status} {out_name}")
        if result:
            success += 1
    print(f"\n总计: {success}/{len(results)} 成功")

    # 写入复核清单
    review_path = OUTPUT_DIR / ".REVIEW_BEFORE_REBUILD.md"
    md = """# 待人工复核清单

以下文件由 LLM 自动生成，**请在运行 `rebuild_vector_store.sh` 前逐项复核**：

"""
    for out_name, result in results:
        if result:
            md += f"- [ ] {out_name}\n"
    md += """
复核要点：
- 数字、日期、税率准确
- 法规编号正确
- YAML frontmatter 完整
- 语义通顺，无遗漏

复核完成后运行：
```bash
cd backend && bash scripts/rebuild_vector_store.sh
```
"""
    review_path.write_text(md, encoding="utf-8")
    print(f"\n📝 待复核清单: {review_path}")

    print(f"\n💡 复核后运行:")
    print(f"   cd backend && bash scripts/rebuild_vector_store.sh")


if __name__ == "__main__":
    main()