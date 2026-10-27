import os, json, time, requests
from bs4 import BeautifulSoup

# 讀取週數（由 workflow_dispatch 傳入，或自動取最新週）
WEEK = os.environ.get('WEEK', '').strip()
if not WEEK:
    with open('data/index.json', encoding='utf-8') as f:
        idx = json.load(f)
    WEEK = idx['weeks'][0]['key']

print(f'🔍 抓取圖片 → {WEEK}')
path = f'data/{WEEK}.json'

with open(path, encoding='utf-8') as f:
    data = json.load(f)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

changed = False
for brand, prods in data['products'].items():
    for p in prods:
        if p.get('image_url'):
            continue
        pid = p['product_id']
        try:
            url = f'https://www.airspaceonline.com/tw/zh-hant/product/TW{pid}'
            r = requests.get(url, headers=HEADERS, timeout=12)
            soup = BeautifulSoup(r.text, 'html.parser')
            pattern = f'photo/{pid}/'
            seen, imgs = set(), []
            for img in soup.find_all('img'):
                src = img.get('src', '')
                if pattern in src and src not in seen:
                    seen.add(src)
                    imgs.append(src)
            chosen = imgs[1] if len(imgs) > 1 else (imgs[0] if imgs else None)
            if chosen:
                p['image_url'] = chosen
                changed = True
                print(f'  ✅ {pid}')
            else:
                print(f'  ⚠️ {pid}：官網無圖')
        except Exception as e:
            print(f'  ❌ {pid}：{e}')
        time.sleep(0.8)

if changed:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'✅ 已更新 {path}')
else:
    print('無需更新')
