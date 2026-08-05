import os, io, json, time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ── 自動計算週期 ──
today = datetime.today()
week_num = today.isocalendar()[1]
year_2digit = str(today.year)[-2:]
WEEK = f'{year_2digit}W{week_num}'

day_tw = ['一','二','三','四','五','六','日']
last_thu = today - timedelta(days=4)
last_sun = today - timedelta(days=1)
PERIOD = f'{last_thu.strftime("%m/%d")}（{day_tw[last_thu.weekday()]}）－ {last_sun.strftime("%m/%d")}（{day_tw[last_sun.weekday()]}）'
GENERATED = today.strftime('%Y-%m-%d')

SHEET_NEW = '總'
FOLDER_ID = os.environ['FOLDER_ID']
OUTPUT_FILE = f'{WEEK}.json'

print(f'週: {WEEK}  期間: {PERIOD}')

# ── Google Drive 驗證（Service Account）──
creds_json = json.loads(os.environ['GDRIVE_CREDENTIALS'])
creds = Credentials.from_service_account_info(
    creds_json,
    scopes=['https://www.googleapis.com/auth/drive.readonly']
)
gdrive = build('drive', 'v3', credentials=creds)

# ── 列出資料夾檔案 ──
all_files = gdrive.files().list(
    q=f"'{FOLDER_ID}' in parents and trashed=false",
    fields='files(id, name)',
    supportsAllDrives=True,
    includeItemsFromAllDrives=True
).execute().get('files', [])

print('雲端硬碟資料夾：')
for f in all_files:
    print(f'  {f["name"]}')

# ── 檔案辨識 ──
FILE_SALES_ID = FILE_INV_ID = FILE_NEW_ID = None
FILE_SALES_NAME = FILE_INV_NAME = FILE_NEW_NAME = None

for f in all_files:
    name = f['name']
    if '新品' in name or '排行' in name:
        FILE_NEW_ID, FILE_NEW_NAME = f['id'], name
    elif '庫存' in name or '周一' in name or '庫' in name:
        FILE_INV_ID, FILE_INV_NAME = f['id'], name
    elif '明細' in name or ('銷售' in name and '新品' not in name and '排行' not in name):
        FILE_SALES_ID, FILE_SALES_NAME = f['id'], name

print(f'銷售明細 → {FILE_SALES_NAME}')
print(f'庫存     → {FILE_INV_NAME}')
print(f'新品總表 → {FILE_NEW_NAME}')

if not all([FILE_SALES_ID, FILE_INV_ID, FILE_NEW_ID]):
    raise Exception('⚠️ 有檔案無法自動辨識，請確認檔案名稱')

# ── 下載 Excel ──
def download_excel(file_id):
    req = gdrive.files().get_media(fileId=file_id, supportsAllDrives=True)
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, req)
    done = False
    while not done: _, done = dl.next_chunk()
    buf.seek(0)
    return buf

print('下載中...')
buf_sales = download_excel(FILE_SALES_ID)
buf_inv   = download_excel(FILE_INV_ID)
buf_new   = download_excel(FILE_NEW_ID)
print('✅ 下載完成')

# ── 新品總表 ──
df_new = pd.read_excel(buf_new, sheet_name=SHEET_NEW, header=0)
df_new.columns = df_new.columns.str.strip()
df_new['品牌'] = df_new['品牌'].astype(str).str.strip()
df_new = df_new[(df_new['品牌'].notna()) & (df_new['品牌'] != 'nan') & (df_new['品牌'] != '')].copy()
df_new = df_new[df_new['款號'].astype(str).str.strip() != 'nan']
df_new['商品編號'] = df_new['商品編號'].astype(str).str.strip().str.split('.').str[0]
BRANDS = list(dict.fromkeys(df_new['品牌'].tolist()))
print(f'支線: {", ".join(BRANDS)}，{len(df_new)} 款新品')

# ── 銷售明細 ──
df_sales = pd.read_excel(buf_sales, header=0)
df_sales.columns = df_sales.columns.str.strip()
COL_STORE = next((c for c in ['倉庫編號','購買當下','門市代碼','門市編號','購買門市','銷售門市','店號'] if c in df_sales.columns), None)
COL_QTY   = next((c for c in ['出貨數量','銷售數量','數量','訂單數量'] if c in df_sales.columns), None)
if not COL_STORE or not COL_QTY:
    raise KeyError(f'找不到欄位：門市={COL_STORE}, 數量={COL_QTY}')

if '品別' in df_sales.columns:
    df_sales = df_sales[df_sales['品別'] == '正品']
if '訂單來源' in df_sales.columns:
    df_sales = df_sales[df_sales['訂單來源'] == '門市']

df_sales['商品編號'] = df_sales['商品編號'].astype(str).str.strip().str.split('.').str[0]
df_sales[COL_STORE]  = df_sales[COL_STORE].astype(str).str.strip()
df_sales = df_sales[df_sales[COL_STORE].str.match(r'^(AS|AT)\d+$')]
df_sales[COL_QTY] = pd.to_numeric(df_sales[COL_QTY], errors='coerce').fillna(0)

store_sales = {}
for (pid, store), qty in df_sales.groupby(['商品編號', COL_STORE])[COL_QTY].sum().items():
    if qty > 0: store_sales.setdefault(pid, {})[store] = int(qty)
total_sales_map = {pid: sum(v.values()) for pid, v in store_sales.items()}

# ── 庫存 ──
df_inv = pd.read_excel(buf_inv, header=0)
df_inv.columns = df_inv.columns.str.strip()
df_inv['倉庫編號'] = df_inv['倉庫編號'].astype(str).str.strip()
df_inv = df_inv[df_inv['倉庫編號'].str.match(r'^(AS|AT)\d+$')]
df_inv['商品編號'] = df_inv['商品編號'].astype(str).str.strip().str.split('.').str[0]
df_inv['庫存數量'] = pd.to_numeric(df_inv['庫存數量'], errors='coerce').fillna(0)

store_inv = {}
for (pid, store), qty in df_inv.groupby(['商品編號','倉庫編號'])['庫存數量'].sum().items():
    store_inv.setdefault(pid, {})[store] = int(qty)
total_inv_map = {pid: sum(v.values()) for pid, v in store_inv.items()}

name_col = next((c for c in ['倉庫名稱','門市名稱','名稱'] if c in df_inv.columns), None)
store_names = df_inv.drop_duplicates('倉庫編號').set_index('倉庫編號')[name_col].to_dict() if name_col else {}
sales_name_col = next((c for c in ['倉庫名稱','門市名稱'] if c in df_sales.columns), None)
if sales_name_col:
    for _, r in df_sales.drop_duplicates(COL_STORE).iterrows():
        code = str(r[COL_STORE]).strip()
        if code not in store_names:
            store_names[code] = str(r[sales_name_col]).strip()

# ── 組合商品資料 ──
products = {b: [] for b in BRANDS}
for _, row in df_new.iterrows():
    pid   = str(row['商品編號'])
    brand = str(row['品牌'])
    products[brand].append({
        'product_id':      pid,
        'sku':             str(row['款號']),
        'name':            str(row['商品名稱']),
        'category':        str(row['大分類']),
        'grade':           str(row['門市級別']),
        'total_sales':     total_sales_map.get(pid, 0),
        'inventory':       total_inv_map.get(pid, 0),
        'store_sales':     store_sales.get(pid, {}),
        'store_inventory': store_inv.get(pid, {})
    })

all_codes = set()
for d in [store_sales, store_inv]:
    for v in d.values(): all_codes.update(v.keys())
stores_list = [{'code': c, 'name': store_names.get(c, c)} for c in sorted(all_codes)]
print(f'✅ 門市 {len(stores_list)} 家，商品 {sum(len(v) for v in products.values())} 款')

# ── 抓官網圖片 ──
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
all_pids = list(dict.fromkeys(p['product_id'] for ps in products.values() for p in ps))
image_urls = {}

print(f'🔍 抓取 {len(all_pids)} 款圖片...')
for pid in all_pids:
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
            image_urls[pid] = chosen
            print(f'  ✅ {pid}')
        else:
            print(f'  ⚠️ {pid}：官網無圖')
    except Exception as e:
        print(f'  ❌ {pid}：{e}')
    time.sleep(0.8)

print(f'共取得 {len(image_urls)} / {len(all_pids)} 款')

# ── 寫入 image_url ──
for brand, prods in products.items():
    for p in prods:
        if p['product_id'] in image_urls:
            p['image_url'] = image_urls[p['product_id']]

# ── 儲存 JSON ──
os.makedirs('data', exist_ok=True)
with open(f'data/{OUTPUT_FILE}', 'w', encoding='utf-8') as f:
    json.dump({'meta': {'week': WEEK, 'period': PERIOD, 'generated': GENERATED},
               'stores': stores_list, 'products': products}, f, ensure_ascii=False, indent=2)
print(f'✅ data/{OUTPUT_FILE}')

# ── 更新 index.json ──
index_path = 'data/index.json'
if os.path.exists(index_path):
    with open(index_path, 'r', encoding='utf-8') as f:
        index_data = json.load(f)
else:
    index_data = {'weeks': []}

index_data['weeks'] = [w for w in index_data['weeks'] if w['key'] != WEEK]
index_data['weeks'].insert(0, {'key': WEEK, 'period': PERIOD, 'file': OUTPUT_FILE})

with open(index_path, 'w', encoding='utf-8') as f:
    json.dump(index_data, f, ensure_ascii=False, indent=2)
print(f'✅ data/index.json（共 {len(index_data["weeks"])} 週）')
