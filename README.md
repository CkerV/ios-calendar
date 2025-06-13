# 华尔街见闻日历同步工具

这是一个自动同步华尔街见闻财经日历的工具，它可以获取全球和中国的财经日历事件，并生成可导入到手机日历的 ICS 文件。此工具还会使用 AI 分析每个事件的投资机会，并将分析结果包含在日历事件的描述中。

## 功能特点

- 自动获取华尔街见闻全球和中国财经日历数据
- 使用 OpenAI API 分析每个事件的投资机会
- 生成标准 ICS 格式的日历文件
- 支持上传到腾讯云 COS 存储
- 支持 GitHub Actions 自动运行
- 完整的日志记录功能

## 项目结构

```
ics-demo/
├── src/
│   ├── core/
│   │   ├── fetch_calendar.py      # 全球日历获取脚本
│   │   └── fetch_china_calendar.py # 中国日历获取脚本
│   └── analysis/
│       ├── __init__.py
│       └── event_analyzer.py      # 事件分析器
├── tests/
│   └── test_analysis.py          # 测试文件
├── logs/                         # 日志目录
├── calendar_files/               # 输出目录
├── .github/
│   └── workflows/
│       └── calendar_sync.yml     # GitHub Actions 配置
├── requirements.txt              # 项目依赖
├── setup.py                      # 包安装配置
└── README.md                     # 项目文档
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
# OpenAI API配置
OPENAI_API_KEY=your_openai_api_key_here

# 腾讯云COS配置（如果需要使用上传功能）
COS_SECRET_ID=your_cos_secret_id_here
COS_SECRET_KEY=your_cos_secret_key_here
COS_REGION=ap-beijing
COS_BUCKET=your_bucket_name_here
COS_OBJECT_KEY=calendar/wsc_events.ics
COS_OBJECT_KEY_CHINA=calendar/wsc_china_events.ics
```

### GitHub Actions 配置

如果要使用 GitHub Actions 自动运行，需要在仓库的 Settings -> Secrets and variables -> Actions 中添加上述环境变量。

## 使用说明

### 本地运行

1. 获取全球财经日历：
```bash
python src/core/fetch_calendar.py
```

2. 获取中国财经日历：
```bash
python src/core/fetch_china_calendar.py
```

生成的 ICS 文件将保存在 `calendar_files` 目录下：
- 全球日历：`calendar_files/wsc_events.ics`
- 中国日历：`calendar_files/wsc_china_events.ics`

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
- 全球日历：`logs/calendar_sync.log`
- 中国日历：`logs/china_calendar_sync.log`

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

[MIT License](LICENSE)
