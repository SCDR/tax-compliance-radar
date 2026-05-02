import { Skeleton } from 'antd'

const isEmptyText = (value) => value === null || value === undefined || value === ''

const StreamingStructuredText = ({ text, placeholder = '暂无', isLoading = false, rows = 2 }) => {
  // 流式加载中时显示鱼骨屏
  if (isLoading) {
    return (
      <div
        className="stream-structured-skeleton"
        style={{
          width: '100%',
          paddingRight: '24px',
          boxSizing: 'border-box'
        }}
      >
        <Skeleton
          active
          paragraph={{
            rows,
            width: Array(rows).fill('100%'),
          }}
          title={false}
        />
      </div>
    )
  }

  // 无内容时显示占位符
  if (isEmptyText(text)) {
    return <span className="stream-structured-placeholder">{placeholder}</span>
  }

  const normalizedText = String(text)
  const lines = normalizedText.split('\n')

  return (
    <span className="stream-structured-root" aria-live="polite" style={{ display: 'inline-block', width: '100%', paddingRight: '24px', boxSizing: 'border-box' }}>
      {lines.map((line, lineIndex) => {
        if (line.length === 0) {
          return <br key={`line-${lineIndex}`} />
        }

        return (
          <span
            key={`line-${lineIndex}`}
            className="stream-structured-line"
            style={{ animationDelay: `${lineIndex * 140}ms` }}
          >
            {Array.from(line).map((char, charIndex) => {
              const displayChar = char === ' ' ? ' ' : char
              const delay = lineIndex * 140 + charIndex * 14

              return (
                <span
                  key={`char-${lineIndex}-${charIndex}`}
                  className="stream-structured-char"
                  style={{ animationDelay: `${delay}ms` }}
                >
                  {displayChar}
                </span>
              )
            })}
          </span>
        )
      })}
    </span>
  )
}

export default StreamingStructuredText
