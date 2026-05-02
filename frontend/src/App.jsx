import { useEffect, useMemo, useRef, useState } from 'react'

// 强制React更新
let forceUpdateCounter = 0
import { Affix, Button, Card, Form, Input, InputNumber, List, Modal, Select, Space, Tabs, Tag, Typography, message, Switch } from 'antd'
import { FileTextOutlined } from '@ant-design/icons'
import { fetchQaHistory, fetchAuditHistory, fetchAuditHistoryDetail, fetchCountries, fetchAllCountryConfigs, submitSseAudit, listenAuditResult, submitStreamQaWithMode, listenQaStream } from './api/client'
import ThinkingIndicator from './components/ThinkingIndicator'
import StreamingAnswerDisplay from './components/StreamingAnswerDisplay'
import AuditResultDisplay from './components/AuditResultDisplay'
import PDFExportButton from './components/PDFExportButton'
import RegulationModal from './components/RegulationModal'
import QaHistoryModal from './components/QaHistoryModal'
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
const renderAnswerWithSourceLinks = (answer, onSourceClick) => {
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
                        // 检测是否是文件名
                        const isFile = Object.keys(REGULATION_TITLES).some(filename => source.includes(filename))
                        if (isFile) {
                            const matchedFilename = Object.keys(REGULATION_TITLES).find(filename => source.includes(filename))
                            return (
                                <Tag
                                    key={idx}
                                    color="blue"
                                    icon={<FileTextOutlined />}
                                    onClick={() => onSourceClick(matchedFilename, REGULATION_TITLES[matchedFilename])}
                                    style={{ cursor: 'pointer' }}
                                >
                                    {REGULATION_TITLES[matchedFilename]}
                                </Tag>
                            )
                        }
                        // 普通文本来源
                        return <Tag key={idx}>{source}</Tag>
                    })}
                </Space>
            </div>
        </>
    )
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
    })
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
    const [countries, setCountries] = useState([])
    const [countryConfigs, setCountryConfigs] = useState({})
    const [selectedCountries, setSelectedCountries] = useState([])
    const [activeTab, setActiveTab] = useState('qa')
    const auditStreamRef = useRef(null)
    const auditRunIdRef = useRef(0)

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

    // 获取国家名称
    const getCountryName = (code) => {
        return countryConfigs[code]?.country_name || code
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
                key: 'qa',
                label: '法规问答',
                children: (
                    <div className="qa-tab-content">
                        <div className="chat-container">
                        {/* 上方：回答结果区域 */}
                        <Card
                            className="tech-card chat-result-card"
                            title="回答结果"
                            extra={qaResult && <PDFExportButton type="qa" data={qaResult} exportFn={exportQAResultToPDF} buttonText="导出报告" />}
                        >
                            {loadingQa ? (
                                <div>
                                    <ThinkingIndicator mode="carousel" />
                                    <div
                                        className="result-list"
                                        style={{ marginTop: '16px', minHeight: '100px' }}
                                    >
                                        <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.8' }}>
                                            <StreamingAnswerDisplay text={qaStreamText} placeholder="正在生成回答..." />
                                        </div>
                                    </div>
                                </div>
                            ) : qaResult ? (
                                <div className="result-list">
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
                                            // 优先使用 core_rules（包含来源标记），保证当前回答卡与历史详情一致
                                            qaResult.answer_text?.core_rules || qaResult.answer_text?.answer || '',
                                            (filename, title) => setRegulationModal({ open: true, filename, title })
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
                                <div style={{ textAlign: 'center', padding: '60px 20px', color: '#999' }}>
                                    <div style={{ fontSize: 16, minHeight: 60, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                        <StreamingAnswerDisplay
                                            key={currentSloganIndex}
                                            text={currentSlogans[currentSloganIndex] || PLACEHOLDER_SLOGANS[0]}
                                            placeholder="请输入问题..."
                                        />
                                    </div>
                                </div>
                            )}
                        </Card>

                        {/* 历史问答记录 */}
                        {qaHistory.length > 0 && (
                            <Card className="tech-card" title="历史问答" style={{ marginTop: '16px' }}>
                                <List
                                    dataSource={qaHistory.slice(0, 10)}
                                    renderItem={(item) => (
                                        <List.Item
                                            style={{ cursor: 'pointer' }}
                                            onClick={() => setQaHistoryModal({ open: true, qaId: item.qa_id })}
                                            actions={[
                                                <Text type="secondary" key="time" style={{ fontSize: '12px' }}>{item.create_time}</Text>
                                            ]}
                                        >
                                            <List.Item.Meta
                                                title={<Text strong style={{ fontSize: '14px' }}>{item.query_text}</Text>}
                                                description={<Text type="secondary" style={{ fontSize: '12px' }}>点击查看详情</Text>}
                                            />
                                        </List.Item>
                                    )}
                                />
                            </Card>
                        )}

                        </div>
                    </div>
                ),
            },
            {
                key: 'audit',
                label: '合规审核',
                children: (
                    <div className="audit-tab-content">
                        <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                        {/* 左侧列：表单 */}
                        <div style={{ flex: '1 1 400px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <Card className="tech-card" title="合规审核">
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
                                        <div key={code} style={{ padding: '12px', background: 'rgba(102, 126, 234, 0.05)', borderRadius: '8px', marginBottom: '12px', border: '1px solid rgba(102, 126, 234, 0.1)' }}>
                                            <Title level={5}>{getCountryFlag(code)} {getCountryName(code)} 业务信息</Title>
                                            {config.business_fields.map(field =>
                                                renderFormField(field, `${field.name}_${code}`)
                                            )}
                                        </div>
                                    )
                                })}

                                <Space style={{ display: 'block', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 12 }}>
                                        <Switch checked={thinkMode} onChange={setThinkMode} />
                                        <div style={{ fontSize: 12, color: '#666' }}>
                                            <div>思考模式</div>
                                            <div style={{ fontSize: 11, color: '#999' }}>开启后可能延长响应时间，但会尝试更深入分析</div>
                                        </div>
                                    </div>
                                    <Button className="tech-btn-primary" type="primary" htmlType="submit" loading={loadingAudit} disabled={selectedCountries.length === 0}>
                                        提交审核
                                    </Button>
                                </Space>

                            </Form>
                        </Card>

                        <Card className="tech-card" title="审核历史">
                            <List
                                dataSource={auditHistory}
                                renderItem={(item) => (
                                    <List.Item style={{ cursor: 'pointer' }} onClick={async () => {
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
                                        <Space direction="vertical" size={0} style={{ width: '100%' }}>
                                            <Text strong>{item.summary_title || item.business_type}</Text>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                                                <Text type="secondary" style={{ fontSize: 12 }}>{item.create_time}</Text>
                                                <div>
                                                    <Tag color="red" style={{ fontSize: 11, padding: '0 6px' }}>高: {item.risk_count?.high_risk || 0}</Tag>
                                                    <Tag color="orange" style={{ fontSize: 11, padding: '0 6px' }}>中: {item.risk_count?.medium_risk || 0}</Tag>
                                                    <Tag color="green" style={{ fontSize: 11, padding: '0 6px' }}>低: {item.risk_count?.low_risk || 0}</Tag>
                                                </div>
                                            </div>
                                        </Space>
                                    </List.Item>
                                )}
                            />
                        </Card>
                    </div>

                    {/* 右侧列：结果 */}
                    <div style={{ flex: '1 1 400px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        <Card
                            className="tech-card"
                            title="审核结果"
                            bodyStyle={{ minHeight: '600px' }}
                            extra={!loadingAudit && auditResult ? <PDFExportButton type="audit" data={auditResult} exportFn={exportAuditReportToPDF} buttonText="导出报告" /> : null}
                        >
                            {loadingAudit ? (
                                <div>
                                    <ThinkingIndicator mode="carousel" />
                                    {auditResult?.isLoading && auditResult?.progress !== undefined && (
                                        <div style={{ marginTop: '16px' }}>
                                            <div style={{
                                                width: '100%',
                                                height: '8px',
                                                background: '#f0f0f0',
                                                borderRadius: '4px',
                                                overflow: 'hidden'
                                            }}>
                                                <div style={{
                                                    width: `${auditResult.progress}%`,
                                                    height: '100%',
                                                    background: 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)',
                                                    transition: 'width 0.3s ease'
                                                }} />
                                            </div>
                                            <p style={{ textAlign: 'center', color: '#999', marginTop: '8px', fontSize: '12px' }}>
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
                                                isLoading={loadingAudit}
                                            />
                                        </div>
                                    )}
                                </div>
                            ) : auditResult ? (
                                <AuditResultDisplay
                                    auditResult={auditResult}
                                    getCountryFlag={getCountryFlag}
                                    onCountryClick={(code) => setSelectedCountries([code])}
                                    isLoading={loadingAudit}
                                />
                            ) : (
                                <div style={{ textAlign: 'center', padding: '60px 20px', color: '#999', minHeight: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <div style={{ fontSize: 14, lineHeight: 1.6 }}>
                                        <StreamingAnswerDisplay
                                            key={`audit-slogan-${currentSloganIndex}`}
                                            text={currentSlogans[currentSloganIndex] || PLACEHOLDER_SLOGANS[0]}
                                            placeholder="请选择国家和业务类型后提交..."
                                        />
                                    </div>
                                </div>
                            )}
                        </Card>
                    </div>
                    </div>
                </div>
                ),
            },
        ],
        [auditForm, auditHistory, auditResult, countries, currentSloganIndex, loadingAudit, loadingQa, qaForm, qaHistory, qaResult, qaStreamText, selectedCountries, thinkMode],
    )

    return (
        <div className="app-shell">
            <div className="hero">
                <div>
                    <Tag color="geekblue">Tax Compliance Radar - 多国支持版</Tag>
                    <Title level={2}>税务合规雷达</Title>
                    <Paragraph>面向多国税务合规场景的法规智能问答与合规风险审核。</Paragraph>
                </div>
                <Card className="hero-card tech-card" size="small">
                    <Text strong>免责声明</Text>
                    <Paragraph className="disclaimer-text">{disclaimer}</Paragraph>
                </Card>
            </div>
            <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabs} />

            {/* 问答页面底部悬浮输入卡片 */}
            <Affix offsetBottom={20} style={{ zIndex: 1000 }}>
                <div className={`chat-input-wrapper ${activeTab === 'qa' ? 'active' : ''}`}>
                    <div className="app-shell" style={{ paddingTop: 0, paddingBottom: 0, minHeight: 'auto', background: 'none' }}>
                        <Card
                            className="tech-card chat-input-card"
                            style={{
                                maxWidth: 'none',
                                boxShadow: '0 -8px 40px rgba(102, 126, 234, 0.18), 0 4px 20px rgba(0, 0, 0, 0.08)',
                                background: 'rgba(255, 255, 255, 0.95)',
                                backdropFilter: 'blur(20px)',
                                WebkitBackdropFilter: 'blur(20px)',
                                borderRadius: '20px',
                                border: '1px solid rgba(102, 126, 234, 0.15)',
                            }}
                        >
                            <Form form={qaForm} layout="vertical" onFinish={async (values) => {
                                setLoadingQa(true)
                                setQaStreamText('')
                                setQaStreaming(true)
                                try {
                                    const taskInfo = await submitStreamQaWithMode(values.query_text, thinkMode)
                                    listenQaStream(taskInfo.task_id, {
                                        onSearchStart: () => message.info('正在检索相关法规...'),
                                        onSearchComplete: (data) => message.success(`检索到 ${data.sources?.length || 0} 条相关法规`),
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
                                        rows={3}
                                        placeholder="请输入您要咨询的合规问题，例如：跨境电商VAT注册有什么要求？"
                                        onPressEnter={(e) => {
                                            if (!e.shiftKey) {
                                                e.preventDefault()
                                                qaForm.submit()
                                            }
                                        }}
                                    />
                                </Form.Item>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                        <Switch checked={thinkMode} onChange={setThinkMode} />
                                        <div style={{ fontSize: 12, color: '#666' }}>
                                            <div>思考模式</div>
                                            <div style={{ fontSize: 11, color: '#999' }}>开启后可能延长响应时间，但会尝试更深入分析</div>
                                        </div>
                                    </div>
                                    <div>
                                        <Button className="tech-btn-primary" type="primary" htmlType="submit" loading={loadingQa}>
                                            提交问答
                                        </Button>
                                    </div>
                                </div>
                            </Form>
                        </Card>
                    </div>
                </div>
                </Affix>
            

            {/* 法规文件查看弹窗 */}
            <RegulationModal
                open={regulationModal.open}
                filename={regulationModal.filename}
                title={regulationModal.title}
                onClose={() => setRegulationModal({ open: false, filename: '', title: '' })}
            />

            {/* QA历史详情弹窗 */}
            <QaHistoryModal
                open={qaHistoryModal.open}
                qaId={qaHistoryModal.qaId}
                onClose={() => setQaHistoryModal({ open: false, qaId: null })}
                onSourceClick={(filename, title) => {
                    setQaHistoryModal({ open: false, qaId: null });
                    setRegulationModal({ open: true, filename, title });
                }}
            />

            {/* 审核历史详情弹窗 */}
            <Modal
                title="审核报告详情"
                open={auditHistoryModal.open}
                onCancel={() => setAuditHistoryModal({ open: false, auditId: null, auditDetail: null })}
                footer={[
                    <Button key="export" type="primary" onClick={() => {
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
                        <AuditResultDisplay
                            auditResult={auditHistoryModal.auditDetail.audit_report}
                            getCountryFlag={getCountryFlag}
                            onCountryClick={(code) => setSelectedCountries([code])}
                        />
                    </div>
                )}
            </Modal>
        </div>
    )
}

export default App
