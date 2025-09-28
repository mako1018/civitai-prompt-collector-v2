start_streamlit.ps1

使い方:

PowerShell でプロジェクトルート（この README と同じ階層）から実行:

```powershell
# 既定: port 8504, logs/ にログを保存
powershell -ExecutionPolicy Bypass -File .\scripts\start_streamlit.ps1

# 指定ポートで起動（例: 8505）
powershell -ExecutionPolicy Bypass -File .\scripts\start_streamlit.ps1 -Port 8505
```

何をするか:
- port に既にプロセスがあれば該当プロセスを停止しようと試みます
- logs/ に stdout/stderr を保存します（streamlit_<port>.log / streamlit_<port>.err）
- Streamlit をバックグラウンドで起動し、ブラウザを開きます

注意:
- Windows の環境差により Get-NetTCPConnection が使えない場合があります（古い PowerShell 等）。その場合はプロセスの停止がスキップされます。
- python 実行パスは PATH 上の `python` を参照します。別の実行環境を使う場合はコマンドラインを編集してください。
