#!/usr/bin/env python3
import requests
import os

def update_cloudflare_ips():
    """更新Cloudflare IP段"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ip_file = os.path.join(base_dir, "data", "cfipv4.txt")
    
    print("🔄 更新Cloudflare IP段...")
    
    try:
        # 从Cloudflare官网获取IP段
        response = requests.get("https://www.cloudflare.com/ips-v4", timeout=10)
        response.raise_for_status()
        
        with open(ip_file, 'w', encoding='utf-8') as f:
            f.write("# Cloudflare IPv4地址段\n")
            f.write("# 自动从 https://www.cloudflare.com/ips-v4 获取\n")
            f.write("# 更新时间: " + response.headers.get('Date', '') + "\n\n")
            f.write(response.text)
        
        print(f"✅ IP段更新完成: {ip_file}")
        
    except Exception as e:
        print(f"❌ 更新IP段失败: {e}")

if __name__ == "__main__":
    update_cloudflare_ips()
