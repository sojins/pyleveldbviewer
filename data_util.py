from json_util import make_cell_safe


table_batch_dict = {}
def extract_table_data(json_data):
    if isinstance(json_data, list):
        if all(isinstance(row, dict) for row in json_data):
            columns = sorted({k for row in json_data for k in row})
            rows = [[row.get(col, "") for col in columns] for row in json_data]
            return columns, rows
        else:
            # list[str] / list[int] / list[float] 등
            columns = ["value"]
            # rows = [[str(item)] for item in json_data]
            rows = [[str(item)] for item in json_data]
            return columns, rows
    return [], []

def normalize_row(row: dict, columns: list):
    return [make_cell_safe(row.get(col)) for col in columns]

