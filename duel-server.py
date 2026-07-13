from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json
import os
import time
import urllib.parse


ROOT = Path(__file__).resolve().parent
ATTACK_VALUES = [10, 18, 30, 45]
rooms = {}


def new_room(code):
    return {
        "code": code,
        "players": {
            "p1": {"connected": False, "hp": 100, "last_seen": 0},
            "p2": {"connected": False, "hp": 100, "last_seen": 0},
        },
        "events": [],
        "next_event": 1,
        "winner": "",
    }


def room_for(code):
    clean = "".join(ch for ch in code.upper() if ch.isalnum())[:8] or "ARCANE"
    if clean not in rooms:
        rooms[clean] = new_room(clean)
    return rooms[clean]


def damage_from_counts(counts):
    total = 0
    for index, count in enumerate(counts[:4]):
        try:
            total += max(0, int(count)) * ATTACK_VALUES[index]
        except (TypeError, ValueError):
            continue
    return total


class DuelHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_json(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/state":
            query = urllib.parse.parse_qs(parsed.query)
            room = room_for(query.get("room", ["ARCANE"])[0])
            player = query.get("player", [""])[0]
            self.send_json(self.state_payload(room, player))
            return
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/join":
            body = self.read_json()
            room = room_for(str(body.get("room", "ARCANE")))
            role = body.get("role")
            player = "p1" if role == "host" else "p2"
            if room["players"][player]["connected"] and time.time() - room["players"][player]["last_seen"] < 15:
                player = "p2" if player == "p1" else "p1"
            room["players"][player]["connected"] = True
            room["players"][player]["last_seen"] = time.time()
            self.send_json({"room": room["code"], "player": player, **self.state_payload(room, player)})
            return

        if parsed.path == "/api/cast":
            body = self.read_json()
            room = room_for(str(body.get("room", "ARCANE")))
            player = str(body.get("player", ""))
            if player not in room["players"]:
                self.send_json({"error": "unknown player"}, 400)
                return
            rival = "p2" if player == "p1" else "p1"
            room["players"][player]["connected"] = True
            room["players"][player]["last_seen"] = time.time()
            damage = damage_from_counts(body.get("counts", []))
            if damage > 0 and not room["winner"]:
                room["players"][rival]["hp"] = max(0, room["players"][rival]["hp"] - damage)
                if room["players"][rival]["hp"] <= 0:
                    room["winner"] = player
                event = {
                    "id": room["next_event"],
                    "player": player,
                    "spell": str(body.get("spell", "Spell")),
                    "damage": damage,
                }
                room["next_event"] += 1
                room["events"].append(event)
                room["events"] = room["events"][-8:]
            self.send_json(self.state_payload(room, player))
            return

        self.send_json({"error": "not found"}, 404)

    def state_payload(self, room, player):
        if player not in room["players"]:
            player = "p1"
        rival = "p2" if player == "p1" else "p1"
        now = time.time()
        for data in room["players"].values():
            if now - data["last_seen"] > 20:
                data["connected"] = False
        return {
            "room": room["code"],
            "you": room["players"][player],
            "rival": room["players"][rival],
            "events": room["events"],
            "winner": room["winner"],
        }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8770"))
    print(f"Arcane duel server running on port {port}")
    ThreadingHTTPServer(("0.0.0.0", port), DuelHandler).serve_forever()
