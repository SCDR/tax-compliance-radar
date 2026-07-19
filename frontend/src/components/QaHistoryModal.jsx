import { useState, useEffect } from 'react';
import { Modal, Spin, Typography, Space, Button, Tag, message } from 'antd';
import { FileTextOutlined, DownloadOutlined } from '@ant-design/icons';
import { fetchQaDetail } from '../api/client';
import { getRegulationAliases, getRegulationAliasesSync } from '../api/regulationAliases';
import AIGeneratedBadge from './AIGeneratedBadge';
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
// sourceFiles 可从外部传入（后端历史接口返回的 sources 字段）；否则从 answer 文本里的 marker 解析
const renderAnswerWithSourceLinks = (answer, onSourceClick, aliases = null, externalSources = null) => {
  if (!answer) return '暂无回答';

  // 分离回答主体和引用来源
  const sourceMarker = '**引用来源：**';
  const sourceIndex = answer.indexOf(sourceMarker);

  let mainAnswer = answer;
  let sourceFiles = [];

  if (sourceIndex !== -1) {
    mainAnswer = answer.substring(0, sourceIndex);
    const sourcesPart = answer.substring(sourceIndex + sourceMarker.length);
    sourceFiles = sourcesPart
      .split(/[;；]/)
      .map((s) => s.trim())
      .filter((s) => s && s.length > 0);
  } else if (Array.isArray(externalSources) && externalSources.length > 0) {
    // 历史详情：answer 文本里不带 marker，用后端接口返回的 sources 独立渲染
    sourceFiles = externalSources;
  } else {
    return <span>{answer}</span>;
  }

  return (
    <>
      <span>{mainAnswer}</span>
      <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #eee' }}>
        <Text strong style={{ display: 'block', marginBottom: '8px' }}>引用来源：</Text>
        <Space wrap size="small">
          {sourceFiles.map((source, idx) => {
            // 1) 硬编码 REGULATION_TITLES 中的旧文件名
            const matchedFilename = Object.keys(REGULATION_TITLES).find(filename => source.includes(filename));
            if (matchedFilename) {
              return (
                <Tag
                  key={idx}
                  className="source-tag"
                  icon={<FileTextOutlined />}
                  onClick={() => onSourceClick(matchedFilename, REGULATION_TITLES[matchedFilename], null)}
                  style={{ cursor: 'pointer' }}
                >
                  {REGULATION_TITLES[matchedFilename]}
                </Tag>
              );
            }
            // 2) 后端别名表命中（宽松匹配：精确 → 去装饰 → substring 双向包含）
            const decorate = /(^[0-9]+[.、)）]\s*|\s*\.md$|^【|】$|^《|》$|^"|"$|^'|'$)/g;
            const cleaned = source.replace(decorate, '').trim();
            let hit = null;
            if (aliases) {
              if (aliases[source]) hit = source;
              else if (aliases[cleaned]) hit = cleaned;
              else {
                for (const alias of Object.keys(aliases)) {
                  if (!alias) continue;
                  if (source.includes(alias) || alias.includes(cleaned)) { hit = alias; break; }
                }
              }
            }
            if (hit) {
              return (
                <Tag
                  key={idx}
                  className="source-tag"
                  icon={<FileTextOutlined />}
                  onClick={() => onSourceClick(hit, hit, null)}
                  style={{ cursor: 'pointer' }}
                >
                  {source}
                </Tag>
              );
            }
            // 3) 未命中：纯文本 tag（不可点击，避免 404）
            return <Tag key={idx} className="source-tag-plain">{source}</Tag>;
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
  const [aliases, setAliases] = useState(() => getRegulationAliasesSync());

  useEffect(() => {
    if (open && !aliases) {
      getRegulationAliases().then(setAliases);
    }
  }, [open, aliases]);

  // 包一层：从 qaData.snippets / qaData.positions 里取对应文件的定位信息一起传给外层
  const handleSourceClick = (filename, title) => {
    const list = qaData?.snippets?.[filename];
    const snippet = Array.isArray(list) ? list[0] || '' : (list || '');
    const posList = qaData?.positions?.[filename];
    const positions = Array.isArray(posList) && posList.length ? posList : null;
    onSourceClick(filename, title, snippet, positions);
  };

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
          <Button className="pdf-export-btn" icon={<DownloadOutlined />} onClick={handleExport}>
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
                <Tag className="section-tag section-tag-question">问题</Tag>
              </div>
              <div className="qa-question-block">
                <Text strong style={{ fontSize: '14px' }}>{qaData.query_text}</Text>
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '8px' }}>
                <Tag className="section-tag section-tag-answer">回答</Tag>
              </div>
              <AIGeneratedBadge style={{ marginBottom: '12px' }} />
              <Paragraph style={{ whiteSpace: 'pre-wrap', lineHeight: '1.8', paddingLeft: '4px' }}>
                {renderAnswerWithSourceLinks(
                  qaData.answer_text?.answer || qaData.answer_text?.core_rules,
                  handleSourceClick,
                  aliases,
                  qaData.sources,
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
