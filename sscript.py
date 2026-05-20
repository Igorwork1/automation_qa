#!/usr/bin/env python3

import argparse
import os
import re
import shutil
import sys
import zlib
from datetime import datetime
from urllib.request import urlopen

from pydantic import BaseModel, ValidationError, field_validator

COLUMN_HEADERS = ["ФИО", "Возраст", "Адрес", "Дата"]
TABLE_TITLE = "ТАБЛИЦА ДАННЫХ"
EXPECTED_DATA_CRC = "0x2c083a45"


def _normalize_time(time_str: str) -> str:
    time_str = time_str.strip()
    if re.fullmatch(r"\d{6}", time_str):
        return f"{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]}"
    return time_str


def preprocess_date(date_str: str) -> str:
    clean_str = date_str.strip().replace("T", " ")

    if re.match(r"^\d{8}", clean_str):  # дата на входе слипшаяся
        clean_str = f"{clean_str[:4]}-{clean_str[4:6]}-{clean_str[6:8]} {clean_str[8:]}"

    parts = clean_str.split()
    date_part = parts[0]

    if len(parts) > 1:
        time_part = _normalize_time(parts[1])
    else:
        time_part = "00:00:00"

    # делим дату на составляющие по разделителю: дефис, точка или слэш
    date_bits = re.split(r"[-./]", date_part)
    if len(date_bits) < 3:
        return clean_str

    y, m, d = int(date_bits[0]), int(date_bits[1]), int(date_bits[2])
    if m > 12:
        m, d = d, m

    dt = datetime(y, m, d)
    return dt.strftime(f"%Y-%m-%d {time_part}")


class TextLine(BaseModel):
    fio: str
    age: int
    address: str
    birth_date: str

    @field_validator("birth_date", mode="before")
    @classmethod
    def validate_birth_date(cls, value: str) -> str:
        return preprocess_date(value)


# ФУНКЦИЯ для аргументов
def arg_parse():
    parser = argparse.ArgumentParser(description="Test automation_qa")
    parser.add_argument("-i", "--input", required=True, help="Путь к файлу или URL")
    return parser.parse_args()


def is_url(source: str) -> bool:# поверка аргументов есть ли это ссылка
    return source.startswith(("http://", "https://")) 


def open_input(source: str):
    if is_url(source):
        return urlopen(source)
    return open(source, "rb")


def crc32_read(path: str) -> str:
    crc = 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            crc = zlib.crc32(chunk, crc)
    return format(crc & 0xFFFFFFFF, "#010x")


def parse_line(line: str) -> TextLine:
    parts = line.strip().split("\t")

    if len(parts) != 4:
        raise ValueError(f"Некорректное количество полей: {len(parts)}")

    return TextLine(
        fio=parts[0].strip(),
        age=parts[1].strip(),
        address=parts[2].strip(),
        birth_date=parts[3].strip(),
    )


def text_cropping(text: str, width: int) -> str: # тут по Тз, как-то красиво обрезать текст
    text = str(text)
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


def calculate_widths(console_width: int) -> list:
    date_w = 19
    age_w = 7
    service_width = 13

    remaining = console_width - date_w - age_w - service_width

    if remaining < 20:
        name_w = 8
        address_w = 8
    else:
        name_w = max(10, int(remaining * 0.35))
        address_w = max(10, remaining - name_w)

    # порядок: ФИО, возраст, адрес, дата
    return [name_w, age_w, address_w, date_w]


def render_title(title: str, console_width: int) -> str:
    return title.center(console_width)


def format_row(values: list, widths: list) -> str:
    row = "|"
    for i in range(len(values)):
        cell_width = widths[i] - 2
        text = text_cropping(str(values[i]), cell_width)
        row += f" {text:<{cell_width}} |"
    return row

# Правим киррилцу, была проблема с   cp1251.
def fix_encoding(text: str) -> str:
    try:
        return text.encode("cp1251").decode("utf-8")
    except UnicodeEncodeError:
        raw = bytearray()
        for char in text:
            try:
                raw.extend(char.encode("cp1251"))
            except UnicodeEncodeError:
                if ord(char) < 256:
                    raw.append(ord(char))
                else:
                    raw.extend(char.encode("utf-8"))
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return text


def read_lines(source: str) -> list:
    lines = []

    if is_url(source):
        with urlopen(source) as stream:
            for raw_line in stream:
                lines.append(fix_encoding(raw_line.decode("utf-8")))
        return lines

    try:
        with open(source, "r", encoding="utf-8") as file:
            for line in file:
                lines.append(fix_encoding(line))
    except UnicodeDecodeError:
        with open(source, "r", encoding="cp1251") as file:
            lines = file.readlines()

    return lines


def print_table(source: str) -> None:
    console_width = shutil.get_terminal_size(fallback=(80, 20)).columns
    widths = calculate_widths(console_width)

    print(render_title(TABLE_TITLE, console_width))
    print(format_row(COLUMN_HEADERS, widths))

    for line in read_lines(source):
        if not line.strip():
            continue
        try:
            person = parse_line(line)
        except (ValidationError, ValueError):
            continue

        print(
            format_row(
                [person.fio, str(person.age), person.address, person.birth_date],
                widths,
            )
        )


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass


def main() -> None:
    configure_stdout()
    args = arg_parse()

    if (
        os.path.basename(args.input) == "data.txt"
        and not is_url(args.input)
        and os.path.isfile(args.input)
    ):
        crc = crc32_read(args.input)
        if crc != EXPECTED_DATA_CRC:
            print(f"ВНИМАНИЕ: CRC32 файла ({crc}) не совпадает с ожидаемым ({EXPECTED_DATA_CRC})")

    print_table(args.input)


if __name__ == "__main__":
    main()
