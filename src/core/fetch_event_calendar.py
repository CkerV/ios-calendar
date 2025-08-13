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

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, project_root)

# 导入事件分析器（在设置路径后）
from src.analysis.event_analyzer import EventAnalyzer


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
        logging.FileHandler(os.path.join(log_dir, "calendar_sync.log")) if not is_github_actions else logging.StreamHandler(),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("calendar_sync")

# 日历数据来源URL
CALENDAR_URL = "https://api-one-wscn.awtmt.com/apiv1/finance/macrodatas"

# ICS文件保存路径
OUTPUT_DIR = "calendar_files"
ICS_FILE = os.path.join(OUTPUT_DIR, "wsc_events.ics")

# 腾讯云COS配置
COS_SECRET_ID = os.environ.get('COS_SECRET_ID', '')  # 从环境变量获取，也可以直接设置
COS_SECRET_KEY = os.environ.get('COS_SECRET_KEY', '')  # 从环境变量获取，也可以直接设置
COS_REGION = os.environ.get('COS_REGION', 'ap-beijing')  # COS存储桶所在地域
COS_BUCKET = os.environ.get('COS_BUCKET', '')  # 存储桶名称
COS_OBJECT_KEY = os.environ.get('COS_OBJECT_KEY', 'calendar/wsc_events.ics')  # 对象键（文件在COS中的路径）

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

def get_next_week_dates():
    """获取未来一周的起始和结束日期（保留原函数以兼容其他代码）"""
    today = datetime.now(CHINA_TZ)
    start_date = today
    end_date = today + timedelta(days=7)
    return start_date, end_date

def fetch_calendar_data():
    """从API获取日历数据"""
    try:
        # 获取本周的时间戳范围
        start_timestamp, end_timestamp = get_current_week_timestamps()
        
        # 构建请求参数
        params = {
            'start': start_timestamp,
            'end': end_timestamp
        }
        
        logger.info(f"请求API: {CALENDAR_URL}")
        logger.info(f"请求参数: {params}")
        
        response = requests.get(CALENDAR_URL, params=params)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"API响应状态: {response.status_code}")
        logger.info(f"响应数据类型: {type(data)}")
        
        # 检查API响应格式
        if isinstance(data, dict) and 'code' in data:
            if data['code'] == 20000 and 'data' in data and 'items' in data['data']:
                items = data['data']['items']
                logger.info(f"成功获取 {len(items)} 个事件")
                return items
            else:
                logger.error(f"API返回错误: {data.get('message', '未知错误')}")
                return None
        else:
            # 如果是旧格式，直接返回
            return data
    except requests.exceptions.RequestException as e:
        logger.error(f"获取日历数据失败: {e}")
        return None

def parse_datetime(dt_string):
    """解析API返回的日期时间字符串（已经是北京时间）"""
    if not dt_string:
        return None
    
    # 尝试解析完整的日期时间格式 (2025-03-17 20:30:00)
    try:
        dt = datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S")
        return dt
    except ValueError:
        pass
    
    # 尝试解析仅有日期的格式 (2025-03-17)
    try:
        dt = datetime.strptime(dt_string, "%Y-%m-%d")
        return dt
    except ValueError:
        logger.warning(f"无法解析日期时间: {dt_string}")
        return None

def parse_summary(summary):
    """从摘要中提取时间和标题"""
    if not summary:
        return None, summary
    
    # 尝试从摘要中提取时间 (例如: "20:30 美国2月零售销售环比")
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

def pycreate_ics_file(calendar_data):
    """将日历数据转换为ICS格式"""
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
            ICS_FILE = os.path.join(OUTPUT_DIR, "wsc_events.ics")
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            logger.info(f"在GitHub Actions环境中使用替代路径: {OUTPUT_DIR}")
    
    # 创建新的日历
    cal = Calendar()
    
    # 初始化事件分析器
    analyzer = EventAnalyzer()
    
    # 添加事件
    event_count = 0
    for event_data in calendar_data:
        # 新API使用 public_date 字段（时间戳格式）
        public_date = event_data.get('public_date')
        if not public_date:
            continue
            
        # 过滤条件：只保留美国和中国的重要性最高事件
        country = event_data.get('country', '')
        importance = event_data.get('importance', 0)
        
        # 只处理美国或中国的重要性为3的事件
        if country not in ['美国', '中国'] or importance != 3:
            continue
            
        # 将时间戳转换为datetime对象
        try:
            event_datetime = datetime.fromtimestamp(public_date, tz=CHINA_TZ)
            logger.info(f"原始时间戳: {public_date}, 转换后时间: {event_datetime.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        except (ValueError, TypeError) as e:
            logger.warning(f"无法解析时间戳 {public_date}: {e}")
            continue
            
        # 处理所有事件，不再进行日期过滤
        cal_event = Event()
        
        # 获取事件UID (使用id字段)
        cal_event.uid = f"{event_data.get('id', '')}_wscn_macro"
        
        # 获取事件标题
        title = event_data.get('title', '未知事件')
        
        # 设置事件名称，包含国家信息
        country = event_data.get('country', '')
        
        # 根据国家使用对应的 emoji
        country_emoji = ""
        if country == "美国":
            country_emoji = "🇺🇸"
        elif country == "中国":
            country_emoji = "🇨🇳"
        else:
            country_emoji = "🌍"  # 其他国家使用地球图标
        
        if country:
            cal_event.name = f"{country_emoji} {title}"
        else:
            cal_event.name = title
        
        # 判断是否为全天事件
        # 1. 如果时间是00:00:00，则视为全天事件
        # 2. 如果时间不是整点或常见时间点（如12:02这样的奇怪时间），也视为待定的全天事件
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
                logger.info(f"创建待定全天事件: {cal_event.name}, 日期: {event_date}, 原时间: {event_datetime.strftime('%H:%M:%S')}")
            else:
                logger.info(f"创建全天事件: {cal_event.name}, 日期: {event_date}")
        else:
            # 普通事件：设置具体时间，默认持续2小时
            cal_event.begin = event_datetime
            cal_event.end = event_datetime + timedelta(hours=2)
            logger.info(f"创建定时事件: {cal_event.name}, 时间: {event_datetime.strftime('%Y-%m-%d %H:%M:%S')}, 持续2小时")
        
        # 分析投资机会
        try:
            # 搜索相关信息
            related_info = analyzer.search_related_info(cal_event.name, event_datetime)
            
            # 分析投资机会
            analysis = analyzer.analyze_investment_opportunity(
                cal_event.name, 
                event_datetime,
                related_info
            )
            
            # 格式化分析结果
            analysis_text = analyzer.format_analysis_for_calendar(analysis)
            
            # 构建事件描述，包含基本信息
            description_parts = []
            
            # 添加基本事件信息
            if event_data.get('event'):
                description_parts.append(f"📊 事件详情: {event_data.get('event')}")
            
            if event_data.get('quantity') and event_data.get('unit'):
                description_parts.append(f"📈 数据: {event_data.get('quantity')} {event_data.get('unit')}")
            
            # 添加foresight信息
            if event_data.get('foresight'):
                description_parts.append(f"🔮 {event_data.get('foresight')}")
            
            # 添加分析结果
            if analysis_text:
                description_parts.append("\n" + analysis_text)
            
            cal_event.description = "\n".join(description_parts)
            
        except Exception as e:
            logger.error(f"分析事件时出错: {e}")
            
            # 如果分析失败，使用基本描述
            basic_info = [country_emoji]
            if event_data.get('event'):
                basic_info.append(f"📊 {event_data.get('event')}")
            if event_data.get('quantity') and event_data.get('unit'):
                basic_info.append(f"📈 {event_data.get('quantity')} {event_data.get('unit')}")
            if event_data.get('foresight'):
                basic_info.append(f"🔮 {event_data.get('foresight')}")
            cal_event.description = "\n".join(basic_info)
        
        # 添加事件到日历
        cal.events.add(cal_event)
        event_count += 1
    
    # 保存ICS文件
    if event_count > 0:
        try:
            with open(ICS_FILE, 'w') as f:
                f.write(str(cal))
            logger.info(f"成功创建ICS文件，包含 {event_count} 个事件")
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
        logger.warning("未找到任何事件")
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
        
        logger.info(f"文件已成功上传到腾讯云COS，对象键为: {COS_OBJECT_KEY}")
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
    logger.info("开始获取日历数据")
    logger.info(f"运行环境: {'GitHub Actions' if is_github_actions else '本地或服务器'}")
    
    calendar_data = fetch_calendar_data()
    
    if calendar_data:
        logger.info(f"成功获取日历数据，共 {len(calendar_data)} 条记录")
        success = pycreate_ics_file(calendar_data)
        
        if success:
            logger.info(f"ICS文件已生成: {ICS_FILE}")
            logger.info("请将此文件导入到iOS日历应用中")
            
            # 上传到腾讯云COS
            upload_success = upload_to_cos(ICS_FILE)
            if upload_success:
                logger.info("ICS文件已成功上传到腾讯云COS")
            else:
                logger.error("ICS文件上传到腾讯云COS失败")
                
            # 在GitHub Actions环境中，显示文件路径
            if is_github_actions:
                logger.info(f"GitHub Actions环境中的文件路径: {os.path.abspath(ICS_FILE)}")
                print(f"##[notice] ICS文件生成路径: {os.path.abspath(ICS_FILE)}")
            
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
            logger.error("创建ICS文件失败")
            if is_github_actions:
                print("##[error] 创建ICS文件失败")
    else:
        logger.error("获取日历数据失败")
        if is_github_actions:
            print("##[error] 获取日历数据失败")

if __name__ == "__main__":
    main() 