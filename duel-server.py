from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json
import os
import time
import urllib.parse


ROOT = Path(__file__).resolve().parent
STARTING_LIFE = 10
ROUND_SECONDS = 5
rooms = {}

BEATS = {
    "Flame": {"Frost", "Storm"},
    "Frost": {"Storm", "Water"},
    "Storm": {"Water", "Lightning"},
    "Water": {"Lightning", "Earth"},
    "Lightning": {"Earth", "Flame"},
    "Earth": {"Flame", "Frost"},
}


def new_room(code):
    return {
        "code": code,
        "players": {
            "p1": {"connected": False, "life": STARTING_LIFE, "last_seen": 0},
            "p2": {"connected": False, "life": STARTING_LIFE, "last_seen": 0},
        },
        "round": None,
        "events": [],
        "next_event": 1,
        "next_round": 1,
        "next_round_at": 0,
        "winner": "",
    }


def room_for(code):
    clean = "".join(ch for ch in code.upper() if ch.isalnum())[:8] or "ARCANE"
    if clean not in rooms:
        rooms[clean] = new_room(clean)
    return rooms[clean]


def connected_count(room, now):
    return sum(1 for data in room["players"].values() if now - data["last_seen"] <= 20)


def server_connected_count(now):
    return sum(connected_count(room, now) for room in rooms.values())


def public_submission(submission):
    if not submission:
        return {"status": "waiting", "spell": ""}
    return {
        "status": submission.get("status", "waiting"),
        "spell": submission.get("spell", ""),
    }


def start_round(room, now):
    if room["winner"] or connected_count(room, now) < 2:
        return
    if now < room.get("next_round_at", 0):
        return
    if room["round"] and not room["round"].get("resolved"):
        return
    room["round"] = {
        "id": room["next_round"],
        "started_at": now,
        "deadline": now + ROUND_SECONDS,
        "submissions": {},
        "resolved": False,
    }
    room["next_round"] += 1


def round_result(p1, p2):
    s1 = p1.get("status", "timeout")
    s2 = p2.get("status", "timeout")
    if s1 != "valid" and s2 != "valid":
        return None, 0, "Both failed. Draw."
    if s1 == "valid" and s2 != "valid":
        penalty = 2 if s2 == "timeout" else 1
        return "p2", penalty, f"{p1['spell']} wins. Player 2 loses {penalty} life."
    if s2 == "valid" and s1 != "valid":
        penalty = 2 if s1 == "timeout" else 1
        return "p1", penalty, f"{p2['spell']} wins. Player 1 loses {penalty} life."
    if p1["spell"] == p2["spell"]:
        return None, 0, f"Both cast {p1['spell']}. Draw."
    if p2["spell"] in BEATS.get(p1["spell"], set()):
        return "p2", 1, f"{p1['spell']} beats {p2['spell']}. Player 2 loses 1 life."
    if p1["spell"] in BEATS.get(p2["spell"], set()):
        return "p1", 1, f"{p2['spell']} beats {p1['spell']}. Player 1 loses 1 life."
    return None, 0, f"{p1['spell']} and {p2['spell']} cancel. Draw."


def resolve_round(room, now):
    round_data = room.get("round")
    if not round_data or round_data.get("resolved"):
        return
    submissions = round_data["submissions"]
    if len(submissions) < 2 and now < round_data["deadline"]:
        return

    p1 = submissions.get("p1", {"status": "timeout", "spell": ""})
    p2 = submissions.get("p2", {"status": "timeout", "spell": ""})
    loser, penalty, message = round_result(p1, p2)
    if loser and penalty:
        room["players"][loser]["life"] = max(0, room["players"][loser]["life"] - penalty)
        if room["players"][loser]["life"] <= 0:
            room["winner"] = "p2" if loser == "p1" else "p1"

    event = {
        "id": room["next_event"],
        "round": round_data["id"],
        "message": message,
        "p1": public_submission(p1),
        "p2": public_submission(p2),
        "winner": room["winner"],
    }
    room["next_event"] += 1
    room["events"].append(event)
    room["events"] = room["events"][-10:]
    round_data["resolved"] = True
    room["next_round_at"] = now + 2.5


class DuelHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format, *args):
        return

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
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/state":
            query = urllib.parse.parse_qs(parsed.query)
            room = room_for(query.get("room", ["ARCANE"])[0])
            player = query.get("player", [""])[0]
            if player in room["players"]:
                room["players"][player]["connected"] = True
                room["players"][player]["last_seen"] = time.time()
            self.send_json(self.state_payload(room, player))
            return
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/join":
            body = self.read_json()
            room_code = "".join(ch for ch in str(body.get("room", "ARCANE")).upper() if ch.isalnum())[:8] or "ARCANE"
            if body.get("reset"):
                rooms[room_code] = new_room(room_code)
            room = room_for(room_code)
            role = body.get("role")
            player = "p1" if role == "host" else "p2"
            if room["players"][player]["connected"] and time.time() - room["players"][player]["last_seen"] < 15:
                player = "p2" if player == "p1" else "p1"
            room["players"][player]["connected"] = True
            room["players"][player]["last_seen"] = time.time()
            self.send_json({"room": room["code"], "player": player, **self.state_payload(room, player)})
            return

        if parsed.path == "/api/submit":
            body = self.read_json()
            room = room_for(str(body.get("room", "ARCANE")))
            player = str(body.get("player", ""))
            if player not in room["players"]:
                self.send_json({"error": "unknown player"}, 400)
                return
            room["players"][player]["connected"] = True
            room["players"][player]["last_seen"] = time.time()
            now = time.time()
            resolve_round(room, now)
            round_data = room.get("round")
            if not room["winner"] and round_data and not round_data.get("resolved") and now <= round_data["deadline"]:
                status = str(body.get("status", "miscast"))
                if status not in {"valid", "miscast"}:
                    status = "miscast"
                spell = str(body.get("spell", "")) if status == "valid" else ""
                round_data["submissions"].setdefault(player, {"status": status, "spell": spell})
                resolve_round(room, now)
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
        resolve_round(room, now)
        start_round(room, now)
        round_data = room.get("round")
        room_users = connected_count(room, now)
        payload_round = None
        if round_data and not round_data.get("resolved"):
            payload_round = {
                "id": round_data["id"],
                "deadline": round_data["deadline"],
                "remaining": max(0, round_data["deadline"] - now),
                "youSubmitted": player in round_data["submissions"],
                "rivalSubmitted": rival in round_data["submissions"],
            }
        return {
            "room": room["code"],
            "you": room["players"][player],
            "rival": room["players"][rival],
            "round": payload_round,
            "roomUsers": room_users,
            "serverUsers": server_connected_count(now),
            "events": room["events"],
            "winner": room["winner"],
            "rules": {
                "startingLife": STARTING_LIFE,
                "roundSeconds": ROUND_SECONDS,
                "beats": {spell: sorted(beats) for spell, beats in BEATS.items()},
            },
        }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8770"))
    print(f"Arcane duel server running on port {port}")
    ThreadingHTTPServer(("0.0.0.0", port), DuelHandler).serve_forever()
