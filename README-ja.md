# replace_txts_with_mapping_csv

* NOTE: See [`README.md`](./README.md) for English README.

## 概要

このリポジトリは、CSVファイルに定義されたマッピングに基づいて、複数のTXTファイル内のテキストを置換するPythonスクリプトを提供します。指定されたフォルダ内のすべてのTXTファイルを読み込み、CSVファイルで定義されたマッピングを上から順に適用して文字列を置換し、結果のTXTファイルを空の出力先フォルダに出力します。

### 実行例

1. [`./data/original_txts`](./data/original_txts)に複数のTXTファイルがあり、[`./data/replace_mapping.csv`](./data/replace_mapping.csv)に置換マッピング用のCSVファイルがあるとします。

1. 次に、スクリプト[`./replace_txts_with_mapping_csv.py`](./replace_txts_with_mapping_csv.py)を、YAML設定ファイル[`./configs/replace_txts_with_mapping_csv.yaml`](./configs/replace_txts_with_mapping_csv.yaml)を指定して実行します。

1. このスクリプトは各TXTファイルを読み込み、CSVに記載された順序で文字列置換を適用し、置換後の内容を新しいTXTファイルとして[`./results`](./results)に出力します。

⚠️置換の競合に関する注意事項は、[`./data/replace_mapping.csv`](./data/replace_mapping.csv)の`comment`列を参照してください。

---

## ライセンス & 開発者

- **ライセンス**: このリポジトリ内の[`LICENSE`](./LICENSE)を参照してください。
- **開発者**: U-MAN Lab. ([https://u-man-lab.com/](https://u-man-lab.com/))

---

## 1. インストールと使用方法

### (1) Pythonをインストールする

[公式サイト](https://www.python.org/downloads/)を参照してPythonをインストールしてください。  
開発者が検証したバージョンより古い場合、スクリプトが正常に動作しない可能性があります。[`.python-version`](./.python-version)を参照してください。

### (2) リポジトリをクローンする

```bash
git clone https://github.com/u-man-lab/replace_txts_with_mapping_csv.git
# gitコマンドを利用できない場合は、別の方法でスクリプトファイルとYAML設定ファイルを環境に配置してください。
cd ./replace_txts_with_mapping_csv
```

### (3) Pythonライブラリをインストールする

開発者が検証したバージョンより古い場合、スクリプトが正常に動作しない可能性があります。
```bash
pip install --upgrade pip
pip install -r ./requirements.txt
```

### (4) 入力用のTXTファイルを用意する

- TXTファイルは単一のフォルダに配置すること
- フォルダ内にはTXTファイルのみを含めること（サブフォルダは不可）
- CSVには以下の列を必ず含めること：
  - `find`（検索対象の文字列）
  - `replace`（置換後の文字列）

### (5) 出力フォルダの準備

- 空フォルダである（フォルダ内にファイルやサブフォルダが存在しない）こと

### (6) 設定ファイルを編集する

設定ファイル[`configs/replace_txts_with_mapping_csv.yaml`](./configs/replace_txts_with_mapping_csv.yaml)を開き、ファイル内のコメントに従って値を編集します。

### (7) スクリプトを実行する

```bash
python ./replace_txts_with_mapping_csv.py ./configs/replace_txts_with_mapping_csv.yaml
```

---

## 2. 期待される出力

成功した場合、標準エラー出力(stderr)に次のようなログが出力されます。:

```
2025-10-26 15:45:57,146 [INFO] __main__: "replace_txts_with_mapping_csv.py" start!
2025-10-26 15:45:57,154 [INFO] __main__: Total TXTs count: 3.
2025-10-26 15:45:57,155 [INFO] __main__: ---
2025-10-26 15:45:57,155 [INFO] __main__: Reading TXT "data\original_txts\01.txt"...
2025-10-26 15:45:57,155 [INFO] __main__: Replacing with CSV "data\replace_mapping.csv"...
2025-10-26 15:45:57,155 [INFO] __main__: Writing new TXT "results\01.txt"...
2025-10-26 15:45:57,155 [INFO] __main__: ---
2025-10-26 15:45:57,155 [INFO] __main__: Reading TXT "data\original_txts\02.txt"...
2025-10-26 15:45:57,155 [INFO] __main__: Replacing with CSV "data\replace_mapping.csv"...
2025-10-26 15:45:57,155 [INFO] __main__: Writing new TXT "results\02.txt"...
2025-10-26 15:45:57,155 [INFO] __main__: ---
2025-10-26 15:45:57,156 [INFO] __main__: Reading TXT "data\original_txts\03.txt"...
2025-10-26 15:45:57,157 [INFO] __main__: Replacing with CSV "data\replace_mapping.csv"...
2025-10-26 15:45:57,157 [INFO] __main__: Writing new TXT "results\03.txt"...
2025-10-26 15:45:57,157 [INFO] __main__: ---
2025-10-26 15:45:57,157 [INFO] __main__: "replace_txts_with_mapping_csv.py" done!
```

置換されたTXTファイルは出力フォルダに作成されます。

---

## 3. よくあるエラー

詳細については、スクリプトのソースコードを参照してください。よくあるエラーには以下のものが含まれます。:

- **スクリプトに引数を渡していない**
  ```
  2025-10-26 16:46:05,471 [ERROR] __main__: This script needs a config file path as an arg.
  ```
- **設定ファイルの値がおかしい**
  ```
  2025-10-26 16:47:40,930 [ERROR] __main__: Failed to parse the config file.: "configs\replace_txts_with_mapping_csv.yaml"
  Traceback (most recent call last):
  :
  ```
