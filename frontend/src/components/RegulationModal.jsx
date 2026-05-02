import { useState, useEffect } from 'react';
import { Modal, Spin, Alert, Space, Button, message } from 'antd';
import { FileTextOutlined, DownloadOutlined } from '@ant-design/icons';
import axios from 'axios';


// 创建axios实例，复用前端已有配置
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 10000,
});

/**
 * 法规文件查看弹窗组件
 * @param {boolean} open - 是否打开弹窗
 * @param {string} filename - 要查看的文件名
 * @param {string} title - 文件标题
 * @param {function} onClose - 关闭回调
 */
const RegulationModal = ({ open, filename, title, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [content, setContent] = useState(null);

  useEffect(() => {
    if (open && filename) {
      fetchRegulationContent();
    } else {
      // 关闭时重置状态
      setContent(null);
    }
  }, [open, filename]);

  const fetchRegulationContent = async () => {
    setLoading(true);

    try {
      const response = await api.get(`/regulations/${filename}`);
      setContent(response.data);
    } catch (err) {
      console.error('加载法规文件失败:', err);
      message.error(err.response?.data?.detail || err.message || '加载文件失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!content) return;

    const blob = new Blob([content.content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const renderContent = () => {
    if (!content) {
      return null;
    }

    // 所有文件用简单的格式显示，先确保页面能正常工作
    return (
      <pre style={{
        whiteSpace: 'pre-wrap',
        wordWrap: 'break-word',
        background: '#f5f5f5',
        padding: '16px',
        borderRadius: '8px',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        fontSize: '13px',
        lineHeight: '1.8',
      }}>
        {content.content}
      </pre>
    );
  };

  return (
    <Modal
      title={
        <Space>
          <FileTextOutlined style={{ color: '#667eea' }} />
          <span>{title || filename}</span>
        </Space>
      }
      open={open}
      onCancel={onClose}
      width={800}
      style={{ top: 20 }}
      footer={
        <Button icon={<DownloadOutlined />} onClick={handleDownload} disabled={!content}>
          下载原文件
        </Button>
      }
    >
      <Spin spinning={loading} tip="正在加载法规文件...">
        {renderContent()}
      </Spin>
    </Modal>
  );
};

export default RegulationModal;
