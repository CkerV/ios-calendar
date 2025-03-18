#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import platform
from crontab import CronTab

def setup_cron_job():
    """设置每周一0点运行脚本的定时任务"""
    # 获取当前工作目录和脚本的绝对路径
    current_dir = os.getcwd()
    global_script_path = os.path.join(current_dir, 'fetch_calendar.py')
    china_script_path = os.path.join(current_dir, 'fetch_china_calendar.py')
    
    # 确保脚本可执行
    os.chmod(global_script_path, 0o755)
    os.chmod(china_script_path, 0o755)
    
    # 获取当前用户
    user = os.environ.get('USER')
    
    # 创建新的crontab
    cron = CronTab(user=user)
    
    # 检查是否已存在相同的任务
    for job in cron:
        if job.comment == 'wsc_calendar_sync' or job.comment == 'wsc_china_calendar_sync':
            print(f"定时任务已存在，正在移除旧任务...({job.comment})")
            cron.remove(job)
            cron.write()
    
    # 创建全球日历任务 - 每周一0点执行
    global_job = cron.new(command=f"{sys.executable} {global_script_path}", comment='wsc_calendar_sync')
    global_job.setall('0 0 * * 1')  # 每周一0点
    
    # 创建中国日历任务 - 每周一0点5分执行（避免并发）
    china_job = cron.new(command=f"{sys.executable} {china_script_path}", comment='wsc_china_calendar_sync')
    china_job.setall('5 0 * * 1')  # 每周一0点5分
    
    # 写入crontab
    cron.write()
    
    print(f"成功设置定时任务:")
    print(f"- 全球日历: 每周一0点自动运行 {global_script_path}")
    print(f"  下次运行时间: {global_job.schedule().get_next()}")
    print(f"- 中国日历: 每周一0点5分自动运行 {china_script_path}")
    print(f"  下次运行时间: {china_job.schedule().get_next()}")

def setup_launchd_job():
    """为macOS创建LaunchAgent定时任务"""
    # 获取当前工作目录和脚本的绝对路径
    current_dir = os.getcwd()
    global_script_path = os.path.join(current_dir, 'fetch_calendar.py')
    china_script_path = os.path.join(current_dir, 'fetch_china_calendar.py')
    
    # 确保脚本可执行
    os.chmod(global_script_path, 0o755)
    os.chmod(china_script_path, 0o755)
    
    # LaunchAgent路径
    plist_dir = os.path.expanduser('~/Library/LaunchAgents')
    os.makedirs(plist_dir, exist_ok=True)
    
    # 创建全球日历LaunchAgent
    global_plist_path = os.path.join(plist_dir, 'com.user.wsccalendarsync.plist')
    
    # 创建plist文件内容
    global_plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.wsccalendarsync</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{global_script_path}</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>0</integer>
        <key>Minute</key>
        <integer>0</integer>
        <key>Weekday</key>
        <integer>1</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{current_dir}/calendar_sync_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>{current_dir}/calendar_sync_stderr.log</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>'''
    
    # 创建中国日历LaunchAgent
    china_plist_path = os.path.join(plist_dir, 'com.user.wscchinalendarsync.plist')
    
    # 创建plist文件内容
    china_plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.wscchinalendarsync</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{china_script_path}</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>0</integer>
        <key>Minute</key>
        <integer>5</integer>
        <key>Weekday</key>
        <integer>1</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{current_dir}/china_calendar_sync_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>{current_dir}/china_calendar_sync_stderr.log</string>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>'''
    
    # 写入全球日历plist文件
    with open(global_plist_path, 'w') as f:
        f.write(global_plist_content)
    
    # 写入中国日历plist文件  
    with open(china_plist_path, 'w') as f:
        f.write(china_plist_content)
    
    # 加载LaunchAgent
    try:
        # 加载全球日历LaunchAgent
        subprocess.run(['launchctl', 'unload', global_plist_path], check=False)
        subprocess.run(['launchctl', 'load', global_plist_path], check=True)
        
        # 加载中国日历LaunchAgent
        subprocess.run(['launchctl', 'unload', china_plist_path], check=False)
        subprocess.run(['launchctl', 'load', china_plist_path], check=True)
        
        print(f"成功创建并加载LaunchAgent:")
        print(f"- 全球日历: {global_plist_path}")
        print(f"- 中国日历: {china_plist_path}")
        print("定时任务将在每周一0点（全球日历）和0点5分（中国日历）自动运行")
    except subprocess.CalledProcessError as e:
        print(f"加载LaunchAgent时出错: {e}")
        print("您可能需要手动加载:")
        print(f"launchctl load {global_plist_path}")
        print(f"launchctl load {china_plist_path}")

def main():
    system = platform.system()
    
    if system == 'Darwin':  # macOS
        print("检测到macOS系统，使用LaunchAgent设置定时任务...")
        setup_launchd_job()
    else:  # Linux或其他类Unix系统
        print("使用Crontab设置定时任务...")
        setup_cron_job()
    
    print("\n设置完成！如果您想手动运行一次脚本来测试，请执行:")
    print("python3 fetch_calendar.py        # 获取全球日历")
    print("python3 fetch_china_calendar.py  # 获取中国日历")

if __name__ == "__main__":
    main() 