import os.path as path


class Options:

    _instance = None

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
            class_._instance.options = {'seed': 0, 'output_dir': '.',
                            'platform_library_path': path.join(path.dirname(__file__), 'data')}
        return class_._instance

    def get(self):
        return self.options
