#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import platform
import sys

def setup_cos_config():
    """设置腾讯云COS配置"""
    print("=== 腾讯云COS配置设置 ===")
    print("请输入以下信息以配置腾讯云COS：")

    # 获取COS配置信息
    secret_id = input("SecretId: ").strip()
    if not secret_id:
        print("错误: SecretId不能为空")
        return False

    secret_key = input("SecretKey: ").strip()
    if not secret_key:
        print("错误: SecretKey不能为空")
        return False

    region = input("区域(Region) [默认: ap-beijing]: ").strip() or "ap-beijing"
    
    bucket = input("存储桶名称(Bucket): ").strip()
    if not bucket:
        print("错误: 存储桶名称不能为空")
        return False
        
    object_key = input("对象键(Object Key) [默认: calendar/wsc_events.ics]: ").strip() or "calendar/wsc_events.ics"

    # 保存配置到文件
    config = {
        "COS_SECRET_ID": secret_id,
        "COS_SECRET_KEY": secret_key,
        "COS_REGION": region,
        "COS_BUCKET": bucket,
        "COS_OBJECT_KEY": object_key
    }
    
    config_dir = os.path.expanduser("~/.config/wsc_calendar")
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "cos_config.json")
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"\n配置已保存到: {config_path}")
    
    # 设置环境变量
    if platform.system() == "Darwin":  # macOS
        # 为.zshrc或.bash_profile添加环境变量
        shell_rc = os.path.expanduser("~/.zshrc")
        if not os.path.exists(shell_rc):
            shell_rc = os.path.expanduser("~/.bash_profile")
        
        with open(shell_rc, "a") as f:
            f.write("\n# 腾讯云COS配置\n")
            for key, value in config.items():
                f.write(f"export {key}='{value}'\n")
        
        print(f"\n环境变量已添加到: {shell_rc}")
        print("请运行以下命令使环境变量生效:")
        print(f"source {shell_rc}")
    
    else:  # Linux或其他
        # 为.bashrc添加环境变量
        bashrc = os.path.expanduser("~/.bashrc")
        
        with open(bashrc, "a") as f:
            f.write("\n# 腾讯云COS配置\n")
            for key, value in config.items():
                f.write(f"export {key}='{value}'\n")
        
        print(f"\n环境变量已添加到: {bashrc}")
        print("请运行以下命令使环境变量生效:")
        print(f"source {bashrc}")
    
    # 临时设置当前会话的环境变量
    for key, value in config.items():
        os.environ[key] = value
    
    print("\n当前会话的环境变量已设置")
    print("配置成功！您现在可以运行 python fetch_calendar.py 来测试上传功能")
    
    return True

if __name__ == "__main__":
    setup_cos_config() 