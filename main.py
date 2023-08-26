#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import os
import time
import shutil
import random
import requests
import argparse
import argcomplete


def get_roblox_launcher() -> str:
    version = requests.get("http://setup.roblox.com/version.txt").content.decode("ascii")
    assert(version)

    app_data = os.getenv("LOCALAPPDATA")
    if app_data:
        path = app_data + "\\Roblox\\Versions\\" + version + "\\RobloxPlayerLauncher.exe"
        if os.path.exists(path):
            return path
    
    if shutil.which("vinegar"):
        return "vinegar player"
    elif shutil.which("grapejuice"):
        return "grapejuice player"

    assert False, "couldn't find a valid roblox launcher"

def get_launch_url(cookie: str, id: int, job_id: str, private_server_code: str | None, channel_name = '') -> str:
    session = requests.session()
    session.headers["Referer"] = "https://www.roblox.com/"
    session.cookies.set(".ROBLOSECURITY", cookie)
    session.headers["X-CSRF-TOKEN"] = session.post("https://catalog.roblox.com/").headers["x-csrf-token"]

    assert(session.request("GET", "https://users.roblox.com/v1/users/authenticated").status_code == 200)

    auth_ticket = session.post("https://auth.roblox.com/v1/authentication-ticket/").headers["RBX-Authentication-Ticket"]
    browser_id = random.randint(100000000, 9999999999999)

    link_code = f"%26GameId%3D{job_id}"
    if private_server_code:
        link_code = f"%26linkcode%3D{private_server_code}"

    channel = ''
    if channel_name:
        channel = "+" + channel_name

    mode = "launchmode:play"
    return f"roblox-player:1+{mode}{channel}+gameinfo:{auth_ticket}+launchtime:{int(time.time() * 1000)}+placelauncherurl:https%3A%2F%2Fassetgame.roblox.com%2Fgame%2FPlaceLauncher.ashx%3Frequest%3DRequestGame%26BrowserTrackerId%3D{browser_id}%26PlaceId%3D{id}{link_code}%26IsPlayTogetherGame%3Dfalse+BrowserTrackerId:{browser_id}+RobloxLocale:en_us+GameLocale:en_us"

def get_places() -> dict[str, int]:
    games = {}
    with open(os.path.dirname(__file__) + "/games") as file:
        lines = file.read().splitlines()
        for i in range(0, len(lines)):
            args = lines[i].split(':', 1)
            games[args[1]] = args[0]
    return games

def get_accounts() -> dict[str, str]:
    accounts = {}
    with open(os.path.dirname(__file__) + "/accounts") as file:
        lines = file.read().splitlines()
        for i in range(0, len(lines)):
            args = lines[i].split(':', 1)
            accounts[args[0]] = args[1]
    return accounts

def get_account(name: str) -> str:
    return get_accounts()[name]

def get_place_id(place: str) -> int:
    return get_places()[place]

def launch(launcher: str, url: str):
    os.system(f"{launcher} \"{url}\"")

def add_parser() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    places = get_places()
    accounts = get_accounts()

    parser.add_argument("--user","-u", choices = accounts, required = True)
    parser.add_argument("--place", "-p", choices = places)
    parser.add_argument("--place-id", "-pid")
    parser.add_argument("--job-id", "-jid")
    parser.add_argument("--link-code", "-lnk")
    parser.add_argument("--channel", "-C")
    parser.add_argument("--launcher", "-L")

    argcomplete.autocomplete(parser)

    arguments = parser.parse_args()
    if not arguments.place_id and not arguments.place:
        parser.print_usage()
        exit(0)

    return arguments

def main(arguments: argparse.Namespace):
    cookie = get_account(arguments.user)
    place_id = arguments.place and get_place_id(arguments.place) or arguments.place_id
    job_id = arguments.job_id or ''

    launcher = arguments.launcher or get_roblox_launcher()
    launch_url = get_launch_url(cookie, place_id, job_id, arguments.link_code, arguments.channel)

    launch(launcher, launch_url)


if __name__ == "__main__":
    arguments = add_parser()
    main(arguments)
