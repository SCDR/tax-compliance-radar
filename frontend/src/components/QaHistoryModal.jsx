import { useState, useEffect } from 'react';
import { Modal, Spin, Typography, Space, Button, Tag, message } from 'antd';
import { FileTextOutlined, DownloadOutlined } from '@ant-design/icons';
import { fetchQaDetail } from '../api/client';
import { exportQAResultToPDF } from '../utils/pdfExport';

const { Paragraph, Text } = Typography;

// 法规文件名到标题的映射
const REGULATION_TITLES = {
  '01_vat_registration_rules.md': '泰国VAT注册规则',
  '02_low_value_goods_policy_2026.md': '低价值商品VAT政策 (2026)',
  '03_platform_withholding_rules.md': '平台代扣代缴规则',
  '04_monthly_reporting_audit.md': '月度申报与稽查要求',
};

// 检测并提取回答中的引用来源，返回可点击的JSX
const renderAnswerWithSourceLinks = (answer, onSourceClick) => {
  if (!answer) return '暂无回答';

  // 分离回答主体和引用来源
  const sourceMarker = '**引用来源：**';
  const sourceIndex = answer.indexOf(sourceMarker);

  if (sourceIndex === -1) {
    return <span>{answer}</span>;
  }

  const mainAnswer = answer.substring(0, sourceIndex);
  const sourcesPart = answer.substring(sourceIndex + sourceMarker.length);

  // 解析来源列表
  const sourceFiles = sourcesPart
    .split(/[;；]/)
    .map(s => s.trim())
    .filter(s => s && s.length > 0);

  return (
    <>
      <span>{mainAnswer}</span>
      <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #eee' }}>
        <Text strong style={{ display: 'block', marginBottom: '8px' }}>引用来源：</Text>
        <Space wrap size="small">
          {sourceFiles.map((source, idx) => {
            // 检测是否是文件名
            const isFile = Object.keys(REGULATION_TITLES).some(filename => source.includes(filename));
            if (isFile) {
              const matchedFilename = Object.keys(REGULATION_TITLES).find(filename => source.includes(filename));
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
              );
            }
            // 普通文本来源
            return <Tag key={idx}>{source}</Tag>;
          })}
        </Space>
      </div>
    </>
  );
};

/**
 * QA历史详情弹窗组件
 * @param {boolean} open - 是否打开弹窗
 * @param {number} qaId - 要查看的QA ID
 * @param {function} onClose - 关闭回调
 * @param {function} onSourceClick - 点击来源的回调
 */
const QaHistoryModal = ({ open, qaId, onClose, onSourceClick }) => {
  const [loading, setLoading] = useState(false);
  const [qaData, setQaData] = useState(null);

  useEffect(() => {
    if (open && qaId) {
      fetchQaDetailData();
    } else {
      setQaData(null);
    }
  }, [open, qaId]);

  const fetchQaDetailData = async () => {
    setLoading(true);
    try {
      const result = await fetchQaDetail(qaId);
      setQaData(result.data);
    } catch (err) {
      console.error('加载问答详情失败:', err);
      message.error('加载问答详情失败');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    if (qaData) {
      exportQAResultToPDF(qaData);
      message.success('导出成功');
    }
  };

  return (
    <Modal
      title="问答详情"
      open={open}
      onCancel={onClose}
      width={800}
      style={{ top: 20 }}
      footer={
        qaData && (
          <Button icon={<DownloadOutlined />} onClick={handleExport}>
            导出PDF
          </Button>
        )
      }
    >
      <Spin spinning={loading} tip="正在加载问答详情...">
        {qaData && (
          <div>
            <div style={{ marginBottom: '16px' }}>
              <Text type="secondary">{qaData.create_time}</Text>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '8px' }}>
                <Tag color="blue">问题</Tag>
              </div>
              <div
                style={{
                  padding: '16px 20px',
                  background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(118, 75, 162, 0.05) 100%)',
                  borderRadius: '12px',
                  borderLeft: '4px solid #667eea',
                }}
              >
                <Text strong style={{ fontSize: '15px' }}>{qaData.query_text}</Text>
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '8px' }}>
                <Tag color="green">回答</Tag>
              </div>
              <Paragraph style={{ whiteSpace: 'pre-wrap', lineHeight: '1.8', paddingLeft: '4px' }}>
                {renderAnswerWithSourceLinks(
                  qaData.answer_text?.answer || qaData.answer_text?.core_rules,
                  onSourceClick
                )}
              </Paragraph>
            </div>

            {qaData.answer_text?.original_link && (
              <div style={{ marginTop: '16px' }}>
                <Text strong>原文链接：</Text>
                <Text>{qaData.answer_text.original_link}</Text>
              </div>
            )}

            <div className="disclaimer-text" style={{ marginTop: '20px' }}>
              {qaData.disclaimer}
            </div>
          </div>
        )}
      </Spin>
    </Modal>
  );
};

export default QaHistoryModal;
