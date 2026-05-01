#!/usr/bin/env python3
"""配置检查脚本 - 验证LLM和Embedding配置是否正确"""

from dotenv import load_dotenv

load_dotenv()

from tax_compliance_radar.config import settings

print("=" * 70)
print("税务合规雷达 - 配置检查报告")
print("=" * 70)
print()

# LLM配置检查
print("📝 LLM 生成模型配置")
print("-" * 50)
print(f"  后端类型:     {settings.llm.source}")
print(f"  API 地址:     {settings.llm.base_url}")
print(f"  模型名称:     {settings.llm.model}")
print(f"  备选模型:     {settings.llm.fallback_models}")
print(f"  温度:         {settings.llm.generation_temperature}")
print(f"  最大Token:    {settings.llm.generation_num_predict}")
print(f"  API Key:      {'已配置' if settings.llm.api_key else '未配置'}")
print()

# Embedding配置检查
print("🔢 Embedding 向量模型配置")
print("-" * 50)
print(f"  后端类型:     {settings.embedding.source}")
print(f"  API 地址:     {settings.embedding.base_url}")
print(f"  模型名称:     {settings.embedding.model}")
print(f"  向量维度:     {settings.embedding.dimensions}")
print(f"  API Key:      {'已配置' if settings.embedding.api_key else '未配置'}")
print(f"  是否同源:     {'是' if settings.embedding.same_as_llm else '否'}")
print()

# 配置组合分析
print("🔍 配置组合分析")
print("-" * 50)

if settings.llm.source == "ollama" and settings.embedding.source == "ollama":
    print("  ✅ 组合类型: 纯本地模式 (本地Ollama LLM + 本地Ollama Embedding)")
    print("     优点: 数据全本地、隐私性好、无API调用费用")
    print("     注意: 需要本地运行Ollama服务并拉取对应模型")
elif settings.llm.source != "ollama" and settings.embedding.source == "ollama":
    print("  ⚙️  组合类型: 混合模式 (云端LLM + 本地Ollama Embedding)")
    print("     优点: LLM效果好、Embedding计算本地完成、成本低")
    print("     注意: 需要本地运行Ollama服务用于Embedding计算")
elif settings.llm.source != "ollama" and settings.embedding.source != "ollama":
    print("  ☁️  组合类型: 全云端模式 (云端LLM + 云端Embedding)")
    print("     优点: 无需本地算力、效果稳定、部署简单")
    print("     注意: 所有计算产生API调用费用")
else:
    print("  🤔 组合类型: 其他组合")
print()

# 完整性检查
print("✅ 配置完整性检查")
print("-" * 50)
issues = []

if settings.llm.source != "ollama" and not settings.llm.api_key:
    issues.append(f"  ❌ {settings.llm.source} 模式需要配置 LLM_API_KEY")
else:
    print(f"  ✅ LLM API配置正常")

if settings.embedding.source != "ollama" and not settings.embedding.api_key:
    issues.append(f"  ❌ {settings.embedding.source} Embedding模式需要配置 EMBEDDING_API_KEY")
else:
    print(f"  ✅ Embedding API配置正常")

print()

if issues:
    print("⚠️  发现以下配置问题:")
    for issue in issues:
        print(issue)
else:
    print("🎉 配置检查通过！")
    print()
    print("使用提示:")
    print("  1. 运行 `uv run python scripts/test_llm.py` 测试LLM调用")
    print("  2. 运行 `uv run python scripts/test_embeddings.py` 测试Embedding生成")
    print("  3. 运行 `bash scripts/start.sh` 启动后端服务")

print()
print("=" * 70)
