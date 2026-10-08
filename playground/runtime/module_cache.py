# module_cache.py
# Cached AST storage for Onyx modules

import os
import hashlib
import pickle


CACHE_DIR = ".onyx_cache"


def ensure_cache_dir():
    if not os.path.isdir(CACHE_DIR):
        os.makedirs(CACHE_DIR)


def file_hash(path):
    """SHA-256 hash of file contents (truncated to 16 chars)."""
    with open(path, 'rb') as f:
        data = f.read()
    return hashlib.sha256(data).hexdigest()[:16]


def cache_path(module_name, hash_value):
    return os.path.join(CACHE_DIR, f"{module_name}-{hash_value}.pickle")


def load_cached(module_name, source_path):
    """Return parsed AST if cache is fresh, else None."""
    if not os.path.isdir(CACHE_DIR):
        return None
    try:
        h = file_hash(source_path)
        cp = cache_path(module_name, h)
        if not os.path.exists(cp):
            return None
        with open(cp, 'rb') as f:
            return pickle.load(f)
    except Exception:
        return None


def save_cached(module_name, source_path, tree):
    """Save parsed AST to cache."""
    try:
        ensure_cache_dir()
        h = file_hash(source_path)
        cp = cache_path(module_name, h)
        with open(cp, 'wb') as f:
            pickle.dump(tree, f, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception:
        pass


def clear_cache():
    """Remove all cached files. Returns number of files removed."""
    if not os.path.isdir(CACHE_DIR):
        return 0
    count = 0
    for f in os.listdir(CACHE_DIR):
        try:
            os.remove(os.path.join(CACHE_DIR, f))
            count += 1
        except Exception:
            pass
    try:
        os.rmdir(CACHE_DIR)
    except Exception:
        pass
    return count


def cache_stats():
    """Return (file_count, total_bytes)."""
    if not os.path.isdir(CACHE_DIR):
        return 0, 0
    count = 0
    size = 0
    for f in os.listdir(CACHE_DIR):
        fp = os.path.join(CACHE_DIR, f)
        if os.path.isfile(fp):
            count += 1
            size += os.path.getsize(fp)
    return count, size