批次上傳工具 for 台江內海研究資料集
===================================

事前準備
--------

1. 詮釋資料 "csv" 檔案 (請將收到的 xls 檔案另存成 csv)
2. 新增一欄位「新檔案名稱」並定義僅含英文數字之檔案名稱
3. 欲上傳之實體檔案 (存於一目錄)
4. 填寫 ``configs.py`` 之連線設定:
   
   - name_prefix: 資料集網址之前綴
   - org_name: 資料集所屬之組織
   - api_url: CKAN 主機所在位址 (如: http://127.0.0.1:5000)
   - api_key: CKAN 使用者 API 密鑰

操作方式
--------

::

   python uploader.py -f META_FILE -d FILE_FOLDER

- META_FILE: 詮釋資料 csv 檔案名稱
- FILE_FOLDER: 實體檔案所在資料夾名稱

使用例:

::

   python uploader.py -f taijiang_bulk_example.csv -d uploads
