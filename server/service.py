#!/usr/bin/env python3
import json
import os
import sys
import pwd
from argparse import ArgumentParser
from typing import Iterable


def install_service(
    i_am_root: bool = False, config_filepath: str = "songfone.conf"
) -> None:
    config = {"audio": "~/Music", "output": "~/.local/share/songfone/output"}
    try:
        with open(config_filepath) as config_file:
            config.update(json.load(config_file))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    try:
        watch_paths = (
            config["audio"] if isinstance(config["audio"], list) else [config["audio"]]
        )
    except KeyError:
        watch_paths = []
    watch_paths.append(os.path.join(config["output"], ".songfone/songs.wants"))
    if sys.platform.startswith("linux"):
        if i_am_root:
            at = "@"
            systemd_unit_dir = "/etc/systemd/system/"
            watch_paths = [_expanduser_sudo(p) for p in watch_paths]
        else:
            at = ""
            systemd_unit_dir = os.path.expanduser("~/.local/share/systemd/user/")
            os.makedirs(systemd_unit_dir, exist_ok=True)
        write_systemd_unit_file(
            os.path.join(systemd_unit_dir, f"songfone{at}.path"),
            SYSTEMD_PATH_TEMPLATE,
            path_modified_lines="\n".join([f"PathModified={a}" for a in watch_paths]),
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


def uninstall_service(i_am_root: bool = False) -> None:
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


def _remove_f(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def _expanduser_sudo(path: str) -> str:
    if path.startswith("~/"):
        sudo_user_home = pwd.getpwnam(os.getenv("SUDO_USER")).pw_dir
        return path.replace("~/", sudo_user_home + "/", 1)
    elif path.startswith("~"):
        first_sep = path.find("/")
        user = path[1:first_sep] if first_sep >= 0 else path[1:]
        user_home = pwd.getpwnam(user).pw_dir
        return path.replace("~" + user, user_home, 1)
    else:
        return path


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
ExecStart=/usr/bin/python3 -u {songfone_path}/songfone.py
WorkingDirectory={songfone_path}
{user_line}

[Install]
WantedBy=multi-user.target
"""


if __name__ == "__main__":
    parser = ArgumentParser("Install songfone as a system service")
    parser.add_argument("-i", "--install", action="store_true", help="Install service")
    parser.add_argument(
        "-u", "--uninstall", action="store_true", help="Uninstall service"
    )
    parser.add_argument(
        "-c", "--config", nargs=1, default="songfone.conf", help="Set config file path"
    )
    args = parser.parse_args()

    if args.install:
        install_service(os.getuid() == 0, args.config[0])
    elif args.uninstall:
        uninstall_service(os.getuid() == 0)
    else:
        parser.print_help()
