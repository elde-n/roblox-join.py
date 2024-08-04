#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import os
import time
import shutil
import random
import pathlib
import requests
import argparse
import argcomplete

import find_job_id


GAMES_CONFIG_FILE = ".config/roblox-join/games"
ACCOUNTS_CONFIG_FILE = ".config/roblox-join/accounts"


def get_roblox_launcher() -> str:
    version = requests.get("https://setup.rbxcdn.com/version.txt").content.decode("ascii")
    assert(version)

    app_data = os.getenv("LOCALAPPDATA")
    if app_data:
        path = app_data + "\\Roblox\\Versions\\" + version + "\\RobloxPlayerLauncher.exe"
        if os.path.exists(path):
            return path

    return "xdg-open"

def get_launch_url(cookie: str, id: int, job_id: str, private_server_code: str | None, channel_name = '') -> str:
    session = requests.session()
    session.headers["Referer"] = "https://www.roblox.com/"
    session.cookies.set(".ROBLOSECURITY", cookie)
    session.headers["Content-Type"] = "application/json"
    session.headers["X-CSRF-TOKEN"] = session.post("https://catalog.roblox.com/").headers["x-csrf-token"]

    assert(session.request("GET", "https://users.roblox.com/v1/users/authenticated").status_code == 200)
    auth_ticket = session.post("https://auth.roblox.com/v1/authentication-ticket/").headers["rbx-authentication-ticket"]
    browser_id = random.randint(100000000, 9999999999999)

    link_code = f"%26GameId%3D{job_id}"
    if private_server_code:
        link_code = f"%26linkcode%3D{private_server_code}"

    channel = ''
    if channel_name:
        channel = "+" + channel_name

    mode = "launchmode:play"
    return f"roblox-player:1+{mode}{channel}+gameinfo:{auth_ticket}+launchtime:{int(time.time() * 1000)}+placelauncherurl:https%3A%2F%2Fassetgame.roblox.com%2Fgame%2FPlaceLauncher.ashx%3Frequest%3DRequestGame%26BrowserTrackerId%3D{browser_id}%26PlaceId%3D{id}{link_code}%26IsPlayTogetherGame%3Dfalse+BrowserTrackerId:{browser_id}+RobloxLocale:en_us+GameLocale:en_us"

def parse_config_file(file_path: str) -> dict[str, str]:
    result = {}

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

    parser.add_argument("--user","-u", choices = accounts)
    parser.add_argument("--place", "-p", choices = places)
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
    launch_url = get_launch_url(cookie, place_id, job_id, arguments.link_code, arguments.channel)

    launch(launcher, launch_url)


if __name__ == "__main__":
    arguments = add_parser()
    main(arguments)
