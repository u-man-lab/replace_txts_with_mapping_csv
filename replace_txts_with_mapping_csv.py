import codecs
import csv
import os
import sys
from collections import OrderedDict
from logging import DEBUG, INFO, basicConfig, getLogger
from pathlib import Path
from typing import Any, Final

import pandas as pd
import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    DirectoryPath,
    FilePath,
    PrivateAttr,
    StrictStr,
    field_validator,
)


class EncodingStr:
    """Represents a validated string that must be a valid text encoding name.

    Validates whether the provided string is a supported encoding.
    """

    def __init__(self, value: Any):
        self.__validate_value(value)
        self.__value: str = value

    def __str__(self) -> str:
        return self.__value

    @staticmethod
    def __validate_value(arg: Any) -> str:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')

        try:
            codecs.lookup(arg)
        except LookupError as err:
            raise ValueError(f'"{arg}" is not supported as an encoding string.') from err
        return arg


class TxtsInFolderConfig(BaseModel):
    """Configuration for txt files which encoding is the same in a folder.

    Attributes:
        FOLDER_PATH: Paths of a folder in which the txts are put.
        ENCODING: Encoding of the txts.
    """

    FOLDER_PATH: DirectoryPath  # Must be existing directory
    ENCODING: EncodingStr

    __txt_paths: tuple[Path, ...] = PrivateAttr()

    model_config = ConfigDict(
        frozen=True, extra='forbid', strict=True, arbitrary_types_allowed=True
    )

    @field_validator('ENCODING', mode='before')
    @classmethod
    def __convert_str_to_encoding_str_and_validate(cls, arg: Any) -> EncodingStr:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')
        return EncodingStr(arg.strip())

    @field_validator('FOLDER_PATH', mode='before')
    @classmethod
    def __convert_str_to_path_and_validate(cls, arg: Any) -> Path:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')
        return Path(arg.strip())

    @staticmethod
    def __get_child_file_paths(path: Path) -> tuple[Path, ...]:
        """Get paths of files in the folder. Assume that only files are in the folder.

        Raises:
            ValueError: If the folder is blank or if any non-file object is in the folder.
        """

        txt_paths = tuple(path.iterdir())

        if not txt_paths:
            raise ValueError(f'No txts in the folder.: "{path}"')

        for txt_path in txt_paths:
            if not txt_path.is_file():
                raise ValueError(f'Non-file object in the folder.: "{path}"')

        return txt_paths

    def __init__(self, **data):
        super().__init__(**data)
        self.__txt_paths = self.__get_child_file_paths(self.FOLDER_PATH)

    @property
    def txt_paths(self) -> tuple[Path, ...]:
        return self.__txt_paths


class ReplaceMappingCsv(BaseModel):
    """Represents a CSV file with columns of find & replace strings.

    Attributes:
        PATH: Path to an existing CSV file.
        ENCODING: Encoding used to read the CSV.
        FIND_STRING_COLUMN: Column name containing strings to find (to be replaced).
        REPLACE_STRING_COLUMN: Column name containing strings to replace.
    """

    PATH: FilePath  # Must be existing file
    ENCODING: EncodingStr
    FIND_STRING_COLUMN: StrictStr
    REPLACE_STRING_COLUMN: StrictStr

    model_config = ConfigDict(
        frozen=True, extra='forbid', strict=True, arbitrary_types_allowed=True
    )

    __mapping_dict: OrderedDict[str, str] = PrivateAttr()

    @field_validator('PATH', mode='before')
    @classmethod
    def __convert_str_to_file_path_and_validate(cls, arg: Any) -> Path:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')
        return Path(arg.strip())

    @field_validator('ENCODING', mode='before')
    @classmethod
    def __convert_str_to_encoding_str_and_validate(cls, arg: Any) -> EncodingStr:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')
        return EncodingStr(arg.strip())

    def __read_csv(
        self, allow_empty: bool = True, use_columns: tuple[str, ...] = tuple()
    ) -> pd.DataFrame:
        """Reads the configured CSV file into a pandas DataFrame.

        Args:
            allow_empty: Whether to allow empty rows below header row.
            use_columns: Columns to use in the CSV.

        Returns:
            pd.DataFrame: DataFrame containing the contents of the CSV file.
        """

        if not isinstance(allow_empty, bool):
            raise TypeError(
                f'The argument must be a bool, got "{allow_empty}" [{type(allow_empty)}].'
            )

        with open(self.PATH, 'r', encoding=str(self.ENCODING), newline='') as fr:

            reader = csv.reader(fr)

            try:
                headers = next(reader)
            except StopIteration as err:
                raise ValueError(f'No columns to parse from file.: "{self.PATH}"') from err

            headers_len = len(headers)
            broken_line_ids = [
                str(line_id)
                for line_id, row in enumerate(reader, start=2)
                if len(row) not in (0, headers_len)
            ]

        if missing_columns := [col for col in use_columns if col not in headers]:
            missing_columns_str = '", "'.join(missing_columns)
            raise ValueError(f'Necessary columns are missing in the CSV.: "{missing_columns_str}"')
        if duplicated_columns := [col for col in use_columns if headers.count(col) > 1]:
            duplicated_columns_str = '", "'.join(duplicated_columns)
            raise ValueError(f'Columns are duplicated in the CSV.: "{duplicated_columns_str}"')
        if broken_line_ids_str := ', line '.join(broken_line_ids):
            raise ValueError(
                f'{headers_len} columns are expected in the CSV, but not at: line {broken_line_ids_str}'
            )

        df = pd.read_csv(self.PATH, encoding=str(self.ENCODING), dtype=str, keep_default_na=False)
        # Overwrite automatically converted strings (e.g., '' -> 'Unnamed: 1', ['a', 'a'] -> ['a', 'a.1'])
        df.columns = pd.Index(headers)

        if not allow_empty and df.shape[0] == 0:
            raise ValueError('Empty rows in the CSV.')

        return df

    @staticmethod
    def __create_mapping_dict_from_df(
        df: pd.DataFrame, two_columns: tuple[str, str]
    ) -> tuple[OrderedDict[str, str], list[str]]:
        """Create mapping dict from two columns in a DataFrame.

        Args:
            df: Source DataFrame.
            two_columns: Two column names in the df. The former is key, and the latter is value.

        Returns:
            OrderedDict[str, str]: Mapping dict which is ordered by the order in CSV.
            list[str]: Duplicated keys in the CSV.
        """

        mapping_dict: OrderedDict[str, str] = OrderedDict()
        duplicated_first_column_values: list[str] = []
        for find_str, replace_str in df[list(two_columns)].values:

            if find_str not in mapping_dict:
                mapping_dict[find_str] = replace_str
                continue

            if find_str not in duplicated_first_column_values:
                duplicated_first_column_values.append(find_str)

        return mapping_dict, duplicated_first_column_values

    def __read_csv_into_mapping_dict(self):
        """Read CSV & set the content to variable "__mapping_dict".

        Raises:
            ValueError: Values in the "find" column are duplicated or blank.
        """

        find_and_replace_columns = (
            self.FIND_STRING_COLUMN,
            self.REPLACE_STRING_COLUMN,
        )

        df = self.__read_csv(allow_empty=False, use_columns=find_and_replace_columns)
        self.__mapping_dict, duplicated_find_strings = self.__create_mapping_dict_from_df(
            df, find_and_replace_columns
        )
        if duplicated_find_strings:
            joined_string = '", "'.join(duplicated_find_strings)
            raise ValueError(f'Duplicated values in find strings.: "{joined_string}"')
        if '' in self.__mapping_dict:
            raise ValueError('Blank string in find strings.')

    def __init__(self, **data):
        super().__init__(**data)
        self.__read_csv_into_mapping_dict()

    def replace_text(self, data: str) -> str:
        """Replace a text with the mapping dict."""

        replaced_text = data
        for find_str, replace_str in self.__mapping_dict.items():
            replaced_text = replaced_text.replace(find_str, replace_str)
        return replaced_text


class InputConfig(BaseModel):
    """Input section of the configuration.
    'INPUT' in YAML.

    Attributes:
        ORIGINAL_TXTS: Configuration for the input TXT files.
        REPLACE_MAPPING_CSV:
            Configuration for the input CSV file with columns of find & replace strings.
    """

    ORIGINAL_TXTS: TxtsInFolderConfig
    REPLACE_MAPPING_CSV: ReplaceMappingCsv

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)


class OutputConfig(BaseModel):
    """Output section of the configuration.
    'OUTPUT' in YAML.

    Attributes:
        FOLDER_PATH: An existing blank folder path to output replaced TXT files.
    """

    FOLDER_PATH: DirectoryPath  # Must be existing directory

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)

    @field_validator('FOLDER_PATH', mode='before')
    @classmethod
    def __convert_str_to_path(cls, arg: Any) -> Path:
        if not isinstance(arg, str):
            raise TypeError(f'The argument must be a string, got "{arg}" [{type(arg)}].')
        return Path(arg.strip())

    @field_validator('FOLDER_PATH', mode='after')
    @classmethod
    def __validate_folder_path(cls, path: DirectoryPath) -> Path:
        """Validate that the folder is a  blank folder."""

        if list(path.iterdir()):
            raise ValueError(f'Output folder must be a blank folder.: "{path}"')
        return path


class Config(BaseModel):
    """Main configuration object loaded from YAML.

    Attributes:
        INPUT: Input file configuration.
        OUTPUT: Output file configuration.
    """

    INPUT: InputConfig
    OUTPUT: OutputConfig

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)

    @classmethod
    def from_yaml(cls, path: Path) -> 'Config':
        """Loads the configuration from a YAML file.

        Args:
            path: Path to the YAML config file.

        Returns:
            Config: Parsed configuration object.
        """

        with open(path, 'r', encoding='utf-8') as fr:
            content = yaml.safe_load(fr)
        return cls(**content)


def __read_arg_config_path():
    """Parses the configuration file path from command-line arguments and loads the config.

    Returns:
        Config: Loaded configuration object.

    Raises:
        SystemExit: If the config path is not provided or cannot be parsed.
    """

    logger = getLogger(__name__)

    if len(sys.argv) != 2:
        logger.error('This script needs a config file path as an arg.')
        sys.exit(1)
    config_path = Path(sys.argv[1])

    try:
        CONFIG: Final[Config] = Config.from_yaml(config_path)
    except Exception:
        logger.exception(f'Failed to parse the config file.: "{config_path}"')
        sys.exit(1)

    return CONFIG


def __replace_txts_with_mapping_csv():

    basicConfig(level=INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    logger = getLogger(__name__)

    logger.info(f'"{os.path.basename(__file__)}" start!')

    CONFIG: Final[Config] = __read_arg_config_path()

    original_txts_config = CONFIG.INPUT.ORIGINAL_TXTS
    mapping_csv = CONFIG.INPUT.REPLACE_MAPPING_CSV
    encoding = str(original_txts_config.ENCODING)

    logger.info(f'Total TXTs count: {len(original_txts_config.txt_paths)}.')

    exceptions = []
    for original_txt_path in original_txts_config.txt_paths:

        logger.info('---')

        logger.info(f'Reading TXT "{original_txt_path}"...')
        try:
            # Prevents line break codes from being unified to "\n" with "newline=''".
            with open(original_txt_path, 'r', encoding=encoding, newline='') as fr:
                original_text = fr.read()
        except Exception as err:
            message = f'Failed to read TXT "{original_txt_path}".'
            err.add_note(message)
            exceptions.append(err)
            logger.error(message)
            continue

        logger.info(f'Replacing with CSV "{mapping_csv.PATH}"...')
        try:
            replaced_text = mapping_csv.replace_text(original_text)
        except Exception as err:
            message = f'Failed to replace with CSV "{mapping_csv.PATH}".'
            err.add_note(message)
            exceptions.append(err)
            logger.error(message)
            continue

        replaced_txt_path = CONFIG.OUTPUT.FOLDER_PATH / original_txt_path.name
        logger.info(f'Writing new TXT "{replaced_txt_path}"...')
        try:
            # Prevents line break codes from being unified to OS-default with "newline=''".
            with open(replaced_txt_path, 'w', encoding=encoding, newline='') as fw:
                fw.write(replaced_text)
        except Exception as err:
            message = f'Failed to write new TXT "{replaced_txt_path}".'
            err.add_note(message)
            exceptions.append(err)
            logger.error(message)
            continue

    logger.info('---')

    if exceptions:
        try:
            raise ExceptionGroup('Some files are failed to be processed.', exceptions)
        except ExceptionGroup:
            logger.exception('Script aborted because some files are failed to be processed.')
            sys.exit(1)

    logger.info(f'"{os.path.basename(__file__)}" done!')


if __name__ == '__main__':
    __replace_txts_with_mapping_csv()
