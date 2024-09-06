#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import os
import time
import random
import urllib
import pathlib
import argparse
import platform
import subprocess

import requests
import argcomplete
import urllib.parse


import find_job_id


GAMES_CONFIG_FILE = ".config/roblox-join/games"
ACCOUNTS_CONFIG_FILE = ".config/roblox-join/accounts"

SOBER_FLATPAK = "org.vinegarhq.Sober"
SOBER_PATH = f".var/app/{SOBER_FLATPAK}"
SOBER_COOKIES_PATH = "data/sober/cookies"
SOBER_INSTANCES_PATH = ".local/share/sober/instances"


def get_roblox_launcher() -> str:
    version = requests.get("https://setup.rbxcdn.com/version.txt").content.decode("ascii")
    assert version

    app_data = os.getenv("LOCALAPPDATA")
    if app_data:
        path = app_data + "\\Roblox\\Versions\\" + version + "\\RobloxPlayerLauncher.exe"
        if os.path.exists(path):
            return path

    return "xdg-open"

def get_launch_url(cookie: str, id: int, job_id: str, private_server_code: str | None, channel_name: str = '') -> str:
    session = requests.session()
    session.headers["Referer"] = "https://www.roblox.com/"
    session.cookies.set(".ROBLOSECURITY", cookie)
    session.headers["Content-Type"] = "application/json"
    session.headers["X-CSRF-TOKEN"] = session.post("https://catalog.roblox.com/").headers["x-csrf-token"]

    assert(session.request("GET", "https://users.roblox.com/v1/users/authenticated").status_code == 200)
    auth_ticket = session.post("https://auth.roblox.com/v1/authentication-ticket/").headers["rbx-authentication-ticket"]
    browser_id = random.randint(100000000, 9999999999999)

    channel = "channel:" + channel_name

    # TODO: make it less ugly

    version = 1
    launch_mode = "launchmode:play"
    launch_time = f"launchtime:{time.time() * 1000}"
    game_info = f"gameinfo:{auth_ticket}"
    base_url = "baseUrl:https://www.roblox.com/"

    game_locale = "gameLocale:en_us"
    roblox_locale = "robloxLocale:en_us"
    launch_experience = "launchexp:InApp"

    join_attempt_id = ""
    place_launcher_parameters = (
        f"https://www.roblox.com/Game/PlaceLauncher.ashx?request=RequestGame"
        f"&browserTrackerId={browser_id}"
        f"&placeId={id}"
        f"&isPlayTogetherGame=false"
        f"&joinAttemptId={join_attempt_id}"
        f"&joinAttemptOrigin=PlayButton"
        f"&gameId={job_id}"
    )

    if private_server_code:
        place_launcher_parameters += f"&linkCode={private_server_code}"

    place_launcher_url = "placelauncherurl:" + urllib.parse.quote(place_launcher_parameters)

    return f"roblox-player:{version}+{launch_mode}+{game_info}+{launch_time}+{place_launcher_url}+{base_url}+{channel}+{roblox_locale}+{game_locale}+{launch_experience}"

def parse_config_file(file_path: str) -> dict[str, str]:
    result: dict[str, str] = {}

    path = pathlib.Path().home().joinpath(file_path)
    with open(path) as file:
        lines = file.read().splitlines()
        for i in range(0, len(lines)):
            if lines[i].strip() == '' or lines[i][0:1] == '#': continue

            args = lines[i].split(':', 1)
            if len(args) < 2:
                print(f"Malformed entry in {file_path} at line: {i + 1}")
                continue

            result[args[0].strip()] = args[1].strip()
    return result

def get_account(name: str) -> str:
    return parse_config_file(ACCOUNTS_CONFIG_FILE)[name]

def get_place_id(place: str) -> int:
    games = {v: k for k, v in parse_config_file(GAMES_CONFIG_FILE).items()}
    return int(games[place])

def launch(launcher: str, url: str):
    os.system(f"{launcher} \"{url}\"")

def add_parser() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    places = parse_config_file(GAMES_CONFIG_FILE).values()
    accounts = parse_config_file(ACCOUNTS_CONFIG_FILE).keys()

    parser.add_argument("--user", "-u", choices=accounts)
    parser.add_argument("--place", "-p", choices=places)
    parser.add_argument("--place-id", "-pid")
    parser.add_argument("--job-id", "-jid")
    parser.add_argument("--link-code", "-lnk")
    parser.add_argument("--channel", "-C")
    parser.add_argument("--launcher", "-L")
    parser.add_argument("--cookie")
    parser.add_argument("--target-user-id", "-tuid")

    argcomplete.autocomplete(parser)

    arguments = parser.parse_args()
    if not arguments.place_id and not arguments.place:
        parser.print_usage()
        exit(0)

    if not arguments.user and not arguments.cookie:
        parser.print_usage()
        exit(0)

    return arguments

def sober_is_launcher(launcher: str) -> bool:
    if platform.system() != "Windows":
        default_launcher = os.popen("xdg-mime query default \"x-scheme-handler/roblox\"").read()
        if default_launcher.startswith(SOBER_FLATPAK):
            return True
    return False

def sober_update_cookie(env: pathlib.Path, cookie: str):
    path = env.joinpath(SOBER_COOKIES_PATH)
    with open(path, 'w') as f:
        f.write(".ROBLOSECURITY=" + cookie)

def sober_is_running(env: pathlib.Path) -> bool:
    path = env.joinpath(SOBER_COOKIES_PATH)
    if not os.path.exists(path):
        return False

    age = time.time() - os.path.getmtime(path)
    if age > 1:
        try: subprocess.check_output(["pidof", "-s", "sober"])
        except subprocess.CalledProcessError: return False
        return True

    return True

def sober_new_env(name: str, cookie: str) -> str:
    path = pathlib.Path().home().joinpath(SOBER_INSTANCES_PATH).joinpath(name)

    env_path = path.joinpath(SOBER_PATH)
    env_config = env_path.joinpath("config")
    env_data = env_path.joinpath("data/sober")

    main_env = pathlib.Path().home().joinpath(SOBER_PATH)
    config = main_env.joinpath("config")
    data = main_env.joinpath("data/sober")

    if not os.path.exists(env_path):
        os.makedirs(env_path)

    if not os.path.exists(env_data):
        os.makedirs(env_data)

    os.system(f"ln -sf {config} {env_config}")

    whitelisted_data = ["state", "appData", "assets"]
    for file in whitelisted_data:
        os.system(f"cp -r {data.joinpath(file)} {env_data.joinpath(file)}")

    sober_update_cookie(env_path, cookie)
    return str(path)


def main(arguments: argparse.Namespace):
    cookie = arguments.user and get_account(arguments.user) or arguments.cookie
    place_id = arguments.place and get_place_id(arguments.place) or arguments.place_id
    job_id = arguments.job_id or ''

    target_user_id = arguments.target_user_id
    if target_user_id:
        job_id = find_job_id.find_job_id_from_user_id(target_user_id, place_id)
        if not job_id:
            print("ERROR: Couldn't find user")
            exit(1)

    launcher = arguments.launcher or get_roblox_launcher()
    launch_url = get_launch_url(cookie,
                                place_id,
                                job_id,
                                arguments.link_code,
                                arguments.channel or '')

    if sober_is_launcher(launcher):
        main_env = pathlib.Path().home().joinpath(SOBER_PATH)
        if sober_is_running(main_env):
            env = sober_new_env(arguments.user, cookie)
            launcher = f"env HOME={env} {launcher}"
        else:
            sober_update_cookie(main_env, cookie)

    launch(launcher, launch_url)


if __name__ == "__main__":
    arguments = add_parser()
    main(arguments)
