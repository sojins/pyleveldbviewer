from collections import defaultdict
class UIContext:
    def __init__(self):
        self.tree = None
        self.json_view = None
        self.notebook = None
        self.root = None
        self.progressbar = None

ui = UIContext()

class TableContext:
    def __init__(self):
        self.current_key = None
        self.batch_generators = {}
        self.batch_pages = defaultdict(int)
        self.batch_cache = {}
        self.tdm_map = {}

        self.page_label = None
        self.prev_btn = None
        self.next_btn = None

    def reset_if_key_changed(self, key):
        if self.current_key != key:
            self.batch_generators[key] = None
            self.batch_cache[key] = []
            self.batch_pages[key] = 0
            self.current_key = key

table = TableContext()

cell_full_data = {}
