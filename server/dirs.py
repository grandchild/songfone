import os


def list_files_absolute(start_dir, extensions=None, ignore_empty=False):
    start_dir = os.path.expanduser(start_dir)
    return _list_files(start_dir, start_dir, extensions, ignore_empty=ignore_empty)


def list_files_relative(start_dir, extensions=None, ignore_empty=False):
    start_dir = os.path.expanduser(start_dir)
    return _list_files(
        start_dir, start_dir, extensions, relative=True, ignore_empty=ignore_empty
    )


def _list_files(
    start_dir, cur_dir, extensions=None, relative=False, ignore_empty=False
):
    paths = []
    with os.scandir(cur_dir) as scanner:
        for entry in scanner:
            if entry.is_dir():
                paths += _list_files(
                    start_dir,
                    entry.path,
                    extensions,
                    relative=relative,
                    ignore_empty=ignore_empty,
                )
            elif (
                (
                    extensions is not None
                    and any([entry.name.endswith("." + ext) for ext in extensions])
                )
                or extensions is None
            ) and ((ignore_empty and entry.stat().st_size > 0) or not ignore_empty):
                if relative:
                    name = os.path.relpath(entry.path, start=start_dir)
                else:
                    name = entry.path
                paths.append((name, entry.stat()))
    return paths
