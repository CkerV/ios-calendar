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
import pytz
import time

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

# 配置日志
# 检查是否在GitHub Actions环境中运行
is_github_actions = os.environ.get('GITHUB_ACTIONS') == 'true'

# 确保日志目录存在
log_dir = os.path.join(project_root, "logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "report_calendar_sync.log")) if not is_github_actions else logging.StreamHandler(),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("report_calendar_sync")

# 财报数据来源URL
REPORT_CALENDAR_URL = "https://api-ddc-wscn.awtmt.com/finance/report/list"

# ICS文件保存路径
OUTPUT_DIR = "calendar_files"
ICS_FILE = os.path.join(OUTPUT_DIR, "wsc_reports.ics")

# 腾讯云COS配置
COS_SECRET_ID = os.environ.get('COS_SECRET_ID', '')  # 从环境变量获取，也可以直接设置
COS_SECRET_KEY = os.environ.get('COS_SECRET_KEY', '')  # 从环境变量获取，也可以直接设置
COS_REGION = os.environ.get('COS_REGION', 'ap-beijing')  # COS存储桶所在地域
COS_BUCKET = os.environ.get('COS_BUCKET', '')  # 存储桶名称
COS_OBJECT_KEY = os.environ.get('COS_REPORT_OBJECT_KEY', 'calendar/wsc_reports.ics')  # 对象键（文件在COS中的路径）

# 定义中国时区
CHINA_TZ = pytz.timezone('Asia/Shanghai')

def get_current_week_timestamps():
    """获取本周周一至周日的时间戳"""
    today = datetime.now(CHINA_TZ)
    # 获取本周周一（0=周一，6=周日）
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    # 设置为周一的00:00:00
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 获取本周周日的23:59:59
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    # 转换为时间戳
    start_timestamp = int(monday.timestamp())
    end_timestamp = int(sunday.timestamp())
    
    logger.info(f"本周时间范围: {monday.strftime('%Y-%m-%d %H:%M:%S')} 至 {sunday.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"时间戳范围: {start_timestamp} 至 {end_timestamp}")
    
    return start_timestamp, end_timestamp

def get_week_days_timestamps():
    """获取本周每天的时间戳列表"""
    today = datetime.now(CHINA_TZ)
    # 获取本周周一（0=周一，6=周日）
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    
    daily_timestamps = []
    for i in range(7):  # 周一到周日
        day = monday + timedelta(days=i)
        # 设置为当天的00:00:00
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        # 设置为当天的23:59:59
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999000)
        
        start_timestamp = int(day_start.timestamp())
        end_timestamp = int(day_end.timestamp())
        
        daily_timestamps.append({
            'date': day.strftime('%Y-%m-%d'),
            'start': start_timestamp,
            'end': end_timestamp
        })
    
    logger.info(f"本周每天的时间戳范围: {len(daily_timestamps)} 天")
    return daily_timestamps

def fetch_single_day_report_data(day_info):
    """获取单天的财报数据"""
    try:
        # 构建请求参数
        params = {
            'country': 'US,HK,CN',
            'start': day_info['start'],
            'end': day_info['end']
        }
        
        logger.info(f"请求 {day_info['date']} 财报数据: {REPORT_CALENDAR_URL}")
        logger.info(f"请求参数: {params}")
        
        # 添加请求头来避免403错误
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://wallstreetcn.com/'
        }
        
        response = requests.get(REPORT_CALENDAR_URL, params=params, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"{day_info['date']} API响应状态: {response.status_code}")
        
        # 检查API响应格式
        if isinstance(data, dict) and 'code' in data:
            if data['code'] == 20000 and 'data' in data:
                fields = data['data'].get('fields', [])
                items = data['data'].get('items', [])
                
                # 将items转换为字典格式，便于处理
                processed_items = []
                for item in items:
                    if len(item) == len(fields):
                        item_dict = dict(zip(fields, item))
                        processed_items.append(item_dict)
                
                logger.info(f"{day_info['date']} 成功获取 {len(processed_items)} 个财报事件")
                return processed_items
            else:
                logger.error(f"{day_info['date']} API返回错误: {data.get('message', '未知错误')}")
                return []
        else:
            logger.error(f"{day_info['date']} API响应格式不正确")
            return []
    except requests.exceptions.RequestException as e:
        logger.error(f"获取 {day_info['date']} 财报数据失败: {e}")
        return []

def fetch_report_calendar_data():
    """从API获取财报日历数据（按天循环调用）"""
    # 获取本周每天的时间戳
    daily_timestamps = get_week_days_timestamps()
    
    all_report_data = []
    
    for day_info in daily_timestamps:
        # 获取单天数据
        day_data = fetch_single_day_report_data(day_info)
        if day_data:
            all_report_data.extend(day_data)
        
        # 添加短暂延迟，避免API频率限制
        time.sleep(0.5)
    
    logger.info(f"总共获取 {len(all_report_data)} 个财报事件")
    return all_report_data if all_report_data else None

def create_report_ics_file(report_data):
    """将财报数据转换为ICS格式"""
    global ICS_FILE
    global OUTPUT_DIR
    
    if not report_data:
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
            ICS_FILE = os.path.join(OUTPUT_DIR, "wsc_reports.ics")
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            logger.info(f"在GitHub Actions环境中使用替代路径: {OUTPUT_DIR}")
    
    # 创建新的日历
    cal = Calendar()
    
    # 添加事件
    event_count = 0
    for report_item in report_data:
        # 获取public_date字段（时间戳格式）
        public_date = report_item.get('public_date')
        if not public_date:
            continue
            
        # 将时间戳转换为datetime对象
        try:
            event_datetime = datetime.fromtimestamp(public_date, tz=CHINA_TZ)
            logger.info(f"原始时间戳: {public_date}, 转换后时间: {event_datetime.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        except (ValueError, TypeError) as e:
            logger.warning(f"无法解析时间戳 {public_date}: {e}")
            continue
            
        # 创建日历事件
        cal_event = Event()
        
        # 获取事件UID (使用id字段)
        cal_event.uid = f"{report_item.get('id', '')}_wscn_report"
        
        # 获取公司信息
        company_name = report_item.get('company_name', '未知公司')
        company_code = report_item.get('code', '')
        country = report_item.get('country', '')
        calendar_type = report_item.get('calendar_type', '')
        observation_date = report_item.get('observation_date', '')
        
        # 根据国家使用对应的 emoji
        country_emoji = ""
        if country == "美国" or country == "US":
            country_emoji = "🇺🇸"
        elif country == "中国" or country == "CN":
            country_emoji = "🇨🇳"
        elif country == "香港" or country == "HK":
            country_emoji = "🇭🇰"
        else:
            country_emoji = "🌍"  # 其他国家使用地球图标
        
        # 设置事件标题
        title_parts = [country_emoji, company_name]
        if company_code:
            title_parts.append(f"({company_code})")
        if observation_date:
            title_parts.append(f"- {observation_date}")
        
        cal_event.name = " ".join(title_parts)
        
        # 判断是否为全天事件
        # 1. 如果时间是00:00:00，则视为全天事件
        # 2. 如果时间不是整点或常见时间点，也视为待定的全天事件
        is_midnight = event_datetime.hour == 0 and event_datetime.minute == 0 and event_datetime.second == 0
        is_odd_time = event_datetime.minute not in [0, 15, 30, 45]  # 非整点或常见时间点
        is_all_day = is_midnight or is_odd_time
        
        # 设置事件时间
        if is_all_day:
            # 全天事件：使用日期对象，避免时区转换问题
            event_date = event_datetime.date()
            cal_event.begin = event_date
            cal_event.end = event_date
            cal_event.make_all_day()  # 标记为全天事件
            
            # 如果是因为时间奇怪而设为全天事件，在标题中添加"待定"标记
            if is_odd_time and not is_midnight:
                cal_event.name = f"{cal_event.name} (待定)"
                logger.info(f"创建待定全天财报事件: {cal_event.name}, 日期: {event_date}, 原时间: {event_datetime.strftime('%H:%M:%S')}")
            else:
                logger.info(f"创建全天财报事件: {cal_event.name}, 日期: {event_date}")
        else:
            # 普通事件：设置具体时间，默认持续2小时
            cal_event.begin = event_datetime
            cal_event.end = event_datetime + timedelta(hours=2)
            logger.info(f"创建定时财报事件: {cal_event.name}, 时间: {event_datetime.strftime('%Y-%m-%d %H:%M:%S')}, 持续2小时")
        
        # 创建事件描述
        description_parts = [country_emoji]
            
        # 添加EPS相关信息
        eps_estimate = report_item.get('eps_estimate', 0)
        if eps_estimate and eps_estimate != 0:
            description_parts.append(f"💰 预期EPS: {eps_estimate}")
            
        # 添加收益相关信息
        earnings_estimate = report_item.get('earnings_estimate', 0)
        if earnings_estimate and earnings_estimate != 0:
            description_parts.append(f"📈 预期收益: {earnings_estimate}")
            
        cal_event.description = "\n".join(description_parts)
        
        # 添加事件到日历
        cal.events.add(cal_event)
        event_count += 1
    
    # 保存ICS文件
    if event_count > 0:
        try:
            with open(ICS_FILE, 'w') as f:
                f.write(str(cal))
            logger.info(f"成功创建财报ICS文件，包含 {event_count} 个事件")
            logger.info(f"财报ICS文件保存位置: {os.path.abspath(ICS_FILE)}")
            return True
        except Exception as e:
            logger.error(f"保存财报ICS文件时出错: {e}")
            # 如果在GitHub Actions环境中尝试使用不同的方法
            if is_github_actions:
                try:
                    # 使用绝对路径
                    absolute_path = os.path.abspath(ICS_FILE)
                    with open(absolute_path, 'w') as f:
                        f.write(str(cal))
                    logger.info(f"使用绝对路径成功创建财报ICS文件: {absolute_path}")
                    return True
                except Exception as e2:
                    logger.error(f"使用绝对路径保存文件时也出错: {e2}")
            return False
    else:
        logger.warning("未找到任何财报事件")
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
        
        logger.info(f"财报文件已成功上传到腾讯云COS，对象键为: {COS_OBJECT_KEY}")
        logger.info(f"财报文件URL: {file_url}")
        return True
    
    except Exception as e:
        logger.error(f"上传财报文件到腾讯云COS时发生错误: {e}")
        # 在GitHub Actions环境中，不因COS上传失败而让整个工作流失败
        if is_github_actions:
            logger.warning("在GitHub Actions环境中，忽略COS上传错误，继续执行")
            return True
        return False

def main():
    """主函数"""
    logger.info("开始获取财报日历数据")
    logger.info(f"运行环境: {'GitHub Actions' if is_github_actions else '本地或服务器'}")
    
    report_data = fetch_report_calendar_data()
    
    if report_data:
        logger.info(f"成功获取财报数据，共 {len(report_data)} 条记录")
        success = create_report_ics_file(report_data)
        
        if success:
            logger.info(f"财报ICS文件已生成: {ICS_FILE}")
            logger.info("请将此文件导入到iOS日历应用中")
            
            # 上传到腾讯云COS
            upload_success = upload_to_cos(ICS_FILE)
            if upload_success:
                logger.info("财报ICS文件已成功上传到腾讯云COS")
            else:
                logger.error("财报ICS文件上传到腾讯云COS失败")
                
            # 在GitHub Actions环境中，显示文件路径
            if is_github_actions:
                logger.info(f"GitHub Actions环境中的财报文件路径: {os.path.abspath(ICS_FILE)}")
                print(f"##[notice] 财报ICS文件生成路径: {os.path.abspath(ICS_FILE)}")
            
            # 显示导入指南
            print("\n如何导入财报日历到iOS:")
            print("1. 将生成的ICS文件发送到您的iOS设备（通过电子邮件、AirDrop或其他方式）")
            print("2. 在iOS设备上打开该文件")
            print("3. 系统会提示您添加到日历，点击'添加'")
            print("或者:")
            print("1. 将此文件上传到iCloud Drive")
            print("2. 在iOS设备上通过'文件'应用访问该文件")
            print("3. 点击文件，选择添加到日历\n")
        else:
            logger.error("创建财报ICS文件失败")
            if is_github_actions:
                print("##[error] 创建财报ICS文件失败")
    else:
        logger.error("获取财报数据失败")
        if is_github_actions:
            print("##[error] 获取财报数据失败")

if __name__ == "__main__":
    main()
