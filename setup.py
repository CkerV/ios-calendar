#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import platform

def check_dependencies():
    """检查并安装依赖"""
    print("检查依赖...")
    
    # 尝试导入所需模块
    missing_modules = []
    try:
        import requests
    except ImportError:
        missing_modules.append("requests")
    
    try:
        import ics
    except ImportError:
        missing_modules.append("ics")
    
    try:
        import crontab
    except ImportError:
        missing_modules.append("python-crontab")
    
    # 如果有缺少的模块，尝试安装
    if missing_modules:
        print(f"需要安装以下依赖: {', '.join(missing_modules)}")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
            print("依赖安装成功！")
        except subprocess.CalledProcessError:
            print("依赖安装失败。请手动运行: pip install -r requirements.txt")
            return False
    else:
        print("所有依赖已安装。")
    
    return True

def test_api():
    """测试API连接"""
    print("\n测试API连接...")
    try:
        result = subprocess.run([sys.executable, "test_api.py"], capture_output=True, text=True)
        print(result.stdout)
        if result.returncode != 0:
            print("API测试失败。")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"运行测试失败: {e}")
        return False
    
    return True

def setup_cron():
    """设置定时任务"""
    print("\n设置定时任务...")
    try:
        result = subprocess.run([sys.executable, "setup_cron.py"], capture_output=True, text=True)
        print(result.stdout)
        if result.returncode != 0:
            print("设置定时任务失败。")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"设置定时任务失败: {e}")
        return False
    
    return True

def fetch_calendar():
    """生成日历文件"""
    print("\n生成日历文件...")
    try:
        result = subprocess.run([sys.executable, "fetch_calendar.py"], capture_output=True, text=True)
        print(result.stdout)
        if result.returncode != 0:
            print("生成日历文件失败。")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"生成日历文件失败: {e}")
        return False
    
    return True

def main():
    """主函数"""
    print("=== 华尔街见闻日历自动订阅工具一键设置 ===\n")
    
    # 检查当前脚本是否有执行权限
    script_path = os.path.abspath(__file__)
    if not os.access(script_path, os.X_OK):
        os.chmod(script_path, 0o755)
    
    # 确保其他脚本有执行权限
    for script in ["fetch_calendar.py", "setup_cron.py", "test_api.py"]:
        if os.path.exists(script) and not os.access(script, os.X_OK):
            os.chmod(script, 0o755)
    
    # 检查并安装依赖
    if not check_dependencies():
        print("安装依赖失败，请手动安装后重试。")
        return
    
    # 测试API连接
    if not test_api():
        print("API测试失败，设置中止。")
        return
    
    # 确认是否继续
    response = input("\n是否继续设置定时任务？(y/n): ")
    if response.lower() != 'y':
        print("设置中止。")
        return
    
    # 设置定时任务
    if not setup_cron():
        print("设置定时任务失败。")
        return
    
    # 生成日历文件
    if not fetch_calendar():
        print("生成日历文件失败。")
        return
    
    print("\n=== 设置完成！===")
    print("日历文件已生成在 calendar_files/wsc_events.ics")
    print("定时任务已设置为每周一0点自动运行")
    
    # 打印导入iOS日历说明
    system = platform.system()
    if system == 'Darwin':  # macOS
        print("\n您可以使用AirDrop将日历文件发送到您的iOS设备。")
    else:
        print("\n请将日历文件传输到您的iOS设备。")
    
    print("\n详细使用说明请参考 README.md 文件。")

if __name__ == "__main__":
    main() 