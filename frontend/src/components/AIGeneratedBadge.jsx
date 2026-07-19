import { ThunderboltOutlined } from '@ant-design/icons'

/**
 * AI 生成内容提示徽章
 * 放置于所有 LLM 生成结果的顶部（或指定位置），提示用户内容由 AI 生成，需人工复核。
 *
 * @param {string} placement - 'inline' | 'block'，默认 'block'（占一行）
 * @param {string} text      - 自定义提示文案，默认："以下内容由 AI 生成，仅供参考，请以专业顾问意见为准。"
 * @param {object} style     - 额外内联样式
 */
const AIGeneratedBadge = ({
  placement = 'block',
  text = '内容由 AI 生成，请以专业顾问意见为准',
  style = {},
}) => {
  return (
    <div
      className={`ai-generated-badge ai-generated-badge-${placement}`}
      role="note"
      aria-label="AI 生成内容提示"
      style={style}
    >
      <ThunderboltOutlined className="ai-generated-badge-icon" />
      <span className="ai-generated-badge-label">AI Generated</span>
      <span className="ai-generated-badge-divider" />
      <span className="ai-generated-badge-text">{text}</span>
    </div>
  )
}

export default AIGeneratedBadge
