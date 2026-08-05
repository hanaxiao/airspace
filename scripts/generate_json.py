name: 每週新品自動更新

on:
  schedule:
    - cron: '0 2 * * 1'  # 每週一 10:00 台灣時間（UTC+8）
  workflow_dispatch:       # 允許手動觸發測試

jobs:
  update:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install google-api-python-client google-auth pandas openpyxl requests beautifulsoup4

      - name: Run update script
        env:
          GDRIVE_CREDENTIALS: ${{ secrets.GDRIVE_CREDENTIALS }}
          FOLDER_ID: '1DTRECrESNkJFuBcMfHLf4w_pz5L6OJI7'
        run: python scripts/generate_json.py

      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/
          git diff --staged --quiet || git commit -m "auto: weekly update $(date +'%Y-W%V')"
          git push
