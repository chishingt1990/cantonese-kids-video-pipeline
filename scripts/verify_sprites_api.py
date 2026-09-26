import urllib.request
import json

url = "http://127.0.0.1:8000/api/characters/all"
try:
    response = urllib.request.urlopen(url)
    data = json.loads(response.read().decode("utf-8"))
    characters = data.get("characters", data)
    print(f"Successfully loaded {len(characters)} characters from {url}:")
    for char in characters:
        pose_ids = [p["id"] for p in char.get("poses", [])]
        print(f"  - {char['name']}: {len(pose_ids)} poses -> {', '.join(pose_ids)}")
except Exception as e:
    print(f"Error fetching {url}: {e}")
