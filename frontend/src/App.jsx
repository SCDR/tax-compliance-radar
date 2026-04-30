import { useEffect, useMemo, useState } from 'react'
import { Button, Card, Form, Input, InputNumber, List, Select, Space, Tabs, Tag, Typography, message } from 'antd'
import { submitAudit, submitQa, fetchQaHistory, fetchAuditHistory } from './api/client'

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
                <Form.Item name="query_text" label="请输入泰国VAT合规问题" rules={[{ required: true, message: '请输入您要咨询的泰国VAT合规问题' }, { max: 500, message: '提问内容不能超过500字' }]}>
                  <Input.TextArea rows={4} placeholder="例如：泰国对外国企业注册VAT有什么要求？" />
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
            <Card className="panel-card" title="泰国VAT合规审核">
              <Form
                form={auditForm}
                layout="vertical"
                initialValues={{ target_market: '泰国', platforms: [] }}
                onFinish={async (values) => {
                  setLoadingAudit(true)
                  try {
                    const result = await submitAudit(values)
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
                <Form.Item name="target_market" label="目标市场" rules={[{ required: true }]}>
                  <Select options={[{ value: '泰国', label: '泰国' }]} disabled />
                </Form.Item>
                <Form.Item name="business_type" label="业务类型" rules={[{ required: true, message: '请选择业务类型' }]}>
                  <Select options={[
                    { value: '跨境电商零售', label: '跨境电商零售' },
                    { value: '品牌出海直营', label: '品牌出海直营' },
                    { value: '外贸综合服务', label: '外贸综合服务' },
                  ]} />
                </Form.Item>
                <Form.Item name="annual_sales" label="年预计销售额（泰铢）" rules={[{ required: true, message: '请输入正确的数字金额' }]}>
                  <InputNumber className="full-width" min={0} placeholder="例如：5000000" />
                </Form.Item>
                <Form.Item name="platforms" label="入驻平台" rules={[{ required: true, message: '请选择入驻平台' }]}>
                  <Select mode="multiple" options={[
                    { value: 'Shopee', label: 'Shopee' },
                    { value: 'Lazada', label: 'Lazada' },
                    { value: 'TikTok Shop', label: 'TikTok Shop' },
                  ]} />
                </Form.Item>
                <Button type="primary" htmlType="submit" loading={loadingAudit}>提交审核</Button>
              </Form>
            </Card>
            <Card className="panel-card" title="审核结果">
              {auditResult ? (
                <div className="result-list">
                  <p><Text strong>VAT注册评估：</Text>{auditResult.audit_report?.vat_register_assessment}</p>
                  <p><Text strong>注册时限：</Text>{auditResult.audit_report?.register_deadline}</p>
                  <div>
                    <Text strong>主要风险：</Text>
                    <List
                      dataSource={auditResult.audit_report?.main_risks || []}
                      renderItem={(item) => (
                        <List.Item>
                          <Space direction="vertical" size={0}>
                            <Space>
                              <Tag color={item.risk_level === '高风险' ? 'red' : item.risk_level === '中风险' ? 'gold' : 'blue'}>{item.risk_level}</Tag>
                              <Text>{item.risk_desc}</Text>
                            </Space>
                            <Text type="secondary">法规依据：{item.regulation_base}</Text>
                          </Space>
                        </List.Item>
                      )}
                    />
                  </div>
                  <div>
                    <Text strong>建议措施：</Text>
                    <List dataSource={auditResult.audit_report?.suggestions || []} renderItem={(item) => <List.Item>{item}</List.Item>} />
                  </div>
                  <p><Text strong>附件指引：</Text>{auditResult.audit_report?.attachment_guide}</p>
                  <Paragraph className="disclaimer-text">{auditResult.disclaimer}</Paragraph>
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
                      <Text type="secondary">销售额：{item.annual_sales} 泰铢 · {item.create_time}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          </div>
        ),
      },
    ],
    [auditForm, auditHistory, loadingAudit, loadingQa, qaForm, qaHistory, qaResult, auditResult],
  )

  return (
    <div className="app-shell">
      <div className="hero">
        <div>
          <Tag color="geekblue">Tax Compliance Radar MVP</Tag>
          <Title level={2}>税务合规雷达</Title>
          <Paragraph>面向泰国 VAT 场景的法规智能问答与合规风险审核。</Paragraph>
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
