批次上傳工具 for 台江內海研究資料集
===================================

套件需求
--------

1. ckanapi

事前準備
--------

1. 詮釋資料 "csv" 檔案 (請將收到的 xls 檔案另存成 csv)
2. 新增一欄位「新檔案名稱」並定義僅含英文數字之檔案名稱
3. 欲上傳之實體檔案 (存於一目錄)
4. 準備一連線設定檔，範例如 ``config_template.json``:
   
   - name_prefix: 檔案名稱之前綴 (因檔案名稱僅支援英文，故需另行指定英文之檔名前綴，系統會自動加上流水號)
   - org_name: 資料集所屬之組織
   - api_url: CKAN 主機所在位址 (如: http://127.0.0.1:5000)
   - api_key: CKAN 使用者 API 密鑰

操作方式
--------

::

   python uploader.py -f META_FILE -d FILE_FOLDER -c CONFIG_FILE

- META_FILE: 詮釋資料 csv 檔案位置
- FILE_FOLDER: 實體檔案所在資料夾位置
- CONFIG_FILE: 連線設定 json 檔案位置

使用例:

::

   python uploader.py -f taijiang_bulk_example.csv -d uploads -c config_template.json
