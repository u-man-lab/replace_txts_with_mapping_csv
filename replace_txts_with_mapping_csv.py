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
    FilePath,
    NewPath,
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


class PathEncodingConverterMixin:
    """Pydantic mixin for automatic validation and conversion of PATH and ENCODING fields.

    Provides field validators for converting string paths to 'Path' and encoding strings
    to 'EncodingStr' during model initialization.
    """

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


class ExistingTxtConfig(PathEncodingConverterMixin, BaseModel):
    """Configuration for an existing TXT file.

    Attributes:
        PATH: Path to an existing TXT file.
        ENCODING: Encoding to use when reading the TXT.
    """

    PATH: FilePath  # Must be an existing file.
    ENCODING: EncodingStr

    model_config = ConfigDict(
        frozen=True, extra='forbid', strict=True, arbitrary_types_allowed=True
    )

    def read_text(self) -> str:
        """Writes the given string to a TXT file."""
        return self.PATH.read_text(encoding=str(self.ENCODING))


class ReplaceMappingCsv(PathEncodingConverterMixin, BaseModel):
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

        if missing_columns := '", "'.join(col for col in use_columns if col not in headers):
            raise ValueError(f'Necessary columns are missing in the CSV.: "{missing_columns}"')
        if duplicated_columns := '", "'.join(col for col in use_columns if headers.count(col) > 1):
            raise ValueError(f'Columns are duplicated in the CSV.: "{duplicated_columns}"')
        if broken_line_ids_str := ', line '.join(broken_line_ids):
            raise ValueError(
                f'{headers_len} columns are expected in the CSV, but not at: line {broken_line_ids_str}'
            )

        df = pd.read_csv(self.PATH, encoding=str(self.ENCODING), dtype=str, keep_default_na=False)

        if not allow_empty and df.shape[0] == 0:
            raise ValueError('Empty rows in the CSV.')

        return df

    @staticmethod
    def __create_mapping_dict_from_df(
        df: pd.DataFrame, two_columns: tuple[str, str]
    ) -> tuple[OrderedDict[str, str], list[str]]:

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

        replaced_text = data
        for find_str, replace_str in self.__mapping_dict.items():
            replaced_text = replaced_text.replace(find_str, replace_str)
        return replaced_text


class InputConfig(BaseModel):
    """Input section of the configuration.
    'INPUT' in YAML.

    Attributes:
        ORIGINAL_TXT: Configuration for the input TXT file.
        REPLACE_MAPPING_CSV:
            Configuration for the input CSV file with columns of find & replace strings.
    """

    ORIGINAL_TXT: ExistingTxtConfig
    REPLACE_MAPPING_CSV: ReplaceMappingCsv

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)


class NewTxtConfig(PathEncodingConverterMixin, BaseModel):
    """Configuration for a new TXT file.

    Attributes:
        PATH: Path to a new output TXT file.
        ENCODING: Encoding to use when writing the TXT.
    """

    PATH: NewPath  # Must not exist & parent must exist
    ENCODING: EncodingStr

    model_config = ConfigDict(
        frozen=True, extra='forbid', strict=True, arbitrary_types_allowed=True
    )

    def write_text(self, data: str):
        """Writes the given string to a TXT file."""
        self.PATH.write_text(data, encoding=str(self.ENCODING))


class OutputConfig(BaseModel):
    """Output section of the configuration.
    'OUTPUT' in YAML.

    Attributes:
        REPLACED_TXT: Configuration for the output TXT file.
    """

    REPLACED_TXT: NewTxtConfig

    model_config = ConfigDict(frozen=True, extra='forbid', strict=True)


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

    original_txt_config = CONFIG.INPUT.ORIGINAL_TXT
    logger.info(f'Reading the TXT "{original_txt_config.PATH}"...')
    try:
        original_string = original_txt_config.read_text()
    except Exception:
        logger.exception(f'Failed to read the TXT "{original_txt_config.PATH}".')
        sys.exit(1)

    mapping_csv = CONFIG.INPUT.REPLACE_MAPPING_CSV
    logger.info(f'Replacing with CSV "{mapping_csv.PATH}"...')
    try:
        replaced_text = mapping_csv.replace_text(original_string)
    except Exception:
        logger.exception(f'Failed to replace with CSV "{mapping_csv.PATH}".')
        sys.exit(1)

    replaced_txt_config = CONFIG.OUTPUT.REPLACED_TXT
    logger.info(f'Writing a new TXT "{replaced_txt_config.PATH}"...')
    try:
        replaced_txt_config.write_text(replaced_text)
    except Exception:
        logger.exception(f'Failed to write a new TXT "{replaced_txt_config.PATH}".')
        sys.exit(1)

    logger.info(f'"{os.path.basename(__file__)}" done!')


if __name__ == '__main__':
    __replace_txts_with_mapping_csv()
