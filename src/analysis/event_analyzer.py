"""
Event Analyzer for Financial Calendar Events
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
import os
from datetime import datetime
import json
import http.client
from urllib.parse import quote
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("event_analyzer")

def load_env():
    """从.env文件加载环境变量"""
    env_path = Path('.env')
    if not env_path.exists():
        logger.warning("找不到 .env 文件")
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

class EventAnalyzer:
    def __init__(self):
        """初始化事件分析器"""
        # 尝试加载 .env 文件
        load_env()
        
        # 配置API密钥
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        
        if not self.openai_api_key:
            logger.warning("OpenAI API密钥未设置")
        
        # 配置OpenAI
        self.client = OpenAI(api_key=self.openai_api_key)

    def search_related_info(self, event_summary: str, event_date: datetime) -> List[Dict]:
        """使用 Reportify API 搜索相关研报信息"""
        try:
            # 构建搜索查询
            date_str = event_date.strftime("%Y-%m-%d")
            
            # URL编码查询参数
            encoded_query = quote(event_summary)
            current_timestamp = int(datetime.now().timestamp() * 1000)
            
            # 构建API URL
            base_url = "https://api.reportify.cn/reports"
            params = {
                "page_num": "1",
                "page_size": "10",
                "channel_id": "",
                "report_types": "7,8,9,10,11,16,19,20,21,22,23,24,25",
                "query": encoded_query,
                "rt": str(current_timestamp)
            }
            
            # 构建完整URL
            url = f"{base_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
            
            logger.info(f"搜索查询URL: {url}")
            
            # 创建HTTP连接
            conn = http.client.HTTPSConnection("api.reportify.cn")
            
            # 发送请求
            logger.info("发送搜索请求...")
            conn.request("GET", f"/reports?{'&'.join(f'{k}={v}' for k, v in params.items())}")
            
            # 获取响应
            response = conn.getresponse()
            data = response.read()
            
            # 解析响应
            results = json.loads(data.decode('utf-8'))
            logger.info(f"搜索结果原始数据: {json.dumps(results, ensure_ascii=False, indent=2)}")
            
            # 提取研报摘要信息
            relevant_info = []
            if "items" in results:
                for item in results["items"]:
                    if "summary" in item and item["summary"]:
                        # 从 labels 中提取行业、概念信息
                        labels = item.get("labels", {})
                        industry = labels.get("industry", [])
                        concept = labels.get("concept", [])
                        
                        # 从 companies 中提取公司信息
                        companies = []
                        
                        # 优先从 companies 字段获取（因为这里有完整的股票信息）
                        if item.get("companies"):
                            for company in item["companies"]:
                                if isinstance(company, dict):
                                    company_name = company.get("name", "")
                                    stocks = company.get("stocks", [])
                                    if company_name and stocks:
                                        # 优先使用 A 股代码
                                        stock_info = None
                                        for stock in stocks:
                                            if isinstance(stock, dict):
                                                symbol = stock.get("symbol", "")
                                                if symbol:
                                                    # 优先级：A股 > 港股 > 美股
                                                    if symbol.startswith(("SH:", "SZ:")):
                                                        stock_info = symbol
                                                        break
                                                    elif symbol.startswith("HK:") and not stock_info:
                                                        stock_info = symbol
                                                    elif symbol.startswith("US:") and not stock_info:
                                                        stock_info = symbol
                                        
                                        if stock_info:
                                            companies.append(f"{company_name}({stock_info})")
                                        else:
                                            companies.append(company_name)
                                elif isinstance(company, str):
                                    companies.append(company)
                        
                        # 如果没有找到公司信息，尝试从摘要中提取
                        if not companies:
                            summary = item.get("summary", "")
                            company_matches = re.findall(r"【([^】]+)】", summary)
                            if company_matches:
                                companies = company_matches
                        
                        # 如果还是没有，尝试从 labels 中获取
                        if not companies and "company" in labels:
                            companies = labels["company"]
                        
                        relevant_info.append({
                            "title": item.get("title", ""),
                            "snippet": item.get("summary", ""),
                            "link": item.get("report_url", ""),
                            "date": date_str,
                            "institution": item.get("institution_name", ""),
                            "author": item.get("author_names", ""),
                            "industry": industry,
                            "concept": concept,
                            "companies": companies
                        })
            else:
                logger.warning(f"未找到研报结果，完整响应: {results}")
                
            return relevant_info
            
        except Exception as e:
            logger.error(f"搜索相关信息时出错: {e}")
            logger.exception("详细错误信息：")
            return []
        finally:
            if 'conn' in locals():
                conn.close()

    def analyze_investment_opportunity(self, event_summary: str, event_date: datetime, 
                                    related_info: List[Dict]) -> Dict:
        """使用OpenAI分析投资机会"""
        if not self.openai_api_key:
            logger.error("OpenAI API密钥未设置，无法执行分析")
            return {}
            
        try:
            # 构建提示词
            prompt = self._build_analysis_prompt(event_summary, event_date, related_info)
            
            # 调用OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # 使用 gpt-4o-mini 模型
                messages=[
                    {"role": "system", "content": """你是一个专业的金融分析师，专注于分析财经事件并提供投资见解。
请严格按照指定的JSON格式输出分析结果。确保输出的JSON格式正确，每个字段都必须存在且格式符合要求。
不要在JSON中包含任何额外的文本说明。"""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            # 解析响应
            analysis = response.choices[0].message.content
            
            # 将分析结果结构化
            try:
                # 清理响应文本，确保它是有效的JSON
                analysis = analysis.strip()
                if analysis.startswith('```json'):
                    analysis = analysis[7:]
                if analysis.endswith('```'):
                    analysis = analysis[:-3]
                analysis = analysis.strip()
                
                analysis_dict = json.loads(analysis)
                
                # 验证结果格式
                required_fields = ['investment_opportunities', 'potential_risks', 'potential_returns']
                if not all(field in analysis_dict for field in required_fields):
                    raise ValueError("Missing required fields in analysis result")
                
                return analysis_dict
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"解析分析结果时出错: {e}")
                # 返回默认结构
                return {
                    "investment_opportunities": [
                        {
                            "type": "未分类",
                            "target": "未指定",
                            "rationale": "无法解析分析结果"
                        }
                    ],
                    "potential_risks": [
                        {
                            "type": "解析错误",
                            "description": "无法正确解析AI的分析结果",
                            "mitigation": "请重试或联系技术支持"
                        }
                    ],
                    "potential_returns": {
                        "timeframe": "未知",
                        "upside": "需要重新分析",
                        "catalysts": ["无法确定"]
                    }
                }
            
        except Exception as e:
            logger.error(f"分析投资机会时出错: {e}")
            return {}

    def _build_analysis_prompt(self, event_summary: str, event_date: datetime, 
                             related_info: List[Dict]) -> str:
        """构建分析提示词"""
        prompt = f"""
请分析以下财经事件和相关信息，提供投资见解：

事件信息：
- 事件：{event_summary}
- 日期：{event_date.strftime('%Y-%m-%d')}

相关资料：
"""
        # 收集所有相关的行业、概念和公司
        all_industries = set()
        all_concepts = set()
        all_companies = set()
        
        for info in related_info:
            prompt += f"- {info['title']}\n"
            prompt += f"  来源：{info.get('institution', '未知')} {info.get('author', '')}\n"
            prompt += f"  摘要：{info['snippet']}\n"
            
            # 收集标签信息
            all_industries.update(info.get('industry', []))
            all_concepts.update(info.get('concept', []))
            all_companies.update(info.get('companies', []))
            
        # 添加标签信息到提示词
        if all_industries:
            prompt += "\n相关行业：\n"
            for industry in all_industries:
                prompt += f"- {industry}\n"
                
        if all_concepts:
            prompt += "\n相关概念：\n"
            for concept in all_concepts:
                prompt += f"- {concept}\n"
                
        if all_companies:
            prompt += "\n相关公司：\n"
            for company in all_companies:
                prompt += f"- {company}\n"
            
        prompt += """
请提供以下格式的JSON分析结果：
{
    "related_sectors": {
        "industries": ["相关行业1", "相关行业2"],
        "concepts": ["相关概念1", "相关概念2"],
        "companies": ["相关公司1", "相关公司2"]
    },
    "investment_opportunities": [
        {
            "type": "机会类型（个股/行业/主题）",
            "target": "投资标的",
            "rationale": "投资逻辑"
        }
    ],
    "potential_risks": [
        {
            "type": "风险类型",
            "description": "风险描述",
            "mitigation": "风险缓解建议"
        }
    ],
    "potential_returns": {
        "timeframe": "预期时间范围",
        "upside": "上行空间预估",
        "catalysts": ["潜在催化剂1", "潜在催化剂2"]
    }
}

请确保在分析中充分利用相关行业、概念和公司信息，并在investment_opportunities中优先考虑这些标的。
"""
        return prompt

    def format_analysis_for_calendar(self, analysis: Dict) -> str:
        """将分析结果格式化为日历事件描述"""
        description = ""
        
        # 添加相关公司
        if "related_sectors" in analysis and analysis["related_sectors"].get("companies"):
            description += "🏢 相关标的\n"
            for company in analysis["related_sectors"]["companies"]:
                # 公司信息可能已经包含股票代码
                if '(' in str(company) and ')' in str(company):
                    description += f"└ {company}\n"
                else:
                    description += f"└ {company}\n"
            description += "\n"
        
        # 添加投资机会和风险分析
        description += "🔍 投资分析\n"
        
        # 添加投资机会
        if "investment_opportunities" in analysis and isinstance(analysis["investment_opportunities"], list):
            description += "\n📈 投资机会\n"
            for opp in analysis["investment_opportunities"]:
                if isinstance(opp, dict):
                    description += f"【{opp.get('type', '未分类')}】{opp.get('target', '未指定')}\n"
                    description += f"└ 投资逻辑: {opp.get('rationale', '无')}\n"
                    # 添加相关催化剂
                    if "potential_returns" in analysis and isinstance(analysis["potential_returns"], dict):
                        catalysts = analysis["potential_returns"].get('catalysts', [])
                        if catalysts:
                            description += "└ 关键催化剂:\n"
                            for catalyst in catalysts:
                                description += f"   • {catalyst}\n"
                else:
                    description += f"【{str(opp)}】\n"
                
        # 添加潜在风险
        if "potential_risks" in analysis and isinstance(analysis["potential_risks"], list):
            description += "\n⚠️ 风险提示\n"
            for risk in analysis["potential_risks"]:
                if isinstance(risk, dict):
                    description += f"【{risk.get('type', '未分类')}】{risk.get('description', '无描述')}\n"
                    description += f"└ 应对策略: {risk.get('mitigation', '无建议')}\n"
                else:
                    description += f"【{str(risk)}】\n"
                
        # 添加免责声明
        description += "\n⚠️ 免责声明: 本分析由AI生成，仅供参考，不构成投资建议。投资有风险，入市需谨慎。"
        
        return description 