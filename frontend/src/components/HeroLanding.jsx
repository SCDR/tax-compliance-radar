import { useEffect, useState } from 'react'
import { Button } from 'antd'
import {
  DashboardOutlined,
  NotificationOutlined,
  QuestionCircleOutlined,
  AuditOutlined,
  ArrowRightOutlined,
  ThunderboltOutlined,
  GlobalOutlined,
  SafetyCertificateOutlined,
  SafetyOutlined,
} from '@ant-design/icons'

import { fetchCountries, fetchQaHistory, fetchAuditHistory, fetchGuideHistory } from '../api/client'

/**
 * Hero 引导页 —— 项目首页。
 * 展示项目名 + slogan + 快速功能入口 + 关键数据。
 */
function HeroLanding({ onNavigate }) {
  const [stats, setStats] = useState({ countries: 0, qa: 0, audits: 0, guides: 0 })

  useEffect(() => {
    let cancelled = false
    Promise.all([
      fetchCountries().catch(() => ({ data: { countries: [] } })),
      fetchQaHistory().catch(() => ({ data: [] })),
      fetchAuditHistory().catch(() => ({ data: [] })),
      fetchGuideHistory(100).catch(() => []),
    ]).then(([c, q, a, g]) => {
      if (cancelled) return
      setStats({
        countries: c.data?.countries?.length || 0,
        qa: Array.isArray(q.data) ? q.data.length : 0,
        audits: Array.isArray(a.data) ? a.data.length : 0,
        guides: Array.isArray(g) ? g.length : 0,
      })
    })
    return () => { cancelled = true }
  }, [])

  const features = [
    {
      key: 'audit',
      icon: <AuditOutlined />,
      title: '合规审核',
      desc: '多国税务审核，AI 自动识别风险等级并给出专业建议，一键导出 PDF',
      accent: 'ink',
    },
    {
      key: 'qa',
      icon: <QuestionCircleOutlined />,
      title: '法规问答',
      desc: '基于 RAG 的法规检索问答，Token 级流式响应，附来源可追溯',
      accent: 'gold',
    },
    {
      key: 'guide',
      icon: <SafetyOutlined />,
      title: '合规指南',
      desc: '按国家 · 业务 · 关注标签生成四板块可打印检查清单，事项均可溯源',
      accent: 'ink',
    },
    {
      key: 'push',
      icon: <NotificationOutlined />,
      title: '为你推送',
      desc: '根据画像标签匹配最新法规动向，每一次业务操作都会让推荐更精准',
      accent: 'gold',
    },
  ]

  const highlights = [
    { icon: <GlobalOutlined />, label: '覆盖国家', value: stats.countries, unit: '个' },
    { icon: <QuestionCircleOutlined />, label: '累计问答', value: stats.qa, unit: '次' },
    { icon: <SafetyCertificateOutlined />, label: '合规审核', value: stats.audits, unit: '次' },
    { icon: <SafetyOutlined />, label: '合规指南', value: stats.guides, unit: '份' },
  ]

  return (
    <div className="hero-landing">
      {/* 背景装饰层 —— 分层柔和渐变、微网点、暗金光晕 */}
      <div className="hero-landing-bg" aria-hidden="true">
        <div className="hero-landing-wash" />
        <div className="hero-landing-dots" />
        <div className="hero-landing-glow hero-landing-glow-1" />
        <div className="hero-landing-glow hero-landing-glow-2" />
        <div className="hero-landing-glow hero-landing-glow-3" />
        <div className="hero-landing-vignette" />
      </div>

      <section className="hero-landing-hero">
        <div className="hero-landing-badge">
          <span className="hero-landing-badge-dot" />
          <span>AI · Multi-Jurisdiction Tax Intelligence</span>
        </div>
        <h1 className="hero-landing-title">
          <span className="hero-landing-title-line">出海不慌</span>
          <span className="hero-landing-title-line hero-landing-title-accent">合规先行</span>
        </h1>
        <p className="hero-landing-subtitle">
          面向跨境电商与出海品牌的一站式税务合规助手，融合多国法规知识库、AI 风险审核与实时政策推送，
          让每一次决策都有据可循。
        </p>
        <div className="hero-landing-cta">
          <Button
            type="primary"
            size="large"
            className="hero-landing-cta-primary"
            icon={<DashboardOutlined />}
            onClick={() => onNavigate?.('dashboard')}
          >
            进入数据看板
            <ArrowRightOutlined className="hero-landing-cta-arrow" />
          </Button>
          <Button
            size="large"
            className="hero-landing-cta-secondary"
            icon={<AuditOutlined />}
            onClick={() => onNavigate?.('audit')}
          >
            开始一次合规审核
          </Button>
          <Button
            size="large"
            className="hero-landing-cta-secondary hero-landing-cta-ghost"
            icon={<QuestionCircleOutlined />}
            onClick={() => onNavigate?.('qa')}
          >
            立即提问 AI
            <ArrowRightOutlined className="hero-landing-cta-arrow" />
          </Button>
        </div>

        {/* 关键数据条 */}
        <div className="hero-landing-highlights">
          {highlights.map((h) => (
            <div key={h.label} className="hero-landing-highlight">
              <span className="hero-landing-highlight-icon">{h.icon}</span>
              <div>
                <div className="hero-landing-highlight-value">
                  {h.value}
                  <span className="hero-landing-highlight-unit">{h.unit}</span>
                </div>
                <div className="hero-landing-highlight-label">{h.label}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 功能卡片网格 */}
      <section className="hero-landing-features">
        <div className="hero-landing-section-title">
          <ThunderboltOutlined />
          <span>核心功能</span>
        </div>
        <div className="hero-landing-features-grid">
          {features.map((f) => (
            <button
              key={f.key}
              type="button"
              className={`hero-landing-feature hero-landing-feature-${f.accent}`}
              onClick={() => onNavigate?.(f.key)}
            >
              <span className="hero-landing-feature-icon">{f.icon}</span>
              <div className="hero-landing-feature-body">
                <h3 className="hero-landing-feature-title">{f.title}</h3>
                <p className="hero-landing-feature-desc">{f.desc}</p>
              </div>
              <span className="hero-landing-feature-arrow">
                <ArrowRightOutlined />
              </span>
            </button>
          ))}
        </div>
      </section>

      {/* 全局 app-footer 已提供品牌与免责信息，此处不再重复 */}
    </div>
  )
}

export default HeroLanding
