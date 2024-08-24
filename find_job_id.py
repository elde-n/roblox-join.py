#!/usr/bin/env python

import sys
import time
import requests
import concurrent.futures


Server = dict[{
    "job-id": str,
    "player-tokens": list[str],
    "players": int
}]


def get_servers_from_place(place_id: int, cursor: str) -> (list[Server], str):
    servers = []

    url = f"https://games.roblox.com/v1/games/{place_id}/servers/0?sortOrder=2&excludeFullGames=false&limit=100&cursor={cursor}"
    response = requests.get(url, headers = {
        "accept": "application/json"
    })

    if response.status_code != 200:
        print(response.text)
        time.sleep(1)
        return get_servers_from_place(place_id, cursor)

    data = response.json()
    cursor = data["nextPageCursor"]

    for i in data["data"]:
        servers.append({
            "job-id": i["id"],
            "player-tokens": i["playerTokens"],
            "players": i["players"]
        })

    return servers, cursor

def get_servers_from_place_all(place_id: int) -> list[Server]:
    servers = []
    cursor = ''
    while cursor != None:
        new_servers, cursor = get_servers_from_place(place_id, cursor)
        servers.extend(new_servers)

    return servers

def get_thumbnails_from_tokens(player_tokens: list[str], size = "150x150", is_circular = True) -> list[str | int]:
    data = []
    for i, token in enumerate(player_tokens):
        data.append({
            "requestId": i,
            "token": token,
            "size": size,
            "isCircular": is_circular,
            "type": "AvatarHeadShot"
        })

    response = requests.post("https://thumbnails.roblox.com/v1/batch/", headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }, json = data)

    thumbnails: list[str | int] = [0] * 100
    for item in response.json()["data"]:
        id = int(item["requestId"])
        thumbnails[id] = item["imageUrl"]
    return thumbnails

def get_thumbnail_from_user_id(user_id: int, size = "150x150", is_circular = True) -> str:
    url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size={size}&format=Png&isCircular={is_circular}"
    response = requests.get(url, headers = {
        "accept": "application/json"
    })

    return response.json()["data"][0]["imageUrl"]

def get_token_groups(tokens: list[str], max_requests = 100) -> list[list]:
    token_groups = []
    for i in range(0, len(tokens), max_requests):
        token_groups.append(tokens[i:i + max_requests])
    return token_groups

def get_tokens_from_servers(servers: list[Server]) -> list[str]:
    tokens = []
    for server in servers:
        for token in server["player-tokens"]:
            tokens.append(token)
    return tokens

def find_job_id_from_token(servers: list[Server], token: str) -> str | None:
    for server in servers:
        if token in server["player-tokens"]:
            return server["job-id"]

def find_job_id_from_user_id(user_id: int, place_id: int) -> str | None:
    size = "150x150"
    is_circular = False

    max_threads = 100
    max_thumbnail_requests = 100

    servers = get_servers_from_place_all(place_id)
    tokens = get_tokens_from_servers(servers)
    u_thumbnail = get_thumbnail_from_user_id(user_id, size, is_circular)

    index = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers = max_threads) as executor:
        for token_group in get_token_groups(tokens, max_thumbnail_requests):
            future = executor.submit(get_thumbnails_from_tokens, token_group, size, is_circular)
            result = future.result()

            if u_thumbnail in result:
                index += result.index(u_thumbnail)
                job_id = find_job_id_from_token(servers, tokens[index])
                if job_id: return job_id
            else:
                index += len(result)

def main(argc: int, argv: list[str]):
    assert(argc > 2)
    user_id = int(argv[1])
    place_id = int(argv[2])

    job_id = find_job_id_from_user_id(user_id, place_id)
    if job_id: print(job_id)
    else: print("No job-id was found")

if __name__ == "__main__":
    argv = sys.argv
    main(len(argv), argv)
