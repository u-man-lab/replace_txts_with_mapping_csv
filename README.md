# replace_txts_with_mapping_csv

* NOTE: 日本語版のREADMEは[`README-ja.md`](./README-ja.md)を参照。

## Overview

This repository provides a Python script that replaces text in multiple TXT files based on a CSV mapping table. It reads all TXT files inside a specified folder, replaces strings using an ordered mapping defined in a CSV file, and outputs the resulting TXT files into a blank destination folder.

### Example

1. Suppose we have several TXT files in [`./data/original_txts`](./data/original_txts) and a replace-mapping CSV at [`./data/replace_mapping.csv`](./data/replace_mapping.csv).

1. Then, run the script [`./replace_txts_with_mapping_csv.py`](./replace_txts_with_mapping_csv.py) with the YAML configuration file [`./configs/replace_txts_with_mapping_csv.yaml`](./configs/replace_txts_with_mapping_csv.yaml).

1. The script reads each TXT, applies string replacements in the order listed in the CSV, and outputs new TXT files with replaced content into [`./results`](./results).

⚠️ Please refer to the `comment` column in [`./data/replace_mapping.csv`](./data/replace_mapping.csv) for notes on replacement conflicts.

---

## License & Developer

- **License**: See [`LICENSE`](./LICENSE) in this repository.
- **Developer**: U-MAN Lab. ([https://u-man-lab.com/](https://u-man-lab.com/))

---

## 1. Installation & Usage

### (1) Install Python

Install Python from the [official Python website](https://www.python.org/downloads/).  
The scripts may not work properly if the version is lower than the verified one. Refer to the [`.python-version`](./.python-version).

### (2) Clone the repository

```bash
git clone https://github.com/u-man-lab/replace_txts_with_mapping_csv.git
# If you don't have "git", copy the scripts and YAMLs manually to your environment.
cd ./replace_txts_with_mapping_csv
```

### (3) Install Python dependencies

The scripts may not work properly if the versions are lower than the verified ones.
```bash
pip install --upgrade pip
pip install -r ./requirements.txt
```

### (4) Prepare input files

- TXT files must be placed in a single folder
- Ensure the folder contains TXT files only (no subfolders)
- CSV must include at least columns:
  - `find` (strings to find)
  - `replace` (replacement strings)

### (5) Prepare output folder

- Ensure the folder contains no files and subfolders

### (6) Edit the configuration file

Open the configuration file [`./configs/replace_txts_with_mapping_csv.yaml`](./configs/replace_txts_with_mapping_csv.yaml) and edit the values according to the comments in the file.

### (7) Run the script

```bash
python ./replace_txts_with_mapping_csv.py ./configs/replace_txts_with_mapping_csv.yaml
```

---

## 2. Expected Output

On success, stderr will include logs similar to:

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

Replaced TXT files will be written into the output folder.

---

## 3. Common Errors

For full details, see the script source. Common errors include:

- **Missing config path argument**
  ```
  2025-10-26 16:46:05,471 [ERROR] __main__: This script needs a config file path as an arg.
  ```
- **Invalid or missing config field**
  ```
  2025-10-26 16:47:40,930 [ERROR] __main__: Failed to parse the config file.: "configs\replace_txts_with_mapping_csv.yaml"
  Traceback (most recent call last):
  :
  ```
