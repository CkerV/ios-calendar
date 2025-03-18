#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
from datetime import datetime, timedelta
from ics import Calendar, Event
import os
import logging
import re
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
import sys

# 配置日志
# 检查是否在GitHub Actions环境中运行
is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("china_calendar_sync.log") if not is_github_actions else logging.StreamHandler(),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("china_calendar_sync")

# 日历数据来源URL - 中国数据源
CALENDAR_URL = "https://ics.wallstreetcn.com/china.json"

# ICS文件保存路径
OUTPUT_DIR = "calendar_files"
ICS_FILE = os.path.join(OUTPUT_DIR, "wsc_china_events.ics")

# 腾讯云COS配置
COS_SECRET_ID = os.environ.get('COS_SECRET_ID', '')  # 从环境变量获取，也可以直接设置
COS_SECRET_KEY = os.environ.get('COS_SECRET_KEY', '')  # 从环境变量获取，也可以直接设置
COS_REGION = os.environ.get('COS_REGION', 'ap-beijing')  # COS存储桶所在地域
COS_BUCKET = os.environ.get('COS_BUCKET', '')  # 存储桶名称
COS_OBJECT_KEY = os.environ.get('COS_OBJECT_KEY_CHINA', 'calendar/wsc_china_events.ics')  # 对象键（文件在COS中的路径）

def get_next_week_dates():
    """获取未来一周的起始和结束日期"""
    today = datetime.now()
    start_date = today
    end_date = today + timedelta(days=7)
    return start_date, end_date

def fetch_calendar_data():
    """从API获取中国日历数据"""
    try:
        response = requests.get(CALENDAR_URL)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"获取中国日历数据失败: {e}")
        return None

def parse_datetime(dt_string):
    """解析API返回的日期时间字符串"""
    if not dt_string:
        return None
    
    # 尝试解析完整的日期时间格式 (2025-03-17 20:30:00)
    try:
        return datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass
    
    # 尝试解析仅有日期的格式 (2025-03-17)
    try:
        return datetime.strptime(dt_string, "%Y-%m-%d")
    except ValueError:
        logger.warning(f"无法解析日期时间: {dt_string}")
        return None

def parse_summary(summary):
    """从摘要中提取时间和标题"""
    if not summary:
        return None, summary
    
    # 尝试从摘要中提取时间 (例如: "20:30 中国2月CPI同比")
    time_pattern = r'^(\d{1,2}:\d{2})\s+(.*)'
    match = re.match(time_pattern, summary)
    
    if match:
        time_str = match.group(1)
        title = match.group(2)
        return time_str, title
    
    # 检查是否有"待定"时间
    if summary.startswith("待定 "):
        return "待定", summary[3:]
    
    return None, summary

def create_ics_file(calendar_data):
    """将中国日历数据转换为ICS格式"""
    global ICS_FILE
    global OUTPUT_DIR
    
    if not calendar_data:
        return False
    
    # 确保输出目录存在
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        logger.info(f"创建或确认输出目录: {OUTPUT_DIR}")
    except Exception as e:
        logger.error(f"创建输出目录时出错: {e}")
        # 在GitHub Actions环境中尝试使用相对路径
        if is_github_actions:
            OUTPUT_DIR = "./calendar_files"
            ICS_FILE = os.path.join(OUTPUT_DIR, "wsc_china_events.ics")
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            logger.info(f"在GitHub Actions环境中使用替代路径: {OUTPUT_DIR}")
    
    # 创建新的日历
    cal = Calendar()
    
    # 不再获取日期范围进行过滤，处理所有事件
    logger.info(f"处理所有中国日历事件，不进行日期过滤")
    
    # 添加事件
    event_count = 0
    for event_data in calendar_data:
        # 解析日期时间
        event_datetime = parse_datetime(event_data.get('dt_start'))
        if not event_datetime:
            continue
            
        # 处理所有事件，不再进行日期过滤
        cal_event = Event()
        
        # 获取事件UID (保持事件唯一性)
        cal_event.uid = event_data.get('uid', '')
        
        # 解析摘要中的时间和标题
        time_str, title = parse_summary(event_data.get('summary', ''))
        
        # 设置事件名称
        cal_event.name = title or event_data.get('summary', '未知事件')
        
        # 设置事件开始和结束时间
        cal_event.begin = event_datetime
        # 大多数金融日历事件默认为30分钟
        cal_event.end = event_datetime + timedelta(minutes=30)
        
        # 添加描述
        cal_event.description = f"华尔街见闻中国日历事件\n原始摘要: {event_data.get('summary', '')}"
        
        # 添加事件到日历
        cal.events.add(cal_event)
        event_count += 1
    
    # 保存ICS文件
    if event_count > 0:
        try:
            with open(ICS_FILE, 'w') as f:
                f.write(str(cal))
            logger.info(f"成功创建中国日历ICS文件，包含 {event_count} 个事件")
            logger.info(f"ICS文件保存位置: {os.path.abspath(ICS_FILE)}")
            return True
        except Exception as e:
            logger.error(f"保存ICS文件时出错: {e}")
            # 如果在GitHub Actions环境中尝试使用不同的方法
            if is_github_actions:
                try:
                    # 使用绝对路径
                    absolute_path = os.path.abspath(ICS_FILE)
                    with open(absolute_path, 'w') as f:
                        f.write(str(cal))
                    logger.info(f"使用绝对路径成功创建ICS文件: {absolute_path}")
                    return True
                except Exception as e2:
                    logger.error(f"使用绝对路径保存文件时也出错: {e2}")
            return False
    else:
        logger.warning("未找到任何中国日历事件")
        return False

def upload_to_cos(file_path):
    """上传文件到腾讯云COS"""
    if not os.path.exists(file_path):
        logger.error(f"要上传的文件不存在: {file_path}")
        return False
        
    # 检查COS配置是否完整
    if not all([COS_SECRET_ID, COS_SECRET_KEY, COS_BUCKET]):
        logger.error("腾讯云COS配置不完整，请设置环境变量或在脚本中直接配置")
        # 在GitHub Actions环境中，可能没有COS配置，但我们不想让工作流失败
        if is_github_actions:
            logger.warning("在GitHub Actions环境中，跳过COS上传")
            return True
        return False
    
    try:
        # 创建COS客户端
        config = CosConfig(
            Region=COS_REGION,
            SecretId=COS_SECRET_ID,
            SecretKey=COS_SECRET_KEY
        )
        client = CosS3Client(config)
        
        # 上传文件
        response = client.upload_file(
            Bucket=COS_BUCKET,
            LocalFilePath=file_path,
            Key=COS_OBJECT_KEY
        )
        
        # 生成文件访问URL（如果是公共读取权限的存储桶）
        file_url = f'https://{COS_BUCKET}.cos.{COS_REGION}.myqcloud.com/{COS_OBJECT_KEY}'
        
        logger.info(f"中国日历文件已成功上传到腾讯云COS，对象键为: {COS_OBJECT_KEY}")
        logger.info(f"文件URL: {file_url}")
        return True
    
    except Exception as e:
        logger.error(f"上传文件到腾讯云COS时发生错误: {e}")
        # 在GitHub Actions环境中，不因COS上传失败而让整个工作流失败
        if is_github_actions:
            logger.warning("在GitHub Actions环境中，忽略COS上传错误，继续执行")
            return True
        return False

def main():
    """主函数"""
    logger.info("开始获取中国日历数据")
    logger.info(f"运行环境: {'GitHub Actions' if is_github_actions else '本地或服务器'}")
    
    calendar_data = fetch_calendar_data()
    
    if calendar_data:
        logger.info(f"成功获取中国日历数据，共 {len(calendar_data)} 条记录")
        success = create_ics_file(calendar_data)
        
        if success:
            logger.info(f"中国日历ICS文件已生成: {ICS_FILE}")
            logger.info("请将此文件导入到iOS日历应用中")
            
            # 上传到腾讯云COS
            upload_success = upload_to_cos(ICS_FILE)
            if upload_success:
                logger.info("中国日历ICS文件已成功上传到腾讯云COS")
            else:
                logger.error("中国日历ICS文件上传到腾讯云COS失败")
                
            # 在GitHub Actions环境中，显示文件路径
            if is_github_actions:
                logger.info(f"GitHub Actions环境中的文件路径: {os.path.abspath(ICS_FILE)}")
                print(f"##[notice] 中国日历ICS文件生成路径: {os.path.abspath(ICS_FILE)}")
            
            # 显示导入指南
            print("\n如何导入到iOS日历:")
            print("1. 将生成的ICS文件发送到您的iOS设备（通过电子邮件、AirDrop或其他方式）")
            print("2. 在iOS设备上打开该文件")
            print("3. 系统会提示您添加到日历，点击'添加'")
            print("或者:")
            print("1. 将此文件上传到iCloud Drive")
            print("2. 在iOS设备上通过'文件'应用访问该文件")
            print("3. 点击文件，选择添加到日历\n")
        else:
            logger.error("创建中国日历ICS文件失败")
            if is_github_actions:
                print("##[error] 创建中国日历ICS文件失败")
    else:
        logger.error("获取中国日历数据失败")
        if is_github_actions:
            print("##[error] 获取中国日历数据失败")

if __name__ == "__main__":
    main() 