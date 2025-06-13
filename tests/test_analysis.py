#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

import logging
from datetime import datetime
import pytz
from analysis.event_analyzer import EventAnalyzer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_analysis")

def load_env():
    """从.env文件加载环境变量"""
    env_path = Path('.env')
    if not env_path.exists():
        logger.error("找不到 .env 文件，请根据以下模板创建：")
        logger.info("""
请创建 .env 文件，内容如下：

# OpenAI API配置
OPENAI_API_KEY=your_openai_api_key_here

# 腾讯云COS配置（如果需要测试上传功能）
COS_SECRET_ID=your_cos_secret_id_here
COS_SECRET_KEY=your_cos_secret_key_here
COS_REGION=ap-beijing
COS_BUCKET=your_bucket_name_here
COS_OBJECT_KEY=calendar/wsc_events.ics
        """)
        return False
    
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
        return True
    except Exception as e:
        logger.error(f"读取 .env 文件时出错: {e}")
        return False

def test_single_event():
    """测试单个事件的分析功能"""
    # 初始化分析器
    analyzer = EventAnalyzer()
    
    # 测试事件（使用更具体的事件）
    test_events = [
        "中国5月M2货币供应同比",
    ]
    
    for test_event in test_events:
        logger.info(f"\n测试事件: {test_event}")
        event_date = datetime.now(pytz.timezone('Asia/Shanghai'))
        
        # 1. 测试相关信息搜索
        logger.info("测试相关信息搜索...")
        related_info = analyzer.search_related_info(test_event, event_date)
        logger.info(f"找到 {len(related_info)} 条相关信息")
        for info in related_info:
            logger.info(f"- 标题: {info['title']}")
            logger.info(f"  来源: {info.get('institution', '未知')} {info.get('author', '')}")
            logger.info(f"  摘要: {info['snippet'][:200]}...")
            if info.get('industry'):
                logger.info(f"  相关行业: {', '.join(info['industry'])}")
            if info.get('concept'):
                logger.info(f"  相关概念: {', '.join(info['concept'])}")
            if info.get('companies'):
                # 处理公司信息，确保是字符串列表
                companies = []
                for company in info['companies']:
                    if isinstance(company, dict):
                        # 如果是字典，尝试获取公司名称
                        company_name = company.get('name', '') or company.get('company_name', '')
                        if company_name:
                            companies.append(company_name)
                    elif isinstance(company, str):
                        # 如果是字符串，直接添加
                        companies.append(company)
                if companies:
                    logger.info(f"  相关公司: {', '.join(companies)}")
        
        # 2. 测试投资机会分析
        logger.info("测试投资机会分析...")
        analysis = analyzer.analyze_investment_opportunity(test_event, event_date, related_info)
        
        # 3. 测试分析结果格式化
        logger.info("测试分析结果格式化...")
        formatted_analysis = analyzer.format_analysis_for_calendar(analysis)
        logger.info("\n最终分析结果:")
        print("\n" + "="*50)
        print(formatted_analysis)
        print("="*50 + "\n")

def main():
    """主测试函数"""
    logger.info("开始测试投资分析功能...")
    
    # 加载环境变量
    if not load_env():
        logger.error("无法加载环境变量，请检查 .env 文件")
        sys.exit(1)
    
    # 检查必要的环境变量
    required_vars = ['OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"缺少必要的环境变量: {', '.join(missing_vars)}")
        logger.info("请在 .env 文件中设置这些变量")
        return
    
    try:
        test_single_event()
        logger.info("测试完成!")
    except Exception as e:
        logger.error(f"测试过程中出错: {e}")
        raise

if __name__ == "__main__":
    main() 