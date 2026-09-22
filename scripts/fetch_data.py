#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取泰康悦享系列各份额净值 → 计算「成立以来年化」→ 更新 data.json

数据源：天天基金 fund.eastmoney.com/pingzhongdata/<code>.js
计算式：成立以来年化 = (最新单位净值 / 首发净值) ^ (365 / 成立天数) - 1

设计约定：
  * 只覆写 taikang 段和 updatedAt / navDate
  * bank 段原样保留 —— 托管行数据无公开接口，需人工维护，不能被定时任务冲掉
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, 'data.json')
CST = timezone(timedelta(hours=8))  # 北京时间

# 份额代码 -> 展示名（需与 index.html 中的 taikangShares 一致）
SHARES = [
    ('019931', '悦享30天持有A'),
    ('019932', '悦享30天持有C'),
    ('020609', '悦享90天持有A'),
    ('020610', '悦享90天持有C'),
    ('025296', '悦享120天持有A'),
    ('025297', '悦享120天持有C'),
    ('024286', '悦享180天持有A'),
    ('024287', '悦享180天持有C'),
    ('020807', '悦享60天持有A'),
    ('020810', '悦享60天持有E'),
    ('020808', '悦享60天持有C'),
    ('020809', '悦享60天持有D'),
]

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')


def fetch_text(code):
    url = 'https://fund.eastmoney.com/pingzhongdata/%s.js' % code
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Referer': 'https://fund.eastmoney.com/',
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode('utf-8', 'ignore')


def ts_to_date(ms):
    return datetime.fromtimestamp(ms / 1000, tz=CST).strftime('%Y-%m-%d')


def fund_name(text):
    m = re.search(r'var\s+fS_name\s*=\s*"([^"]*)"', text)
    return m.group(1) if m else ''


def calc(text):
    """从净值走势算成立以来年化"""
    m = re.search(r'var\s+Data_netWorthTrend\s*=\s*(\[.*?\])\s*;', text, re.S)
    if not m:
        return None
    try:
        pts = json.loads(m.group(1))
    except ValueError:
        return None

    pts = [p for p in pts
           if isinstance(p, dict) and p.get('y') and p.get('x')]
    if len(pts) < 2:
        return None

    first, last = pts[0], pts[-1]
    days = (last['x'] - first['x']) / 86400000.0
    if days <= 30 or first['y'] <= 0:
        return None

    return {
        'annual': round((pow(last['y'] / first['y'], 365.0 / days) - 1) * 100, 4),
        'nav': last['y'],
        'navDate': ts_to_date(last['x']),
        'days': int(round(days)),
    }


def main():
    old = {}
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, encoding='utf-8') as f:
                old = json.load(f)
        except (ValueError, OSError):
            old = {}

    taikang = old.get('taikang') or {}
    bank = old.get('bank') or {}          # 人工维护，原样保留
    ok = fail = 0
    failed = []
    newest = ''

    for code, name in SHARES:
        try:
            text = fetch_text(code)
            r = calc(text)
            if r:
                r['name'] = fund_name(text) or name
                taikang[code] = r
                ok += 1
                if r['navDate'] > newest:
                    newest = r['navDate']
                print('OK   %s %-16s %6.2f%%  nav=%-8s %s  (%d天)'
                      % (code, name, r['annual'], r['nav'], r['navDate'], r['days']))
            else:
                fail += 1
                print('SKIP %s %-16s 无有效净值（可能新成立）' % (code, name))
        except Exception as e:
            fail += 1
            failed.append(code)
            print('FAIL %s %-16s %s' % (code, name, e))

    if ok == 0:
        # 全部失败时绝不覆写，否则会把「本轮报错」伪装成「刚刚更新过」
        print('FATAL: 本轮无任何有效净值，data.json 保持原样（保留上一次成功结果）')
        return 1

    out = {
        'updatedAt': datetime.now(CST).strftime('%Y-%m-%d %H:%M'),
        'navDate': newest or old.get('navDate', ''),
        'source': 'github-actions · fund.eastmoney.com/pingzhongdata',
        'failed': failed,
        'taikang': taikang,
        'bank': bank,
    }

    with open(DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write('\n')

    print('---- 完成：成功 %d / 失败或跳过 %d，净值截至 %s' % (ok, fail, out['navDate']))
    if failed:
        print('---- 失败代码：' + '、'.join(failed) + '（这些份额沿用上一次的数值）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
