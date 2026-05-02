/**
 * 打字机效果文本组件
 * 支持逐字淡入 + 光标闪烁
 */
import { useEffect, useState, useRef } from 'react'
import { smartTypewriter } from '../utils/typewriter'

const TypewriterText = ({ text, speed = 30, onComplete, children }) => {
  const [displayText, setDisplayText] = useState('')
  const stopFnRef = useRef(null)

  useEffect(() => {
    // 有新文本时开始打字机
    if (text) {
      setDisplayText('')
      // 停止之前的
      if (stopFnRef.current) {
        stopFnRef.current()
      }
      stopFnRef.current = smartTypewriter(text, (currentText) => {
        setDisplayText(currentText)
        if (currentText === text) {
          onComplete?.()
        }
      })
    }

    return () => {
      if (stopFnRef.current) {
        stopFnRef.current()
      }
    }
  }, [text, onComplete])

  // 如果有 children，作为渲染函数传递 displayText
  if (children) {
    return children(displayText)
  }

  // 默认渲染：带光标
  return (
    <span className="typewriter-wrapper">
      {displayText}
      {displayText !== text && (
        <span className="typewriter-cursor" />
      )}
    </span>
  )
}

export default TypewriterText

// 附带的 CSS 样式（需要在全局或这里用 styled-components）
// 在 CSS 中添加：
// .typewriter-wrapper {
//   position: relative;
// }
// .typewriter-cursor {
//   display: inline-block;
//   width: 2px;
//   height: 1.2em;
//   background: #667eea;
//   margin-left: 2px;
//   vertical-align: text-bottom;
//   animation: typewriterBlink 0.8s infinite;
// }
