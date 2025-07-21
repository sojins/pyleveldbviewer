from json_util import make_cell_safe


table_batch_dict = {}

def normalize_row(row: dict, columns: list):
    return [make_cell_safe(row.get(col)) for col in columns]

