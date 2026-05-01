import { useEffect, useMemo, useState } from 'react'
import { Button, Card, Form, Input, InputNumber, List, Select, Space, Tabs, Tag, Typography, message } from 'antd'
import { submitQa, fetchQaHistory, fetchAuditHistory, fetchCountries, submitMultiAudit } from './api/client'

const { Title, Paragraph, Text } = Typography
const disclaimer = '本工具仅供参考，不构成税务/法律意见，不替代专业顾问服务。'

function App() {
  const [qaForm] = Form.useForm()
  const [auditForm] = Form.useForm()
  const [loadingQa, setLoadingQa] = useState(false)
  const [loadingAudit, setLoadingAudit] = useState(false)
  const [qaResult, setQaResult] = useState(null)
  const [auditResult, setAuditResult] = useState(null)
  const [qaHistory, setQaHistory] = useState([])
  const [auditHistory, setAuditHistory] = useState([])
  const [countries, setCountries] = useState([])
  const [selectedCountries, setSelectedCountries] = useState([])

  // 加载支持的国家列表
  useEffect(() => {
    const loadCountries = async () => {
      try {
        const result = await fetchCountries()
        setCountries(result.data.countries)
        // 默认选中泰国
        setSelectedCountries(['TH'])
      } catch {
        message.error('加载国家列表失败')
      }
    }
    loadCountries()
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
    const country = countries.find(c => c.code === code)
    return country ? country.name : code
  }

  // 获取国家国旗emoji
  const getCountryFlag = (code) => {
    const flags = { 'TH': '🇹🇭', 'VN': '🇻🇳', 'MY': '🇲🇾' }
    return flags[code] || '🌍'
  }

  const tabs = useMemo(
    () => [
      {
        key: 'qa',
        label: '法规问答',
        children: (
          <div className="panel-grid">
            <Card className="panel-card" title="中文法规智能问答">
              <Form form={qaForm} layout="vertical" onFinish={async (values) => {
                setLoadingQa(true)
                try {
                  const result = await submitQa(values.query_text)
                  setQaResult(result.data)
                  message.success('问答生成完成')
                  await loadHistory()
                } catch (error) {
                  message.error(error?.response?.data?.detail || '提交失败')
                } finally {
                  setLoadingQa(false)
                }
              }}>
                <Form.Item name="query_text" label="请输入合规问题" rules={[{ required: true, message: '请输入您要咨询的合规问题' }, { max: 500, message: '提问内容不能超过500字' }]}>
                  <Input.TextArea rows={4} placeholder="例如：跨境电商VAT注册有什么要求？" />
                </Form.Item>
                <Button type="primary" htmlType="submit" loading={loadingQa}>提交问答</Button>
              </Form>
            </Card>
            <Card className="panel-card" title="回答结果">
              {qaResult ? (
                <div className="result-list">
                  <p><Text strong>法规依据：</Text>{qaResult.answer_text?.regulation_base}</p>
                  <p><Text strong>核心规则：</Text>{qaResult.answer_text?.core_rules}</p>
                  <p><Text strong>合规建议：</Text>{qaResult.answer_text?.compliance_suggestion}</p>
                  <p><Text strong>风险提示：</Text>{qaResult.answer_text?.risk_warning}</p>
                  <p><Text strong>操作指引：</Text>{qaResult.answer_text?.operation_guide}</p>
                  <p><Text strong>原文链接：</Text>{qaResult.answer_text?.original_link || '待接入'}</p>
                  <Paragraph className="disclaimer-text">{qaResult.disclaimer}</Paragraph>
                </div>
              ) : (
                <Paragraph type="secondary">提交问题后，这里将展示结构化回答。</Paragraph>
              )}
            </Card>
            <Card className="panel-card" title="问答历史">
              <List
                dataSource={qaHistory}
                renderItem={(item) => (
                  <List.Item>
                    <Space direction="vertical" size={0}>
                      <Text strong>{item.query_text}</Text>
                      <Text type="secondary">{item.create_time}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          </div>
        ),
      },
      {
        key: 'audit',
        label: '合规审核',
        children: (
          <div className="panel-grid">
            <Card className="panel-card" title="多国合规审核">
              <Form
                form={auditForm}
                layout="vertical"
                initialValues={{ platforms: {} }}
                onFinish={async (values) => {
                  setLoadingAudit(true)
                  try {
                    // 构造多国审核请求
                    const annual_sales_by_country = {}
                    const platforms_by_country = {}

                    selectedCountries.forEach(code => {
                      annual_sales_by_country[code] = values[`annual_sales_${code}`] || 0
                      platforms_by_country[code] = values[`platforms_${code}`] || []
                    })

                    const payload = {
                      selected_countries: selectedCountries,
                      business_profile: {
                        business_type: values.business_type,
                        annual_sales_by_country,
                        platforms_by_country,
                      }
                    }

                    const result = await submitMultiAudit(payload)
                    setAuditResult(result.data)
                    message.success('审核完成')
                    await loadHistory()
                  } catch (error) {
                    message.error(error?.response?.data?.detail || '提交失败')
                  } finally {
                    setLoadingAudit(false)
                  }
                }}
              >
                <Form.Item name="countries" label="选择审核国家（可多选）" rules={[{ required: true }]}>
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

                {/* 为每个选中国家生成独立的输入表单 */}
                {selectedCountries.map(code => (
                  <div key={code} style={{ padding: '12px', background: '#f5f5f5', borderRadius: '8px', marginBottom: '12px' }}>
                    <Title level={5}>{getCountryFlag(code)} {getCountryName(code)} 业务信息</Title>
                    <Form.Item
                      name={`annual_sales_${code}`}
                      label="年预计销售额"
                      rules={[{ required: true, message: '请输入正确的数字金额' }]}
                    >
                      <InputNumber className="full-width" min={0} placeholder="请输入年销售额" />
                    </Form.Item>
                    <Form.Item name={`platforms_${code}`} label="入驻平台">
                      <Select mode="multiple" options={[
                        { value: 'Shopee', label: 'Shopee' },
                        { value: 'Lazada', label: 'Lazada' },
                        { value: 'TikTok Shop', label: 'TikTok Shop' },
                      ]} />
                    </Form.Item>
                  </div>
                ))}

                <Button type="primary" htmlType="submit" loading={loadingAudit} disabled={selectedCountries.length === 0}>
                  提交多国审核
                </Button>
              </Form>
            </Card>

            <Card className="panel-card" title="审核结果">
              {auditResult ? (
                <div className="result-list">
                  <Title level={4}>整体摘要</Title>
                  <p>{auditResult.overall_summary}</p>

                  <Title level={4}>按国家分组的详细结果</Title>
                  {Object.entries(auditResult.results_by_country || {}).map(([code, countryData]) => (
                    <Card key={code} size="small" title={`${getCountryFlag(code)} ${countryData.country_name}`} style={{ marginBottom: '12px' }}>
                      <p><Text strong>VAT注册评估：</Text>{countryData.vat_register_assessment}</p>
                      <p><Text strong>注册时限：</Text>{countryData.register_deadline}</p>
                    </Card>
                  ))}

                  <Title level={4}>所有风险（带来源标注）</Title>
                  <List
                    dataSource={auditResult.all_risks || []}
                    renderItem={(item) => (
                      <List.Item>
                        <Space direction="vertical" size="small" style={{ width: '100%' }}>
                          <Space>
                            {/* 来源国家标签 */}
                            <Tag color="blue">{getCountryFlag(item.source_info?.country_code)} {item.source_info?.country_name}</Tag>
                            {/* 风险等级标签 */}
                            <Tag color={item.risk_level === '高风险' ? 'red' : item.risk_level === '中风险' ? 'gold' : 'blue'}>
                              {item.risk_level}
                            </Tag>
                            <Text strong>{item.risk_desc}</Text>
                          </Space>
                          <Text type="secondary">法规依据：{item.regulation_base}</Text>
                        </Space>
                      </List.Item>
                    )}
                  />

                  <Title level={4}>所有建议（带来源标注）</Title>
                  <List
                    dataSource={auditResult.all_suggestions || []}
                    renderItem={(item) => (
                      <List.Item>
                        <Space>
                          {/* 来源国家标签 */}
                          <Tag color="blue">{getCountryFlag(item.source_info?.country_code)} {item.source_info?.country_name}</Tag>
                          <Tag color={item.suggestion_type === 'professional' ? 'green' : 'purple'}>
                            {item.suggestion_type === 'professional' ? '专业建议' : '通用建议'}
                          </Tag>
                          <Text>{item.content}</Text>
                        </Space>
                      </List.Item>
                    )}
                  />

                  <Paragraph className="disclaimer-text" style={{ marginTop: '16px' }}>{disclaimer}</Paragraph>
                </div>
              ) : (
                <Paragraph type="secondary">提交表单后，这里将展示结构化审核报告。</Paragraph>
              )}
            </Card>

            <Card className="panel-card" title="审核历史">
              <List
                dataSource={auditHistory}
                renderItem={(item) => (
                  <List.Item>
                    <Space direction="vertical" size={0}>
                      <Text strong>{item.business_type}</Text>
                      <Text type="secondary">{item.create_time}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          </div>
        ),
      },
    ],
    [auditForm, auditHistory, loadingAudit, loadingQa, qaForm, qaHistory, qaResult, auditResult, countries, selectedCountries],
  )

  return (
    <div className="app-shell">
      <div className="hero">
        <div>
          <Tag color="geekblue">Tax Compliance Radar - 多国支持版</Tag>
          <Title level={2}>税务合规雷达</Title>
          <Paragraph>面向多国税务合规场景的法规智能问答与合规风险审核。</Paragraph>
        </div>
        <Card className="hero-card" size="small">
          <Text strong>免责声明</Text>
          <Paragraph className="disclaimer-text">{disclaimer}</Paragraph>
        </Card>
      </div>
      <Tabs defaultActiveKey="qa" items={tabs} />
    </div>
  )
}

export default App
