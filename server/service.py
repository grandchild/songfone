#!/usr/bin/env python3
import json
import os
import sys
from typing import Iterable


def install_service(i_am_root: bool = False) -> None:
    data = {}
    with open("songfone.conf") as config_file:
        data = json.load(config_file)
    audio_dirs = data["audio"] if isinstance(data["audio"], list) else [data["audio"]]
    if sys.platform.startswith("linux"):
        if i_am_root:
            at = "@"
            systemd_unit_dir = "/etc/systemd/system/"
        else:
            at = ""
            systemd_unit_dir = os.path.expanduser("~/.local/share/systemd/user/")
        write_systemd_unit_file(
            os.path.join(systemd_unit_dir, f"songfone{at}.path"),
            SYSTEMD_PATH_TEMPLATE,
            path_modified_lines="\n".join([f"PathModified={a}" for a in audio_dirs]),
        )
        write_systemd_unit_file(
            os.path.join(systemd_unit_dir, f"songfone{at}.timer"),
            SYSTEMD_TIMER_TEMPLATE,
        )
        write_systemd_unit_file(
            os.path.join(systemd_unit_dir, f"songfone{at}.service"),
            SYSTEMD_SERVICE_TEMPLATE,
            user_line="User=%I" if i_am_root else "",
            songfone_path=os.path.dirname(os.path.realpath(__file__)),
        )
    else:
        raise NotImplementedError("OS {sys.platform} not supported for service install")


def write_systemd_unit_file(name: str, template: str, **kwargs) -> None:
    with open(name, "w") as file:
        file.write(template.format(**kwargs))


def uninstall_service(i_am_root: bool = False):
    if sys.platform.startswith("linux"):
        if i_am_root:
            systemd_unit_dir = "/etc/systemd/system/"
            _remove_f(os.path.join(systemd_unit_dir, "songfone@.service"))
            _remove_f(os.path.join(systemd_unit_dir, "songfone@.path"))
            _remove_f(os.path.join(systemd_unit_dir, "songfone@.timer"))
        else:
            systemd_unit_dir = os.path.expanduser("~/.local/share/systemd/user/")
            _remove_f(os.path.join(systemd_unit_dir, "songfone.service"))
            _remove_f(os.path.join(systemd_unit_dir, "songfone.path"))
            _remove_f(os.path.join(systemd_unit_dir, "songfone.timer"))


def _remove_f(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


SYSTEMD_PATH_TEMPLATE = """[Unit]
Description=songfone library path monitoring trigger

[Path]
{path_modified_lines}

[Install]
WantedBy=multi-user.target
"""

SYSTEMD_TIMER_TEMPLATE = """[Unit]
Description=songfone library timer trigger every 5min

[Timer]
OnUnitActiveSec=5min

[Install]
WantedBy=multi-user.target
"""

SYSTEMD_SERVICE_TEMPLATE = """[Unit]
Description=songfone library update service

[Service]
Type=oneshot
ExecStart=python3 -u {songfone_path}/songfone.py
WorkingDirectory={songfone_path}
{user_line}

[Install]
WantedBy=multi-user.target
"""

USAGE = f"""Usage:
    {__file__}              Install service files
    {__file__} uninstall    Remove service files
"""

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "uninstall":
            uninstall_service(os.getuid() == 0)
        else:
            print(USAGE)
    else:
        install_service(os.getuid() == 0)
