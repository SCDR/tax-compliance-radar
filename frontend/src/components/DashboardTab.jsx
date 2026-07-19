import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Card, Statistic, Tag, Typography, Skeleton, Empty, Segmented } from 'antd'
import {
  QuestionCircleOutlined,
  AuditOutlined,
  WarningOutlined,
  GlobalOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  SafetyOutlined,
  TagsOutlined,
} from '@ant-design/icons'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from 'recharts'
import {
  fetchQaHistory,
  fetchAuditHistory,
  fetchGuideHistory,
  fetchCountries,
  listRegulations,
} from '../api/client'
import { onProfileChange } from '../api/profile'
import PolicyPushMini from './PolicyPushMini'

const { Text } = Typography

/** 主题色板 —— 与 CSS 变量保持一致 */
const THEME = {
  accent: '#a68a5b',
  accentHover: '#8b7048',
  accentSoft: 'rgba(166, 138, 91, 0.14)',
  ink900: '#0f172a',
  ink700: '#334155',
  ink500: '#64748b',
  ink400: '#94a3b8',
  ink200: '#e2e8f0',
  ink100: '#f1f5f9',
  border: 'rgba(15, 23, 42, 0.08)',
  risk: {
    high: '#8a2c2c',
    medium: '#a68a5b',
    low: '#3d5c47',
  },
}

/** 相对日期分桶：过去 7 天 [6 天前, ..., 今天] */
const buildRecentDaysBuckets = (items, getDate) => {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(today.getTime() - (6 - i) * 24 * 3600 * 1000)
    return { d, key: `${d.getMonth() + 1}/${d.getDate()}`, qa: 0, audit: 0, guide: 0, total: 0 }
  })
  items.forEach((it) => {
    const raw = getDate(it)
    if (!raw) return
    const t = new Date(raw)
    if (isNaN(t.getTime())) return
    const day = new Date(t.getFullYear(), t.getMonth(), t.getDate())
    const idx = 6 - Math.round((today.getTime() - day.getTime()) / (24 * 3600 * 1000))
    if (idx >= 0 && idx < 7) {
      if (it.__type === 'qa') days[idx].qa += 1
      else if (it.__type === 'guide') days[idx].guide += 1
      else days[idx].audit += 1
      days[idx].total += 1
    }
  })
  return days
}

/** Recharts 通用 tooltip 样式 */
const ChartTooltip = ({ active, payload, label, unit = '次' }) => {
  if (!active || !payload || !payload.length) return null
  return (
    <div className="chart-tooltip">
      {label && <div className="chart-tooltip-title">{label}</div>}
      {payload.map((entry, i) => (
        <div key={i} className="chart-tooltip-row">
          <span className="chart-tooltip-dot" style={{ background: entry.color || entry.fill }} />
          <span className="chart-tooltip-label">{entry.name}</span>
          <span className="chart-tooltip-value">{entry.value}{unit}</span>
        </div>
      ))}
    </div>
  )
}

/** 相对时间：刚刚 / N 分钟前 / N 小时前 / N 天前 / YYYY-MM-DD */
const formatRelative = (iso) => {
  if (!iso) return '—'
  const t = new Date(iso).getTime()
  if (isNaN(t)) return '—'
  const diff = Date.now() - t
  const m = Math.floor(diff / 60000)
  if (m < 1) return '刚刚'
  if (m < 60) return `${m} 分钟前`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} 小时前`
  const d = Math.floor(h / 24)
  if (d < 30) return `${d} 天前`
  return new Date(t).toISOString().slice(0, 10)
}

/** 根据容器高度按每条估算高度算出可展示条数 —— 用于最近活动、推送等长列表卡片 */
const useFitCount = (itemHeight, fallback = 5, min = 2, max = 12) => {
  const ref = useRef(null)
  const [count, setCount] = useState(fallback)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const update = () => {
      const h = el.clientHeight
      if (h <= 20) return
      const n = Math.max(min, Math.min(max, Math.floor(h / itemHeight)))
      setCount(n)
    }
    update()
    // 初次挂载时布局尚未稳定（min-height / 字体 / 图表加载），下一帧和 100ms/300ms 后各补测一次
    const raf = requestAnimationFrame(update)
    const t1 = setTimeout(update, 100)
    const t2 = setTimeout(update, 300)
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => {
      cancelAnimationFrame(raf)
      clearTimeout(t1)
      clearTimeout(t2)
      ro.disconnect()
    }
  }, [itemHeight, min, max])
  return [ref, count]
}

/** 内联 7 日 sparkline —— 使用指标格右侧,与文字同行 */
const Sparkline = ({ data, color, height = 56 }) => {
  const hasData = data && data.some((d) => d.v > 0)
  if (!hasData) {
    return (
      <div
        aria-hidden="true"
        style={{
          width: '100%',
          height,
          borderBottom: '1px dashed rgba(15,23,42,0.12)',
        }}
      />
    )
  }
  const gradId = `sparkGrad-${color.replace(/[^a-z0-9]/gi, '')}`
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 2 }}>
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.32} />
            <stop offset="100%" stopColor={color} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="v"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#${gradId})`}
          isAnimationActive={false}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}

/** KPI 右下环比徽标：↑ +N% / ↓ N% / 持平 */
const TrendBadge = ({ delta, current, suffix }) => {
  if (delta === undefined || delta === null) return null
  const dir = delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat'
  const symbol = dir === 'up' ? '↑' : dir === 'down' ? '↓' : '→'
  const text = dir === 'flat' ? '持平' : `${symbol} ${Math.abs(delta)}%`
  return (
    <div className={`dashboard-kpi-trend dashboard-kpi-trend-${dir}`}>
      <span className="dashboard-kpi-trend-badge">{text}</span>
      <span className="dashboard-kpi-trend-sub">
        {suffix} <b>{current}</b>
      </span>
    </div>
  )
}

const DashboardTab = ({ getCountryFlag, onOpenPush }) => {
  const [loading, setLoading] = useState(true)
  const [qaHistory, setQaHistory] = useState([])
  const [auditHistory, setAuditHistory] = useState([])
  const [guideHistory, setGuideHistory] = useState([])
  const [countries, setCountries] = useState([])
  const [regulations, setRegulations] = useState([])
  const [riskView, setRiskView] = useState('总览')

  // 最近活动条：每行 10 padding × 2 + 单行 13px 文字 ≈ 41px；bottom border 1px
  const [activityBodyRef, activityFit] = useFitCount(41, 6, 3, 15)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      try {
        const [qaRes, auditRes, guideRes, countriesRes, regsRes] = await Promise.all([
          fetchQaHistory(),
          fetchAuditHistory(),
          fetchGuideHistory(100).catch(() => []),
          fetchCountries(),
          listRegulations().catch(() => ({ data: [] })), // 兜底
        ])
        if (cancelled) return
        setQaHistory(Array.isArray(qaRes.data) ? qaRes.data : [])
        setAuditHistory(Array.isArray(auditRes.data) ? auditRes.data : [])
        setGuideHistory(Array.isArray(guideRes) ? guideRes : [])
        setCountries(countriesRes.data?.countries || [])
        setRegulations(Array.isArray(regsRes.data) ? regsRes.data : (regsRes.data || regsRes || []))
      } catch (e) {
        console.error('看板数据加载失败', e)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    // 切换画像时重新加载全部看板数据（QA / 审核历史都是按 profile 隔离的）
    const unsub = onProfileChange(() => {
      if (!cancelled) load()
    })
    return () => {
      cancelled = true
      unsub()
    }
  }, [])

  const stats = useMemo(() => {
    let high = 0, mid = 0, low = 0
    auditHistory.forEach((a) => {
      high += a.risk_count?.high_risk || 0
      mid += a.risk_count?.medium_risk || 0
      low += a.risk_count?.low_risk || 0
    })
    // 指南统计 —— 事项总数按 referenced_docs 长度做粗估;完整 sections 未在列表接口返回
    let guideItems = 0
    const tagCounter = new Map()
    guideHistory.forEach((g) => {
      guideItems += (g.referenced_docs || []).length
      ;(g.input_tags || []).forEach((t) => {
        tagCounter.set(t, (tagCounter.get(t) || 0) + 1)
      })
    })
    const topGuideTags = Array.from(tagCounter.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map(([tag, count]) => ({ tag, count }))
    return {
      totalQa: qaHistory.length,
      totalAudit: auditHistory.length,
      totalGuide: guideHistory.length,
      totalGuideItems: guideItems,
      totalCountries: countries.length,
      totalHigh: high,
      totalMid: mid,
      totalLow: low,
      totalRisks: high + mid + low,
      totalRegulations: regulations.length,
      topGuideTags,
    }
  }, [qaHistory, auditHistory, guideHistory, countries, regulations])

  // 近 7 日 vs 前 7 日 环比（用于 KPI 卡右上角的趋势徽标）
  const weekOverWeek = useMemo(() => {
    const now = Date.now()
    const day = 24 * 3600 * 1000
    const inRange = (iso, from, to) => {
      if (!iso) return false
      const t = new Date(iso).getTime()
      return !isNaN(t) && t >= from && t < to
    }
    const cur7Start = now - 7 * day
    const prev7Start = now - 14 * day
    const countIn = (arr, from, to) => arr.filter((it) => inRange(it.create_time, from, to)).length
    const qaCur = countIn(qaHistory, cur7Start, now)
    const qaPrev = countIn(qaHistory, prev7Start, cur7Start)
    const auditCur = countIn(auditHistory, cur7Start, now)
    const auditPrev = countIn(auditHistory, prev7Start, cur7Start)
    const guideCur = countIn(guideHistory, cur7Start, now)
    const guidePrev = countIn(guideHistory, prev7Start, cur7Start)
    const delta = (cur, prev) => {
      if (prev === 0) return cur > 0 ? 100 : 0
      return Math.round(((cur - prev) / prev) * 100)
    }
    return {
      qaCur, qaDelta: delta(qaCur, qaPrev),
      auditCur, auditDelta: delta(auditCur, auditPrev),
      guideCur, guideDelta: delta(guideCur, guidePrev),
    }
  }, [qaHistory, auditHistory, guideHistory])

  const recentActivity = useMemo(() => {
    const combined = [
      ...qaHistory.map((q) => ({ ...q, __type: 'qa' })),
      ...auditHistory.map((a) => ({ ...a, __type: 'audit' })),
      ...guideHistory.map((g) => ({ ...g, __type: 'guide' })),
    ]
    return buildRecentDaysBuckets(combined, (it) => it.create_time)
  }, [qaHistory, auditHistory, guideHistory])

  // 7 日 sparkline 数据(每个使用指标一条),风险按每天审核当天累计的 high+mid+low 估算
  const sparkSeries = useMemo(() => {
    // 按天累计风险:遍历 auditHistory,把 risk_count.* 塞进对应日期
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const riskBuckets = Array.from({ length: 7 }, () => 0)
    auditHistory.forEach((a) => {
      if (!a.create_time) return
      const t = new Date(a.create_time)
      if (isNaN(t.getTime())) return
      const day = new Date(t.getFullYear(), t.getMonth(), t.getDate())
      const idx = 6 - Math.round((today.getTime() - day.getTime()) / (24 * 3600 * 1000))
      if (idx >= 0 && idx < 7) {
        riskBuckets[idx] +=
          (a.risk_count?.high_risk || 0) +
          (a.risk_count?.medium_risk || 0) +
          (a.risk_count?.low_risk || 0)
      }
    })
    return {
      qa: recentActivity.map((d) => ({ k: d.key, v: d.qa })),
      audit: recentActivity.map((d) => ({ k: d.key, v: d.audit })),
      guide: recentActivity.map((d) => ({ k: d.key, v: d.guide })),
      risk: recentActivity.map((d, i) => ({ k: d.key, v: riskBuckets[i] })),
    }
  }, [recentActivity, auditHistory])

  const auditsByCountry = useMemo(() => {
    // 中文国名 → ISO code 兜底映射（老数据 target_market 字段用）
    const NAME_TO_CODE = {
      '泰国': 'TH', 'Thailand': 'TH',
      '越南': 'VN', 'Vietnam': 'VN',
      '印度尼西亚': 'ID', '印尼': 'ID', 'Indonesia': 'ID',
      '马来西亚': 'MY', 'Malaysia': 'MY',
      '菲律宾': 'PH', 'Philippines': 'PH',
      '新加坡': 'SG', 'Singapore': 'SG',
    }

    const extractCodes = (a) => {
      // 1. 后端 list_history 已解析出的 selected_countries
      if (Array.isArray(a.selected_countries) && a.selected_countries.length > 0) {
        return a.selected_countries
      }
      // 2. 老数据 target_market 中文名 → ISO code
      if (typeof a.target_market === 'string' && a.target_market.trim()) {
        const code = NAME_TO_CODE[a.target_market.trim()]
        return code ? [code] : [a.target_market.trim()]
      }
      // 3. 极端兜底：尝试解析 business_info（详情接口才有）
      let info = a.business_info
      if (typeof info === 'string') {
        try { info = JSON.parse(info) } catch { info = null }
      }
      if (info) {
        const byCountryKey = Object.keys(info).find((k) => k.endsWith('_by_country') && info[k] && typeof info[k] === 'object')
        if (byCountryKey) return Object.keys(info[byCountryKey])
        if (info.target_market) {
          const code = NAME_TO_CODE[info.target_market]
          return code ? [code] : [info.target_market]
        }
      }
      return []
    }

    const counter = {}
    auditHistory.forEach((a) => {
      extractCodes(a).forEach((c) => { counter[c] = (counter[c] || 0) + 1 })
    })
    return Object.entries(counter)
      .map(([code, count]) => ({
        code,
        count,
        display: `${getCountryFlag?.(code) || '🌍'} ${code}`,
      }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 6)
  }, [auditHistory, getCountryFlag])

  // ==== 风险分布：细粒度视图数据 ====
  // 每次审核平均触发多国国家数（用于把 risk_count 摊分到各国 —— 后端历史列表没细分到国家维度，做等分近似）
  const risksByCountry = useMemo(() => {
    const NAME_TO_CODE = {
      '泰国': 'TH', '越南': 'VN', '印度尼西亚': 'ID', '印尼': 'ID',
      '马来西亚': 'MY', '菲律宾': 'PH', '新加坡': 'SG',
    }
    const extractCodes = (a) => {
      if (Array.isArray(a.selected_countries) && a.selected_countries.length > 0) return a.selected_countries
      if (typeof a.target_market === 'string' && a.target_market.trim()) {
        return [NAME_TO_CODE[a.target_market.trim()] || a.target_market.trim()]
      }
      return []
    }
    const bucket = {}
    auditHistory.forEach((a) => {
      const codes = extractCodes(a)
      if (codes.length === 0) return
      const share = 1 / codes.length
      const h = (a.risk_count?.high_risk || 0) * share
      const m = (a.risk_count?.medium_risk || 0) * share
      const l = (a.risk_count?.low_risk || 0) * share
      codes.forEach((c) => {
        if (!bucket[c]) bucket[c] = { code: c, high: 0, medium: 0, low: 0, total: 0 }
        bucket[c].high += h
        bucket[c].medium += m
        bucket[c].low += l
        bucket[c].total += h + m + l
      })
    })
    return Object.values(bucket)
      .map((b) => ({
        ...b,
        // 摊分后可能是小数，四舍五入到整数展示
        high: Math.round(b.high),
        medium: Math.round(b.medium),
        low: Math.round(b.low),
        total: Math.round(b.total),
        display: `${getCountryFlag?.(b.code) || '🌍'} ${b.code}`,
      }))
      .filter((b) => b.total > 0)
      .sort((a, b) => b.total - a.total)
      .slice(0, 6)
  }, [auditHistory, getCountryFlag])

  // 近 7 日风险趋势：按创建日期分桶累加高/中/低
  const riskTrend = useMemo(() => {
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const days = Array.from({ length: 7 }, (_, i) => {
      const d = new Date(today.getTime() - (6 - i) * 24 * 3600 * 1000)
      return { key: `${d.getMonth() + 1}/${d.getDate()}`, high: 0, medium: 0, low: 0 }
    })
    auditHistory.forEach((a) => {
      if (!a.create_time) return
      const t = new Date(a.create_time)
      if (isNaN(t.getTime())) return
      const day = new Date(t.getFullYear(), t.getMonth(), t.getDate())
      const idx = 6 - Math.round((today.getTime() - day.getTime()) / (24 * 3600 * 1000))
      if (idx >= 0 && idx < 7) {
        days[idx].high += a.risk_count?.high_risk || 0
        days[idx].medium += a.risk_count?.medium_risk || 0
        days[idx].low += a.risk_count?.low_risk || 0
      }
    })
    return days
  }, [auditHistory])

  // 风险深度指标：平均每次审核触发的风险数 / 单次最高风险数 / 高风险占比
  const riskMetrics = useMemo(() => {
    const n = auditHistory.length
    if (n === 0) return { avgRisks: 0, maxHigh: 0, highRatio: 0, coverage: 0 }
    let sumRisks = 0
    let maxHigh = 0
    auditHistory.forEach((a) => {
      const h = a.risk_count?.high_risk || 0
      const m = a.risk_count?.medium_risk || 0
      const l = a.risk_count?.low_risk || 0
      sumRisks += h + m + l
      if (h > maxHigh) maxHigh = h
    })
    const total = stats.totalRisks
    return {
      avgRisks: total > 0 ? (sumRisks / n).toFixed(1) : '0',
      maxHigh,
      highRatio: total > 0 ? Math.round((stats.totalHigh / total) * 100) : 0,
      coverage: risksByCountry.length, // 曾出现风险的国家数
    }
  }, [auditHistory, stats, risksByCountry])

  // 问答引用来源 TOP —— 从 qa_history 里的 sources 字段（字符串数组）累计
  const topSources = useMemo(() => {
    const counter = new Map()
    qaHistory.forEach((q) => {
      const arr = Array.isArray(q.sources) ? q.sources : []
      arr.forEach((s) => {
        const key = typeof s === 'string' ? s.trim() : ''
        if (!key) return
        counter.set(key, (counter.get(key) || 0) + 1)
      })
    })
    return Array.from(counter.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 6)
  }, [qaHistory])

  // 问答关键词 TOP —— 优先用浏览器原生 Intl.Segmenter 做中文分词，退化到简单正则
  const topKeywords = useMemo(() => {
    const STOP = new Set([
      // 中文虚词/常见词
      '的', '了', '和', '与', '及', '或', '是', '在', '有', '为', '对', '被', '把', '给', '让', '从',
      '这', '那', '就', '也', '都', '还', '不', '会', '要', '吗', '呢', '着', '过', '并', '而', '但',
      '一个', '这个', '那个', '什么', '如何', '怎么', '怎样', '哪些', '哪个', '需要', '可以', '应该', '如果',
      '还有', '关于', '进行', '通过', '包括', '以及', '因为', '所以', '但是', '然后', '而且', '或者',
      '一下', '一些', '这样', '那样', '目前', '当前', '现在', '之前', '之后', '其中', '此外', '另外',
      '请问', '请', '我', '你', '他', '她', '它', '我们', '你们', '他们', '自己', '公司', '业务',
      // 常见通用英文词
      'the', 'is', 'and', 'or', 'a', 'an', 'to', 'of', 'for', 'in', 'on', 'at', 'by', 'with',
      'as', 'be', 'are', 'was', 'were', 'this', 'that', 'these', 'those', 'it', 'its', 'what',
      'how', 'why', 'when', 'where', 'which', 'who',
    ])

    // 优先用 Intl.Segmenter；不可用则退化到"整段抓 2-4 字"的简易切分
    let segmenter = null
    try {
      if (typeof Intl !== 'undefined' && Intl.Segmenter) {
        segmenter = new Intl.Segmenter('zh', { granularity: 'word' })
      }
    } catch {
      segmenter = null
    }

    const CJK = /[一-鿿]/
    const isCJK = (s) => CJK.test(s)
    const isAlnum = (s) => /^[A-Za-z][A-Za-z0-9]{2,}$/.test(s)

    const counter = new Map()
    qaHistory.forEach((q) => {
      const text = (q.query_text || '').trim()
      if (!text) return

      const tokens = []
      if (segmenter) {
        for (const seg of segmenter.segment(text)) {
          if (!seg.isWordLike) continue
          const w = seg.segment.trim()
          if (!w) continue
          // 中文词：保留 2-6 字；英文词：保留 3+ 字母数字
          if (isCJK(w) && w.length >= 2 && w.length <= 6) tokens.push(w)
          else if (isAlnum(w)) tokens.push(w)
        }
      } else {
        // 退化路径：不做贪心的 2-6 字截取（那正是"奇怪分词"的成因），
        // 改为按标点/空白切段，只保留 2-4 字的短片段作为候选
        text.split(/[\s，。；：？！,.;:?!、（）()【】\[\]"'"'—–…]+/).forEach((seg) => {
          const s = seg.trim()
          if (!s) return
          if (isCJK(s)) {
            if (s.length >= 2 && s.length <= 4) tokens.push(s)
          } else if (isAlnum(s)) {
            tokens.push(s)
          }
        })
      }

      // 去重+计数：同一条问题中同一词只算 1
      const uniq = new Set(tokens.map((t) => t.toLowerCase()))
      uniq.forEach((low) => {
        const orig = tokens.find((t) => t.toLowerCase() === low) || low
        if (STOP.has(low) || STOP.has(orig)) return
        // 单个汉字 / 单个字母数字 一律丢弃
        if (orig.length < 2) return
        counter.set(orig, (counter.get(orig) || 0) + 1)
      })
    })

    return Array.from(counter.entries())
      .filter(([, c]) => c > 0)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
      .map(([name, count]) => ({ name, count }))
  }, [qaHistory])

  // 最近活动流：QA + audit + guide 混合按时间排序，保留最近 20 条，前端按卡片高度动态裁剪
  const recentActivityStream = useMemo(() => {
    const items = [
      ...qaHistory.map((q) => ({
        kind: 'qa',
        time: q.create_time,
        text: q.query_text,
        id: `qa-${q.qa_id}`,
      })),
      ...auditHistory.map((a) => ({
        kind: 'audit',
        time: a.create_time,
        text: a.summary_title || a.business_type || '合规审核',
        id: `audit-${a.audit_id}`,
        countries: a.selected_countries || [],
        risks: (a.risk_count?.high_risk || 0) + (a.risk_count?.medium_risk || 0) + (a.risk_count?.low_risk || 0),
        high: a.risk_count?.high_risk || 0,
      })),
      ...guideHistory.map((g) => ({
        kind: 'guide',
        time: g.create_time,
        text: `合规指南 · ${(g.countries || []).join(' / ') || '多国'} · ${g.business_type || '跨境电商'}`,
        id: `guide-${g.guide_id}`,
        countries: g.countries || [],
      })),
    ]
      .filter((it) => it.time)
      .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())
      .slice(0, 20)
    return items
  }, [qaHistory, auditHistory, guideHistory])

  const riskPieData = [
    { name: '高风险', value: stats.totalHigh, color: THEME.risk.high },
    { name: '中风险', value: stats.totalMid, color: THEME.risk.medium },
    { name: '低风险', value: stats.totalLow, color: THEME.risk.low },
  ]

  if (loading) {
    return (
      <div className="dashboard-tab-content">
        <Card className="tech-card dashboard-summary-usage">
          <Skeleton active paragraph={{ rows: 3 }} title={false} />
        </Card>
      </div>
    )
  }

  const hasActivity = recentActivity.some((d) => d.total > 0)
  const hasRisks = stats.totalRisks > 0

  return (
    <div className="dashboard-tab-content">
      {/* ---------- 顶部摘要 · 单一横条,6 项指标(4 使用 + 2 覆盖) ---------- */}
      <Card className="tech-card dashboard-summary-usage">
        <div className="dashboard-summary-usage-inner">
          <div className="dashboard-summary-metric">
            <QuestionCircleOutlined className="dashboard-summary-icon" />
            <div className="dashboard-summary-body">
              <div className="dashboard-summary-label">累计问答</div>
              <div className="dashboard-summary-value">{stats.totalQa}</div>
              <div className="dashboard-summary-footer">
                <TrendBadge delta={weekOverWeek.qaDelta} current={weekOverWeek.qaCur} suffix="近 7 日" />
              </div>
            </div>
            <div className="dashboard-summary-spark">
              <Sparkline data={sparkSeries.qa} color={THEME.accent} />
            </div>
          </div>
          <div className="dashboard-summary-divider" />
          <div className="dashboard-summary-metric">
            <AuditOutlined className="dashboard-summary-icon" />
            <div className="dashboard-summary-body">
              <div className="dashboard-summary-label">累计审核</div>
              <div className="dashboard-summary-value">{stats.totalAudit}</div>
              <div className="dashboard-summary-footer">
                <TrendBadge delta={weekOverWeek.auditDelta} current={weekOverWeek.auditCur} suffix="近 7 日" />
              </div>
            </div>
            <div className="dashboard-summary-spark">
              <Sparkline data={sparkSeries.audit} color={THEME.ink700} />
            </div>
          </div>
          <div className="dashboard-summary-divider" />
          <div className="dashboard-summary-metric">
            <SafetyOutlined className="dashboard-summary-icon" />
            <div className="dashboard-summary-body">
              <div className="dashboard-summary-label">合规指南</div>
              <div className="dashboard-summary-value">{stats.totalGuide}</div>
              <div className="dashboard-summary-footer">
                <TrendBadge delta={weekOverWeek.guideDelta} current={weekOverWeek.guideCur} suffix="近 7 日" />
              </div>
            </div>
            <div className="dashboard-summary-spark">
              <Sparkline data={sparkSeries.guide} color={THEME.risk.low} />
            </div>
          </div>
          <div className="dashboard-summary-divider" />
          <div className="dashboard-summary-metric">
            <WarningOutlined className="dashboard-summary-icon dashboard-summary-icon-warn" />
            <div className="dashboard-summary-body">
              <div className="dashboard-summary-label">识别高风险</div>
              <div className="dashboard-summary-value" style={{ color: THEME.risk.high }}>{stats.totalHigh}</div>
              <div className="dashboard-summary-footer">
                <div className="dashboard-summary-sub">中 <b>{stats.totalMid}</b> · 低 <b>{stats.totalLow}</b></div>
              </div>
            </div>
            <div className="dashboard-summary-spark">
              <Sparkline data={sparkSeries.risk} color={THEME.risk.high} />
            </div>
          </div>
          <div className="dashboard-summary-divider" />
          <div className="dashboard-summary-metric dashboard-summary-metric-compact">
            <GlobalOutlined className="dashboard-summary-icon" />
            <div className="dashboard-summary-body">
              <div className="dashboard-summary-label">支持国家</div>
              <div className="dashboard-summary-value">{stats.totalCountries}</div>
              <div className="dashboard-summary-footer">
                <div className="dashboard-summary-sub">已审核 <b>{auditsByCountry.length}</b> / {stats.totalCountries}</div>
              </div>
            </div>
          </div>
          <div className="dashboard-summary-divider" />
          <div className="dashboard-summary-metric dashboard-summary-metric-compact">
            <FileTextOutlined className="dashboard-summary-icon" />
            <div className="dashboard-summary-body">
              <div className="dashboard-summary-label">法规库文档</div>
              <div className="dashboard-summary-value">{stats.totalRegulations}</div>
              <div className="dashboard-summary-footer">
                <div className="dashboard-summary-sub">被引用 <b>{topSources.length}</b> 份</div>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* 主内容网格：12 列语义化布局 */}
      <div className="dashboard-grid">
        {/* 第 1 行：活跃趋势（宽）+ 为你推送（窄侧栏） */}
        <Card className="tech-card dashboard-chart-card dashboard-col-8" title="近 7 日活跃趋势">
          {hasActivity ? (
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={recentActivity} margin={{ top: 10, right: 12, left: -12, bottom: 0 }}>
                  <defs>
                    <linearGradient id="gradQa" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={THEME.accent} stopOpacity={0.35} />
                      <stop offset="100%" stopColor={THEME.accent} stopOpacity={0.04} />
                    </linearGradient>
                    <linearGradient id="gradAudit" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={THEME.ink700} stopOpacity={0.3} />
                      <stop offset="100%" stopColor={THEME.ink700} stopOpacity={0.03} />
                    </linearGradient>
                    <linearGradient id="gradGuide" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={THEME.risk.low} stopOpacity={0.32} />
                      <stop offset="100%" stopColor={THEME.risk.low} stopOpacity={0.03} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke={THEME.border} strokeDasharray="3 6" vertical={false} />
                  <XAxis
                    dataKey="key"
                    stroke={THEME.ink400}
                    fontSize={11}
                    tickLine={false}
                    axisLine={{ stroke: THEME.border }}
                  />
                  <YAxis
                    stroke={THEME.ink400}
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    allowDecimals={false}
                    width={30}
                  />
                  <Tooltip content={<ChartTooltip />} cursor={{ stroke: THEME.ink200, strokeDasharray: '3 3' }} />
                  <Area
                    type="monotone"
                    dataKey="qa"
                    name="问答"
                    stroke={THEME.accent}
                    strokeWidth={2}
                    fill="url(#gradQa)"
                    activeDot={{ r: 4, fill: THEME.accent, stroke: '#fff', strokeWidth: 2 }}
                  />
                  <Area
                    type="monotone"
                    dataKey="audit"
                    name="审核"
                    stroke={THEME.ink700}
                    strokeWidth={2}
                    fill="url(#gradAudit)"
                    activeDot={{ r: 4, fill: THEME.ink700, stroke: '#fff', strokeWidth: 2 }}
                  />
                  <Area
                    type="monotone"
                    dataKey="guide"
                    name="指南"
                    stroke={THEME.risk.low}
                    strokeWidth={2}
                    fill="url(#gradGuide)"
                    activeDot={{ r: 4, fill: THEME.risk.low, stroke: '#fff', strokeWidth: 2 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
              <div className="dashboard-chart-legend">
                <span className="dashboard-legend-item">
                  <span className="dashboard-legend-dot" style={{ background: THEME.accent }} /> 问答
                </span>
                <span className="dashboard-legend-item">
                  <span className="dashboard-legend-dot" style={{ background: THEME.ink700 }} /> 审核
                </span>
                <span className="dashboard-legend-item">
                  <span className="dashboard-legend-dot" style={{ background: THEME.risk.low }} /> 指南
                </span>
              </div>
            </div>
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<Text type="secondary">近 7 日暂无记录</Text>} style={{ padding: '40px 0' }} />
          )}
        </Card>

        {/* 为你推送 —— 作为活跃趋势的右侧栏，垂直 4 列宽 */}
        <div className="dashboard-col-4">
          <PolicyPushMini onOpenPage={onOpenPush} limit={3} />
        </div>

        <Card
          className="tech-card dashboard-chart-card dashboard-risk-card dashboard-col-6"
          title={
            <div className="dashboard-risk-header">
              <span>风险分布</span>
              <Segmented
                size="small"
                value={riskView}
                onChange={setRiskView}
                options={['总览', '按国家', '近 7 日']}
              />
            </div>
          }
        >
          {!hasRisks ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<Text type="secondary">暂无审核数据</Text>} style={{ padding: '40px 0' }} />
          ) : riskView === '总览' ? (
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={riskPieData.filter((d) => d.value > 0)}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={54}
                    outerRadius={80}
                    paddingAngle={2}
                    stroke="#fff"
                    strokeWidth={2}
                  >
                    {riskPieData.filter((d) => d.value > 0).map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTooltip unit=" 条" />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="dashboard-donut-center">
                <div className="dashboard-donut-value">{stats.totalRisks}</div>
                <div className="dashboard-donut-label">条风险</div>
              </div>
              <div className="dashboard-chart-legend">
                {riskPieData.map((s) => {
                  const pct = stats.totalRisks > 0 ? Math.round((s.value / stats.totalRisks) * 100) : 0
                  return (
                    <span key={s.name} className="dashboard-legend-item">
                      <span className="dashboard-legend-dot" style={{ background: s.color }} />
                      {s.name}
                      <span className="dashboard-legend-value">{s.value}</span>
                      <span className="dashboard-legend-pct">{pct}%</span>
                    </span>
                  )
                })}
              </div>
              {/* 额外指标行 */}
              <div className="dashboard-risk-metrics">
                <div className="dashboard-risk-metric">
                  <span className="dashboard-risk-metric-label">单次均值</span>
                  <span className="dashboard-risk-metric-value">{riskMetrics.avgRisks}</span>
                  <span className="dashboard-risk-metric-unit">条/次</span>
                </div>
                <div className="dashboard-risk-metric">
                  <span className="dashboard-risk-metric-label">高风险占比</span>
                  <span className="dashboard-risk-metric-value" style={{ color: THEME.risk.high }}>
                    {riskMetrics.highRatio}%
                  </span>
                </div>
                <div className="dashboard-risk-metric">
                  <span className="dashboard-risk-metric-label">单次最多高风险</span>
                  <span className="dashboard-risk-metric-value">{riskMetrics.maxHigh}</span>
                  <span className="dashboard-risk-metric-unit">条</span>
                </div>
                <div className="dashboard-risk-metric">
                  <span className="dashboard-risk-metric-label">涉险国家</span>
                  <span className="dashboard-risk-metric-value">{riskMetrics.coverage}</span>
                </div>
              </div>
            </div>
          ) : riskView === '按国家' ? (
            risksByCountry.length > 0 ? (
              <div className="chart-container">
                <ResponsiveContainer width="100%" height={Math.max(200, risksByCountry.length * 44)}>
                  <BarChart
                    data={risksByCountry}
                    layout="vertical"
                    margin={{ top: 4, right: 24, left: 8, bottom: 0 }}
                    stackOffset="none"
                  >
                    <CartesianGrid stroke={THEME.border} strokeDasharray="3 6" horizontal={false} />
                    <XAxis
                      type="number"
                      stroke={THEME.ink400}
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      allowDecimals={false}
                    />
                    <YAxis
                      dataKey="display"
                      type="category"
                      stroke={THEME.ink700}
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                      width={80}
                    />
                    <Tooltip content={<ChartTooltip unit=" 条" />} cursor={{ fill: THEME.accentSoft }} />
                    <Bar dataKey="high" name="高风险" stackId="risk" fill={THEME.risk.high} radius={[0, 0, 0, 0]} barSize={14} />
                    <Bar dataKey="medium" name="中风险" stackId="risk" fill={THEME.risk.medium} radius={[0, 0, 0, 0]} barSize={14} />
                    <Bar dataKey="low" name="低风险" stackId="risk" fill={THEME.risk.low} radius={[0, 6, 6, 0]} barSize={14} />
                  </BarChart>
                </ResponsiveContainer>
                <div className="dashboard-chart-legend">
                  <span className="dashboard-legend-item">
                    <span className="dashboard-legend-dot" style={{ background: THEME.risk.high }} /> 高
                  </span>
                  <span className="dashboard-legend-item">
                    <span className="dashboard-legend-dot" style={{ background: THEME.risk.medium }} /> 中
                  </span>
                  <span className="dashboard-legend-item">
                    <span className="dashboard-legend-dot" style={{ background: THEME.risk.low }} /> 低
                  </span>
                  <span className="dashboard-legend-hint">摊分至各审核国家（等分近似）</span>
                </div>
              </div>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<Text type="secondary">暂无按国家的风险数据</Text>} style={{ padding: '40px 0' }} />
            )
          ) : (
            // 近 7 日
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={riskTrend} margin={{ top: 10, right: 12, left: -12, bottom: 0 }}>
                  <CartesianGrid stroke={THEME.border} strokeDasharray="3 6" vertical={false} />
                  <XAxis
                    dataKey="key"
                    stroke={THEME.ink400}
                    fontSize={11}
                    tickLine={false}
                    axisLine={{ stroke: THEME.border }}
                  />
                  <YAxis
                    stroke={THEME.ink400}
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    allowDecimals={false}
                    width={30}
                  />
                  <Tooltip content={<ChartTooltip unit=" 条" />} cursor={{ fill: THEME.accentSoft }} />
                  <Bar dataKey="high" name="高" stackId="d" fill={THEME.risk.high} />
                  <Bar dataKey="medium" name="中" stackId="d" fill={THEME.risk.medium} />
                  <Bar dataKey="low" name="低" stackId="d" fill={THEME.risk.low} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
              <div className="dashboard-chart-legend">
                <span className="dashboard-legend-item">
                  <span className="dashboard-legend-dot" style={{ background: THEME.risk.high }} /> 高风险
                </span>
                <span className="dashboard-legend-item">
                  <span className="dashboard-legend-dot" style={{ background: THEME.risk.medium }} /> 中风险
                </span>
                <span className="dashboard-legend-item">
                  <span className="dashboard-legend-dot" style={{ background: THEME.risk.low }} /> 低风险
                </span>
              </div>
            </div>
          )}
        </Card>

        <Card className="tech-card dashboard-chart-card dashboard-col-6" title="最近活动">
          <div ref={activityBodyRef} className="dashboard-activity-body">
            {recentActivityStream.length > 0 ? (
              <ul className="dashboard-activity-list">
                {recentActivityStream.slice(0, activityFit).map((it) => (
                  <li key={it.id} className="dashboard-activity-item">
                    <span className={`dashboard-activity-kind dashboard-activity-kind-${it.kind}`}>
                      {it.kind === 'qa' ? '问答' : it.kind === 'audit' ? '审核' : '指南'}
                    </span>
                    <span className="dashboard-activity-text" title={it.text}>{it.text}</span>
                    <span className="dashboard-activity-meta">
                      {it.kind === 'audit' && it.high > 0 && (
                        <Tag className="risk-tag risk-high" style={{ marginRight: 6 }}>高 {it.high}</Tag>
                      )}
                      {(it.kind === 'audit' || it.kind === 'guide') && it.countries?.length > 0 && (
                        <span className="dashboard-activity-flags">
                          {it.countries.slice(0, 3).map((c) => getCountryFlag?.(c) || '🌍').join(' ')}
                        </span>
                      )}
                      <span className="dashboard-activity-time">{formatRelative(it.time)}</span>
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<Text type="secondary">暂无活动记录</Text>} style={{ padding: '20px 0' }} />
            )}
          </div>
        </Card>

        <Card className="tech-card dashboard-chart-card dashboard-col-4" title="国家审核次数 TOP">
          {auditsByCountry.length > 0 ? (
            <ResponsiveContainer width="100%" height={Math.max(200, auditsByCountry.length * 40)}>
              <BarChart
                data={auditsByCountry}
                layout="vertical"
                margin={{ top: 4, right: 24, left: 8, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="gradBar" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor={THEME.accent} />
                    <stop offset="100%" stopColor={THEME.accentHover} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke={THEME.border} strokeDasharray="3 6" horizontal={false} />
                <XAxis
                  type="number"
                  stroke={THEME.ink400}
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  allowDecimals={false}
                />
                <YAxis
                  dataKey="display"
                  type="category"
                  stroke={THEME.ink700}
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  width={80}
                />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: THEME.accentSoft }} />
                <Bar
                  dataKey="count"
                  name="审核次数"
                  fill="url(#gradBar)"
                  radius={[0, 6, 6, 0]}
                  barSize={16}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<Text type="secondary">暂无审核数据</Text>} style={{ padding: '40px 0' }} />
          )}
        </Card>

        <Card className="tech-card dashboard-chart-card dashboard-col-4" title="高频引用法规">
          {topSources.length > 0 ? (
            <ul className="dashboard-source-list">
              {topSources.map((s, i) => {
                const max = topSources[0]?.count || 1
                const pct = Math.max(6, (s.count / max) * 100)
                return (
                  <li key={s.name} className="dashboard-source-item">
                    <span className="dashboard-source-rank">{i + 1}</span>
                    <div className="dashboard-source-body">
                      <div className="dashboard-source-name" title={s.name}>{s.name}</div>
                      <div className="dashboard-source-bar">
                        <div className="dashboard-source-bar-fill" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                    <span className="dashboard-source-count">{s.count}</span>
                  </li>
                )
              })}
            </ul>
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<Text type="secondary">暂无引用数据</Text>} style={{ padding: '20px 0' }} />
          )}
        </Card>

        <Card
          className="tech-card dashboard-chart-card dashboard-col-4"
          title={<span><TagsOutlined style={{ marginRight: 6, color: THEME.accent }} />指南关注标签 TOP</span>}
        >
          {stats.topGuideTags.length > 0 ? (
            <ul className="dashboard-source-list">
              {stats.topGuideTags.map((s, i) => {
                const max = stats.topGuideTags[0]?.count || 1
                const pct = Math.max(6, (s.count / max) * 100)
                return (
                  <li key={s.tag} className="dashboard-source-item">
                    <span className="dashboard-source-rank">{i + 1}</span>
                    <div className="dashboard-source-body">
                      <div className="dashboard-source-name" title={s.tag}>{s.tag}</div>
                      <div className="dashboard-source-bar">
                        <div className="dashboard-source-bar-fill" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                    <span className="dashboard-source-count">{s.count}</span>
                  </li>
                )
              })}
            </ul>
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<Text type="secondary">暂无指南记录</Text>} style={{ padding: '20px 0' }} />
          )}
        </Card>

        <Card className="tech-card dashboard-chart-card dashboard-col-12" title="问答热词">
          {topKeywords.length > 0 ? (
            <div className="dashboard-cloud">
              {topKeywords.map((k, i) => {
                const max = topKeywords[0]?.count || 1
                const size = 12 + (k.count / max) * 10 // 12–22px
                const alpha = 0.55 + (k.count / max) * 0.45
                return (
                  <span
                    key={k.name}
                    className="dashboard-cloud-item"
                    style={{
                      fontSize: `${size}px`,
                      color: i < 3 ? THEME.accent : `rgba(15, 23, 42, ${alpha})`,
                      fontWeight: i < 3 ? 600 : 500,
                    }}
                    title={`${k.name} · ${k.count} 次`}
                  >
                    {k.name}
                    <sub className="dashboard-cloud-count">{k.count}</sub>
                  </span>
                )
              })}
            </div>
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<Text type="secondary">暂无问答关键词</Text>} style={{ padding: '20px 0' }} />
          )}
        </Card>
      </div>
    </div>
  )
}

export default DashboardTab
