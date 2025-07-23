import os
from threading import Thread
from ttkbootstrap.widgets import Progressbar
from ccl_chromium_reader.ccl_chromium_indexeddb import WrappedIndexDB

def entry_generator(db : WrappedIndexDB, db_name: str, table_name: str):
    if not db_name or not table_name:
        return
    
    obj_store = db[db_name][table_name]  # accessing object store using name
    record_iter = obj_store.iterate_records(errors_to_stdout=True)
    for record in record_iter:
        if record.value:
            yield record.value

def count_generator_items(gen_func):
    count = 0
    for _ in gen_func():
        count += 1
    return count

class LevelDBWrapper:
    class TableDataManager:
        def __init__(self, db, db_name, table_name):
            self.db = db
            self.db_name = db_name
            self.table_name = table_name
            self._gen_func = lambda: entry_generator(db, db_name, table_name)
            self.reset()

        def reset(self):
            self._gen = self._gen_func()

        def get_next_batch(self, batch_size=50):
            batch = []
            try:
                for _ in range(batch_size):
                    batch.append(next(self._gen))
            except StopIteration:
                pass
            return batch

        def count_total(self):
            return count_generator_items(self._gen_func)

        def is_exhausted(self):
            try:
                peek = next(self._gen)
                self._gen = iter([peek]) + self._gen  # peek 복원
                return False
            except StopIteration:
                return True

    def find_indexeddb_components(self, selected_dir):
        # 폴더 이름이 '.leveldb'로 끝나는지 확인
        if str(os.path.basename(selected_dir)).endswith(".leveldb"):
            leveldb_path = selected_dir
            return None, leveldb_path

        # 마지막 폴더 이름이 'IndexedDB'인지 확인
        if os.path.basename(selected_dir) != "IndexedDB":
            return None

        # 하위 폴더 중 '.blob', '.leveldb'로 끝나는 폴더 찾기
        blob_path = None
        leveldb_path = None

        for entry in os.listdir(selected_dir):
            full_path = os.path.join(selected_dir, entry)
            if os.path.isdir(full_path):
                if entry.endswith(".blob"):
                    blob_path = full_path
                elif entry.endswith(".leveldb"):
                    leveldb_path = full_path

        if blob_path and leveldb_path:
            return blob_path, leveldb_path
        elif leveldb_path:
            return '', leveldb_path
        else:
            return None
        
    def load(self, base_dir):
        (blob_dir, db_dir) = self.find_indexeddb_components(base_dir)
        (wrapper, db_names) = self.load_data(db_dir=db_dir, blob_dir=blob_dir)

        return (wrapper, db_names)

    def load_data(self, db_dir, blob_dir):
        leveldb_folder_path = db_dir
        blob_folder_path = blob_dir
        db_names = []
        if not db_dir:
            return (None, db_names)

        # open the indexedDB:
        wrapper : WrappedIndexDB = WrappedIndexDB(leveldb_folder_path, blob_folder_path)
        dict_table = {}
        for name in wrapper._db_name_lookup:
            dict_table[f'{name[0]}'] = wrapper[name[0]]._obj_store_names
        return (wrapper, dict_table)
    
    def load_data_with_progress(self, progressbar:Progressbar, folder_path, callback):
        progressbar.start(10)  # 10ms마다 움직임

        def task():
            try:
                (wrapper, db_names) = self.load(folder_path)
                callback(wrapper, db_names, folder_path)
            except Exception as e:
                print("예외: ", e)
            finally:
                progressbar.stop()
                progressbar.pack_forget()
        
        Thread(target=task).start()
        
    def _make_batch_gen(self, generator, batch_size=10):
            '''
            batch 생성기 (n개씩 가져오기)
            '''
            batch = []
            for item in generator:
                batch.append(item)
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
            if batch:
                yield batch
    
    def get_tables(self, db_name):
        try:
            tables = [item for item in self.data if item['name'] == db_name][0]['tables']
            return tables
        except:
            pass
