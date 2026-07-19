import { useState, useEffect } from 'react';
import { LoadingOutlined } from '@ant-design/icons';

// 思考文本库
const THINKING_TEXTS = [
  '思考中...',
  '规划中...',
  '正在审核...',
  '分析数据...',
  '检索法规...',
  '生成报告...',
  'Processing...',
  'Analyzing...',
  '匹配风险规则...',
  '整理结构化内容...',
];

const CarouselStrategy = () => {
  const [currentText, setCurrentText] = useState(THINKING_TEXTS[0]);
  const [isFading, setIsFading] = useState(false);

  useEffect(() => {
    let timeoutId;

    const switchText = () => {
      setIsFading(true);
      setTimeout(() => {
        const randomIndex = Math.floor(Math.random() * THINKING_TEXTS.length);
        setCurrentText(THINKING_TEXTS[randomIndex]);
        setIsFading(false);
      }, 300);

      // 随机切换时长：1500ms ~ 2500ms 之间随机，更自然
      const randomInterval = Math.floor(Math.random() * 3000) + 2500;
      timeoutId = setTimeout(switchText, randomInterval);
    };

    // 首次启动
    timeoutId = setTimeout(switchText, 1800);

    return () => clearTimeout(timeoutId);
  }, []);

  return (
    <div className="thinking-indicator">
      <LoadingOutlined className="thinking-spin loading-icon" style={{ fontSize: '28px', color: 'var(--ink-500)' }} />
      <div className="thinking-text-wrapper">
        <span className={`thinking-text ${isFading ? 'fade-out' : 'fade-in'}`}>
          {currentText}
        </span>
      </div>
    </div>
  );
};

export default CarouselStrategy;
