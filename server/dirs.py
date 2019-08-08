import os


def list_files_absolute(start_dir, extensions=None):
    start_dir = os.path.expanduser(start_dir)
    return _list_files(start_dir, start_dir, extensions)


def list_files_relative(start_dir, extensions=None):
    start_dir = os.path.expanduser(start_dir)
    return _list_files(start_dir, start_dir, extensions, relative=True)


def _list_files(start_dir, cur_dir, extensions=None, relative=False):
    paths = []
    with os.scandir(cur_dir) as scanner:
        for entry in scanner:
            if entry.is_dir():
                paths += _list_files(start_dir, entry.path, extensions, relative)
            elif (
                extensions is not None
                and any([entry.name.endswith("." + ext) for ext in extensions])
            ) or extensions is None:
                if relative:
                    name = os.path.relpath(entry.path, start=start_dir)
                else:
                    name = entry.path
                paths.append((name, entry.stat()))
    return paths


if __name__ == "__main__":
    import doctest

    doctest.testmod()
