import json
import re


def highlight_keys_fast(text_widget):
    text_widget.tag_configure("key", foreground="blue")

    # 전체 줄 수 가져오기
    total_lines = int(text_widget.index("end-1c").split('.')[0])

    for lineno in range(1, total_lines + 1):
        line = text_widget.get(f"{lineno}.0", f"{lineno}.end")

        # "key": 패턴 찾기
        for match in re.finditer(r'"(.*?)"\s*:', line):
            start_idx = f"{lineno}.{match.start(1)}"
            end_idx = f"{lineno}.{match.end(1)}"
            text_widget.tag_add("key", start_idx, end_idx)
            
def make_json_safe(obj):
    def default(o):
        if isinstance(o, bytes):
            return o.decode('utf-8', errors='replace')  # 또는 base64 인코딩
        return str(o)
    return json.dumps(obj, indent=2, ensure_ascii=False, default=default)

def make_cell_safe(value):
    """테이블 셀에 안전하게 표시할 값으로 변환"""
    def default(o):
        if isinstance(o, bytes):
            try:
                return o.decode('utf-8', errors='replace')
            except:
                return str(o)
        return str(o)
    if isinstance(value, (dict, list)):
        try:
            avalue = json.dumps(value, ensure_ascii=False, indent=None, default=default)
            return avalue 
        except Exception:
            avalue = make_json_safe(value)
            return avalue
    elif isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')  # 또는 base64.b64encode(value).decode()
    elif value is None:
        return ""
    else:
        return str(value)
