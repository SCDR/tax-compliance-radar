import { useEffect, useState } from 'react'
import { Card, List, Space, Tag, Typography, Skeleton } from 'antd'
import { FileTextOutlined } from '@ant-design/icons'
import StreamingStructuredText from './StreamingStructuredText'
import { getRegulationAliases, getRegulationAliasesSync } from '../api/regulationAliases'

const { Paragraph, Text } = Typography

const isPlainObject = (value) => Boolean(value) && typeof value === 'object' && !Array.isArray(value)

const formatFallbackValue = (value) => {
  if (value === null || value === undefined || value === '') {
    return '暂无'
  }
  if (typeof value === 'string') {
    return value
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  return JSON.stringify(value, null, 2)
}

const FadeBlock = ({ delay = 0, children, className = '' }) => (
  <div className={`audit-fade-block ${className}`.trim()} style={{ animationDelay: `${delay}ms` }}>
    {children}
  </div>
)

const renderStructuredField = (label, value, isLoading = false) => {
  if (Array.isArray(value)) {
    return (
      <div>
        <Text strong>{label}：</Text>
        <Space wrap size="small" style={{ marginTop: '8px' }}>
          {value.length > 0 ? value.map((item, index) => (
            <Tag key={`${label}-${index}`} className="source-tag">
              {isPlainObject(item) ? formatFallbackValue(item) : formatFallbackValue(item)}
            </Tag>
          )) : <Text type="secondary">暂无</Text>}
        </Space>
      </div>
    )
  }
  if (isPlainObject(value)) {
    return (
      <div>
        <Text strong>{label}：</Text>
        <div className="audit-related-block">
          {Object.entries(value).map(([key, nestedValue], index) => (
            <div key={`${label}-${key}`} style={{ marginBottom: index === Object.keys(value).length - 1 ? 0 : '8px' }}>
              <Text type="secondary">{key}：</Text>
              <span style={{ marginLeft: '6px' }}>
                <StreamingStructuredText text={formatFallbackValue(nestedValue)} isLoading={isLoading} />
              </span>
            </div>
          ))}
        </div>
      </div>
    )
  }
  return (
    <div>
      <Text strong>{label}：</Text>
      <span style={{ marginLeft: '6px' }}>
        <StreamingStructuredText text={formatFallbackValue(value)} isLoading={isLoading} />
      </span>
    </div>
  )
}

const renderRegulationBase = (value, onRegulationClick, aliases) => {
  const raw = typeof value === 'string' ? value : formatFallbackValue(value)
  const tokens = (raw || '')
    .split(/[;；]/)
    .map((s) => s.trim())
    .filter(Boolean)
  return (
    <div>
      <Text strong>法规依据：</Text>
      <Space wrap size="small" style={{ marginTop: '6px' }}>
        {tokens.length > 0 ? tokens.map((token, idx) => {
          const clickable = onRegulationClick && aliases && aliases[token]
          if (clickable) {
            return (
              <Tag
                key={`reg-${idx}`}
                className="source-tag"
                icon={<FileTextOutlined />}
                onClick={() => onRegulationClick(token, token)}
                style={{ cursor: 'pointer' }}
              >
                {token}
              </Tag>
            )
          }
          return (
            <Tag key={`reg-${idx}`} className="source-tag-plain">{token}</Tag>
          )
        }) : <Text type="secondary">暂无</Text>}
      </Space>
    </div>
  )
}

const AuditResultDisplay = ({
  auditResult,
  getCountryFlag,
  onCountryClick,
  onRegulationClick,
  isLoading = false,
}) => {
  const [aliases, setAliases] = useState(() => getRegulationAliasesSync())
  useEffect(() => {
    if (!aliases) getRegulationAliases().then(setAliases)
  }, [aliases])
  if (!auditResult) {
    return null
  }

  const { overall_summary: overallSummary, results_by_country: resultsByCountry = {}, all_risks: allRisks = [], all_suggestions: allSuggestions = [], disclaimer } = auditResult

  return (
    <div className="audit-structure-root">
      <FadeBlock delay={0}>
        <Card className="tech-card audit-section-card" title="整体摘要">
          <Paragraph style={{ whiteSpace: 'pre-wrap', lineHeight: '1.8', marginBottom: 0 }}>
            <StreamingStructuredText
              text={formatFallbackValue(overallSummary)}
              isLoading={isLoading && !overallSummary}
              rows={4}
            />
          </Paragraph>
        </Card>
      </FadeBlock>

      <FadeBlock delay={120}>
        <Card className="tech-card audit-section-card" title="按国家分组的详细结果">
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {Object.entries(resultsByCountry).map(([code, countryData], index) => (
              <FadeBlock key={code} delay={index * 120} className="audit-country-block">
                <Card size="small" className="tech-card audit-country-card" title={`${getCountryFlag(code)} ${countryData.country_name}`} onClick={() => onCountryClick?.(code, countryData)}>
                  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    {renderStructuredField('VAT注册评估', countryData.vat_register_assessment, isLoading)}
                    {renderStructuredField('注册时限', countryData.register_deadline, isLoading)}
                  </Space>
                </Card>
              </FadeBlock>
            ))}
          </Space>
        </Card>
      </FadeBlock>

      <FadeBlock delay={240}>
        <Card className="tech-card audit-section-card" title="所有风险">
          <List dataSource={allRisks} locale={{ emptyText: isLoading ? <div style={{ padding: '20px 0' }}><Skeleton active paragraph={{ rows: 2, width: ['90%', '80%'] }} title={false} /></div> : '暂无风险记录' }} renderItem={(item, index) => (
            <FadeBlock delay={index * 90}>
              <List.Item className="audit-list-item">
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <Space wrap>
                    <Tag className="country-tag">{getCountryFlag(item.source_info?.country_code)} {item.source_info?.country_name}</Tag>
                    <Tag className={`risk-tag ${item.risk_level === '高风险' ? 'risk-high' : item.risk_level === '中风险' ? 'risk-medium' : 'risk-low'}`}>
                      {item.risk_level}
                    </Tag>
                    {item.risk_desc && <Text strong>{item.risk_desc}</Text>}
                  </Space>

                  {isLoading && !item.risk_desc && (
                    <div style={{ width: '100%', padding: '8px 0 4px 0' }}>
                      <Skeleton active paragraph={{ rows: 1, width: ['100%'] }} title={false} />
                    </div>
                  )}

                  <Space direction="vertical" size={10} style={{ width: '100%', paddingTop: '4px' }}>
                    <div style={{ width: '100%' }}>
                      {renderStructuredField('触发条件', item.trigger_condition, isLoading)}
                    </div>
                    <div style={{ width: '100%' }}>
                      {renderRegulationBase(item.regulation_base, onRegulationClick, aliases)}
                    </div>
                    <div style={{ width: '100%' }}>
                      {renderStructuredField('违规后果', item.violation_consequence, isLoading)}
                    </div>
                  </Space>
                </Space>
              </List.Item>
            </FadeBlock>
          )} />
        </Card>
      </FadeBlock>

      <FadeBlock delay={360}>
        <Card className="tech-card audit-section-card" title="所有建议">
          <List dataSource={allSuggestions} locale={{ emptyText: isLoading ? <div style={{ padding: '20px 0' }}><Skeleton active paragraph={{ rows: 2, width: ['90%', '85%'] }} title={false} /></div> : '暂无建议记录' }} renderItem={(item, index) => (
            <FadeBlock delay={index * 90}>
              <List.Item className="audit-list-item">
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <Space wrap>
                    <Tag className="country-tag">{getCountryFlag(item.source_info?.country_code)} {item.source_info?.country_name}</Tag>
                    <Tag className={`suggestion-tag ${item.suggestion_type === 'professional' ? 'suggestion-pro' : 'suggestion-general'}`}>
                      {item.suggestion_type === 'professional' ? '专业建议' : '通用建议'}
                    </Tag>
                  </Space>
                  <div style={{ width: '100%', paddingTop: '4px' }}>
                    <Paragraph style={{ whiteSpace: 'pre-wrap', lineHeight: '1.8', marginBottom: 0 }}>
                      <StreamingStructuredText text={formatFallbackValue(item.content)} isLoading={isLoading && !item.content} rows={3} />
                    </Paragraph>
                  </div>
                </Space>
              </List.Item>
            </FadeBlock>
          )} />
        </Card>
      </FadeBlock>

      <FadeBlock delay={480}>
        <Paragraph className="disclaimer-text" style={{ marginTop: '16px' }}>
          <StreamingStructuredText text={formatFallbackValue(disclaimer)} isLoading={isLoading && !disclaimer} />
        </Paragraph>
      </FadeBlock>
    </div>
  )
}

export default AuditResultDisplay
