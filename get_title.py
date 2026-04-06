import urllib.request, json

url = "https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=uboqyhorx2A&format=json"
req = urllib.request.Request(url)
with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    print(data.get('title', ''))
