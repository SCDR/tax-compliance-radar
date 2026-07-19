import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider, App as AntdApp, theme as antdTheme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App'
import './styles.css'

// 全局主题：把 antd 的默认蓝/绿/红映射到项目"墨黑 + 暗金"体系
const themeConfig = {
  algorithm: antdTheme.defaultAlgorithm,
  token: {
    colorPrimary: '#a68a5b',            // 暗金
    colorPrimaryHover: '#8b7048',
    colorInfo: '#0f172a',               // 墨黑
    colorSuccess: '#3f6b52',            // 低饱和墨绿
    colorWarning: '#a68a5b',            // 与主色一致，避免醒目黄
    colorError: '#a83a2a',              // 砖红
    colorText: '#0f172a',
    colorTextSecondary: '#64748b',
    colorBgBase: '#ffffff',
    colorBorder: '#e2e8f0',
    borderRadius: 10,
    fontFamily: '-apple-system, BlinkMacSystemFont, "PingFang SC", "Segoe UI", Roboto, sans-serif',
  },
  components: {
    Message: {
      contentBg: '#0f172a',
      contentPadding: '10px 16px',
      colorText: '#f8fafc',
    },
    Notification: {
      colorText: '#0f172a',
      colorTextHeading: '#0f172a',
    },
    Button: {
      borderRadius: 999,
    },
    Tag: {
      borderRadiusSM: 999,
    },
  },
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN} theme={themeConfig}>
      {/* AntdApp 为 message/notification/modal 提供上下文，确保主题生效 */}
      <AntdApp>
        <App />
      </AntdApp>
    </ConfigProvider>
  </React.StrictMode>,
)
