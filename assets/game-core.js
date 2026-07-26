window.GAME_CORE = {
  "config": {
    "startingLife": 10,
    "roundSeconds": 5,
    "connectionTimeout": 90,
    "penalties": {
      "miscast": 1,
      "timeout": 2
    }
  },
  "wheel": ["Flame", "Frost", "Water", "Lightning", "Storm", "Earth"],
  "matchups": {
    "Flame": ["Frost", "Water"],
    "Frost": ["Water", "Lightning"],
    "Water": ["Lightning", "Storm"],
    "Lightning": ["Storm", "Earth"],
    "Storm": ["Earth", "Flame"],
    "Earth": ["Flame", "Frost"]
  },
  "spells": [
    {
      "id": "flame1",
      "name": "Flame",
      "level": 1,
      "color": "#ff6a2a",
      "pattern": [7, 2, 9, 5, 7],
      "spellImage": "assets/spells/flame.png",
      "elementImage": "assets/elements/flame.jpeg"
    },
    {
      "id": "frost1",
      "name": "Frost",
      "level": 1,
      "color": "#79d7ff",
      "pattern": [2, 4, 8, 6, 2],
      "spellImage": "assets/spells/frost.png",
      "elementImage": "assets/elements/frost.jpeg"
    },
    {
      "id": "storm1",
      "name": "Storm",
      "level": 1,
      "color": "#ffd25f",
      "pattern": [9, 8, 7, 4, 1, 2, 3, 6, 5],
      "spellImage": "assets/spells/storm.png",
      "elementImage": "assets/elements/storm.jpeg"
    },
    {
      "id": "water1",
      "name": "Water",
      "level": 1,
      "color": "#4fb7ff",
      "pattern": [7, 4, 5, 6, 9, 5, 7],
      "spellImage": "assets/spells/water.png",
      "elementImage": "assets/elements/water.jpeg"
    },
    {
      "id": "lightning1",
      "name": "Lightning",
      "level": 1,
      "color": "#f6ff5b",
      "pattern": [2, 4, 5, 6, 8],
      "spellImage": "assets/spells/lightning.png",
      "elementImage": "assets/elements/lightning.jpeg"
    },
    {
      "id": "earth1",
      "name": "Earth",
      "level": 1,
      "color": "#88d071",
      "pattern": [4, 5, 6, 9, 8, 7, 4],
      "spellImage": "assets/spells/earth.png",
      "elementImage": "assets/elements/earth.jpeg"
    }
  ]
};
