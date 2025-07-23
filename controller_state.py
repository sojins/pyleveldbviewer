class BatchStateManager:
    def __init__(self):
        self.batch_generators = {}   # "db.table" → generator
        self.batch_pages = {}        # "db.table" → int
        self.batch_cache = {}        # "db.table" → list
        self.tdm_map = {}            # "db.table" → TDM
        self.current_key = None      # 현재 선택된 key

        self.page_label = None
        self.prev_btn = None
        self.next_btn = None

    def set_current_key(self, key):
        self.current_key = key

    def get_current_key(self):
        return self.current_key

    def reset_cache_if_key_changed(self, key):
        if self.current_key != key:
            self.batch_generators[key] = None
            self.batch_cache[key] = None
            self.batch_pages[key] = 0
        self.set_current_key(key)

    def clear(self):
        self.batch_generators.clear()
        self.batch_pages.clear()
        self.batch_cache.clear()
        self.tdm_map.clear()
        self.current_key = None

state = BatchStateManager()
