# environment.py
# Runtime environment: variable storage during execution

from suggestions import find_similar


class RuntimeError_Onyx(Exception):
    pass


class Environment:
    def __init__(self, parent=None):
        self.values = {}
        self.consts = set()
        self.parent = parent

    def define(self, name, value, is_const=False):
        if name in self.values:
            raise RuntimeError_Onyx(f"variable '{name}' already defined in this scope")
        self.values[name] = value
        if is_const:
            self.consts.add(name)

    def get(self, name, line=0):
        if name in self.values:
            return self.values[name]
        if self.parent is not None:
            return self.parent.get(name, line)
        similar = self._suggest(name)
        msg = f"[line {line}] variable '{name}' is not defined"
        if similar:
            msg += " -- did you mean: " + ", ".join("'" + s + "'" for s in similar) + "?"
        raise RuntimeError_Onyx(msg)

    def set(self, name, value, line=0):
        if name in self.values:
            if name in self.consts:
                raise RuntimeError_Onyx(
                    f"[line {line}] cannot reassign constant '{name}'"
                )
            self.values[name] = value
            return
        if self.parent is not None:
            self.parent.set(name, value, line)
            return
        similar = self._suggest(name)
        msg = f"[line {line}] variable '{name}' is not defined"
        if similar:
            msg += " -- did you mean: " + ", ".join("'" + s + "'" for s in similar) + "?"
        raise RuntimeError_Onyx(msg)

    def has(self, name):
        if name in self.values:
            return True
        if self.parent is not None:
            return self.parent.has(name)
        return False

    def all_names(self):
        names = set(self.values.keys())
        if self.parent is not None:
            names.update(self.parent.all_names())
        return names

    def _suggest(self, name):
        try:
            return find_similar(name, list(self.all_names()))
        except Exception:
            return []