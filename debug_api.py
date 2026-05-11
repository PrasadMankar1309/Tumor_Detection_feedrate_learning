import requests
from PIL import Image
import numpy as np
import json

# create a dummy image
img = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
img.save("dummy.jpg")

# send request
with open("dummy.jpg", "rb") as f:
    resp = requests.post("http://127.0.0.1:5000/api/predict", files={"file": ("dummy.jpg", f)})

print("Status Code:", resp.status_code)
# We only want to print first 500 chars if the heatmap is huge, but we must see if 'error' is in it.
try:
    data = resp.json()
    if "heatmap_b64" in data:
        data["heatmap_b64"] = "TRUNCATED_B64"
    print("JSON:", json.dumps(data, indent=2))
except Exception as e:
    print("Failed to decode json:", e)
    print("Text:", resp.text[:1000])
