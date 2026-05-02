const StreamingAnswerDisplay = ({ text, placeholder = '正在生成回答...' }) => {
  if (!text) {
    return <span className="stream-answer-placeholder">{placeholder}</span>
  }

  return (
    <div className="stream-answer-block" aria-live="polite">
      {Array.from(text).map((char, index) => {
        if (char === '\n') {
          return <br key={`br-${index}`} />
        }

        const displayChar = char === ' ' ? '\u00A0' : char

        return (
          <span
            key={`${index}-${char}`}
            className="stream-answer-char"
            style={{ animationDelay: `${Math.min(index, 120) * 12}ms` }}
          >
            {displayChar}
          </span>
        )
      })}
    </div>
  )
}

export default StreamingAnswerDisplay