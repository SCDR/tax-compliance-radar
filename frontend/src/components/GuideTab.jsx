import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Button,
  Card,
  Checkbox,
  Collapse,
  Divider,
  Empty,
  Input,
  List,
  Modal,
  Progress,
  Row,
  Col,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd'
import {
  BankOutlined,
  CalculatorOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  CopyrightOutlined,
  GlobalOutlined,
  DownloadOutlined,
  EditOutlined,
  FilePdfOutlined,
  FileTextOutlined,
  FileUnknownOutlined,
  FileWordOutlined,
  HistoryOutlined,
  InboxOutlined,
  LoadingOutlined,
  ReloadOutlined,
  SearchOutlined,
  StarFilled,
  ThunderboltOutlined,
  UpOutlined,
} from '@ant-design/icons'

import AIGeneratedBadge from './AIGeneratedBadge'
import ThinkingIndicator from './ThinkingIndicator'
import StreamingAnswerDisplay from './StreamingAnswerDisplay'
import {
  fetchGuideTagLibrary,
  fetchProfileGuideTags,
  submitGuideStream,
  listenGuideStream,
  extractContractFields,
  fetchGuideHistory,
  fetchGuideDetail,
} from '../api/client'
import { onProfileChange } from '../api/profile'
import { exportGuideToPDF, exportGuideToDocx } from '../utils/pdfExport'

const { Text, Paragraph, Title } = Typography

const COUNTRY_OPTIONS = [
  { label: '🇹🇭 泰国', value: 'TH' },
  { label: '🇮🇩 印尼', value: 'ID' },
  { label: '🇲🇾 马来西亚', value: 'MY' },
  { label: '🇻🇳 越南', value: 'VN' },
]

const BUSINESS_OPTIONS = [
  { label: '跨境电商零售', value: '跨境电商零售' },
  { label: '品牌出海直营', value: '品牌出海直营' },
  { label: '外贸综合服务', value: '外贸综合服务' },
]

const STATUS_OPTIONS = [
  '待办理', '待确认', '评估中', '视情况', '已知悉',
  '待建立', '待评估', '待实施', '已确认', '已排查',
  '待指定', '待制定', '已建立流程', '待审查', '待安排',
  '待对接', '视品类',
]

const SECTION_META = {
  funds: { title: '资金合规', icon: <BankOutlined /> },
  tax: { title: '税务', icon: <CalculatorOutlined /> },
  ip: { title: '知识产权', icon: <CopyrightOutlined /> },
  trade: { title: '贸易与海关', icon: <GlobalOutlined /> },
}

const priorityStars = (p) => (p === 3 ? '★★★' : p === 1 ? '★☆☆' : '★★☆')

const GUIDE_SLOGANS = [
  '从画像出发，为你的业务定制一份可执行的合规自检清单',
  '资金 · 税务 · 知识产权 · 贸易与海关 —— 覆盖跨境经营的四条主脉',
  '每一条事项都锚定具体法规条款，出处可溯、结论有据',
  '把碎片化的合规要点，整理成可打印、可核对、可复用的检查表',
  '一份清单同时服务于业务、法务与外部顾问的沟通',
  '关注点越明确，清单越精准 —— 用标签告诉我们你在意什么',
  '带 ★ 的是「猜你关注」，来自你此前的问答与审核轨迹',
  '合规不是一次性的动作，而是可以持续复核与更新的日常',
]

const UPLOAD_STEPS = [
  { label: '接收文件', desc: '读取上传流并做安全校验' },
  { label: '文本抽取', desc: '解码 PDF / DOCX，还原纯文本' },
  { label: '语义分析', desc: '识别国家、业务类型、平台与商品类目' },
  { label: '关键词归一', desc: '按标签库对齐并去重' },
  { label: '写入关注池', desc: '标签自动勾选，可继续人工调整' },
]

const COUNTRY_CN = { TH: '泰国', ID: '印尼', MY: '马来西亚', VN: '越南', SG: '新加坡', PH: '菲律宾' }

const formatHistoryTime = (timeStr) => {
  if (!timeStr) return ''
  try {
    const t = new Date(timeStr)
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const yesterday = new Date(today.getTime() - 86400000)
    const d = new Date(t.getFullYear(), t.getMonth(), t.getDate())
    const hh = String(t.getHours()).padStart(2, '0')
    const mm = String(t.getMinutes()).padStart(2, '0')
    if (d.getTime() === today.getTime()) return `${hh}:${mm}`
    if (d.getTime() === yesterday.getTime()) return `昨天 ${hh}:${mm}`
    return `${String(t.getMonth() + 1).padStart(2, '0')}-${String(t.getDate()).padStart(2, '0')} ${hh}:${mm}`
  } catch {
    return timeStr
  }
}

const fmtBytes = (bytes) => {
  if (bytes == null) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

const iconForFile = (name = '') => {
  const l = name.toLowerCase()
  if (l.endsWith('.pdf')) return <FilePdfOutlined style={{ color: '#c14444' }} />
  if (l.endsWith('.docx') || l.endsWith('.doc')) return <FileWordOutlined style={{ color: '#2b579a' }} />
  if (l.endsWith('.txt') || l.endsWith('.md')) return <FileTextOutlined style={{ color: '#64748b' }} />
  return <FileUnknownOutlined style={{ color: '#94a3b8' }} />
}

/**
 * 把合同抽取结果转换成可归一到标签池里的关键词集合。
 * 来源:
 *  - countries → 中文国家名
 *  - business_type
 *  - fields_by_country[*].platforms → 平台名
 *  - fields_by_country[*].product_categories / *.categories → 商品类目
 *  - raw_hits 里的短语(去掉过长的整句)
 */
const deriveTagsFromExtract = (payload) => {
  const bag = new Set()
  const push = (v) => {
    if (!v) return
    const s = String(v).trim()
    if (!s) return
    // 过滤过长的原文摘句(>16 字符视为不适合作为标签)
    if (s.length > 16) return
    bag.add(s)
  }
  (payload.countries || []).forEach((c) => push(COUNTRY_CN[c] || c))
  push(payload.business_type)
  Object.values(payload.fields_by_country || {}).forEach((fields) => {
    if (!fields || typeof fields !== 'object') return
    Object.entries(fields).forEach(([k, v]) => {
      // 跳过纯数字字段(annual_sales / monthly_turnover 等)
      if (typeof v === 'number') return
      if (Array.isArray(v)) v.forEach(push)
      else if (typeof v === 'string' && !/^[\d,.\s]+$/.test(v)) push(v)
    })
  })
  Object.values(payload.raw_hits || {}).forEach(push)
  return Array.from(bag)
}

const TAG_GROUP_LABELS = {
  guess: '猜你关注',
  country: '国家 / 地区',
  tax: '税种',
  topic: '主题事项',
  industry: '行业模式',
  channel: '销售渠道',
}

const TAG_GROUP_ORDER = ['guess', 'country', 'tax', 'topic', 'industry', 'channel']

/**
 * GuideGigTab — 模块四 · 合规指南
 * onOpenRegulation(filename, title, highlight) 供外层 App 打开 RegulationModal
 */
export default function GuideTab({ onOpenRegulation }) {
  const [tagLibrary, setTagLibrary] = useState({})
  const [profileTags, setProfileTags] = useState([])

  const [countries, setCountries] = useState(['TH', 'ID', 'MY', 'VN'])
  const [businessType, setBusinessType] = useState('跨境电商零售')
  // 标签库(含"猜你关注")与自定义标签合并成单一勾选池 —— 用户不再区分来源
  const [selectedTags, setSelectedTags] = useState([])
  const [customTags, setCustomTags] = useState([])
  const [tagSearch, setTagSearch] = useState('')
  const [activeGroups, setActiveGroups] = useState(['guess']) // 默认只展开"猜你关注"
  const [includeOptional, setIncludeOptional] = useState(true)

  const [loading, setLoading] = useState(false)
  const [inputCollapsed, setInputCollapsed] = useState(false)
  const [progress, setProgress] = useState({ percent: 0, message: '' })
  const [sections, setSections] = useState([]) // ordered by SECTION_META keys
  const [appendixTimeline, setAppendixTimeline] = useState([])
  const [appendixGlossary, setAppendixGlossary] = useState([])
  const [statusMap, setStatusMap] = useState({}) // itemKey → status word
  const [sloganIndex, setSloganIndex] = useState(0)

  // 指南历史
  const [history, setHistory] = useState([])
  const [detailModal, setDetailModal] = useState({ open: false, loading: false, detail: null })

  // 上传合同/文档 → 自动提取关键词的状态机
  const [uploadStage, setUploadStage] = useState(null) // null | 'scanning' | 'ready'
  const [uploadStep, setUploadStep] = useState(0)
  const [uploadExtracting, setUploadExtracting] = useState(false)
  const [uploadResult, setUploadResult] = useState(null) // {filename,size,uploadedAt,tags[],countries[],businessType}
  const uploadTimersRef = useRef([])

  const clearUploadTimers = () => {
    uploadTimersRef.current.forEach((t) => clearTimeout(t))
    uploadTimersRef.current = []
  }

  const resetUploadCard = () => {
    clearUploadTimers()
    setUploadStage(null)
    setUploadStep(0)
    setUploadResult(null)
  }

  const runExtractFromFile = async (file) => {
    clearUploadTimers()
    setUploadExtracting(true)
    setUploadStage('scanning')
    setUploadStep(0)
    const stepTimings = [700, 900, 1300, 1200] // step 0→1, 1→2, 2→3, 3→4
    let acc = 0
    stepTimings.forEach((delay, i) => {
      acc += delay
      const t = setTimeout(() => setUploadStep(i + 1), acc)
      uploadTimersRef.current.push(t)
    })

    try {
      const res = await extractContractFields(file)
      const payload = res?.data || {}
      const derived = deriveTagsFromExtract(payload)
      const nextCountries = Array.isArray(payload.countries) ? payload.countries.filter(Boolean) : []

      if (!derived.length && !nextCountries.length && !payload.business_type) {
        resetUploadCard()
        message.warning('未能从文档中识别出可用关键词，请人工输入')
        return
      }

      // 回填基础上下文
      if (nextCountries.length) setCountries(nextCountries)
      if (payload.business_type) setBusinessType(payload.business_type)

      // 关键词归一并加入 selectedTags(去重)
      setSelectedTags((prev) => {
        const merged = new Set(prev)
        derived.forEach((t) => merged.add(t))
        return Array.from(merged)
      })

      clearUploadTimers()
      setUploadStep(UPLOAD_STEPS.length - 1)
      const finish = setTimeout(() => {
        setUploadStage('ready')
        setUploadResult({
          filename: file?.name || '文档',
          size: file?.size,
          uploadedAt: new Date().toLocaleString('zh-CN', { hour12: false }),
          tags: derived,
          countries: nextCountries,
          businessType: payload.business_type || null,
        })
        message.success(`已识别 ${derived.length} 个关键词并加入关注池`)
      }, 500)
      uploadTimersRef.current.push(finish)
    } catch (err) {
      console.error('[guide] extractContractFields failed', err)
      resetUploadCard()
      message.error(err?.response?.data?.detail || err?.message || '文档解析失败,请重试')
    } finally {
      setUploadExtracting(false)
    }
  }

  useEffect(() => () => clearUploadTimers(), [])

  useEffect(() => {
    const timer = setInterval(() => {
      setSloganIndex((i) => (i + 1) % GUIDE_SLOGANS.length)
    }, 3500)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    fetchGuideTagLibrary().then(setTagLibrary).catch(() => setTagLibrary({}))
    loadProfileAndHistory()
    // 切换 profile 时重新拉取
    const unsub = onProfileChange(() => loadProfileAndHistory())
    return unsub
  }, [])

  const loadProfileAndHistory = () => {
    fetchProfileGuideTags(12)
      .then((tags) => {
        setProfileTags(tags)
        setSelectedTags(tags.map((t) => t.tag_key))
      })
      .catch(() => setProfileTags([]))
    fetchGuideHistory(20).then(setHistory).catch(() => setHistory([]))
  }

  // 画像标签快速查表:tag_key → weight
  const profileTagMap = useMemo(() => {
    const map = new Map()
    profileTags.forEach((t) => map.set(t.tag_key, t.weight))
    return map
  }, [profileTags])

  // 组装 6 组标签:第一组"猜你关注"= 未在其它 5 组出现的画像标签;后 5 组内画像命中项排前面并标记
  const groupedTags = useMemo(() => {
    const libraryTagSet = new Set()
    Object.values(tagLibrary).forEach((tags) => (tags || []).forEach((t) => libraryTagSet.add(t)))

    // 猜你关注 = 权重最高的画像标签(不管是否在其它组里),取 TopN 展示,若不在任意分类里的画像标签也归入这里
    const guess = profileTags.map((t) => t.tag_key)

    const groups = { guess }
    for (const key of ['country', 'tax', 'topic', 'industry', 'channel']) {
      const list = [...(tagLibrary[key] || [])]
      // 画像命中项排前;组内其余保持原顺序
      list.sort((a, b) => {
        const aHit = profileTagMap.has(a)
        const bHit = profileTagMap.has(b)
        if (aHit === bHit) return 0
        return aHit ? -1 : 1
      })
      groups[key] = list
    }
    return groups
  }, [tagLibrary, profileTags, profileTagMap])

  const mergedTags = useMemo(() => {
    const all = [...selectedTags, ...customTags]
    return Array.from(new Set(all.filter(Boolean)))
  }, [selectedTags, customTags])

  const guidePayload = useMemo(
    () => ({
      sections,
      appendix_timeline: appendixTimeline,
      appendix_glossary: appendixGlossary,
      statusMap,
      input: {
        countries,
        business_type: businessType,
        tags: mergedTags,
        include_optional: includeOptional,
      },
    }),
    [sections, appendixTimeline, appendixGlossary, statusMap, countries, businessType, mergedTags, includeOptional],
  )

  const hasResult = sections.some((s) => (s.items || []).length > 0)

  const handleGenerate = async () => {
    if (!countries.length) {
      message.warning('请至少选择一个国家')
      return
    }
    setLoading(true)
    setInputCollapsed(true)
    setSections([])
    setAppendixTimeline([])
    setAppendixGlossary([])
    setStatusMap({})
    setProgress({ percent: 3, message: '任务已提交...' })

    try {
      const { task_id } = await submitGuideStream({
        countries,
        business_type: businessType,
        tags: mergedTags,
        include_optional: includeOptional,
      })

      listenGuideStream(task_id, {
        onProgress: (data) => {
          setProgress({ percent: data.percent || 0, message: data.message || '' })
        },
        onSection: (data) => {
          const { section, value } = data
          if (section === 'appendix_timeline') {
            setAppendixTimeline(Array.isArray(value) ? value : [])
          } else if (section === 'appendix_glossary') {
            setAppendixGlossary(Array.isArray(value) ? value : [])
          } else if (value && typeof value === 'object') {
            setSections((prev) => {
              const next = prev.filter((s) => s.key !== value.key)
              next.push(value)
              // 固定四板块顺序
              const order = ['funds', 'tax', 'ip', 'trade']
              return next.sort((a, b) => order.indexOf(a.key) - order.indexOf(b.key))
            })
          }
        },
        onComplete: () => {
          setProgress({ percent: 100, message: '生成完成' })
          setLoading(false)
          message.success('合规指南已生成')
          fetchGuideHistory(20).then(setHistory).catch(() => {})
        },
        onError: (err) => {
          setLoading(false)
          message.error(`生成失败：${err}`)
        },
      })
    } catch (err) {
      setLoading(false)
      message.error(err?.message || '提交失败')
    }
  }

  const columns = (sectionKey) => [
    { title: '序号', dataIndex: 'seq', width: 60, align: 'center' },
    {
      title: '事项',
      dataIndex: 'title',
      width: 130,
      render: (t) => <Text strong>{t}</Text>,
    },
    {
      title: '具体要求',
      dataIndex: 'requirement',
      render: (t) => <div style={{ lineHeight: 1.65 }}>{t}</div>,
    },
    {
      title: '法律依据',
      dataIndex: 'legal_basis',
      width: 180,
      render: (t) => (
        <Text style={{ fontSize: 12, fontFamily: 'Menlo, Consolas, monospace', color: '#334155' }}>{t}</Text>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      width: 76,
      align: 'center',
      render: (p) => (
        <span style={{ color: '#a68a5b', letterSpacing: 1 }}>{priorityStars(p)}</span>
      ),
    },
    {
      title: '状态',
      key: 'status',
      width: 110,
      render: (_, record) => {
        const k = `${sectionKey}:${record.seq}`
        return (
          <Select
            size="small"
            value={statusMap[k] || '待办理'}
            style={{ width: '100%' }}
            variant="borderless"
            onChange={(v) => setStatusMap((prev) => ({ ...prev, [k]: v }))}
            options={STATUS_OPTIONS.map((s) => ({ value: s, label: `☐ ${s}` }))}
          />
        )
      },
    },
  ]

  const expandedRowRender = (record) => (
    <div style={{ padding: '4px 12px 8px', color: '#334155', lineHeight: 1.75 }}>
      {record.explanation && (
        <div style={{ marginBottom: 6 }}>
          <Text strong>解释：</Text>
          <span>{record.explanation}</span>
        </div>
      )}
      {record.advice_and_risk && (
        <div style={{ marginBottom: 6 }}>
          <Text strong>建议与违反风险：</Text>
          <span>{record.advice_and_risk}</span>
        </div>
      )}
      {record.cost_hint && (
        <div style={{ marginBottom: 6 }}>
          <Text strong>合规成本参考：</Text>
          <span>{record.cost_hint}</span>
        </div>
      )}
      {record.operation_hint && (
        <div style={{ marginBottom: 6 }}>
          <Text strong>实务操作指引：</Text>
          <span>{record.operation_hint}</span>
        </div>
      )}
      {record.sources?.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <Text strong style={{ marginRight: 8 }}>来源：</Text>
          {record.sources.map((s, i) => (
            <Tag
              key={i}
              className="source-tag"
              color="default"
              style={{ cursor: 'pointer', borderRadius: 999 }}
              onClick={() =>
                onOpenRegulation?.(s.filename || s.doc_name, s.doc_name, s.snippet || '')
              }
            >
              {s.doc_name}
            </Tag>
          ))}
        </div>
      )}
    </div>
  )

  const openHistoryDetail = async (guideId) => {
    setDetailModal({ open: true, loading: true, detail: null })
    try {
      const data = await fetchGuideDetail(guideId)
      setDetailModal({ open: true, loading: false, detail: data })
    } catch (err) {
      message.error('获取指南详情失败')
      setDetailModal({ open: false, loading: false, detail: null })
    }
  }

  return (
    <div className="guide-tab-content" style={{ paddingBottom: 60 }}>
      {/* ---------- 输入卡（可折叠） ---------- */}
      <Card
        className={`tech-card guide-input-card ${inputCollapsed ? 'is-collapsed' : 'is-expanded'}`}
        title={
          <span
            style={{ display: 'inline-flex', alignItems: 'center', cursor: 'pointer' }}
            onClick={() => setInputCollapsed((v) => !v)}
          >
            <ThunderboltOutlined style={{ marginRight: 8, color: '#a68a5b' }} />
            合规指南生成
            {inputCollapsed && (
              <Text
                type="secondary"
                style={{ marginLeft: 14, fontSize: 12, fontWeight: 400 }}
              >
                {(countries || []).map((c) => COUNTRY_OPTIONS.find((o) => o.value === c)?.label.replace(/^\S+\s/, '') || c).join(' / ')}
                {' · '}
                {businessType}
                {mergedTags.length > 0 && ` · ${mergedTags.length} 个标签`}
              </Text>
            )}
          </span>
        }
        extra={
          <Button
            type="text"
            size="small"
            icon={inputCollapsed ? <EditOutlined /> : <UpOutlined />}
            onClick={() => setInputCollapsed((v) => !v)}
            style={{ color: 'var(--ink-500)' }}
          >
            {inputCollapsed ? '修改条件' : '收起'}
          </Button>
        }
        style={{ marginBottom: 16 }}
      >
        <div
          className={`guide-input-body ${inputCollapsed ? 'collapsed' : 'expanded'}`}
          aria-hidden={inputCollapsed}
        >
          <div className="guide-input-body-inner">
        <Row gutter={[24, 16]}>
          <Col xs={24} md={12}>
            <Text strong>目标国家</Text>
            <div style={{ marginTop: 8 }}>
              <Checkbox.Group
                value={countries}
                onChange={setCountries}
                options={COUNTRY_OPTIONS}
              />
            </div>
          </Col>
          <Col xs={24} md={12}>
            <Text strong>业务类型</Text>
            <div style={{ marginTop: 8 }}>
              <Select
                value={businessType}
                onChange={setBusinessType}
                options={BUSINESS_OPTIONS}
                style={{ width: 260 }}
              />
            </div>
          </Col>
        </Row>

        <Divider style={{ margin: '20px 0 12px' }} />

        {/* ---------- 上传文档 → 提取关键词 ---------- */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
            <Text strong>从文档识别关键词</Text>
            <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
              上传合同、业务方案或政策解读，AI 自动提取国家/业务/平台/类目等关键词并加入下方关注池
            </Text>
          </div>
          <div className="guide-upload-wrapper">
            {uploadStage === 'ready' && uploadResult ? (
              <div className="contract-file-card">
                <div className="contract-file-icon">{iconForFile(uploadResult.filename)}</div>
                <div className="contract-file-main">
                  <div className="contract-file-title-row">
                    <span className="contract-file-name" title={uploadResult.filename}>
                      {uploadResult.filename}
                    </span>
                    <span className="contract-file-badge">
                      <CheckCircleFilled /> 已提取 {uploadResult.tags.length} 个关键词
                    </span>
                  </div>
                  <div className="contract-file-meta">
                    <span>{fmtBytes(uploadResult.size)}</span>
                    <span className="contract-file-dot">·</span>
                    <span>{uploadResult.uploadedAt}</span>
                    {uploadResult.businessType && (
                      <>
                        <span className="contract-file-dot">·</span>
                        <span>{uploadResult.businessType}</span>
                      </>
                    )}
                  </div>
                  {uploadResult.tags.length > 0 && (
                    <div className="contract-file-tags" style={{ marginTop: 6 }}>
                      {uploadResult.tags.slice(0, 10).map((t) => (
                        <span key={t} className="contract-country-chip">
                          {t}
                        </span>
                      ))}
                      {uploadResult.tags.length > 10 && (
                        <span className="contract-country-chip" style={{ opacity: 0.7 }}>
                          +{uploadResult.tags.length - 10}
                        </span>
                      )}
                    </div>
                  )}
                </div>
                <div className="contract-file-actions">
                  <Upload
                    name="file"
                    accept=".pdf,.docx,.txt,.md"
                    multiple={false}
                    maxCount={1}
                    showUploadList={false}
                    disabled={uploadExtracting || loading}
                    beforeUpload={() => true}
                    customRequest={({ file }) => runExtractFromFile(file)}
                  >
                    <Button
                      type="text"
                      size="small"
                      icon={<ReloadOutlined />}
                      loading={uploadExtracting}
                    >
                      重新上传
                    </Button>
                  </Upload>
                </div>
              </div>
            ) : (
              <Upload.Dragger
                name="file"
                accept=".pdf,.docx,.txt,.md"
                multiple={false}
                maxCount={1}
                showUploadList={false}
                disabled={uploadExtracting || loading}
                className="contract-upload-dragger"
                customRequest={({ file }) => runExtractFromFile(file)}
              >
                {uploadStage === 'scanning' ? (
                  <div className="contract-dragger-inner contract-dragger-scanning">
                    <div className="contract-scan-head">
                      <div className="contract-scan-icon">
                        <span className="contract-scan-doc" />
                        <span className="contract-scan-beam" />
                      </div>
                      <div className="contract-scan-title-block">
                        <div className="contract-step-index">
                          步骤 {uploadStep + 1} / {UPLOAD_STEPS.length}
                        </div>
                        <div
                          key={uploadStep}
                          className="contract-dragger-title contract-step-fade"
                        >
                          <LoadingOutlined /> {UPLOAD_STEPS[uploadStep]?.label ?? '解析中'}
                        </div>
                        <div
                          key={`d-${uploadStep}`}
                          className="contract-dragger-hint contract-step-fade"
                        >
                          {UPLOAD_STEPS[uploadStep]?.desc ?? ''}
                        </div>
                      </div>
                    </div>
                    <div className="contract-progress-track">
                      <div
                        className="contract-progress-fill"
                        style={{
                          width: `${((uploadStep + 1) / UPLOAD_STEPS.length) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                ) : (
                  <div className="contract-dragger-inner">
                    <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                    <p className="ant-upload-text">
                      拖入或点击上传合同 / 业务方案（PDF / DOCX / TXT）
                    </p>
                    <p className="ant-upload-hint">
                      AI 将自动识别国家、业务类型、平台与商品类目等关键词
                    </p>
                  </div>
                )}
              </Upload.Dragger>
            )}
          </div>
        </div>

        <Divider style={{ margin: '4px 0 12px' }} />

        <div style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 10 }}>
            <Text strong>关注标签</Text>
            <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
            <StarFilled style={{ color: '#a68a5b', fontSize: 10 }} /> 为「猜你关注」
            </Text>
            <Text type="secondary" style={{ marginLeft: 'auto', fontSize: 12 }}>
              已选 <span style={{ color: '#a68a5b', fontWeight: 600 }}>{selectedTags.length}</span> 个
              {selectedTags.length > 0 && (
                <Button
                  type="link"
                  size="small"
                  style={{ padding: '0 6px', fontSize: 12 }}
                  onClick={() => setSelectedTags([])}
                >
                  清空
                </Button>
              )}
            </Text>
          </div>

          {/* 顶部:搜索框 —— 大量标签时按关键词过滤 */}
          <Input
            allowClear
            size="middle"
            placeholder="搜索标签(支持中英文,例如 vat / 泰国 / 电子发票)"
            prefix={<SearchOutlined style={{ color: 'var(--ink-400)' }} />}
            value={tagSearch}
            onChange={(e) => {
              const val = e.target.value
              setTagSearch(val)
              // 搜索时自动展开全部分组,便于用户看到所有命中
              if (val.trim()) setActiveGroups(TAG_GROUP_ORDER)
              else setActiveGroups(['guess'])
            }}
            style={{ marginBottom: 12, borderRadius: 999 }}
          />

          {/* 已选标签摘要栏:随时可见,支持单击移除 */}
          {selectedTags.length > 0 && (
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 6,
                padding: '8px 12px',
                marginBottom: 10,
                background: 'rgba(166,138,91,0.06)',
                border: '1px dashed rgba(166,138,91,0.35)',
                borderRadius: 10,
              }}
            >
              {selectedTags.map((t) => {
                const isGuess = profileTagMap.has(t)
                return (
                  <Tag
                    key={`sel-${t}`}
                    closable
                    closeIcon={<CloseCircleFilled />}
                    onClose={(e) => {
                      e.preventDefault()
                      setSelectedTags((prev) => prev.filter((x) => x !== t))
                    }}
                    style={{
                      borderRadius: 999,
                      padding: '2px 10px',
                      background: isGuess ? 'rgba(166,138,91,0.14)' : 'rgba(15,23,42,0.06)',
                      border: `1px solid ${isGuess ? '#a68a5b' : '#0f172a'}`,
                      color: isGuess ? '#7c623b' : '#0f172a',
                      fontWeight: 500,
                    }}
                  >
                    {isGuess && (
                      <StarFilled style={{ color: '#a68a5b', fontSize: 10, marginRight: 4 }} />
                    )}
                    {t}
                  </Tag>
                )
              })}
            </div>
          )}

          {/* 主体:折叠分组 + 分组内标签胶囊 */}
          <Collapse
            ghost
            activeKey={activeGroups}
            onChange={(keys) => setActiveGroups(Array.isArray(keys) ? keys : [keys])}
            items={TAG_GROUP_ORDER.map((group) => {
              const rawTags = groupedTags[group] || []
              const kw = tagSearch.trim().toLowerCase()
              const filtered = kw
                ? rawTags.filter((t) => t.toLowerCase().includes(kw))
                : rawTags
              if (!filtered.length) return null

              const selectedInGroup = filtered.filter((t) => selectedTags.includes(t)).length

              return {
                key: group,
                label: (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                    <Text strong style={{ fontSize: 13 }}>
                      {TAG_GROUP_LABELS[group] || group}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {selectedInGroup}/{filtered.length}
                    </Text>
                    {group === 'guess' && (
                      <StarFilled style={{ color: '#a68a5b', fontSize: 11 }} />
                    )}
                  </span>
                ),
                children: (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, paddingLeft: 4 }}>
                    {filtered.map((t) => {
                      const active = selectedTags.includes(t)
                      const isGuess = profileTagMap.has(t)
                      const accent = isGuess ? '#a68a5b' : '#0f172a'
                      const softBg = isGuess
                        ? 'rgba(166,138,91,0.14)'
                        : 'rgba(15,23,42,0.06)'
                      return (
                        <Tag.CheckableTag
                          key={`${group}-${t}`}
                          checked={active}
                          onChange={(checked) =>
                            setSelectedTags((prev) =>
                              checked ? [...prev, t] : prev.filter((x) => x !== t),
                            )
                          }
                          style={{
                            borderRadius: 999,
                            border: `1px solid ${active ? accent : 'var(--border, #e2e8f0)'}`,
                            padding: '2px 12px',
                            background: active ? softBg : 'transparent',
                            color: active ? accent : 'var(--ink-700, #334155)',
                            fontWeight: active ? 600 : 400,
                            transition: 'all 0.18s ease',
                          }}
                        >
                          {isGuess && (
                            <StarFilled
                              style={{ color: '#a68a5b', fontSize: 10, marginRight: 4 }}
                            />
                          )}
                          {t}
                        </Tag.CheckableTag>
                      )
                    })}
                  </div>
                ),
              }
            }).filter(Boolean)}
          />

          {profileTags.length === 0 && !tagSearch && (
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 8 }}>
              （当前用户画像还没有积累标签，可以直接从上方分类中勾选或自由输入）
            </Text>
          )}
        </div>

        <div style={{ marginBottom: 12 }}>
          <Text strong>自定义标签</Text>
          <div style={{ marginTop: 8 }}>
            <Select
              mode="tags"
              value={customTags}
              onChange={setCustomTags}
              placeholder="输入你关注的关键词，回车添加，例如：直播带货、印花税、Shopee"
              style={{ width: '100%' }}
              tokenSeparators={[',', '，', ' ']}
            />
          </div>
        </div>

        <div className="form-action-bar">
          <div className="think-mode-toggle think-mode-toggle-flat">
            <Switch checked={includeOptional} onChange={setIncludeOptional} />
            <div className="think-mode-text">
              <div className="think-mode-title">附加合规成本 & 实务指引</div>
              <div className="think-mode-hint">让每个事项额外附带成本参考与办理路径</div>
            </div>
          </div>
          <Button
            className="tech-btn-primary"
            type="primary"
            onClick={handleGenerate}
            loading={loading}
            disabled={countries.length === 0}
          >
            {loading ? '生成中…' : '生成合规指南'}
          </Button>
        </div>
          </div>
        </div>
      </Card>

      {/* ---------- 结果区 ---------- */}
      <Card
        className="tech-card"
        title="合规自检清单"
        extra={
          hasResult && !loading ? (
            <Space>
              <Button
                icon={<FilePdfOutlined />}
                onClick={() => exportGuideToPDF(guidePayload)}
              >
                导出 PDF
              </Button>
              <Button
                icon={<FileWordOutlined />}
                onClick={() => exportGuideToDocx(guidePayload)}
              >
                导出 Word
              </Button>
            </Space>
          ) : null
        }
      >
        <AIGeneratedBadge />

        {loading && (
          <div style={{ margin: '12px 0 4px' }}>
            <ThinkingIndicator mode="carousel" />
            <div style={{ marginTop: 10 }}>
              <Progress
                percent={progress.percent}
                size="small"
                strokeColor={{ from: '#a68a5b', to: '#c9b284' }}
                showInfo={false}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {progress.message}
              </Text>
            </div>
          </div>
        )}

        {sections.length === 0 && !loading ? (
          <div className="empty-state" style={{ marginTop: 20 }}>
            <StreamingAnswerDisplay
              key={`guide-slogan-${sloganIndex}`}
              text={GUIDE_SLOGANS[sloganIndex]}
              placeholder="选择国家和标签后，点击「生成合规指南」..."
            />
          </div>
        ) : (
          <Row gutter={[16, 16]} style={{ marginTop: 12 }}>
            {['funds', 'tax', 'ip', 'trade'].map((key) => {
              const sec = sections.find((s) => s.key === key)
              const meta = SECTION_META[key]
              const isPending = !sec && loading
              return (
                <Col xs={24} key={key}>
                  <Card
                    size="small"
                    className={`guide-section-card ${sec ? 'guide-section-ready' : isPending ? 'guide-section-pending' : ''}`}
                    title={
                      <span style={{ display: 'inline-flex', alignItems: 'center' }}>
                        <span style={{ color: '#a68a5b', marginRight: 8 }}>{meta.icon}</span>
                        <span style={{ fontWeight: 600 }}>{meta.title}</span>
                        {sec ? (
                          <Text type="secondary" style={{ marginLeft: 12, fontSize: 12 }}>
                            {sec.items?.length || 0} 条事项
                          </Text>
                        ) : isPending ? (
                          <span
                            className="guide-section-dot"
                            style={{ marginLeft: 12 }}
                            aria-label="生成中"
                          >
                            <span />
                            <span />
                            <span />
                          </span>
                        ) : null}
                      </span>
                    }
                    style={{ borderRadius: 14 }}
                  >
                    {!sec ? (
                      <div className="guide-skeleton-rows" aria-hidden="true">
                        <div className="skeleton-row" />
                        <div className="skeleton-row" style={{ width: '82%' }} />
                        <div className="skeleton-row" style={{ width: '68%' }} />
                      </div>
                    ) : sec.items?.length ? (
                      <Table
                        rowKey={(r) => `${key}-${r.seq}`}
                        columns={columns(key)}
                        dataSource={sec.items}
                        pagination={false}
                        size="small"
                        expandable={{ expandedRowRender, defaultExpandAllRows: false }}
                      />
                    ) : (
                      <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description="本板块暂未检索到匹配法规"
                      />
                    )}
                  </Card>
                </Col>
              )
            })}

            {appendixTimeline.length > 0 && (
              <Col xs={24}>
                <Card size="small" className="guide-section-card" title="附录 A · 时间节点汇总">
                  <Table
                    rowKey={(r, i) => `t-${i}`}
                    dataSource={appendixTimeline}
                    pagination={false}
                    size="small"
                    columns={[
                      { title: '事项', dataIndex: 'item' },
                      { title: '时间节点', dataIndex: 'deadline', width: 220 },
                      { title: '备注', dataIndex: 'note' },
                    ]}
                  />
                </Card>
              </Col>
            )}

            {appendixGlossary.length > 0 && (
              <Col xs={24}>
                <Card size="small" className="guide-section-card" title="附录 B · 法律依据速查">
                  <Table
                    rowKey={(r, i) => `g-${i}`}
                    dataSource={appendixGlossary}
                    pagination={false}
                    size="small"
                    columns={[
                      { title: '缩写', dataIndex: 'abbr', width: 120 },
                      { title: '全称', dataIndex: 'full' },
                      { title: '中文', dataIndex: 'cn', width: 220 },
                    ]}
                  />
                </Card>
              </Col>
            )}
          </Row>
        )}
      </Card>

      {/* ---------- 指南历史 ---------- */}
      <Card
        className="tech-card"
        style={{ marginTop: 16 }}
        title={
          <span>
            <HistoryOutlined style={{ marginRight: 8, color: '#a68a5b' }} />
            指南历史
            {history.length > 0 && (
              <Text type="secondary" style={{ marginLeft: 10, fontSize: 12, fontWeight: 400 }}>
                共 {history.length} 条
              </Text>
            )}
          </span>
        }
      >
        {history.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="尚未生成过合规指南"
          />
        ) : (
          <List
            dataSource={history}
            renderItem={(item) => {
              const countryText = (item.countries || [])
                .map((c) => COUNTRY_CN[c] || c)
                .join(' · ') || '—'
              return (
                <List.Item
                  className="history-list-item"
                  style={{ cursor: 'pointer' }}
                  onClick={() => openHistoryDetail(item.guide_id)}
                >
                  <Space direction="vertical" size={4} style={{ width: '100%' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Text strong style={{ fontSize: 13 }}>
                        {countryText}
                      </Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        · {item.business_type || '跨境电商'}
                      </Text>
                    </div>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        width: '100%',
                        gap: 8,
                      }}
                    >
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {(item.input_tags || []).slice(0, 6).map((t) => (
                          <Tag
                            key={t}
                            style={{
                              borderRadius: 999,
                              padding: '0 8px',
                              fontSize: 11,
                              background: 'rgba(15,23,42,0.05)',
                              border: '1px solid rgba(15,23,42,0.08)',
                              color: 'var(--ink-700, #334155)',
                            }}
                          >
                            {t}
                          </Tag>
                        ))}
                        {(item.input_tags || []).length > 6 && (
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            +{item.input_tags.length - 6}
                          </Text>
                        )}
                      </div>
                      <Text
                        type="secondary"
                        style={{ fontSize: 12, whiteSpace: 'nowrap' }}
                      >
                        {formatHistoryTime(item.create_time)}
                      </Text>
                    </div>
                  </Space>
                </List.Item>
              )
            }}
          />
        )}
      </Card>

      {/* ---------- 历史详情 Modal ---------- */}
      <Modal
        open={detailModal.open}
        onCancel={() => setDetailModal({ open: false, loading: false, detail: null })}
        footer={
          detailModal.detail
            ? [
                <Button
                  key="pdf"
                  icon={<FilePdfOutlined />}
                  onClick={() => exportGuideToPDF(detailModal.detail.sections)}
                >
                  导出 PDF
                </Button>,
                <Button
                  key="docx"
                  icon={<FileWordOutlined />}
                  onClick={() => exportGuideToDocx(detailModal.detail.sections)}
                >
                  导出 Word
                </Button>,
                <Button
                  key="close"
                  onClick={() =>
                    setDetailModal({ open: false, loading: false, detail: null })
                  }
                >
                  关闭
                </Button>,
              ]
            : null
        }
        width={860}
        title={
          detailModal.detail ? (
            <span>
              指南历史 · {formatHistoryTime(detailModal.detail.create_time)}
              <Text
                type="secondary"
                style={{ marginLeft: 10, fontSize: 12, fontWeight: 400 }}
              >
                {(detailModal.detail.countries || [])
                  .map((c) => COUNTRY_CN[c] || c)
                  .join(' · ')}{' '}
                · {detailModal.detail.business_type || '跨境电商'}
              </Text>
            </span>
          ) : (
            '指南历史'
          )
        }
        destroyOnClose
      >
        {detailModal.loading ? (
          <div style={{ padding: 32, textAlign: 'center' }}>
            <ThinkingIndicator mode="carousel" />
          </div>
        ) : detailModal.detail ? (
          <div>
            {(detailModal.detail.input_tags || []).length > 0 && (
              <div style={{ marginBottom: 14 }}>
                <Text type="secondary" style={{ fontSize: 12, marginRight: 6 }}>
                  关注标签：
                </Text>
                {detailModal.detail.input_tags.map((t) => (
                  <Tag
                    key={t}
                    style={{
                      borderRadius: 999,
                      padding: '0 10px',
                      fontSize: 11,
                      background: 'rgba(166,138,91,0.1)',
                      border: '1px solid rgba(166,138,91,0.3)',
                      color: '#7c623b',
                      marginBottom: 4,
                    }}
                  >
                    {t}
                  </Tag>
                ))}
              </div>
            )}
            {(detailModal.detail.sections?.sections || []).map((sec) => {
              const meta = SECTION_META[sec.key] || { title: sec.title, icon: null }
              return (
                <Card
                  key={sec.key}
                  size="small"
                  className="guide-section-card"
                  style={{ marginBottom: 12 }}
                  title={
                    <span>
                      <span style={{ color: '#a68a5b', marginRight: 8 }}>{meta.icon}</span>
                      <span style={{ fontWeight: 600 }}>{meta.title}</span>
                      <Text type="secondary" style={{ marginLeft: 12, fontSize: 12 }}>
                        {sec.items?.length || 0} 条事项
                      </Text>
                    </span>
                  }
                >
                  {sec.items?.length ? (
                    <Table
                      rowKey={(r) => `${sec.key}-${r.seq}`}
                      columns={columns(sec.key)}
                      dataSource={sec.items}
                      pagination={false}
                      size="small"
                      expandable={{ expandedRowRender, defaultExpandAllRows: false }}
                    />
                  ) : (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description="本板块暂无事项"
                    />
                  )}
                </Card>
              )
            })}
          </div>
        ) : null}
      </Modal>
    </div>
  )
}
