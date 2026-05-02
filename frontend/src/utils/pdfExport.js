/**
 * PDF 导出工具 - 使用浏览器打印功能确保中文正确显示
 * 这是最可靠的中文 PDF 导出方案
 */

// 打印样式 - 确保表格边框和所有样式正确渲染
const printStyles = `
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Microsoft JhengHei", sans-serif;
      font-size: 14px;
      color: #333;
      line-height: 1.8;
      background: white;
    }
    .print-container {
      padding: 20px;
      max-width: 800px;
      margin: 0 auto;
    }
    .header {
      border-bottom: 3px solid #667eea;
      padding-bottom: 12px;
      margin-bottom: 25px;
    }
    .title {
      font-size: 22px;
      font-weight: 700;
      color: #667eea;
    }
    .subtitle {
      font-size: 12px;
      color: #999;
      margin-top: 5px;
    }
    .section {
      margin-bottom: 20px;
    }
    .section-title {
      font-size: 15px;
      font-weight: 700;
      margin-bottom: 10px;
      color: #333;
      padding-left: 8px;
      border-left: 4px solid #667eea;
    }
    .content-box {
      background: #f8faff;
      padding: 15px;
      border-radius: 6px;
      white-space: pre-wrap;
      word-break: break-word;
      border: 1px solid #e0e7ff;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 8px;
      font-size: 13px;
    }
    table, th, td {
      border: 1px solid #d1d5db;
    }
    th {
      padding: 10px 12px;
      text-align: left;
      font-weight: 600;
      color: white;
      background: #667eea;
    }
    td {
      padding: 10px 12px;
      vertical-align: top;
    }
    tr:nth-child(even) td {
      background-color: #f8faff;
    }
    .risk-table th {
      background: #ef4444;
    }
    .risk-table tr:nth-child(even) td {
      background: #fef2f2;
    }
    .suggestion-table th {
      background: #10b981;
    }
    .suggestion-table tr:nth-child(even) td {
      background: #f0fdf4;
    }
    .risk-high {
      color: #dc2626;
      font-weight: 700;
    }
    .risk-medium {
      color: #d97706;
    }
    .disclaimer {
      background: #fff7ed;
      border: 1px solid #fed7aa;
      padding: 15px;
      border-radius: 6px;
      margin-top: 25px;
      font-size: 13px;
      color: #7c2d12;
      line-height: 1.7;
    }
    .disclaimer strong {
      color: #9a3412;
    }
    .footer {
      margin-top: 30px;
      text-align: center;
      font-size: 12px;
      color: #999;
      padding-top: 15px;
      border-top: 1px solid #e5e7eb;
    }
    @media print {
      body {
        padding: 0;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }
      .print-container {
        padding: 10px;
      }
      @page {
        margin: 20mm 15mm;
        size: A4;
      }
      .page-break {
        page-break-before: always;
      }
      .no-break {
        page-break-inside: avoid;
      }
      /* 表格跨页断行和重复表头关键设置 */
      table {
        page-break-inside: auto;
        page-break-after: auto;
      }
      thead {
        display: table-header-group; /* 每页重复显示表头 */
      }
      tbody {
        display: table-row-group;
      }
      tr {
        page-break-inside: avoid; /* 尽量不拆分单行内容 */
        page-break-after: auto;
      }
      td, th {
        page-break-inside: auto;
        word-wrap: break-word;
        max-width: 150mm; /* 防止单元格过宽超出页面 */
      }
    }
  </style>
`;

/**
 * 生成 QA 报告的 HTML
 */
const generateQAReportHTML = (qaResult) => {
  const queryText = qaResult.query_text || '无';
  const answerText = qaResult.answer_text?.answer || qaResult.answer_text?.core_rules || '暂无回答';
  const regulationBase = qaResult.answer_text?.regulation_base || '';
  const originalLink = qaResult.answer_text?.original_link || '';
  const date = new Date().toLocaleDateString('zh-CN');

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>税务合规问答报告</title>
  ${printStyles}
</head>
<body>
  <div class="print-container">
    <div class="header">
      <div class="title">税务合规问答报告</div>
      <div class="subtitle">生成日期：${date} | Tax Compliance Radar</div>
    </div>

    <div class="section no-break">
      <div class="section-title">咨询问题</div>
      <div class="content-box">${queryText}</div>
    </div>

    <div class="section no-break">
      <div class="section-title">回答内容</div>
      <div class="content-box">${answerText}</div>
    </div>

    ${regulationBase || originalLink ? `
    <div class="section no-break">
      <div class="section-title">法规依据</div>
      <table>
        <thead>
          <tr>
            <th style="width: 20%">项目</th>
            <th>内容</th>
          </tr>
        </thead>
        <tbody>
          ${regulationBase ? `<tr><td>法规依据</td><td>${regulationBase}</td></tr>` : ''}
          ${originalLink ? `<tr><td>原文链接</td><td>${originalLink}</td></tr>` : ''}
        </tbody>
      </table>
    </div>
    ` : ''}

    <div class="disclaimer">
      <strong>免责声明：</strong>本报告仅供参考，不构成税务/法律意见，不替代专业顾问服务。使用本报告内容产生的任何后果由使用者自行承担。
    </div>

    <div class="footer">Tax Compliance Radar - 多国税务合规智能助手</div>
  </div>
</body>
</html>
`;
};

/**
 * 生成审核报告的 HTML
 */
const generateAuditReportHTML = (auditResult) => {
  const date = new Date().toLocaleDateString('zh-CN');
  const overallSummary = auditResult.overall_summary || '无';
  const resultsByCountry = auditResult.results_by_country || {};
  const allRisks = auditResult.all_risks || [];
  const allSuggestions = auditResult.all_suggestions || [];

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>多国税务合规审核报告</title>
  ${printStyles}
</head>
<body>
  <div class="print-container">
    <div class="header">
      <div class="title">多国税务合规审核报告</div>
      <div class="subtitle">生成日期：${date} | Tax Compliance Radar</div>
    </div>

    <div class="section no-break">
      <div class="section-title">整体摘要</div>
      <div class="content-box">${overallSummary}</div>
    </div>

    ${Object.keys(resultsByCountry).length > 0 ? `
    <div class="section no-break">
      <div class="section-title">各国 VAT 注册评估</div>
      <table>
        <thead>
          <tr>
            <th style="width: 30%">国家</th>
            <th style="width: 40%">VAT 注册评估</th>
            <th style="width: 30%">注册时限</th>
          </tr>
        </thead>
        <tbody>
          ${Object.entries(resultsByCountry).map(([code, data]) => `
            <tr>
              <td>${data.country_name || code} (${code})</td>
              <td>${data.vat_register_assessment || '无'}</td>
              <td>${data.register_deadline || '无'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
    ` : ''}

    ${allRisks.length > 0 ? `
    <div class="section">
      <div class="section-title">风险清单</div>
      <table class="risk-table">
        <thead>
          <tr>
            <th style="width: 20%">来源国家</th>
            <th style="width: 15%">风险等级</th>
            <th style="width: 35%">风险描述</th>
            <th style="width: 30%">法规依据</th>
          </tr>
        </thead>
        <tbody>
          ${allRisks.map(risk => `
            <tr>
              <td>${risk.source_info?.country_name || '未知'}</td>
              <td class="${risk.risk_level === '高风险' ? 'risk-high' : risk.risk_level === '中风险' ? 'risk-medium' : ''}">${risk.risk_level || '未知'}</td>
              <td>${risk.risk_desc || '无'}</td>
              <td>${risk.regulation_base || '无'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
    ` : ''}

    ${allSuggestions.length > 0 ? `
    <div class="section">
      <div class="section-title">合规建议</div>
      <table class="suggestion-table">
        <thead>
          <tr>
            <th style="width: 20%">来源国家</th>
            <th style="width: 15%">建议类型</th>
            <th style="width: 65%">建议内容</th>
          </tr>
        </thead>
        <tbody>
          ${allSuggestions.map(sug => `
            <tr>
              <td>${sug.source_info?.country_name || '未知'}</td>
              <td>${sug.suggestion_type === 'professional' ? '专业建议' : '通用建议'}</td>
              <td>${sug.content || '无'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
    ` : ''}

    <div class="disclaimer">
      <strong>免责声明：</strong>本报告仅供参考，不构成税务/法律意见，不替代专业顾问服务。使用本报告内容产生的任何后果由使用者自行承担。
    </div>

    <div class="footer">Tax Compliance Radar - 多国税务合规智能助手</div>
  </div>
</body>
</html>
`;
};

/**
 * 打印并导出为 PDF
 */
const printToPDF = (html, filename) => {
  const printWindow = window.open('', '_blank');
  if (!printWindow) {
    alert('弹出窗口被阻止，请允许弹窗后重试');
    return;
  }

  // 直接设置 innerHTML 代替废弃的 document.write
  printWindow.document.open();
  printWindow.document.close();
  printWindow.document.getElementsByTagName('html')[0].innerHTML = html;

  // 设置标题（保存 PDF 时的默认文件名）
  printWindow.document.title = filename;

  // 等待样式和图片加载完成
  const loadTimer = setInterval(() => {
    if (printWindow.document.readyState === 'complete') {
      clearInterval(loadTimer);
      setTimeout(() => {
        printWindow.print();
        // 监听打印对话框关闭
        printWindow.addEventListener('afterprint', () => {
          setTimeout(() => printWindow.close(), 100);
        });
      }, 200);
    }
  }, 100);

  // 超时保护
  setTimeout(() => {
    clearInterval(loadTimer);
    printWindow.print();
    printWindow.addEventListener('afterprint', () => {
      setTimeout(() => printWindow.close(), 100);
    });
  }, 3000);
};

/**
 * 导出 QA 结果为 PDF
 * 使用浏览器打印功能确保中文正确显示
 */
export const exportQAResultToPDF = (qaResult) => {
  if (!qaResult) return;
  const filename = `税务合规问答_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}`;
  const html = generateQAReportHTML(qaResult);
  printToPDF(html, filename);
};

/**
 * 导出审核报告为 PDF
 * 使用浏览器打印功能确保中文正确显示
 */
export const exportAuditReportToPDF = (auditResult) => {
  if (!auditResult) return;
  const filename = `税务合规审核报告_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}`;
  const html = generateAuditReportHTML(auditResult);
  printToPDF(html, filename);
};
