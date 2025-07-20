import json
from tkinter import filedialog
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


def delete_all_nodes(tree_obj):
    try:
        for i in tree_obj.get_children():
            tree_obj.delete(i)
    except:
        pass
    
def select_log_dir(event=None, param=None):
    """
    :param event: event arg (not used)
    """
    global g_wrapper
    tree = param
    file_path = filedialog.askdirectory(
        initialdir = '',
        title='Select IndexedDB Directory')
    (wrapper, db) = LevelDBWrapper().load(file_path)
    g_wrapper = wrapper
    try:
        # TreeView 구성
        delete_all_nodes(tree)
        for db_name, tables in db.items():
            db_node = tree.insert("", "end", text=db_name)
            if isinstance(tables, dict):
                table_keys = tables.keys()
            else:
                table_keys = tables
            for table_name in table_keys:
                tree.insert(db_node, "end", text=f"{db_name}.{table_name}")
    except:
        pass

def remove_tabs():
    '''
    # 기존 탭 모두 제거
    '''
    for tab_id in notebook.tabs():
        if tab_id.split('.')[-1] != '!frame':
            notebook.forget(tab_id)

def create_table_tab(schema: tuple, rows: list, index: int):
    # global notebook
    frame = tk.Frame(notebook)
    new_sheet = Sheet(frame, headers=list(schema))
    new_sheet.pack(fill="both", expand=True)

    new_sheet.enable_bindings((
        "single_select", "cell_select", "column_width_resize", "cell_double_click"
    ))

    table_data = [normalize_row(row, list(schema)) for row in rows]
    new_sheet.set_sheet_data(table_data)

    notebook.add(frame, text=f"Table-{index+1}")
    
                
# 선택 시 데이터 렌더링
def on_select(root, db_data, event): #wrapper, event):
    # global g_wrapper, _batch_gen
    # if wrapper is None:
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
    
    # db = wrapper[db_name]
    obj_store = wrapper[db_name][table_name]  # accessing object store using name
    
    record_iter = obj_store.iterate_records(errors_to_stdout=True)
    batched_gen = (record.value for record in record_iter if record.value)
    return batched_gen
