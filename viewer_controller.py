import json
from data_util import extract_table_data
from json_util import highlight_keys_fast, make_json_safe
from leveldb_wrapper import LevelDBWrapper


tree = None
json_view = None
table_view = None
table_batch_dict = {}

def init_controllers(_tree, _json_view, _table_view):
    tree = _tree
    json_view = _json_view
    table_view = _table_view
    pass

def get_tree():
    return tree

# 선택 시 데이터 렌더링
def on_select(root, db_data, wrapper, event):
    global g_wrapper, _batch_gen
    if wrapper is None:
        wrapper = g_wrapper
    tree = event.widget
    sel = tree.selection()
    if not sel:
        return
    text = tree.item(sel[0], "text")
    if "." not in text:
        return
    db_name, table_name = text.split(".", 1)
    create_first_gen = False
    batch = []
    try:
        data = db_data[db_name][table_name]
        pretty = json.dumps(data, indent=2, ensure_ascii=False)
    except:
        gen = view_table_new_cb(root, wrapper, db_name, table_name)
        try:
            if _batch_gen is None or table_batch_dict.get(text) is None:
                table_batch_dict[text] = _batch_gen = LevelDBWrapper()._make_batch_gen(gen, 10)
                create_first_gen = True
        except NameError:
            table_batch_dict[text] = _batch_gen = LevelDBWrapper()._make_batch_gen(gen, 10)
            create_first_gen = True
        try:
            batch = next(_batch_gen)
        except StopIteration:
            try:
                if not create_first_gen:
                    table_batch_dict[text] = _batch_gen = LevelDBWrapper()._make_batch_gen(gen, 10)
                    batch = next(_batch_gen)
                else:
                    print("1")
            except:
                pass
        data = []
        # 📌 스키마별 그룹핑
        schema_groups = {}
        for item in batch:
            data.append(item)
            try:
                schema = tuple(sorted(item.keys())) # 스키마 식별자
            except:
                schema = ('')
            schema_groups.setdefault(schema, []).append(item)

        remove_tabs()
        
        # 그룹마다 새 탭 생성
        for i, (schema, rows) in enumerate(schema_groups.items()):
            create_table_tab(schema, rows, i)

        pretty = make_json_safe(data)

    # highlight_json(json_view, pretty)
    json_view.delete("1.0", "end")       # 기존 내용 지우기
    json_view.insert("1.0", pretty)
    highlight_keys_fast(json_view)
    
    cols, rows = extract_table_data(data)
    table_view.set_sheet_data(rows)
    if cols:
        table_view.headers(cols)
        
def view_table_new_cb(root, wrapper, db_name=None, table_name=None):
    if not db_name or not table_name:
        return
    
    db = wrapper[db_name]
    obj_store = db[table_name]  # accessing object store using name
    
    record_iter = obj_store.iterate_records(errors_to_stdout=True)
    batched_gen = (record.value for record in record_iter if record.value)
    return batched_gen
