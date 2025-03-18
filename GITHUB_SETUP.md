# 在GitHub上设置自动日历同步

本文档提供了如何在GitHub上设置自动日历同步的详细步骤。

## 前提条件

- 拥有GitHub账号
- 已经注册腾讯云账号并创建了COS存储桶（如需上传到腾讯云COS）

## 部署步骤

### 1. Fork或克隆本仓库

1. 访问本项目的GitHub仓库页面
2. 点击页面右上角的"Fork"按钮，将仓库复制到您的GitHub账号下
3. 等待Fork完成

### 2. 配置GitHub Secrets

需要在GitHub仓库中添加以下Secrets，这样GitHub Actions才能访问您的腾讯云COS：

1. 在您Fork的仓库页面中，点击"Settings"（设置）
2. 在左侧菜单中，选择"Secrets and variables" > "Actions"
3. 点击"New repository secret"按钮，添加以下Secrets：

   - `COS_SECRET_ID`: 您的腾讯云SecretId
   - `COS_SECRET_KEY`: 您的腾讯云SecretKey
   - `COS_REGION`: 存储桶所在区域（例如：ap-guangzhou）
   - `COS_BUCKET`: 存储桶名称
   - `COS_OBJECT_KEY`: 对象键（默认：calendar/wsc_events.ics）

### 3. 启用GitHub Actions

1. 在您Fork的仓库中，点击"Actions"选项卡
2. 如果看到"I understand my workflows, go ahead and enable them"按钮，请点击它
3. 在列表中找到"华尔街见闻日历同步"工作流，点击它
4. 点击"Enable workflow"按钮启用

### 4. 手动触发工作流（可选）

您可以手动触发工作流，而不必等到预定的时间：

1. 在"Actions"页面，选择"华尔街见闻日历同步"工作流
2. 点击"Run workflow"按钮
3. 点击绿色的"Run workflow"按钮确认

### 5. 查看运行结果

1. 在工作流运行后，点击对应的运行记录
2. 您可以查看运行日志，确认是否成功
3. 在运行详情页面的"Artifacts"部分，您可以下载生成的ICS文件

## 工作流说明

GitHub Actions工作流配置在`.github/workflows/calendar_sync.yml`文件中：

- 定时触发：每周一0点（北京时间）自动运行
- 手动触发：支持通过GitHub界面手动触发
- 环境：使用Ubuntu最新版和Python 3.10
- 步骤：
  1. 检出代码
  2. 设置Python环境
  3. 安装依赖
  4. 获取日历数据并生成ICS文件
  5. 保存ICS文件为构件，可直接下载

## 常见问题

### Q: 工作流没有按时运行？

A: GitHub Actions的定时任务可能有延迟，特别是在GitHub负载高的时候。这是正常的，任务最终会被执行。

### Q: 上传到腾讯云COS失败？

A: 请检查您的Secrets是否正确设置，特别是腾讯云的密钥和存储桶信息。

### Q: 我需要修改执行时间？

A: 编辑`.github/workflows/calendar_sync.yml`文件，修改`cron`表达式。请注意GitHub Actions使用UTC时间，需要换算为您需要的时区。 