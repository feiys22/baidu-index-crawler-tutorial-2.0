#!/usr/bin/env python3
"""
百度指数爬虫 - Scrapling 版
使用 Scrapling 的 FetcherSession（模拟 Chrome TLS 指纹 + stealth 请求头）调用百度指数 API
相比原 qdata 方案，Scrapling 的 anti-bot 能力更强，长期更稳定

========== 安装 ==========
pip install scrapling[all,full]

========== 使用 ==========
python baidu_index_scrapling.py              # 完整爬取（支持断点续爬）
python baidu_index_scrapling.py --test        # 测试模式（只爬上海）
python baidu_index_scrapling.py --city 北京    # 爬单个城市

========== Cookie 获取 ==========
1. Chrome 打开 https://index.baidu.com 并登录
2. F12 → Application → Cookies → https://index.baidu.com
3. 复制所有 Cookie 字符串，填入下方 COOKIE_LIST
"""

from scrapling.fetchers import FetcherSession
from Crypto.Cipher import AES
from base64 import b64encode
import csv
import time
import random
import json
import os
import re
import math
import argparse
import datetime
from urllib.parse import urlencode, quote

# ==================== 配置 ====================

COOKIE_LIST = [
    # ==== 在这里填入你的百度 Cookie ====
    # 获取方法：
    # 1. Chrome 打开 https://index.baidu.com 并登录
    # 2. F12 -> Application -> Cookies
    # 3. 复制全部 Cookie 字符串
    # 4. 用三引号包裹，填入下方（示例见README）
    # 5. 多个Cookie用逗号分隔，可实现轮询
    "",
]

KEYWORDS = [
    '人工智能', '大数据', '云计算', '物联网', '区块链',
    '半导体', '金融安全', '智能交通'
]

CITY_LIST = [
    ("上海", 910), ("北京", 911), ("深圳", 94), ("重庆", 904), ("广州", 95)
   
]

START_DATE = '2026-03-01'
END_DATE = '2026-03-15'
# 每次最多请求的天数（百度限制约300天）
MAX_DAYS_PER_REQUEST = 300

# 输出目录（脚本同目录下的 output/）
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
PROGRESS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crawl_progress.json')

# ==================== 百度指数 API 加密工具函数 ====================
# 百度指数对请求参数和返回数据都做了加密，需要在请求头加上 Cipher-Text
# 并用 uniqid 作为密钥对返回数据解密

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"


def get_cipher_text(keyword):
    """生成 Cipher-Text 请求头（百度指数反爬机制）"""
    byte_list = [bytes([i]) for i in range(17)]
    # 这个起始时间戳是从百度前端脚本 acs-2057.js 来的
    start_time = 1763957172935
    end_time = int(datetime.datetime.now().timestamp() * 1000)
    
    quoted_keyword = quote(keyword)
    wait_encrypted_data = {
        "ua": USER_AGENT,
        "url": f"https://index.baidu.com/v2/main/index.html#/trend/{quoted_keyword}?words={quoted_keyword}",
        "platform": "MacIntel",
        "clientTs": end_time,
        "version": "1.0.0.5",
    }
    password = b"goqwgaiiacaykuwo"
    iv = b"1234567887654321"
    aes = AES.new(password, AES.MODE_CBC, iv)
    wait_encrypted_str = json.dumps(wait_encrypted_data, separators=(",", ":")).encode()
    filled_count = 16 - len(wait_encrypted_str) % 16
    wait_encrypted_str += byte_list[filled_count] * filled_count
    encrypted_str = aes.encrypt(wait_encrypted_str)
    cipher_text = f"{start_time}_{end_time}_{b64encode(encrypted_str).decode()}"
    return cipher_text


def get_key(session, uniqid, cookie_str):
    """获取 uniqid 对应的解密密钥"""
    url = f"https://index.baidu.com/Interface/api/ptbk?uniqid={uniqid}"
    cookies = dict(item.strip().split("=", 1) for item in cookie_str.split(";") if "=" in item)
    resp = session.get(url, cookies=cookies, stealthy_headers=True, impersonate="chrome", timeout=15)
    if resp.status == 200:
        data = resp.json()
        return data.get("data", "")
    return ""


def decrypt_func(key, data):
    """百度指数数据解密"""
    if not key or not data:
        return []
    n = {}
    s = []
    for o in range(len(key) // 2):
        n[key[o]] = key[len(key) // 2 + o]
    for r in range(len(data)):
        s.append(n[data[r]])
    return "".join(s).split(",")


def split_keywords(keywords):
    """百度 API 限制一个请求最多3个关键词"""
    n = 3
    return [keywords[i*n:(i+1)*n] for i in range(math.ceil(len(keywords)/n))]


def get_time_range_list(startdate, enddate):
    """切分时间段（不超过300天/段）"""
    date_range_list = []
    startdate = datetime.datetime.strptime(startdate, "%Y-%m-%d")
    enddate = datetime.datetime.strptime(enddate, "%Y-%m-%d")
    while True:
        tempdate = startdate + datetime.timedelta(days=MAX_DAYS_PER_REQUEST)
        if tempdate > enddate:
            date_range_list.append((startdate, enddate))
            break
        date_range_list.append((startdate, tempdate))
        startdate = tempdate + datetime.timedelta(days=1)
    return date_range_list


def build_cookie_dict(cookie_str):
    """Cookie 字符串转 dict"""
    cookies = {}
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


# ==================== 爬取逻辑 ====================

def crawl_city(session, city_name, city_code, cookie_str):
    """爬取单个城市的数据"""
    all_data = []
    keyword_batches = split_keywords(KEYWORDS)
    total_batch = len(keyword_batches)
    time_ranges = get_time_range_list(START_DATE, END_DATE)
    
    cookies = build_cookie_dict(cookie_str)
    
    print(f"[{city_name}] 开始爬取, {total_batch} 批关键词 × {len(time_ranges)} 个时间段")
    
    for batch_num, kw_batch in enumerate(keyword_batches, 1):
        print(f"  [{batch_num}/{total_batch}] 关键词: {kw_batch}")
        
        retry_count = 0
        max_retry = 3
        success = False
        
        while retry_count < max_retry and not success:
            try:
                # 构造关键词参数
                word_list = [[{"name": kw, "wordType": 1} for kw in kw_batch]]
                
                # 遍历时间段
                for sd, ed in time_ranges:
                    params = {
                        "word": json.dumps(word_list),
                        "startDate": sd.strftime("%Y-%m-%d"),
                        "endDate": ed.strftime("%Y-%m-%d"),
                        "area": city_code,
                    }
                    url = "https://index.baidu.com/api/SearchApi/index?" + urlencode(params)
                    
                    # 生成 Cipher-Text
                    cipher_text = get_cipher_text(kw_batch[0])
                    
                    headers = {
                        "Cipher-Text": cipher_text,
                        "Referer": "https://index.baidu.com/v2/main/index.html",
                        "Origin": "https://index.baidu.com",
                        "Accept": "application/json, text/plain, */*",
                    }
                    
                    resp = session.get(
                        url,
                        cookies=cookies,
                        headers=headers,
                        impersonate="chrome",
                        stealthy_headers=True,
                        timeout=30,
                    )
                    
                    if resp.status != 200:
                        raise Exception(f"HTTP {resp.status}")
                    
                    data = resp.json()
                    if data.get("status") == 10000:
                        raise Exception("未登录，Cookie 可能需要更新")
                    if data.get("status") == 10001:
                        raise Exception("REQUEST_LIMITED 触发限流")
                    if data.get("status") != 0:
                        raise Exception(f"API 错误: {data}")
                    
                    # 解密数据
                    encrypt_datas = data["data"]["userIndexes"]
                    uniqid = data["data"]["uniqid"]
                    key = get_key(session, uniqid, cookie_str)
                    
                    for enc_data in encrypt_datas:
                        word_data = enc_data["word"]
                        if isinstance(word_data, str):
                            keyword_list = json.loads(word_data.replace("'", '"'))
                        else:
                            keyword_list = word_data
                        
                        for kind in ["all", "pc", "wise"]:
                            raw = enc_data.get(kind, {}).get("data", "")
                            decrypted = decrypt_func(key, raw)
                            
                            # 生成日期列表
                            sd_str = enc_data[kind]["startDate"]
                            ed_str = enc_data[kind]["endDate"]
                            sdd = datetime.datetime.strptime(sd_str, "%Y-%m-%d")
                            edd = datetime.datetime.strptime(ed_str, "%Y-%m-%d")
                            date_list = []
                            cur = sdd
                            while cur <= edd:
                                date_list.append(cur)
                                cur += datetime.timedelta(days=1)
                            
                            # 百度 API 对同一批次的所有关键词返回相同指数
                            # 所以每批关键词共享一组日期序列数据
                            kw_names = [kw["name"] for kw in keyword_list]
                            for i, d in enumerate(date_list):
                                index_val = decrypted[i] if i < len(decrypted) else "0"
                                if not index_val:
                                    index_val = "0"
                                for kw_name in kw_names:
                                    all_data.append({
                                        "date": d.strftime("%Y-%m-%d"),
                                        "keyword": kw_name,
                                        "city": city_name,
                                        "type": kind,
                                        "index": index_val
                                    })
                
                success = True
                print(f"  ✅ 完成")
                
            except Exception as e:
                retry_count += 1
                err = str(e)
                print(f"  第{retry_count}次失败: {err[:80]}")
                
                if "REQUEST_LIMITED" in err:
                    wait = 15 * (2 ** (retry_count - 1))
                    print(f"  限流，等待{wait}秒换 Cookie 重试...")
                    time.sleep(wait)
                    # 换一个 Cookie
                    cookie_str = random.choice([c for c in COOKIE_LIST if c])
                    cookies = build_cookie_dict(cookie_str)
                else:
                    time.sleep(5 * retry_count)
        
        # 批次间延时
        if batch_num < total_batch:
            delay = random.gauss(3, 1)
            delay = max(1, delay)
            time.sleep(delay)
    
    # 保存 CSV
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_file = os.path.join(OUTPUT_DIR, f"{city_name}_baidu_index.csv")
    with open(out_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "keyword", "city", "type", "index"])
        writer.writeheader()
        writer.writerows(all_data)
    
    print(f"✅ {city_name}: 共 {len(all_data)} 条 → {os.path.basename(out_file)}")
    return True


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed_cities": []}


def save_progress(completed):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({"completed_cities": completed}, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="百度指数爬虫 - Scrapling 版")
    parser.add_argument("--test", action="store_true", help="测试模式（只爬上海）")
    parser.add_argument("--city", type=str, help="只爬指定城市")
    args = parser.parse_args()
    
    valid_cookies = [c for c in COOKIE_LIST if c]
    if not valid_cookies:
        print("\n⚠️  请先在脚本顶部的 COOKIE_LIST 中填入百度 Cookie！")
        print("   获取方法：Chrome 登录 https://index.baidu.com → F12 → Application → Cookies\n")
        return
    
    if args.city:
        todo = [c for c in CITY_LIST if c[0] == args.city]
        if not todo:
            print(f"未找到城市: {args.city}")
            return
    elif args.test:
        todo = [CITY_LIST[0]]
        print("🧪 测试模式：只爬取上海")
    else:
        progress = load_progress()
        done = set(progress.get("completed_cities", []))
        todo = [c for c in CITY_LIST if c[0] not in done]
        print(f"已有 {len(done)} 个城市完成，待爬 {len(todo)} 个")
    
    print(f"关键词: {len(KEYWORDS)} | 城市: {len(todo)} | 日期: {START_DATE} ~ {END_DATE}\n")
    
    with FetcherSession(impersonate="chrome", stealthy_headers=True) as session:
        for idx, (city_name, city_code) in enumerate(todo, 1):
            print(f"\n{'='*50}")
            print(f"[{idx}/{len(todo)}] {city_name} ({city_code})")
            print(f"{'='*50}")
            
            try:
                cookie = random.choice(valid_cookies)
                ok = crawl_city(session, city_name, city_code, cookie)
                if ok and not args.city and not args.test:
                    done_list = load_progress().get("completed_cities", [])
                    if city_name not in done_list:
                        done_list.append(city_name)
                        save_progress(done_list)
                
                if idx < len(todo):
                    delay = random.gauss(12, 3)
                    delay = max(5, delay)
                    print(f"⏳ 等待 {delay:.0f} 秒切换城市...")
                    time.sleep(delay)
                    
            except KeyboardInterrupt:
                print("\n⚠️ 用户中断")
                break
            except Exception as e:
                print(f"❌ {city_name} 异常: {e}")
                continue
    
    print(f"\n🎉 完成！数据保存在: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
