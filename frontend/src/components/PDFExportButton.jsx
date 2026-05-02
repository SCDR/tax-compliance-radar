import { Button, message } from 'antd';
import { FilePdfOutlined } from '@ant-design/icons';

/**
 * PDF导出按钮组件
 * @param {string} type - 导出类型: 'qa' | 'audit'
 * @param {object} data - 要导出的数据
 * @param {function} exportFn - 导出函数
 * @param {string} buttonText - 按钮文字
 */
const PDFExportButton = ({ type, data, exportFn, buttonText = '导出PDF' }) => {
  const handleExport = () => {
    if (!data) {
      message.warning('暂无数据可导出');
      return;
    }

    try {
      exportFn(data);
      message.success('PDF导出成功！');
    } catch (error) {
      console.error('PDF导出失败:', error);
      message.error('PDF导出失败，请重试');
    }
  };

  return (
    <Button
      className="pdf-export-btn"
      icon={<FilePdfOutlined />}
      onClick={handleExport}
      disabled={!data}
    >
      {buttonText}
    </Button>
  );
};

export default PDFExportButton;
