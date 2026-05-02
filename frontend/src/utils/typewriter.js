/**
 * 打字机效果工具函数
 * 逐字展示文本，带淡入效果
 */

/**
 * 逐字输出文本
 * @param {string} text - 要输出的完整文本
 * @param {function} onChar - 每个字符输出时的回调，参数为当前已输出的文本
 * @param {number} speed - 输出速度（毫秒/字符），默认 30ms
 * @returns {function} 停止函数
 */
export function typewriter(text, onChar, speed = 30) {
  let index = 0
  let stopped = false
  let currentText = ''

  const tick = () => {
    if (stopped || index >= text.length) {
      return
    }

    currentText = text.substring(0, index + 1)
    onChar(currentText)
    index++

    setTimeout(tick, speed)
  }

  setTimeout(tick, 0)

  return () => {
    stopped = true
  }
}

/**
 * 分段逐行输出（适合带格式的长文本）
 * @param {string} text - 完整文本
 * @param {function} onLine - 每段输出完成的回调
 * @param {number} lineSpeed - 每行间隔（毫秒）
 * @returns {function} 停止函数
 */
export function lineByLine(text, onLine, lineSpeed = 500) {
  const lines = text.split('\n').filter(line => line.trim())
  let index = 0
  let stopped = false
  let currentLines = []

  const tick = () => {
    if (stopped || index >= lines.length) {
      return
    }

    currentLines.push(lines[index])
    onLine(currentLines.join('\n'))
    index++

    setTimeout(tick, lineSpeed)
  }

  setTimeout(tick, 0)

  return () => {
    stopped = true
  }
}

/**
 * 智能逐字输出，自动识别段落边界减速
 * @param {string} text - 完整文本
 * @param {function} onUpdate - 更新回调
 * @returns {function} 停止函数
 */
export function smartTypewriter(text, onUpdate) {
  let index = 0
  let stopped = false
  let currentText = ''

  const tick = () => {
    if (stopped || index >= text.length) {
      return
    }

    const char = text[index]
    currentText += char
    onUpdate(currentText)
    index++

    // 段落结束时减速
    let delay = 25
    if (char === '\n') {
      delay = 200
    } else if (char === '。' || char === '！' || char === '？') {
      delay = 100
    } else if (char === ',' || char === '，' || char === ';' || char === '；') {
      delay = 50
    }

    setTimeout(tick, delay)
  }

  setTimeout(tick, 0)

  return () => {
    stopped = true
  }
}

/**
 * 支持 Markdown 的流式输出组件
 * 检测引用来源、标题等，做特殊效果
 */
export class MarkdownStream {
  constructor(onUpdate, onComplete) {
    this.fullText = ''
    this.displayText = ''
    this.onUpdate = onUpdate
    this.onComplete = onComplete
    this.stopFlag = false
  }

  /**
   * 追加新内容（模拟真实流式响应）
   * @param {string} chunk - 新到的文本块
   */
  append(chunk) {
    this.fullText += chunk
    this._animate()
  }

  /**
   * 设置完整文本（非流式，直接开始打字机）
   * @param {string} text - 完整文本
   */
  setText(text) {
    this.fullText = text
    this.displayText = ''
    this._animate()
  }

  _animate() {
    if (this.stopFlag) return

    if (this.displayText.length < this.fullText.length) {
      const nextChar = this.fullText[this.displayText.length]
      this.displayText += nextChar
      this.onUpdate(this.displayText)

      // 根据字符类型调整速度
      let delay = 25
      if (nextChar === '\n') delay = 150
      else if ('。！？；：'.includes(nextChar)) delay = 80
      else if ('，,;'.includes(nextChar)) delay = 40

      setTimeout(() => this._animate(), delay)
    } else {
      this.onComplete?.()
    }
  }

  stop() {
    this.stopFlag = true
  }
}

export default {
  typewriter,
  lineByLine,
  smartTypewriter,
  MarkdownStream,
}
