#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

# 日历数据来源URL
CALENDAR_URL = "https://ics.wallstreetcn.com/global.json"

def check_response_structure():
    """检查API返回的具体数据结构"""
    print("正在获取API响应...")
    try:
        response = requests.get(CALENDAR_URL)
        response.raise_for_status()
        data = response.json()
        
        print(f"API返回数据类型: {type(data)}")
        
        if isinstance(data, list):
            print(f"列表长度: {len(data)}")
            
            if data:
                # 获取第一个元素的所有键
                first_item = data[0]
                print(f"\n第一个元素的数据类型: {type(first_item)}")
                
                if isinstance(first_item, dict):
                    print(f"第一个元素的键: {list(first_item.keys())}")
                    
                    # 打印第一个元素的所有值
                    print("\n第一个元素的值:")
                    for key, value in first_item.items():
                        print(f"{key}: {value} (类型: {type(value)})")
                else:
                    print(f"第一个元素的值: {first_item}")
        else:
            print("返回的不是列表，而是:", data)
            
        # 保存完整响应到文件以便检查
        with open("api_response.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print("\n完整的API响应已保存到 api_response.json 文件")
        
    except requests.exceptions.RequestException as e:
        print(f"API请求失败: {e}")
        return
        
if __name__ == "__main__":
    check_response_structure() 