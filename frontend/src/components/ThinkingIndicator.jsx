import CarouselStrategy from './thinking/CarouselStrategy';
import StreamingStrategy from './thinking/StreamingStrategy';

// 策略映射
const strategies = {
  carousel: CarouselStrategy,
  streaming: StreamingStrategy,
};

/**
 * 思考态指示器组件
 * @param {string} mode - 显示模式: 'carousel' (轮播, 默认) | 'streaming' (流式)
 * @param {object} props - 传递给策略组件的其他属性
 */
const ThinkingIndicator = ({ mode = 'carousel', ...props }) => {
  const StrategyComponent = strategies[mode] || CarouselStrategy;
  return <StrategyComponent {...props} />;
};

export default ThinkingIndicator;
