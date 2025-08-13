# 华尔街见闻日历同步工具

这是一个自动同步华尔街见闻财经日历的工具，包含宏观经济事件日历和上市公司财报日历两个模块。工具可以获取相关数据并生成可导入到手机日历的 ICS 文件。事件日历还会使用 AI 分析每个事件的投资机会，并将分析结果包含在日历事件的描述中。

## 功能特点

- 📅 **宏观事件日历**：获取华尔街见闻宏观经济事件数据
- 📊 **财报日历**：获取上市公司财报发布时间表（美国、香港、中国）  
- 🤖 **AI投资分析**：使用 OpenAI API 分析宏观事件的投资机会
- 📱 **手机日历兼容**：生成标准 ICS 格式文件，支持iOS/Android导入
- ☁️ **云端同步**：支持自动上传到腾讯云 COS 存储
- 🔄 **自动化运行**：支持 GitHub Actions 每周自动执行
- 📝 **完整日志**：详细记录运行过程和错误信息

## 项目结构

```
ics-demo/
├── src/
│   ├── core/
│   │   ├── fetch_event_calendar.py    # 宏观事件日历获取脚本（含AI分析）
│   │   └── fetch_report_calendar.py   # 财报日历获取脚本
│   └── analysis/
│       ├── __init__.py
│       └── event_analyzer.py          # 事件分析器（AI投资分析）
├── tests/                             # 测试目录
├── logs/                             # 日志目录
├── calendar_files/                   # ICS文件输出目录
├── .github/
│   └── workflows/
│       └── calendar_sync.yml         # GitHub Actions 自动化配置
├── requirements.txt                  # Python依赖包
├── setup.py                          # 项目安装配置
└── README.md                         # 项目文档
```

## 安装说明

1. 克隆项目：
```bash
git clone https://github.com/your-username/ics-demo.git
cd ics-demo
```

2. 创建并激活虚拟环境（可选但推荐）：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\\Scripts\\activate  # Windows
```

3. 安装项目：
```bash
pip install -e .
```

## 配置说明

### 环境变量

在项目根目录创建 `.env` 文件，包含以下配置：

```ini
# OpenAI API配置（用于AI投资分析功能）
OPENAI_API_KEY=your_openai_api_key_here

# 腾讯云COS配置（如果需要使用云端上传功能）
COS_SECRET_ID=your_cos_secret_id_here
COS_SECRET_KEY=your_cos_secret_key_here
COS_REGION=ap-beijing
COS_BUCKET=your_bucket_name_here
COS_OBJECT_KEY=calendar/wsc_events.ics
COS_REPORT_OBJECT_KEY=calendar/wsc_reports.ics
```

### GitHub Actions 配置

如果要使用 GitHub Actions 自动运行，需要在仓库的 Settings -> Secrets and variables -> Actions 中添加上述环境变量。

## 使用说明

### 本地运行

1. **获取宏观事件日历**（包含AI投资分析）：
```bash
python src/core/fetch_event_calendar.py
```

2. **获取财报日历**：
```bash
python src/core/fetch_report_calendar.py
```

生成的 ICS 文件将保存在 `calendar_files` 目录下：
- **事件日历**：`calendar_files/wsc_events.ics`（美国+中国重要宏观事件，含AI分析）
- **财报日历**：`calendar_files/wsc_reports.ics`（美国+香港+中国上市公司财报）

### 导入到手机日历

有以下几种方式：

1. 通过电子邮件：
   - 将 ICS 文件发送到您的邮箱
   - 在手机上打开邮件
   - 点击附件，选择"添加到日历"

2. 通过 iCloud（iOS 用户）：
   - 将 ICS 文件上传到 iCloud Drive
   - 在手机上通过"文件"应用打开
   - 选择添加到日历

3. 通过腾讯云 COS（如果已配置）：
   - 文件会自动上传到配置的 COS 存储桶
   - 通过生成的 URL 在手机上访问和导入

### 自动运行

项目配置了 GitHub Actions 工作流，会在每周一早上 8 点（北京时间）自动运行。您也可以：

1. 在 GitHub 仓库的 Actions 页面手动触发工作流
2. 修改 `.github/workflows/calendar_sync.yml` 中的计划时间

## 测试

运行测试：
```bash
python tests/test_analysis.py
```

## 日志

日志文件位于 `logs` 目录：
- 宏观事件日历：`logs/calendar_sync.log`
- 财报日历：`logs/report_calendar_sync.log`

## AI投资分析功能

宏观事件日历包含强大的AI投资分析功能：

### 分析内容
- 🏢 **相关标的**：自动识别与事件相关的股票和公司
- 📈 **投资机会**：分析个股、行业和主题层面的投资机会
- ⚠️ **风险提示**：识别潜在风险并提供应对策略
- 🔮 **前瞻信息**：包含华尔街见闻的专业前瞻分析

### 示例输出
每个宏观事件都会包含类似以下的分析内容：
```
🏢 相关标的
└ 特斯拉(US:TSLA)
└ 比亚迪(SZ:002594)

📈 投资机会
【个股】特斯拉
└ 投资逻辑: 新能源政策受益，产业链完整
└ 关键催化剂: 政策支持、技术突破

⚠️ 风险提示
【市场风险】政策变动可能影响行业发展
└ 应对策略: 关注政策动向，分散投资组合
```

## 财报日历特点

财报日历模块具有以下优势：

### 数据来源可靠
- 📊 **多市场覆盖**：美国、香港、中国三大主要市场
- 🔄 **按天获取**：解决API时间段限制，确保获取完整数据
- ⏰ **智能时间处理**：自动识别全天事件和定时事件

### 信息丰富
- 🏢 **公司详情**：包含公司名称、股票代码、市场标识
- 📋 **报告类型**：年报、中报、季报等详细分类
- 💰 **财务预期**：显示预期EPS、收益等关键指标

### 示例事件
```
🇺🇸 特斯拉 (TSLA.US) - 第三季报
💰 预期EPS: 0.73
📈 预期收益: 25.8B

🇭🇰 腾讯控股 (00700.HK) - 中报  
💰 预期EPS: 3.52
```

## 使用建议

### 最佳实践
- 🔑 **API密钥安全**：请妥善保管OpenAI API密钥，避免泄露
- ⏰ **运行时间**：建议在工作日运行，获取最新的财经数据
- 📱 **导入频率**：建议每周导入一次新的日历文件
- 🔄 **自动化**：推荐使用GitHub Actions实现自动化运行

### 注意事项
- 宏观事件AI分析功能需要OpenAI API密钥
- 财报日历使用按天循环调用API，确保数据完整性
- 生成的ICS文件兼容主流日历应用（iOS日历、Google日历、Outlook等）

## 贡献

欢迎提交 Issue 和 Pull Request！

如有问题或建议，请通过以下方式联系：
- 🐛 **Bug报告**：提交 GitHub Issue
- 💡 **功能建议**：提交 Feature Request  
- 🔧 **代码贡献**：提交 Pull Request

## 许可证

[MIT License](LICENSE)
