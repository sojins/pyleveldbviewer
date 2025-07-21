from json_util import make_cell_safe


table_batch_dict = {}

def normalize_row(row: dict | str | list, columns: list):
    if isinstance(row, dict):
        return [make_cell_safe(row.get(col)) for col in columns]
    elif isinstance(row, list):
        # 목록일 경우 단일 셀에 넣기, 나머지는 공백
        return [make_cell_safe(row)] + [""] * (len(columns) - 1)
    elif isinstance(row, str):
        # 문자열일 경우 단일 셀에 넣기, 나머지는 공백
        return [make_cell_safe(row)] + [""] * (len(columns) - 1)
    else:
        # 예외적인 경우 전체 빈 값
        return [""] * len(columns)
