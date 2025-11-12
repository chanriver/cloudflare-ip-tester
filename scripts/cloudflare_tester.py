#!/usr/bin/env python3
import requests
import time
import concurrent.futures
import ipaddress
import os
from datetime import datetime
from typing import List, Dict
import sys
import random
import json

class CloudflareTester:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.geoip_db_path = os.path.join(self.base_dir, "data", "GeoLite2-Country.mmdb")
        self.ip_file_path = os.path.join(self.base_dir, "data", "cfipv4.txt")
        self.output_path = os.path.join(self.base_dir, "results", "results.txt")
        
        self.results = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*'
        })
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        
        # 中文国家名映射
        self.country_names_zh = {
            'US': '美国', 'GB': '英国', 'DE': '德国', 'FR': '法国', 'JP': '日本',
            'KR': '韩国', 'SG': '新加坡', 'AU': '澳大利亚', 'CA': '加拿大', 'BR': '巴西',
            'IN': '印度', 'RU': '俄罗斯', 'CN': '中国', 'HK': '中国香港', 'TW': '中国台湾',
            'NL': '荷兰', 'CH': '瑞士', 'SE': '瑞典', 'NO': '挪威', 'FI': '芬兰',
        }
        
        # 国旗emoji映射
        self.flag_emojis = {
            'US': '🇺🇸', 'GB': '🇬🇧', 'DE': '🇩🇪', 'FR': '🇫🇷', 'JP': '🇯🇵',
            'KR': '🇰🇷', 'SG': '🇸🇬', 'AU': '🇦🇺', 'CA': '🇨🇦', 'BR': '🇧🇷',
            'IN': '🇮🇳', 'RU': '🇷🇺', 'CN': '🇨🇳', 'HK': '🇭🇰', 'TW': '🇹🇼',
            'NL': '🇳🇱', 'CH': '🇨🇭', 'SE': '🇸🇪', 'NO': '🇳🇴', 'FI': '🇫🇮',
        }

    def get_country_by_online_api(self, ip: str) -> tuple:
        """使用在线API获取国家信息"""
        try:
            response = self.session.get(f"http://ip-api.com/json/{ip}?fields=countryCode", timeout=3)
            if response.status_code == 200:
                data = response.json()
                country_code = data.get('countryCode', '')
                if country_code:
                    country_name = self.country_names_zh.get(country_code, country_code)
                    flag = self.flag_emojis.get(country_code, '🏴')
                    return country_name, flag
        except:
            pass
        return "未知", "🏴"

    def generate_test_ips(self) -> List[str]:
        """生成测试IP"""
        print("📝 生成测试IP...")
        
        try:
            with open(self.ip_file_path, 'r', encoding='utf-8') as f:
                cidrs = [line.strip() for line in f if line.strip()]
            
            test_ips = []
            
            for cidr in cidrs:
                if not cidr or cidr.startswith('#'):
                    continue
                    
                try:
                    net = ipaddress.ip_network(cidr)
                    
                    # 采样数量（4倍于原始数量）
                    if net.num_addresses > 100000:
                        sample_size = 40
                    elif net.num_addresses > 10000:
                        sample_size = 24
                    elif net.num_addresses > 1000:
                        sample_size = 12
                    elif net.num_addresses > 100:
                        sample_size = 8
                    else:
                        sample_size = 4
                    
                    hosts = list(net.hosts())
                    if len(hosts) >= sample_size:
                        samples = random.sample(hosts, min(sample_size, len(hosts)))
                        test_ips.extend(str(ip) for ip in samples)
                    else:
                        test_ips.extend(str(ip) for ip in hosts[:min(20, len(hosts))])
                        
                except Exception as e:
                    continue
            
            test_ips = list(set(test_ips))
            print(f"✅ 生成 {len(test_ips)} 个测试IP")
            return test_ips
            
        except Exception as e:
            print(f"❌ 读取IP段文件失败: {e}")
            return []

    def test_ip_speed(self, ip: str) -> float:
        """测试IP速度"""
        test_urls = [
            f"http://{ip}/cdn-cgi/trace",
            f"http://{ip}/__down?bytes=1000",
        ]
        
        delays = []
        
        for url in test_urls:
            try:
                start_time = time.time()
                response = self.session.get(url, timeout=3, verify=False)
                end_time = time.time()
                
                if response.status_code in [200, 204]:
                    delay = (end_time - start_time) * 1000
                    if delay < 5000:
                        delays.append(delay)
            except:
                continue
        
        return min(delays) if delays else 9999.0

    def test_single_ip(self, ip: str) -> Dict:
        """测试单个IP"""
        try:
            ipaddress.IPv4Address(ip)
            
            delay = self.test_ip_speed(ip)
            
            if delay < 9999:
                country, flag = self.get_country_by_online_api(ip)
                
                return {
                    'ip': ip,
                    'delay': delay,
                    'country': country,
                    'flag': flag
                }
            else:
                return None
                
        except:
            return None

    def run_test(self):
        """运行测试"""
        print("🌐 Cloudflare IP测速开始...")
        
        test_ips = self.generate_test_ips()
        if not test_ips:
            return
        
        results = []
        
        # 并发测试
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_ip = {executor.submit(self.test_single_ip, ip): ip for ip in test_ips}
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_ip):
                try:
                    result = future.result()
                    if result is not None:
                        results.append(result)
                    completed += 1
                except:
                    completed += 1
                
                if completed % 50 == 0:
                    print(f"📊 进度: {completed}/{len(test_ips)}")
        
        # 排序并取前20
        sorted_results = sorted(results, key=lambda x: x['delay'])[:20]
        self.results = sorted_results
        
        # 保存结果
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write("# Cloudflare最佳IPv4节点列表\n")
            f.write(f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# 格式: IP#国家 国旗 延迟ms\n\n")
            
            for result in sorted_results:
                line = f"{result['ip']}#{result['country']} {result['flag']} {result['delay']:.0f}ms"
                f.write(line + '\n')
        
        print(f"✅ 测试完成！找到 {len(sorted_results)} 个最佳IP")
        print(f"💾 结果保存到: {self.output_path}")

if __name__ == "__main__":
    tester = CloudflareTester()
    tester.run_test()
