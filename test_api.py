#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
from datetime import datetime
import sys

# 日历数据来源URL
CALENDAR_URL = "https://ics.wallstreetcn.com/global.json"

def test_api_connection():
    """测试API连接并显示样本数据"""
    print("正在测试API连接...")
    try:
        response = requests.get(CALENDAR_URL)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            print("API返回了空数据。")
            return False
        
        print(f"API连接成功！获取到 {len(data)} 条日历记录。")
        
        # 显示前3条数据作为样本
        print("\n数据样本（前3条）:")
        sample_count = min(3, len(data))
        for i in range(sample_count):
            event = data[i]
            print(f"\n--- 事件 {i+1} ---")
            print(f"日期: {event.get('date', 'N/A')}")
            print(f"时间: {event.get('time', 'N/A')}")
            print(f"标题: {event.get('title', 'N/A')}")
            print(f"国家/地区: {event.get('country', 'N/A')}")
            print(f"重要性: {event.get('importance', 'N/A')}")
            
        # 提取当前日期后一周内的事件数量
        today = datetime.now().date()
        next_week_events = 0
        for event in data:
            try:
                event_date = datetime.strptime(event.get('date', ''), "%Y-%m-%d").date()
                days_diff = (event_date - today).days
                if 0 <= days_diff <= 7:
                    next_week_events += 1
            except ValueError:
                continue
        
        print(f"\n未来一周内的事件数量: {next_week_events}")
        
        return True
    except requests.exceptions.RequestException as e:
        print(f"API连接失败: {e}")
        return False

if __name__ == "__main__":
    success = test_api_connection()
    if success:
        print("\nAPI测试成功！您可以继续设置定时任务。")
        print("运行以下命令来生成日历文件：")
        print("python3 fetch_calendar.py")
    else:
        print("\nAPI测试失败。请检查您的网络连接或联系API提供者。")
        sys.exit(1) 