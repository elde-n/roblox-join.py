#!/usr/bin/env python

import sys
import time
import requests
import concurrent.futures
from typing import List, Tuple, Optional, TypedDict, Union, cast

class Server(TypedDict):
    job_id: str
    player_tokens: List[str]
    players: int

def get_servers_from_place(place_id: int, cursor: str) -> Tuple[List[Server], Optional[str]]:
    servers: List[Server] = []

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
        servers.append(Server(
            job_id=i["id"],
            player_tokens=i["playerTokens"],
            players=i["players"]
            ))

    return servers, cursor

def get_servers_from_place_all(place_id: int) -> List[Server]:
    servers: List[Server] = []
    cursor: Optional[str] = ''
    while cursor is not None:
        new_servers, cursor = get_servers_from_place(place_id, cursor)
        servers.extend(new_servers)

    return servers

def get_thumbnails_from_tokens(player_tokens: List[str], size: str = "150x150", is_circular: bool = True) -> List[Union[str, int]]:
    data = cast(dict[str, str], [])
    for i, token in enumerate(player_tokens):
        data.append({
            "requestId": str(i),
            "token": token,
            "size": size,
            "isCircular": str(is_circular),
            "type": "AvatarHeadShot"
            })

    response = requests.post("https://thumbnails.roblox.com/v1/batch/", headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
        }, json = data)

    thumbnails: List[Union[str, int]] = [0] * 100
    for item in response.json()["data"]:
        id = int(item["requestId"])
        thumbnails[id] = item["imageUrl"]
    return thumbnails

def get_thumbnail_from_user_id(user_id: int, size: str = "150x150", is_circular: bool = True) -> str:
    url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size={size}&format=Png&isCircular={is_circular}"
    response = requests.get(url, headers = {
        "accept": "application/json"
        })

    return response.json()["data"][0]["imageUrl"]

def get_token_groups(tokens: List[str], max_requests: int = 100) -> List[List[str]]:
    token_groups: List[List[str]] = []
    for i in range(0, len(tokens), max_requests):
        token_groups.append(tokens[i:i + max_requests])
    return token_groups

def get_tokens_from_servers(servers: List[Server]) -> List[str]:
    tokens: List[str] = []
    for server in servers:
        tokens.extend(server["player_tokens"])
    return tokens

def find_job_id_from_token(servers: List[Server], token: str) -> Optional[str]:
    for server in servers:
        if token in server["player_tokens"]:
            return server["job_id"]
    return None

def find_job_id_from_user_id(user_id: int, place_id: int) -> Optional[str]:
    size = "150x150"
    is_circular = False

    max_threads = 100
    max_thumbnail_requests = 100

    servers = get_servers_from_place_all(place_id)
    tokens = get_tokens_from_servers(servers)
    u_thumbnail = get_thumbnail_from_user_id(user_id, size, is_circular)

    index = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        for token_group in get_token_groups(tokens, max_thumbnail_requests):
            future = executor.submit(get_thumbnails_from_tokens, token_group, size, is_circular)
            result = future.result()

            if u_thumbnail in result:
                index += result.index(u_thumbnail)
                job_id = find_job_id_from_token(servers, tokens[index])
                if job_id:
                    return job_id
            else:
                index += len(result)
    return None

def main(argc: int, argv: List[str]) -> None:
    assert(argc > 2)
    user_id = int(argv[1])
    place_id = int(argv[2])

    job_id = find_job_id_from_user_id(user_id, place_id)
    if job_id:
        print(job_id)
    else:
        print("No job-id was found")

if __name__ == "__main__":
    argv = sys.argv
    main(len(argv), argv)
