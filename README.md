# 华尔街见闻日历自动订阅工具

这个工具可以帮助您自动获取华尔街见闻网站的日历数据，并将其转换为ICS文件，以便导入到iOS日历应用中。

## 功能特点

- 自动从 https://ics.wallstreetcn.com/global.json 获取未来一周的日历数据
- 生成兼容iOS日历的ICS文件
- 设置自动任务，每周一0点自动更新日历数据
- 支持自动上传ICS文件到腾讯云COS
- 支持通过GitHub Actions自动定时执行
- 支持macOS和Linux系统

## 安装依赖

在使用前，请确保您已安装以下Python依赖：

```bash
pip install requests ics python-crontab cos-python-sdk-v5
```

## 使用方法

### 1. 配置腾讯云COS（可选）

如果您希望将生成的ICS文件上传到腾讯云COS，请运行以下命令进行配置：

```bash
python3 setup_cos.py
```

按照提示输入您的腾讯云SecretId、SecretKey、存储桶名称等信息。此脚本会将配置保存到环境变量中。

### 2. 手动获取日历数据

如果您想立即获取未来一周的日历数据，可以直接运行：

```bash
python3 fetch_calendar.py
```

这会在`calendar_files`目录中生成一个`wsc_events.ics`文件，并尝试将其上传到腾讯云COS（如已配置）。

### 3. 设置自动任务

#### 3.1 在本地计算机上设置

要在本地设置每周一0点自动更新日历数据的任务，请运行：

```bash
python3 setup_cron.py
```

- 在macOS上，这将创建一个LaunchAgent
- 在Linux上，这将设置一个Crontab任务

#### 3.2 使用GitHub Actions自动执行（推荐）

您也可以利用GitHub Actions来自动执行此任务，无需本地计算机一直开机：

1. Fork或克隆此仓库到您的GitHub账号
2. 在仓库设置中添加以下Secrets（设置 > Secrets and variables > Actions）：
   - `COS_SECRET_ID`: 腾讯云API密钥ID
   - `COS_SECRET_KEY`: 腾讯云API密钥
   - `COS_REGION`: 存储桶所在区域（如：ap-guangzhou）
   - `COS_BUCKET`: 存储桶名称
   - `COS_OBJECT_KEY`: 对象键（文件在COS中的路径，默认: calendar/wsc_events.ics）
3. GitHub Actions将按照设定的时间（每周一0点北京时间）自动执行脚本
4. 您可以在Actions选项卡中查看执行历史和日志
5. 每次执行后，ICS文件也会保存为工作流程构件，可以直接从GitHub下载

### 4. 将日历导入iOS设备

有以下方法可以将生成的ICS文件导入到iOS日历：

**方法一：直接发送到手机**

1. 将生成的`wsc_events.ics`文件发送到您的iOS设备（通过电子邮件、AirDrop或其他方式）
2. 在iOS设备上打开该文件
3. 系统会提示您添加到日历，点击"添加"

**方法二：通过iCloud同步**

1. 将`wsc_events.ics`文件上传到iCloud Drive
2. 在iOS设备上通过"文件"应用访问该文件
3. 点击文件，选择添加到日历

**方法三：通过腾讯云COS访问（如已配置）**

1. 在iOS设备上通过浏览器访问腾讯云COS中的ICS文件URL
2. 点击下载文件，选择使用"日历"应用打开
3. 系统会提示您添加到日历，点击"添加"

**方法四：从GitHub Actions下载（如使用GitHub Actions）**

1. 访问您的GitHub仓库的Actions页面
2. 查看最近一次成功运行的工作流
3. 下载calendar-files构件
4. 将其中的ICS文件导入到iOS日历

### 5. 自动化导入iOS日历（需要额外设置）

要实现完全自动化，您可以：

1. 配置腾讯云COS，使ICS文件有固定的URL
2. 在iOS上设置自动化，使用快捷指令应用定期从该URL下载并导入ICS文件（需要手动创建）

## 日志和故障排除

- 在本地运行时，脚本运行日志保存在`calendar_sync.log`文件中
- 如果使用LaunchAgent，stdout和stderr日志分别保存在`calendar_sync_stdout.log`和`calendar_sync_stderr.log`文件中
- 如果使用GitHub Actions，日志可以在Actions标签页中查看

如果遇到问题：

1. 确认您的网络连接正常
2. 检查日志文件了解详细错误信息
3. 确保所有的依赖已正确安装
4. 如果使用腾讯云COS，确保您的SecretId、SecretKey和存储桶配置正确
5. 如果使用GitHub Actions，请检查Secrets是否正确设置

## 注意事项
- 如果使用本地自动化，请确保您的计算机在预定的更新时间（每周一0点）是开机状态，否则更新将不会执行
- 由于iOS限制，目前没有完全无需人工干预的方法来自动导入ICS文件到iOS日历
- 使用腾讯云COS可能会产生相关费用，请参考腾讯云的计费说明
- GitHub Actions有免费额度限制，但对于这样的周期性小任务通常不会超出限制
