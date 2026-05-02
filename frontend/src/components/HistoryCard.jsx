import { useState } from 'react';
import { Card, Space, Typography, Button, Tag } from 'antd';
import { DownOutlined, UpOutlined, FilePdfOutlined, ReloadOutlined } from '@ant-design/icons';

const { Text, Paragraph } = Typography;

/**
 * 历史记录卡片组件
 * @param {object} item - 历史记录数据
 * @param {string} type - 类型: 'qa' | 'audit'
 * @param {function} onResubmit - 重新提交回调
 * @param {function} onExportPDF - 导出PDF回调
 */
const HistoryCard = ({ item, type, onResubmit, onExportPDF }) => {
  const [expanded, setExpanded] = useState(false);

  const toggleExpand = () => {
    setExpanded(!expanded);
  };

  // QA类型的内容渲染
  const renderQAContent = () => {
    if (type !== 'qa') return null;
    return (
      <div>
        <Paragraph>
          <Text strong>法规依据：</Text>{item.answer_text?.regulation_base}
        </Paragraph>
        <Paragraph>
          <Text strong>合规建议：</Text>{item.answer_text?.compliance_suggestion}
        </Paragraph>
      </div>
    );
  };

  // Audit类型的内容渲染
  const renderAuditContent = () => {
    if (type !== 'audit') return null;
    return (
      <div>
        <Paragraph>
        <Text strong>业务类型：</Text>{item.business_type}
        </Paragraph>
        <Paragraph>
        <Text strong>整体摘要：</Text>{item.overall_summary}
        </Paragraph>
        {item.all_risks?.length > 0 && (
          <div>
            <Text strong>风险数量：</Text>
            {item.all_risks.map((risk, idx) => (
              <Tag key={idx} color={risk.risk_level === '高风险' ? 'red' : 'gold'}>
                {risk.risk_level}
              </Tag>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <Card
      className="tech-card history-card"
      size="small"
      style={{ marginBottom: '12px' }}
      onClick={toggleExpand}
    >
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <Text strong>{type === 'qa' ? item.query_text : item.business_type}</Text>
            {expanded ? <UpOutlined style={{ fontSize: '12px', color: '#999' }} /> : <DownOutlined style={{ fontSize: '12px', color: '#999' }} />
          </Space>
          <Text type="secondary" style={{ fontSize: '12px' }}>{item.create_time}</Text>
        </div>

        {/* 展开的详情
        <div className={`history-card-expand ${expanded ? 'expanded' : ''}`}>
          <div style={{ paddingTop: '12px', borderTop: '1px solid rgba(102, 126, 234, 0.1)' }}>
            {renderQAContent()}
            {renderAuditContent()}

            {/* 操作按钮 */}
            <Space style={{ marginTop: '12px' }} onClick={(e) => e.stopPropagation()}}>
              {onResubmit && (
                <Button size="small" icon={<ReloadOutlined />} onClick={() => onResubmit(item)}>
                重新提交
              </Button>
              )}
              {onExportPDF && (
                <Button size="small" icon={<FilePdfOutlined />} onClick={() => onExportPDF(item)}>
                导出PDF
                </Button>
              )}
            </Space>
          </div>
        </div>
      </Space>
    </Card>
  );
};

export default HistoryCard;
