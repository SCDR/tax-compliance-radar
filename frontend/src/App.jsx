import { useEffect, useMemo, useRef, useState } from 'react'

// 强制React更新
let forceUpdateCounter = 0
import { Button, Card, Form, Input, InputNumber, List, Menu, Modal, Select, Space, Tag, Typography, message, notification, Switch, Tooltip, Upload } from 'antd'
import { FileTextOutlined, QuestionCircleOutlined, AuditOutlined, DownOutlined, MessageOutlined, DashboardOutlined, NotificationOutlined, HomeOutlined, InboxOutlined, FilePdfOutlined, FileWordOutlined, FileUnknownOutlined, ReloadOutlined, CheckCircleFilled, LoadingOutlined, SafetyOutlined, RightOutlined } from '@ant-design/icons'
import { fetchQaHistory, fetchAuditHistory, fetchAuditHistoryDetail, fetchCountries, fetchAllCountryConfigs, submitSseAudit, listenAuditResult, submitStreamQaWithMode, listenQaStream, extractContractFields } from './api/client'
import { onProfileChange } from './api/profile'
import { getRegulationAliases, getRegulationAliasesSync } from './api/regulationAliases'
import ThinkingIndicator from './components/ThinkingIndicator'
import StreamingAnswerDisplay from './components/StreamingAnswerDisplay'
import AuditResultDisplay from './components/AuditResultDisplay'
import AIGeneratedBadge from './components/AIGeneratedBadge'
import DashboardTab from './components/DashboardTab'
import GuideTab from './components/GuideTab'
import PDFExportButton from './components/PDFExportButton'
import RegulationModal from './components/RegulationModal'
import QaHistoryModal from './components/QaHistoryModal'
import PolicyPushCard from './components/PolicyPushCard'
import PolicyPushMarquee from './components/PolicyPushMarquee'
import PolicyPushMini from './components/PolicyPushMini'
import HeroLanding from './components/HeroLanding'
import TutorialGuide from './components/TutorialGuide'
import DebugPanel from './components/DebugPanel'
import { exportQAResultToPDF, exportAuditReportToPDF } from './utils/pdfExport'

const { Title, Paragraph, Text } = Typography
const disclaimer = '本工具仅供参考，不构成税务/法律意见，不替代专业顾问服务。'

// 占位符 Slogan 列表 - 在未显示回答时轮播
const PLACEHOLDER_SLOGANS = [
    '请输入您要咨询的合规问题，AI 将为您提供专业解答',
    '探索跨境合规的细节，保护您的业务运营',
    '让合规变得简单，让业务更有把握',
    '深度法规分析，助力跨境业务合规',
    '实时合规预警，规避税务风险隐患',
    '专业建议指导，助您轻松应对复杂税务',
    '智能风险评估，用数据说话更安心',
    '多国法规对标比较，找到最优合规方案',
    '从单国到全球，合规制度如此清晰',
    '不懂外国税法？AI 为您深度解读',
    '跨境电商必备工具，让合规成为竞争优势',
    '精准定位风险点，化被动执法为主动应对',
]

// 动态 Slogan 机制 - 根据业务类型和国家获取相关建议
const getDynamicSlogans = (businessType = null, selectedCountries = []) => {
    let dynamicSlogans = [...PLACEHOLDER_SLOGANS]
    
    // 根据业务类型添加针对性建议
    const businessTypeTips = {
        '跨境电商零售': [
            '电商税务必知：海外销售地税、进口税、VAT是三大成本杀手',
            '多渠道销售需要多国申报，让 AI 帮您整理合规清单',
            '低值商品免税政策在变，与其被罚不如提前问',
        ],
        '品牌出海直营': [
            '品牌直营要注意转移定价问题，规避反避税审查',
            '常设机构认定很关键，搞清楚才能省税',
            '国际协议价格指南（MAP）不容忽视',
        ],
        '外贸综合服务': [
            '代理出口涉及多方税务协议，合规流程有讲究',
            '跨境代理需要规范发票、合同、支付凭证',
            '外汇管制和进出口许可证是核心合规要素',
        ],
    }
    
    // 如果选择了业务类型，补充相关建议
    if (businessType && businessTypeTips[businessType]) {
        dynamicSlogans = [...dynamicSlogans, ...businessTypeTips[businessType]]
    }
    
    // 根据选择的国家数量添加多国税务相关建议
    if (selectedCountries.length >= 2) {
        dynamicSlogans.push(
            '多国经营涉及复杂的成本分配和费用归集问题',
            '集团企业的利润分配必须符合各国转移定价规则'
        )
    }
    
    return dynamicSlogans
}


// 法规文件名到标题的映射
const REGULATION_TITLES = {
    '01_vat_registration_rules.md': '泰国VAT注册规则',
    '02_low_value_goods_policy_2026.md': '低价值商品VAT政策 (2026)',
    '03_platform_withholding_rules.md': '平台代扣代缴规则',
    '04_monthly_reporting_audit.md': '月度申报与稽查要求',
}

// 检测并提取回答中的引用来源，返回可点击的JSX
const renderAnswerWithSourceLinks = (answer, onSourceClick, aliases = null) => {
    if (!answer) return '暂无回答'

    // 分离回答主体和引用来源
    const sourceMarker = '**引用来源：**'
    const sourceIndex = answer.indexOf(sourceMarker)

    if (sourceIndex === -1) {
        return <span>{answer}</span>
    }

    const mainAnswer = answer.substring(0, sourceIndex)
    const sourcesPart = answer.substring(sourceIndex + sourceMarker.length)

    // 解析来源列表
    const sourceFiles = sourcesPart
        .split(/[;；]/)
        .map(s => s.trim())
        .filter(s => s && s.length > 0)

    return (
        <>
            <span>{mainAnswer}</span>
            <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #eee' }}>
                <Text strong style={{ display: 'block', marginBottom: '8px' }}>引用来源：</Text>
                <Space wrap size="small">
                    {sourceFiles.map((source, idx) => {
                        // 1) 硬编码 REGULATION_TITLES 中的旧文件名
                        const matchedFilename = Object.keys(REGULATION_TITLES).find(filename => source.includes(filename))
                        if (matchedFilename) {
                            return (
                                <Tag
                                    key={idx}
                                    className="source-tag"
                                    icon={<FileTextOutlined />}
                                    onClick={() => onSourceClick(matchedFilename, REGULATION_TITLES[matchedFilename])}
                                    style={{ cursor: 'pointer' }}
                                >
                                    {REGULATION_TITLES[matchedFilename]}
                                </Tag>
                            )
                        }
                        // 2) 后端别名表命中（doc_name / doc_id / 文号别名）
                        //    LLM 有时会返回带编号/后缀/引号/括号的 source，比如 `1. 泰国VAT注册规则.md` 或 `《…》`。
                        //    做宽松匹配：精确 → 去装饰后精确 → substring 双向包含。
                        const decorate = /(^[0-9]+[.、\)）]\s*|\s*\.md$|^【|】$|^《|》$|^"|"$|^'|'$)/g
                        const cleaned = source.replace(decorate, '').trim()
                        let hit = null
                        if (aliases) {
                            if (aliases[source]) hit = source
                            else if (aliases[cleaned]) hit = cleaned
                            else {
                                // substring 双向包含（例如 "泰国VAT注册规则（示例）" 里含别名 "泰国VAT注册规则"）
                                for (const alias of Object.keys(aliases)) {
                                    if (!alias) continue
                                    if (source.includes(alias) || alias.includes(cleaned)) { hit = alias; break }
                                }
                            }
                        }
                        if (hit) {
                            return (
                                <Tag
                                    key={idx}
                                    className="source-tag"
                                    icon={<FileTextOutlined />}
                                    onClick={() => onSourceClick(hit, hit)}
                                    style={{ cursor: 'pointer' }}
                                >
                                    {source}
                                </Tag>
                            )
                        }
                        if (import.meta.env.DEV) {
                            console.warn('[source-tag] alias miss', { source, cleaned, aliasKeys: aliases ? Object.keys(aliases).slice(0, 20) : null })
                        }
                        // 3) 仍未命中：灰色不可点击 tag，避免 404
                        return <Tag key={idx} className="source-tag-plain">{source}</Tag>
                    })}
                </Space>
            </div>
        </>
    )
}

// 从 snippets 字典中取文件对应的首个片段用于弹窗定位。兼容 string 与 string[] 两种后端返回。
// 支持"别名回退"：如果按传入 key 找不到，尝试通过 aliases 表把 key 解析成真实文件名后再查。
const pickSnippet = (snippets, filename, aliases = null) => {
    const tryKey = (k) => {
        const v = snippets?.[k]
        if (!v) return ''
        if (Array.isArray(v)) return v[0] || ''
        return String(v)
    }
    let hit = tryKey(filename)
    if (hit) return hit
    // 别名回退：filename 可能是中文 doc_name，snippets 却以真实 .md 文件名为键（或反之）
    if (aliases) {
        const resolved = aliases[filename]
        if (resolved) hit = tryKey(resolved)
        if (hit) return hit
        // 反向：filename 是真实文件名，snippets 却以 doc_name 为键
        for (const [alias, real] of Object.entries(aliases)) {
            if (real === filename && alias !== filename) {
                hit = tryKey(alias)
                if (hit) return hit
            }
        }
    }
    return ''
}

// 从 positions 字典中取文件对应的 block 定位数组，用于精准滚动到原文段落
const pickPositions = (positions, filename, aliases = null) => {
    const tryKey = (k) => {
        const v = positions?.[k]
        return Array.isArray(v) && v.length ? v : null
    }
    let hit = tryKey(filename)
    if (hit) return hit
    if (aliases) {
        const resolved = aliases[filename]
        if (resolved) hit = tryKey(resolved)
        if (hit) return hit
        for (const [alias, real] of Object.entries(aliases)) {
            if (real === filename && alias !== filename) {
                hit = tryKey(alias)
                if (hit) return hit
            }
        }
    }
    return null
}

function App() {
    const [qaForm] = Form.useForm()
    const [auditForm] = Form.useForm()
    const [loadingQa, setLoadingQa] = useState(false)
    const [loadingAudit, setLoadingAudit] = useState(false)
    // 法规弹窗状态
    const [regulationModal, setRegulationModal] = useState({
        open: false,
        filename: '',
        title: '',
        highlight: '',
        positions: null,
    })
    // 检索到的来源片段：{ filename: snippet } —— 用于弹窗内定位（老兜底）
    const [sourceSnippets, setSourceSnippets] = useState({})
    // 检索到的 block 级位置：{ filename: [{block_start, block_end}] } —— 精准定位首选
    const [sourcePositions, setSourcePositions] = useState({})
    // QA历史弹窗状态
    const [qaHistoryModal, setQaHistoryModal] = useState({
        open: false,
        qaId: null,
    })
    // 审核历史弹窗状态
    const [auditHistoryModal, setAuditHistoryModal] = useState({
        open: false,
        auditId: null,
        auditDetail: null,
    })
    const [qaResult, setQaResult] = useState(null)
    const [auditResult, setAuditResult] = useState(null)
    const [qaStreamText, setQaStreamText] = useState('')  // 流式回答的文本
    const [qaStreaming, setQaStreaming] = useState(false)  // 是否正在流式输出
    const [thinkMode, setThinkMode] = useState(false) // 思考模式，默认关闭
    // 直接使用 state setter，无需通过 ref 间接调用
    // 用于调试：追踪qaStreamText的变化
    //   useEffect(() => {
    //     console.log('qaStreamText updated:', { length: qaStreamText.length, preview: qaStreamText.slice(0, 50) })
    //   }, [qaStreamText])
    const [qaHistory, setQaHistory] = useState([])
    const [auditHistory, setAuditHistory] = useState([])
    const [regulationAliases, setRegulationAliases] = useState(() => getRegulationAliasesSync())
    const [countries, setCountries] = useState([])
    const [countryConfigs, setCountryConfigs] = useState({})
    const [selectedCountries, setSelectedCountries] = useState([])
    const [activeTab, setActiveTab] = useState('hero')
    const [chatDockOpen, setChatDockOpen] = useState(true)
    const [chatDockHeight, setChatDockHeight] = useState(0)
    const chatDockRef = useRef(null)
    const auditStreamRef = useRef(null)
    const auditRunIdRef = useRef(0)
    const [contractExtracting, setContractExtracting] = useState(false)
    const [contractStage, setContractStage] = useState(null) // null | 'scanning' | 'ready'
    const [contractStep, setContractStep] = useState(0)      // 0..4 during scanning
    const [contractResult, setContractResult] = useState(null) // {filename,size,filledCount,countries,businessType}
    const contractStepTimersRef = useRef([])

    // 格式化时间显示：今天显示 HH:mm，昨天显示"昨天 HH:mm"，更早显示 MM-dd HH:mm
    const formatTime = (timeStr) => {
        if (!timeStr) return ''
        try {
            const time = new Date(timeStr)
            const now = new Date()
            const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
            const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000)
            const timeDate = new Date(time.getFullYear(), time.getMonth(), time.getDate())

            const hours = time.getHours().toString().padStart(2, '0')
            const minutes = time.getMinutes().toString().padStart(2, '0')

            if (timeDate.getTime() === today.getTime()) {
                return `${hours}:${minutes}`
            } else if (timeDate.getTime() === yesterday.getTime()) {
                return `昨天 ${hours}:${minutes}`
            } else {
                const month = (time.getMonth() + 1).toString().padStart(2, '0')
                const day = time.getDate().toString().padStart(2, '0')
                return `${month}-${day} ${hours}:${minutes}`
            }
        } catch {
            return timeStr
        }
    }

    // 占位符 Slogan 轮播状态
    const [currentSloganIndex, setCurrentSloganIndex] = useState(0)
    const prevSloganIndexRef = useRef(-1)
    const sloganTimerRef = useRef(null)

    // 计算当前使用的动态 Slogan 列表（基于业务类型和选择的国家）
    const currentSlogans = useMemo(() => {
        const businessType = auditForm.getFieldValue('business_type')
        return getDynamicSlogans(businessType, selectedCountries)
    }, [auditForm, selectedCountries])

    // 监听 currentSloganIndex 变化
    useEffect(() => {
        // 状态已正常更新，调试告示：如需查看变化可取消注释
        // console.log(`✅ currentSloganIndex 状态变化: ${currentSloganIndex} → ${PLACEHOLDER_SLOGANS[currentSloganIndex]}`)
    }, [currentSloganIndex])

    // 占位符 Slogan 轮播效果（基于动态 Slogan 列表）
    useEffect(() => {
        // 当 slogan 列表变化时，重置索引
        if (currentSloganIndex >= currentSlogans.length) {
            setCurrentSloganIndex(0)
        }

        // 定时器只在初始化时创建一次，持续运行
        const sloganTimer = setInterval(() => {
            setCurrentSloganIndex(prevIdx => {
                // 简化逻辑：直接选择一个不同的随机索引
                let newIdx = Math.floor(Math.random() * currentSlogans.length)
                // 确保不重复（最多尝试 10 次）
                let attempts = 0
                while ((newIdx === prevIdx || newIdx === prevSloganIndexRef.current) && attempts < 10) {
                    newIdx = Math.floor(Math.random() * currentSlogans.length)
                    attempts++
                }
                prevSloganIndexRef.current = newIdx
                return newIdx
            })
        }, 3500) // 3.5秒轮播一次

        return () => {
            clearInterval(sloganTimer)
        }
    }, [currentSlogans])

    // 加载支持的国家列表和配置
    useEffect(() => {
        const loadCountryConfigs = async () => {
            try {
                // 同时加载国家列表和完整配置
                const [countriesResult, configsResult] = await Promise.all([
                    fetchCountries(),
                    fetchAllCountryConfigs()
                ])
                setCountries(countriesResult.data.countries)
                setCountryConfigs(configsResult.data)
                // 默认选中泰国
                setSelectedCountries(['TH'])
            } catch {
                message.error('加载国家配置失败')
            }
        }
        loadCountryConfigs()
    }, [])

    const loadHistory = async () => {
        try {
            const [qaRes, auditRes] = await Promise.all([fetchQaHistory(), fetchAuditHistory()])
            setQaHistory(Array.isArray(qaRes.data) ? qaRes.data : [])
            setAuditHistory(Array.isArray(auditRes.data) ? auditRes.data : [])
        } catch {
            setQaHistory([])
            setAuditHistory([])
        }
    }

    useEffect(() => {
        loadHistory()
    }, [])

    // 首次加载法规别名缓存（用于判断"引用来源" tag 是否可点击）
    useEffect(() => {
        if (!regulationAliases) {
            getRegulationAliases().then(setRegulationAliases)
        }
    }, [regulationAliases])

    // 用户画像切换时：清空正在展示的结果 + 关闭进行中的流 + 重新拉取历史
    useEffect(() => {
        const unsub = onProfileChange(() => {
            // 关闭进行中的审核 SSE 流，避免旧画像的结果继续写入新画像的 UI
            if (auditStreamRef.current) {
                auditStreamRef.current.close?.()
                auditStreamRef.current = null
            }
            auditRunIdRef.current += 1 // 使旧 SSE 回调命中 stale check 直接丢弃
            setQaResult(null)
            setAuditResult(null)
            setQaStreamText('')
            setQaStreaming(false)
            setLoadingQa(false)
            setLoadingAudit(false)
            setSourceSnippets({})
            setSourcePositions({})
            loadHistory()
        })
        return unsub
    }, [])

    // 动态测量悬浮 dock 高度，写入 CSS 变量，让 shell 底部预留空间自适应
    useEffect(() => {
        const el = chatDockRef.current
        if (!el) return
        const update = () => {
            const rect = el.getBoundingClientRect()
            setChatDockHeight(Math.ceil(rect.height))
        }
        update()
        const ro = new ResizeObserver(update)
        ro.observe(el)
        window.addEventListener('resize', update)
        return () => {
            ro.disconnect()
            window.removeEventListener('resize', update)
        }
    }, [activeTab, chatDockOpen, loadingQa])

    // 获取国家名称
    const getCountryName = (code) => {
        return countryConfigs[code]?.country_name || code
    }

    // 合同抽取流程步骤 —— 展示给用户的详细状态
    const CONTRACT_STEPS = [
        { label: '接收文件', desc: '读取上传流并做安全校验' },
        { label: '文本抽取', desc: '解码 PDF / DOCX，还原纯文本' },
        { label: '语义分析', desc: '识别国家、业务类型、金额与平台等实体' },
        { label: '字段抽取', desc: '按国家 schema 对齐并做单位归一' },
        { label: '结构化回填', desc: '写入 表单 并高亮低置信项' },
    ]

    const formatBytes = (bytes) => {
        if (!bytes && bytes !== 0) return '—'
        if (bytes < 1024) return `${bytes} B`
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
    }

    const getFileTypeIcon = (name = '') => {
        const lower = name.toLowerCase()
        if (lower.endsWith('.pdf')) return <FilePdfOutlined style={{ color: '#c14444' }} />
        if (lower.endsWith('.docx') || lower.endsWith('.doc')) return <FileWordOutlined style={{ color: '#2b579a' }} />
        if (lower.endsWith('.txt') || lower.endsWith('.md')) return <FileTextOutlined style={{ color: '#64748b' }} />
        return <FileUnknownOutlined style={{ color: '#94a3b8' }} />
    }

    const clearContractStepTimers = () => {
        contractStepTimersRef.current.forEach(t => clearTimeout(t))
        contractStepTimersRef.current = []
    }

    const resetContractCard = () => {
        clearContractStepTimers()
        setContractStage(null)
        setContractStep(0)
        setContractResult(null)
    }

    const runContractExtract = async (file, onSuccess, onError) => {
        clearContractStepTimers()
        setContractExtracting(true)
        setContractStage('scanning')
        setContractStep(0)
        // 前四步走定时推进，节奏与 LLM 请求耗时相近；最后一步由回填完成时手动置位
        const stepTimings = [700, 900, 1400, 1400] // ms per step transition (step 0→1, 1→2, 2→3, 3→4)
        let acc = 0
        stepTimings.forEach((delay, i) => {
            acc += delay
            const t = setTimeout(() => setContractStep(i + 1), acc)
            contractStepTimersRef.current.push(t)
        })

        try {
            const res = await extractContractFields(file)
            const payload = res?.data || {}
            const nextCountries = Array.isArray(payload.countries) ? payload.countries : []
            const fieldsByCountry = payload.fields_by_country || {}
            const rawHits = payload.raw_hits || {}
            const confidence = payload.confidence || {}

            if (nextCountries.length === 0 && !payload.business_type) {
                resetContractCard()
                message.warning('AI 未能从合同中识别出可用字段，请人工填写')
                onSuccess?.({}, file)
                return
            }

            // 切国家并回填顶层字段
            setSelectedCountries(nextCountries)
            auditForm.setFieldsValue({
                countries: nextCountries,
                business_type: payload.business_type || undefined,
            })

            // 等下一帧，等动态 Form.Item 挂载完再回填
            setTimeout(() => {
                const patch = {}
                let filledCount = 0
                Object.entries(fieldsByCountry).forEach(([code, fields]) => {
                    Object.entries(fields || {}).forEach(([name, value]) => {
                        patch[`${name}_${code}`] = value
                        filledCount += 1
                    })
                })
                if (Object.keys(patch).length) auditForm.setFieldsValue(patch)
                const totalFilled = filledCount + (payload.business_type ? 1 : 0) + (nextCountries.length ? 1 : 0)

                // 直接跳到最后一步并短暂展示后进入 ready 卡片态
                clearContractStepTimers()
                setContractStep(CONTRACT_STEPS.length - 1)
                const finish = setTimeout(() => {
                    setContractStage('ready')
                    setContractResult({
                        filename: file?.name || '合同文件',
                        size: file?.size,
                        filledCount: totalFilled,
                        countries: nextCountries,
                        businessType: payload.business_type || null,
                        uploadedAt: new Date().toLocaleString('zh-CN', { hour12: false }),
                    })
                }, 500)
                contractStepTimersRef.current.push(finish)

                // 置信度较低的字段做二次提醒
                const lowConfHits = Object.entries(confidence)
                    .filter(([, v]) => typeof v === 'number' && v < 0.5)
                    .map(([k]) => k)
                if (lowConfHits.length && Object.keys(rawHits).length) {
                    notification.info({
                        message: '以下字段建议人工二次确认',
                        description: (
                            <div style={{ maxHeight: 160, overflow: 'auto', fontSize: 12 }}>
                                {lowConfHits.map(k => (
                                    <div key={k}>· <b>{k}</b>：{rawHits[k] || '—'}</div>
                                ))}
                            </div>
                        ),
                        placement: 'topRight',
                        duration: 6,
                    })
                }
            }, 0)

            onSuccess?.(payload, file)
        } catch (err) {
            resetContractCard()
            const detail = err?.response?.data?.detail || err?.message || '解析失败'
            message.error(`合同解析失败：${detail}`)
            onError?.(err)
        } finally {
            setContractExtracting(false)
        }
    }

    // 获取国家配置
    const getCountryConfig = (code) => {
        return countryConfigs[code] || {}
    }

    // 获取国家国旗emoji（来自后端配置）
    const getCountryFlag = (code) => {
        return countryConfigs[code]?.flag || '🌍'
    }

    // 根据字段类型渲染表单控件
    const renderFormField = (field, fieldName) => {
        const rules = []

        // 必填校验
        if (field.required) {
            let placeholderText = field.placeholder || field.label
            // 如果已有"请"开头，就不再加前缀
            if (placeholderText.startsWith('请')) {
                placeholderText = placeholderText.replace(/^请/, '')
            }
            // 根据字段类型选择合适的动词
            const action = field.type === 'select' || field.type === 'multiselect' ? '选择' : '输入'
            rules.push({
                required: true,
                message: `请${action}${placeholderText}`,
            })
        }

        // 数字字段额外校验
        if (field.type === 'number') {
            // 防止 JavaScript 大数字精度丢失（Number.MAX_SAFE_INTEGER = 9007199254740991
            const safeMax = Math.min(field.max_value || 999999999999999, 9007199254740991)

            if (field.min_value !== undefined && field.min_value !== null) {
                rules.push({
                    type: 'number',
                    min: field.min_value,
                    message: `${field.label} 不能小于 ${field.min_value}`,
                })
            }
            rules.push({
                type: 'number',
                max: safeMax,
                message: `${field.label} 不能超过 ${safeMax.toLocaleString()}（防止精度丢失）`,
            })
        }

        switch (field.type) {
            case 'number':
                return (
                    <Form.Item name={fieldName} label={field.label} rules={rules} key={fieldName}>
                        <InputNumber
                            className="full-width"
                            min={field.min_value}
                            max={field.max_value}
                            placeholder={field.placeholder}
                            formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                            parser={value => value.replace(/\$\s?|(,*)/g, '')}
                        />
                    </Form.Item>
                )
            case 'select':
                return (
                    <Form.Item name={fieldName} label={field.label} rules={rules} key={fieldName}>
                        <Select placeholder={field.placeholder || `请选择${field.label}`}>
                            {field.options.map(opt => (
                                <Select.Option key={opt} value={opt}>{opt}</Select.Option>
                            ))}
                        </Select>
                    </Form.Item>
                )
            case 'multiselect':
                return (
                    <Form.Item name={fieldName} label={field.label} rules={rules} key={fieldName}>
                        <Select mode="multiple" placeholder={field.placeholder || `请选择${field.label}`}>
                            {field.options.map(opt => (
                                <Select.Option key={opt} value={opt}>{opt}</Select.Option>
                            ))}
                        </Select>
                    </Form.Item>
                )
            default:
                return null
        }
    }

    const tabs = useMemo(
        () => [
            {
                key: 'hero',
                label: '首页',
                children: <HeroLanding onNavigate={(key) => setActiveTab(key)} />,
            },
            {
                key: 'dashboard',
                label: '数据看板',
                children: <DashboardTab getCountryFlag={getCountryFlag} onOpenPush={() => setActiveTab('push')} />,
            },
            {
                key: 'push',
                label: '为你推送',
                children: (
                    <div className="push-tab-content">
                        <PolicyPushCard />
                    </div>
                ),
            },
            {
                key: 'qa',
                label: '法规问答',
                children: (
                    <div className="qa-tab-content">
                        <TutorialGuide
                            storageKey="tcr-tour-qa-v1"
                            demoLabel="填入示例问题"
                            demoStepIndex={1}
                            onFillDemo={() => {
                                qaForm.setFieldsValue({
                                    query_text: '我们是跨境电商，月销售额约 60 万泰铢，是否需要在泰国注册 VAT？TikTok Shop 平台代扣代缴如何处理？',
                                })
                                setChatDockOpen(true)
                                message.success('已填入示例问题，点击"提交问答"即可体验流式回答')
                                setTimeout(() => {
                                    document.querySelector('.chat-input-card textarea')?.focus()
                                }, 200)
                            }}
                            steps={[
                                {
                                    title: '欢迎使用「法规问答」',
                                    description: '基于 RAG 的法规检索问答，AI 会先向量检索最相关的法规条文，再结合上下文流式生成回答，并附带可追溯的来源。',
                                    target: () => document.querySelector('.qa-tab-content'),
                                },
                                {
                                    title: '① 在底部输入你的问题',
                                    description: '这里是常驻的悬浮提问框，随时可以展开/收起。回车快速提交，Shift+回车换行。',
                                    target: () => document.querySelector('.chat-input-card'),
                                    placement: 'top',
                                },
                                {
                                    title: '② 开启思考模式（可选）',
                                    description: '打开后 AI 会进行更深入的推理，响应稍慢但回答更严谨，适合复杂合规判断。',
                                    target: () => document.querySelector('.chat-input-card .think-mode-toggle'),
                                    placement: 'top',
                                },
                                {
                                    title: '③ 实时查看流式回答',
                                    description: 'AI 会以 Token 级流式方式逐字呈现回答；生成完毕后可在文末点击「引用来源」标签跳转到法规原文并高亮定位段落。',
                                    target: () => document.querySelector('.chat-result-card'),
                                },
                                {
                                    title: '④ 历史问答一览',
                                    description: '所有问答都会持久化，点击历史记录可查看当时的完整回答、来源和高亮片段。',
                                    target: () => document.querySelector('.qa-history-card'),
                                },
                            ]}
                        />
                        <PolicyPushMarquee onOpenPage={() => setActiveTab('push')} />
                        <div className="qa-layout-grid">
                            {/* 主区：回答结果 */}
                            <div className="qa-main-column">
                                <Card
                                    className="tech-card chat-result-card"
                                    title="回答结果"
                                    extra={qaResult && <PDFExportButton type="qa" data={qaResult} exportFn={exportQAResultToPDF} buttonText="导出报告" />}
                                >
                                    {loadingQa ? (
                                        <div>
                                            <AIGeneratedBadge />
                                            <ThinkingIndicator mode="carousel" />
                                            <div
                                                className="result-list"
                                                style={{ marginTop: '16px' }}
                                            >
                                                <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.8' }}>
                                                    <StreamingAnswerDisplay text={qaStreamText} placeholder="正在生成回答..." />
                                                </div>
                                            </div>
                                        </div>
                                    ) : qaResult ? (
                                        <div className="result-list">
                                            <AIGeneratedBadge />
                                            <div className="question-label">
                                                <Text strong>问题：{qaResult.query_text}</Text>
                                            </div>
                                            <Paragraph
                                                style={{
                                                    whiteSpace: 'pre-wrap',
                                                    lineHeight: '1.8',
                                                    marginTop: '16px',
                                                }}
                                            >
                                                {renderAnswerWithSourceLinks(
                                                    qaResult.answer_text?.core_rules || qaResult.answer_text?.answer || '',
                                                    (filename, title) => setRegulationModal({
                                                        open: true,
                                                        filename,
                                                        title,
                                                        highlight: pickSnippet(sourceSnippets, filename, regulationAliases),
                                                        positions: pickPositions(sourcePositions, filename, regulationAliases),
                                                    }),
                                                    regulationAliases,
                                                )}
                                            </Paragraph>
                                            {qaResult.answer_text?.original_link && (
                                                <p>
                                                    <Text strong>原文链接：</Text>{qaResult.answer_text.original_link}
                                                </p>
                                            )}
                                            <Paragraph className="disclaimer-text">{qaResult.disclaimer}</Paragraph>
                                        </div>
                                    ) : (
                                        <div className="empty-state">
                                            <StreamingAnswerDisplay
                                                key={currentSloganIndex}
                                                text={currentSlogans[currentSloganIndex] || PLACEHOLDER_SLOGANS[0]}
                                                placeholder="请输入问题..."
                                            />
                                        </div>
                                    )}
                                </Card>
                            </div>

                            {/* 侧栏：历史问答（sticky） */}
                            <aside className="qa-side-column">
                                <Card className="tech-card qa-history-card" title="历史问答">
                                    {qaHistory.length > 0 ? (
                                        <List
                                            dataSource={qaHistory.slice(0, 10)}
                                            renderItem={(item) => (
                                                <List.Item
                                                    className="history-list-item"
                                                    style={{ cursor: 'pointer' }}
                                                    onClick={() => setQaHistoryModal({ open: true, qaId: item.qa_id })}
                                                >
                                                    <div className="history-item-body">
                                                        <Text strong className="history-item-title" ellipsis={{ tooltip: item.query_text }}>
                                                            {item.query_text}
                                                        </Text>
                                                        <div className="history-item-meta">
                                                            <Text type="secondary" className="history-item-time">{formatTime(item.create_time)}</Text>
                                                            {Array.isArray(item.sources) && item.sources.length > 0 && (
                                                                <span className="history-item-sources" title={item.sources.join(' · ')}>
                                                                    <FileTextOutlined className="history-item-sources-icon" />
                                                                    {item.sources.length}
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                </List.Item>
                                            )}
                                        />
                                    ) : (
                                        <div className="empty-hint">暂无历史记录</div>
                                    )}
                                </Card>
                            </aside>
                        </div>
                    </div>
                ),
            },
            {
                key: 'audit',
                label: '合规审核',
                children: (
                    <div className="audit-tab-content">
                        <TutorialGuide
                            storageKey="tcr-tour-audit-v1"
                            demoLabel="一键填入示例业务档案"
                            demoStepIndex={2}
                            onFillDemo={() => {
                                const demoCountries = ['TH', 'VN']
                                setSelectedCountries(demoCountries)
                                // 等下一次渲染把国家动态字段挂上再填值
                                setTimeout(() => {
                                    auditForm.setFieldsValue({
                                        countries: demoCountries,
                                        business_type: '跨境电商零售',
                                        // TH
                                        annual_sales_TH: 24000000,
                                        monthly_orders_TH: 8000,
                                        platforms_TH: ['Shopee', 'Lazada', 'TikTok Shop'],
                                        product_categories_TH: ['电子产品', '服饰', '美妆'],
                                        warehousing_mode_TH: '海外仓',
                                        has_local_entity_TH: '否',
                                        // VN
                                        annual_sales_VN: 3200000000,
                                        monthly_orders_VN: 5000,
                                        platforms_VN: ['Shopee', 'TikTok Shop'],
                                        product_categories_VN: ['服饰', '家居'],
                                        warehousing_mode_VN: '直邮',
                                        has_local_entity_VN: '否',
                                    })
                                    message.success('已填入泰国 + 越南示例档案，点击"提交审核"即可查看多国流式审核过程')
                                }, 150)
                            }}
                            steps={[
                                {
                                    title: '欢迎使用「合规审核」',
                                    description: '输入业务档案后，AI 会为每个国家并行分析税务合规风险，逐条流式生成建议，最终可一键导出 PDF 报告。',
                                    target: () => document.querySelector('.audit-tab-content'),
                                },
                                {
                                    title: '① 选择审核国家',
                                    description: '支持多选。每个国家都有独立的税种、法规库与业务字段，可覆盖东南亚主流市场。',
                                    target: () => document.querySelector('.audit-form-card .ant-form-item:first-child'),
                                    placement: 'right',
                                },
                                {
                                    title: '② 填写业务档案',
                                    description: '不同国家会动态显示不同的业务字段（销售额、平台、仓储模式等），全部由后端 YAML 驱动，字段自适应。',
                                    target: () => document.querySelector('.audit-form-card .country-section'),
                                    placement: 'right',
                                },
                                {
                                    title: '③ 开启思考模式（可选）',
                                    description: '思考模式下 AI 会做更深入的多步推理，适合展示时选择，突出结构化风险分析能力。',
                                    target: () => document.querySelector('.audit-form-card .think-mode-toggle'),
                                    placement: 'top',
                                },
                                {
                                    title: '④ 实时流式审核结果',
                                    description: '结果卡片会显示整体总结、各国风险分级（高/中/低）、专业建议——所有内容以 SSE Token 流式增量渲染。',
                                    target: () => document.querySelector('.audit-result-card'),
                                },
                                {
                                    title: '⑤ 审核历史 & PDF 导出',
                                    description: '每次审核都会自动落库，可回看详情；右上角"导出报告"一键生成 PDF，方便交付客户。',
                                    target: () => document.querySelector('.audit-history-card'),
                                },
                            ]}
                        />
                        <PolicyPushMarquee onOpenPage={() => setActiveTab('push')} />
                        {/* 使用 CSS Grid 实现响应式布局：窄屏1列，宽屏2列 */}
                        <div className="audit-layout-grid">
                            {/* 1. 表单卡片 - 始终在最前 */}
                            <Card className="tech-card audit-form-card" title="合规审核">
                            <Form
                                form={auditForm}
                                layout="vertical"
                                initialValues={{ platforms: {} }}
                                onFinish={async (values) => {
                                    // 每次提交先清空旧结果并关闭上一次流，避免旧内容残留或串线
                                    auditRunIdRef.current += 1
                                    const currentRunId = auditRunIdRef.current
                                    if (auditStreamRef.current) {
                                        auditStreamRef.current.close?.()
                                        auditStreamRef.current = null
                                    }
                                    setAuditResult(null)
                                    setLoadingAudit(true)
                                    try {
                                        // 构造多国审核请求 - 根据配置动态生成 by_country 字段
                                        const business_profile = {
                                            business_type: values.business_type,
                                        }

                                        // 为每个配置字段生成 by_country 字典
                                        selectedCountries.forEach(code => {
                                            const config = countryConfigs[code]
                                            if (config?.business_fields) {
                                                config.business_fields.forEach(field => {
                                                    const dictName = `${field.name}_by_country`
                                                    if (!business_profile[dictName]) {
                                                        business_profile[dictName] = {}
                                                    }
                                                    business_profile[dictName][code] = values[`${field.name}_${code}`]
                                                })
                                            }
                                        })

                                        const payload = {
                                            selected_countries: selectedCountries,
                                            business_profile,
                                        }

                                        // 使用 SSE 流式提交，避免超时
                                        // 将思考模式标记随提交传递到后端
                                        payload.think_mode = !!thinkMode
                                        const taskInfo = await submitSseAudit(payload)
                                        message.info('审核任务已提交，正在执行...')

                                        // 监听 SSE 结果流
                                        auditStreamRef.current = listenAuditResult(taskInfo.task_id, {
                                            onProgress: (progress, message) => {
                                                if (auditRunIdRef.current !== currentRunId) return
                                                // 更新进度提示
                                                setAuditResult(prev => ({
                                                    ...(prev || {}),
                                                    isLoading: true,
                                                    progress,
                                                    message,
                                                }))
                                            },
                                            onResultStart: (data) => {
                                                if (auditRunIdRef.current !== currentRunId) return
                                                setAuditResult(prev => ({
                                                    ...(prev || {}),
                                                    isLoading: true,
                                                    result_streaming: true,
                                                    stream_message: data?.message || '审核结果生成中...',
                                                }))
                                            },
                                            onResultSection: (chunk) => {
                                                if (auditRunIdRef.current !== currentRunId) return
                                                setAuditResult(prev => {
                                                    const next = { ...(prev || {}), isLoading: true, result_streaming: true }

                                                    if (chunk.section === 'overall_summary') {
                                                        next.overall_summary = chunk.value
                                                    } else if (chunk.section === 'country_result' && chunk.country_code) {
                                                        next.results_by_country = {
                                                            ...(next.results_by_country || {}),
                                                            [chunk.country_code]: chunk.value,
                                                        }
                                                    } else if (chunk.section === 'all_risks') {
                                                        next.all_risks = chunk.value
                                                    } else if (chunk.section === 'all_suggestions') {
                                                        // 如果后端一次性发回所有建议，直接使用
                                                        next.all_suggestions = chunk.value
                                                    } else if (chunk.section === 'suggestion_start') {
                                                        // 为单条建议创建占位
                                                        const idx = Number(chunk.suggestion_index || 0)
                                                        if (!next._streaming_suggestions) next._streaming_suggestions = []
                                                        while (next._streaming_suggestions.length <= idx) next._streaming_suggestions.push({ content: '', source_info: chunk.source || chunk.metadata })
                                                        // 同步到展示数组
                                                        next.all_suggestions = next._streaming_suggestions
                                                    } else if (chunk.section === 'suggestion_complete') {
                                                        const idx = Number(chunk.suggestion_index || 0)
                                                        if (!next._streaming_suggestions) next._streaming_suggestions = []
                                                        while (next._streaming_suggestions.length <= idx) next._streaming_suggestions.push({ content: '' })
                                                        next._streaming_suggestions[idx].content = chunk.value || next._streaming_suggestions[idx].content
                                                        if (chunk.source) next._streaming_suggestions[idx].source_info = chunk.source
                                                        // 将流式建议镜像到 all_suggestions（覆盖）
                                                        next.all_suggestions = next._streaming_suggestions
                                                    } else if (chunk.section === 'disclaimer') {
                                                        next.disclaimer = chunk.value
                                                    }

                                                    return next
                                                })
                                            },
                                            onResultToken: (chunk) => {
                                                if (auditRunIdRef.current !== currentRunId) return
                                                setAuditResult(prev => {
                                                    const next = { ...(prev || {}), isLoading: true, result_streaming: true }

                                                    // 初始化临时流式建议缓存
                                                    if (!next._streaming_suggestions) {
                                                        next._streaming_suggestions = []
                                                    }

                                                    if (chunk.section === 'all_suggestions') {
                                                        const idx = Number(chunk.suggestion_index || 0)
                                                        while (next._streaming_suggestions.length <= idx) {
                                                            next._streaming_suggestions.push({ content: '', source_info: null, suggestion_type: 'professional' })
                                                        }
                                                        next._streaming_suggestions[idx].content = (next._streaming_suggestions[idx].content || '') + (chunk.delta || '')
                                                        // 将流式建议镜像到 all_suggestions，供展示组件渲染
                                                        next.all_suggestions = next._streaming_suggestions
                                                    } else if (chunk.section === 'overall_summary') {
                                                        next.overall_summary = (next.overall_summary || '') + (chunk.delta || '')
                                                    } else if (chunk.section === 'disclaimer') {
                                                        next.disclaimer = (next.disclaimer || '') + (chunk.delta || '')
                                                    }

                                                    return next
                                                })
                                            },
                                            onComplete: async (result) => {
                                                if (auditRunIdRef.current !== currentRunId) return
                                                setAuditResult({
                                                    ...result,
                                                    isLoading: false,
                                                    result_streaming: false,
                                                })
                                                auditStreamRef.current = null
                                                message.success('审核完成')
                                                setLoadingAudit(false)
                                                await loadHistory()
                                            },
                                            onError: (errorMsg) => {
                                                if (auditRunIdRef.current !== currentRunId) return
                                                message.error(errorMsg || '审核失败')
                                                setLoadingAudit(false)
                                                setAuditResult(null)
                                                auditStreamRef.current = null
                                            },
                                        })
                                    } catch (error) {
                                        // SSE 连接失败，降级到普通请求
                                        const errData = error?.response?.data
                                        let errorMsg = errData?.detail || errData?.msg || '提交失败，请稍后重试'
                                        message.error(errorMsg)
                                        setLoadingAudit(false)
                                        auditStreamRef.current = null
                                    }
                                }}
                            >
                                <div className="contract-upload-wrapper">
                                    {contractStage === 'ready' && contractResult ? (
                                        <div className="contract-file-card">
                                            <div className="contract-file-icon">
                                                {getFileTypeIcon(contractResult.filename)}
                                            </div>
                                            <div className="contract-file-main">
                                                <div className="contract-file-title-row">
                                                    <span className="contract-file-name" title={contractResult.filename}>
                                                        {contractResult.filename || '合同文件'}
                                                    </span>
                                                    <span className="contract-file-badge">
                                                        <CheckCircleFilled /> 已识别 {contractResult.filledCount} 个字段
                                                    </span>
                                                </div>
                                                <div className="contract-file-meta">
                                                    <span>{formatBytes(contractResult.size)}</span>
                                                    <span className="contract-file-dot">·</span>
                                                    <span>{contractResult.uploadedAt}</span>
                                                    {contractResult.businessType && (
                                                        <>
                                                            <span className="contract-file-dot">·</span>
                                                            <span>{contractResult.businessType}</span>
                                                        </>
                                                    )}
                                                </div>
                                                {contractResult.countries?.length > 0 && (
                                                    <div className="contract-file-tags">
                                                        {contractResult.countries.map(code => (
                                                            <span key={code} className="contract-country-chip">
                                                                {getCountryFlag(code)} {getCountryName(code)}
                                                            </span>
                                                        ))}
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
                                                    disabled={contractExtracting || loadingAudit}
                                                    beforeUpload={() => true}
                                                    customRequest={({ file, onSuccess, onError }) => {
                                                        // 复用主 dragger 的处理器：直接触发一次同样的抽取
                                                        runContractExtract(file, onSuccess, onError)
                                                    }}
                                                >
                                                    <Button
                                                        type="text"
                                                        size="small"
                                                        icon={<ReloadOutlined />}
                                                        loading={contractExtracting}
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
                                            disabled={contractExtracting || loadingAudit}
                                            className="contract-upload-dragger"
                                            customRequest={({ file, onSuccess, onError }) => runContractExtract(file, onSuccess, onError)}
                                        >
                                            {contractStage === 'scanning' ? (
                                                <div className="contract-dragger-inner contract-dragger-scanning">
                                                    <div className="contract-scan-head">
                                                        <div className="contract-scan-icon">
                                                            <span className="contract-scan-doc" />
                                                            <span className="contract-scan-beam" />
                                                        </div>
                                                        <div className="contract-scan-title-block">
                                                            <div className="contract-step-index">
                                                                步骤 {contractStep + 1} / {CONTRACT_STEPS.length}
                                                            </div>
                                                            <div
                                                                key={contractStep}
                                                                className="contract-dragger-title contract-step-fade"
                                                            >
                                                                <LoadingOutlined /> {CONTRACT_STEPS[contractStep]?.label ?? '解析中'}
                                                            </div>
                                                            <div
                                                                key={`d-${contractStep}`}
                                                                className="contract-dragger-hint contract-step-fade"
                                                            >
                                                                {CONTRACT_STEPS[contractStep]?.desc ?? ''}
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <div className="contract-progress-track">
                                                        <div
                                                            className="contract-progress-fill"
                                                            style={{ width: `${((contractStep + 1) / CONTRACT_STEPS.length) * 100}%` }}
                                                        />
                                                    </div>
                                                </div>
                                            ) : (
                                                <div className="contract-dragger-inner">
                                                    <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                                                    <p className="ant-upload-text">拖入或点击上传合同（PDF / DOCX / TXT）</p>
                                                    <p className="ant-upload-hint">AI 将自动识别国家 / 业务类型 / 销售额等字段，帮你填好表单</p>
                                                </div>
                                            )}
                                        </Upload.Dragger>
                                    )}
                                </div>

                                <Form.Item name="countries" label="选择审核国家（可多选）" rules={[{ required: true, message: '请至少选择一个审核国家' }]}>
                                    <Select
                                        mode="multiple"
                                        placeholder="请选择要审核的国家"
                                        value={selectedCountries}
                                        onChange={setSelectedCountries}
                                        options={countries.map(c => ({
                                            value: c.code,
                                            label: `${getCountryFlag(c.code)} ${c.name} (${c.tax_type})`
                                        }))}
                                        style={{ width: '100%' }}
                                    />
                                </Form.Item>

                                <Form.Item name="business_type" label="业务类型" rules={[{ required: true, message: '请选择业务类型' }]}>
                                    <Select options={[
                                        { value: '跨境电商零售', label: '跨境电商零售' },
                                        { value: '品牌出海直营', label: '品牌出海直营' },
                                        { value: '外贸综合服务', label: '外贸综合服务' },
                                    ]} />
                                </Form.Item>

                                {/* 为每个选中国家根据配置动态生成表单字段 */}
                                {selectedCountries.map(code => {
                                    const config = countryConfigs[code]
                                    if (!config?.business_fields) return null

                                    return (
                                        <div key={code} className="country-section">
                                            <Title level={5}>{getCountryFlag(code)} {getCountryName(code)} 业务信息</Title>
                                            {config.business_fields.map(field =>
                                                renderFormField(field, `${field.name}_${code}`)
                                            )}
                                        </div>
                                    )
                                })}

                                <div className="form-action-bar">
                                    <div className="think-mode-toggle think-mode-toggle-flat">
                                        <Switch checked={thinkMode} onChange={setThinkMode} />
                                        <div className="think-mode-text">
                                            <div className="think-mode-title">思考模式</div>
                                            <div className="think-mode-hint">响应更慢，分析更深入</div>
                                        </div>
                                    </div>
                                    <Button className="tech-btn-primary" type="primary" htmlType="submit" loading={loadingAudit} disabled={selectedCountries.length === 0}>
                                        提交审核
                                    </Button>
                                </div>

                            </Form>
                        </Card>

                        <Card
                            className="tech-card audit-result-card"
                            title="审核结果"
                            extra={!loadingAudit && auditResult ? <PDFExportButton type="audit" data={auditResult} exportFn={exportAuditReportToPDF} buttonText="导出报告" /> : null}
                        >
                            {loadingAudit ? (
                                <div>
                                    <AIGeneratedBadge />
                                    <ThinkingIndicator mode="carousel" />
                                    {auditResult?.isLoading && auditResult?.progress !== undefined && (
                                        <div style={{ marginTop: '16px' }}>
                                            <div style={{
                                                width: '100%',
                                                height: '4px',
                                                background: 'var(--ink-100)',
                                                borderRadius: '999px',
                                                overflow: 'hidden'
                                            }}>
                                                <div style={{
                                                    width: `${auditResult.progress}%`,
                                                    height: '100%',
                                                    background: 'var(--ink-900)',
                                                    transition: 'width 0.3s ease'
                                                }} />
                                            </div>
                                            <p style={{ textAlign: 'center', color: 'var(--ink-400)', marginTop: '8px', fontSize: 12 }}>
                                                {auditResult.message || '审核进行中...'} ({auditResult.progress}%)
                                            </p>
                                        </div>
                                    )}
                                    {auditResult && (
                                        <div style={{ marginTop: '16px' }}>
                                            <AuditResultDisplay
                                                auditResult={auditResult}
                                                getCountryFlag={getCountryFlag}
                                                onCountryClick={(code) => setSelectedCountries([code])}
                                                onRegulationClick={(name, title) => setRegulationModal({ open: true, filename: name, title, highlight: '' })}
                                                isLoading={loadingAudit}
                                            />
                                        </div>
                                    )}
                                </div>
                            ) : auditResult ? (
                                <div>
                                    <AIGeneratedBadge />
                                    <AuditResultDisplay
                                        auditResult={auditResult}
                                        getCountryFlag={getCountryFlag}
                                        onCountryClick={(code) => setSelectedCountries([code])}
                                        onRegulationClick={(name, title) => setRegulationModal({ open: true, filename: name, title, highlight: '' })}
                                        isLoading={loadingAudit}
                                    />
                                </div>
                            ) : (
                                <div className="empty-state">
                                    <StreamingAnswerDisplay
                                        key={`audit-slogan-${currentSloganIndex}`}
                                        text={currentSlogans[currentSloganIndex] || PLACEHOLDER_SLOGANS[0]}
                                        placeholder="请选择国家和业务类型后提交..."
                                    />
                                </div>
                            )}
                        </Card>

                        <Card className="tech-card audit-history-card" title="审核历史">
                            <List
                                dataSource={auditHistory}
                                renderItem={(item) => (
                                    <List.Item className="history-list-item" style={{ cursor: 'pointer' }} onClick={async () => {
                                        try {
                                            const data = await fetchAuditHistoryDetail(item.audit_id)
                                            setAuditHistoryModal({
                                                open: true,
                                                auditId: item.audit_id,
                                                auditDetail: data.data,
                                            })
                                        } catch {
                                            message.error('获取审核详情失败')
                                        }
                                    }}>
                                        <Space direction="vertical" size={4} style={{ width: '100%' }}>
                                            <Text strong style={{ fontSize: 13 }}>{item.summary_title || item.business_type}</Text>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                                                <Text type="secondary" style={{ fontSize: 12, whiteSpace: 'nowrap' }}>{formatTime(item.create_time)}</Text>
                                                <div>
                                                    <Tag className="risk-tag risk-high">高 {item.risk_count?.high_risk || 0}</Tag>
                                                    <Tag className="risk-tag risk-medium">中 {item.risk_count?.medium_risk || 0}</Tag>
                                                    <Tag className="risk-tag risk-low">低 {item.risk_count?.low_risk || 0}</Tag>
                                                </div>
                                            </div>
                                        </Space>
                                    </List.Item>
                                )}
                            />
                        </Card>
                    </div>
                </div>
                ),
            },
            {
                key: 'guide',
                label: '合规指南',
                children: (
                    <GuideTab
                        onOpenRegulation={(filename, title, highlight) =>
                            setRegulationModal({ open: true, filename, title, highlight })
                        }
                    />
                ),
            },
        ],
        [auditForm, auditHistory, auditResult, contractExtracting, countries, countryConfigs, currentSloganIndex, loadingAudit, loadingQa, qaForm, qaHistory, qaResult, qaStreamText, selectedCountries, sourceSnippets, thinkMode],
    )

    return (
        <div
            className={`app-shell app-shell-tab-${activeTab} ${
                activeTab === 'qa' && chatDockOpen ? 'chat-dock-open' : 'chat-dock-closed'
            }`}
            style={{ '--chat-dock-height': `${chatDockHeight}px` }}
        >
            {activeTab !== 'hero' && (
            <div className="hero">
                <div className="hero-brand">
                    <span className="hero-eyebrow">TAX COMPLIANCE RADAR</span>
                    <h1 className="hero-title">
                        <span className="hero-title-text">税务合规雷达</span>
                        <span className="hero-subtitle">Multi-Jurisdiction Intelligence</span>
                    </h1>
                </div>
                <div className="hero-disclaimer" role="note" aria-label="免责声明">
                    <span className="hero-disclaimer-label">Disclaimer</span>
                    <span className="hero-disclaimer-text">{disclaimer}</span>
                </div>
            </div>
            )}
            <Menu
                mode="horizontal"
                selectedKeys={[activeTab]}
                onClick={({ key }) => setActiveTab(key)}
                className="tech-nav-menu"
                items={[
                    { key: 'hero', icon: <HomeOutlined />, label: '首页' },
                    { key: 'dashboard', icon: <DashboardOutlined />, label: '数据看板' },
                    { key: 'push', icon: <NotificationOutlined />, label: '为你推送' },
                    { key: 'qa', icon: <QuestionCircleOutlined />, label: '法规问答' },
                    {
                        key: 'flow-1',
                        disabled: true,
                        className: 'nav-flow-sep',
                        label: <RightOutlined />,
                    },
                    { key: 'audit', icon: <AuditOutlined />, label: '合规审核' },
                    {
                        key: 'flow-2',
                        disabled: true,
                        className: 'nav-flow-sep',
                        label: <RightOutlined />,
                    },
                    { key: 'guide', icon: <SafetyOutlined />, label: '合规指南' },
                ]}
            />
            <div className="tab-content-wrapper">
                {tabs.find(t => t.key === activeTab)?.children}
            </div>

            {/* 问答页面底部悬浮输入 —— 可折叠固钉（fixed 定位） */}
            <div
                ref={chatDockRef}
                className={`chat-dock ${activeTab === 'qa' ? 'active' : ''} ${chatDockOpen ? 'expanded' : 'collapsed'}`}
                aria-hidden={activeTab !== 'qa'}
            >
                <div className="chat-dock-inner">
                    {/* 展开态 —— 卡片 */}
                    <div
                        className="chat-dock-stage chat-dock-stage-expanded"
                        inert={!chatDockOpen ? '' : undefined}
                    >
                        <Card className="tech-card chat-input-card">
                            <div className="chat-dock-header">
                                <div className="chat-dock-title">
                                    <MessageOutlined className="chat-dock-title-icon" />
                                    <span>提问</span>
                                    {loadingQa && <span className="chat-dock-status">生成中…</span>}
                                </div>
                                <Tooltip title="收起">
                                    <Button
                                        type="text"
                                        size="small"
                                        className="chat-dock-collapse-btn"
                                        icon={<DownOutlined />}
                                        onClick={() => setChatDockOpen(false)}
                                        aria-label="收起提问框"
                                        tabIndex={chatDockOpen ? 0 : -1}
                                    />
                                </Tooltip>
                            </div>
                            <Form form={qaForm} layout="vertical" onFinish={async (values) => {
                                setLoadingQa(true)
                                setQaStreamText('')
                                setQaStreaming(true)
                                try {
                                    const taskInfo = await submitStreamQaWithMode(values.query_text, thinkMode)
                                    listenQaStream(taskInfo.task_id, {
                                        onSearchStart: () => message.info('正在检索相关法规...'),
                                        onSearchComplete: (data) => {
                                            if (data.snippets) setSourceSnippets(prev => ({ ...prev, ...data.snippets }))
                                            if (data.positions) setSourcePositions(prev => ({ ...prev, ...data.positions }))
                                            if (import.meta.env.DEV) {
                                                console.debug('[QA] search_complete', { sources: data.sources, snippets: data.snippets })
                                            }
                                            message.success(`检索到 ${data.sources?.length || 0} 条相关法规`)
                                        },
                                        onAnswerStart: () => setQaResult(null),
                                        onAnswerDelta: (_, fullText) => {
                                            setQaStreamText(prev => fullText && fullText.length >= prev.length ? fullText : (fullText || prev))
                                        },
                                        onComplete: async (data) => {
                                            const rawAnswer = data.answer || data.core_rules || ''
                                            const regulationBase = data.regulation_base || ''
                                            const sourceMarker = '**引用来源：**'
                                            let displayCoreRules = data.core_rules || rawAnswer
                                            if (regulationBase && !String(displayCoreRules).includes(sourceMarker)) {
                                                displayCoreRules = String(rawAnswer || '') + '\n\n' + sourceMarker + '\n' + regulationBase
                                            }
                                            setQaResult({
                                                query_text: values.query_text,
                                                answer_text: {
                                                    answer: data.answer || rawAnswer,
                                                    core_rules: displayCoreRules,
                                                    regulation_base: regulationBase,
                                                    original_link: data.original_link || '',
                                                },
                                                disclaimer: data.disclaimer || disclaimer,
                                            })
                                            setQaStreamText(displayCoreRules || '')
                                            setQaStreaming(false)
                                            setLoadingQa(false)
                                            message.success('问答生成完成')
                                            await loadHistory()
                                        },
                                        onError: (errorMsg) => {
                                            message.error(errorMsg || '生成失败')
                                            setQaStreaming(false)
                                            setLoadingQa(false)
                                        }
                                    })
                                } catch (error) {
                                    message.error(error?.response?.data?.detail || '提交失败')
                                    setQaStreaming(false)
                                    setLoadingQa(false)
                                }
                            }}>
                                <Form.Item name="query_text" rules={[{ required: true, message: '请输入您要咨询的合规问题' }, { max: 500, message: '提问内容不能超过500字' }]} style={{ marginBottom: '12px' }}>
                                    <Input.TextArea
                                        autoSize={{ minRows: 2, maxRows: 5 }}
                                        placeholder="请输入您要咨询的合规问题，例如：跨境电商VAT注册有什么要求？"
                                        onPressEnter={(e) => {
                                            if (!e.shiftKey) {
                                                e.preventDefault()
                                                qaForm.submit()
                                            }
                                        }}
                                    />
                                </Form.Item>
                                <div className="form-action-bar">
                                    <div className="think-mode-toggle think-mode-toggle-flat">
                                        <Switch checked={thinkMode} onChange={setThinkMode} />
                                        <div className="think-mode-text">
                                            <div className="think-mode-title">思考模式</div>
                                            <div className="think-mode-hint">响应更慢，分析更深入</div>
                                        </div>
                                    </div>
                                    <Button className="tech-btn-primary" type="primary" htmlType="submit" loading={loadingQa} tabIndex={chatDockOpen ? 0 : -1}>
                                        提交问答
                                    </Button>
                                </div>
                            </Form>
                            <div className="chat-dock-footnote">
                                内容由 AI 生成，仅供参考 · © {new Date().getFullYear()} Tax Compliance Radar
                            </div>
                        </Card>
                    </div>

                    {/* 折叠态 —— 胶囊按钮 */}
                    <div className="chat-dock-stage chat-dock-stage-collapsed" aria-hidden={chatDockOpen}>
                        <button
                            type="button"
                            className="chat-dock-pill"
                            onClick={() => setChatDockOpen(true)}
                            aria-label="展开提问框"
                            tabIndex={chatDockOpen ? -1 : 0}
                        >
                            <MessageOutlined className="chat-dock-pill-icon" />
                            <span className="chat-dock-pill-label">
                                {loadingQa ? '生成中…' : '继续提问'}
                            </span>
                            {loadingQa && <span className="chat-dock-pill-dot" aria-hidden="true" />}
                        </button>
                    </div>
                </div>
            </div>
            

            {/* 法规文件查看弹窗 */}
            <RegulationModal
                open={regulationModal.open}
                filename={regulationModal.filename}
                title={regulationModal.title}
                highlight={regulationModal.highlight}
                onClose={() => setRegulationModal({ open: false, filename: '', title: '', highlight: '' })}
            />

            {/* QA历史详情弹窗 */}
            <QaHistoryModal
                open={qaHistoryModal.open}
                qaId={qaHistoryModal.qaId}
                onClose={() => setQaHistoryModal({ open: false, qaId: null })}
                onSourceClick={(filename, title, snippet, positions) => {
                    setQaHistoryModal({ open: false, qaId: null });
                    // 历史来源优先使用持久化的片段，回退到当前会话的实时 snippets
                    const highlight = snippet || pickSnippet(sourceSnippets, filename, regulationAliases);
                    const pos = positions || pickPositions(sourcePositions, filename, regulationAliases);
                    setRegulationModal({ open: true, filename, title, highlight, positions: pos });
                }}
            />

            {/* 审核历史详情弹窗 */}
            <Modal
                title="审核报告详情"
                open={auditHistoryModal.open}
                onCancel={() => setAuditHistoryModal({ open: false, auditId: null, auditDetail: null })}
                footer={[
                    <Button key="export" className="pdf-export-btn" icon={<FileTextOutlined />} onClick={() => {
                        if (auditHistoryModal.auditDetail?.audit_report) {
                            exportAuditReportToPDF(auditHistoryModal.auditDetail.audit_report);
                            message.success('导出成功');
                        }
                    }}>
                        导出PDF
                    </Button>,
                    <Button key="close" onClick={() => setAuditHistoryModal({ open: false, auditId: null, auditDetail: null })}>
                        关闭
                    </Button>,
                ]}
                width={800}
                styles={{ body: { maxHeight: '70vh', overflowY: 'auto', padding: 0 } }}
            >
                {auditHistoryModal.auditDetail?.audit_report && (
                    <div style={{ padding: '20px 24px' }}>
                        <AIGeneratedBadge />
                        <AuditResultDisplay
                            auditResult={auditHistoryModal.auditDetail.audit_report}
                            getCountryFlag={getCountryFlag}
                            onCountryClick={(code) => setSelectedCountries([code])}
                            onRegulationClick={(name, title) => {
                                setAuditHistoryModal({ open: false, auditDetail: null });
                                setRegulationModal({ open: true, filename: name, title, highlight: '' });
                            }}
                        />
                    </div>
                )}
            </Modal>

            <footer className="app-footer" hidden={activeTab === 'qa'}>
                <div className="app-footer-inner">
                    <span className="app-footer-brand">Tax Compliance Radar</span>
                    <span className="app-footer-divider" aria-hidden="true">·</span>
                    <span className="app-footer-note">本工具仅供参考，不构成税务或法律意见</span>
                    <span className="app-footer-spacer" />
                    <span className="app-footer-meta">© {new Date().getFullYear()}</span>
                </div>
            </footer>
            {import.meta.env.DEV && <DebugPanel />}
        </div>
    )
}

export default App
