from tksheet import Sheet, ColumnHeaders
def auto_resize_column(sheet:Sheet, col_index: int, max_width: int = 600, min_width: int = 40, refresh=True):
    """선택한 열을 셀 내용에 맞춰 자동 너비 조정"""
    try:
        col_data = sheet.get_column_data(col_index)
        max_len = max(len(str(cell)) for cell in col_data)
        new_width = max(min(max_len * 7 + 10, max_width), min_width)
        sheet.column_width(col_index, new_width)
        if refresh:
            sheet.refresh()
    except Exception as e:
        print(f"⚠️ Failed to auto resize column {col_index}: {e}")

def auto_resize_all_columns(sheet, max_width: int = 600, min_width: int = 40):
    """전체 열의 너비를 셀 내용 기준으로 자동 조정"""
    try:
        total_cols = sheet.total_columns()
        for col_index in range(total_cols):
            auto_resize_column(sheet, col_index, max_width, min_width, refresh=False)
        sheet.refresh()
    except Exception as e:
        print(f"⚠️ Failed to auto resize all columns: {e}")
