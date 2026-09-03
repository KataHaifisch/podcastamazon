import urllib.request
import xml.etree.ElementTree as ET
import re

# Trage hier deine SoundCloud-RSS-URL ein:
SC_FEED_URL = "https://feeds.soundcloud.com/users/soundcloud:users:173046334/sounds.rss"
PODCAST_FILE = "katahaifisch_podcasts.xml"

def parse_duration(dur_str):
    if not dur_str:
        return 0
    if ":" in dur_str:
        parts = [int(p) for p in dur_str.split(":")]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    try:
        return int(dur_str)
    except:
        return 0

# 1. Bestehende GUIDs aus der Datei laden
with open(PODCAST_FILE, "r", encoding="utf-8") as f:
    content = f.read()

existing_guids = set(re.findall(r"<guid[^>]*>(.*?)</guid>", content, re.DOTALL))

# 2. SoundCloud RSS Feed abrufen
req = urllib.request.Request(SC_FEED_URL, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    sc_xml = resp.read()

root = ET.fromstring(sc_xml)
channel = root.find("channel")
ns = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}

new_items = []
for item in channel.findall("item"):
    guid_el = item.find("guid")
    guid = guid_el.text.strip() if guid_el is not None else ""

    if not guid or guid in existing_guids:
        continue

    dur_el = item.find("itunes:duration", ns)
    dur_sec = parse_duration(dur_el.text.strip()) if dur_el is not None else 0

    # Nur Tracks ab 20 Minuten (1200 Sekunden)
    if dur_sec >= 1200:
        title = item.find("title").text or ""
        desc = item.find("description").text or title if item.find("description") is not None else title
        pub_date = item.find("pubDate").text or "" if item.find("pubDate") is not None else ""

        enc = item.find("enclosure")
        enc_url = enc.attrib.get("url", "") if enc is not None else ""

        img = item.find("itunes:image", ns)
        img_url = img.attrib.get("href", "") if img is not None else ""

        item_xml = f"""    <item>
      <title><![CDATA[{title}]]></title>
      <description><![CDATA[{desc}]]></description>
      <pubDate>{pub_date}</pubDate>
      <guid isPermaLink="false">{guid}</guid>
      <enclosure url="{enc_url}" length="0" type="audio/mpeg"/>
      <itunes:duration>{dur_sec}</itunes:duration>
      <itunes:image href="{img_url}"/>
    </item>"""
        new_items.append(item_xml)

# 3. Neue Episoden oben einfügen
if new_items:
    print(f"{len(new_items)} neue Folge(n) gefunden. Ergänze Datei...")
    pos = content.find("<item>")
    if pos != -1:
        updated_content = content[:pos] + "\n".join(new_items) + "\n" + content[pos:]
    else:
        pos = content.find("</channel>")
        updated_content = content[:pos] + "\n".join(new_items) + "\n" + content[pos:]

    with open(PODCAST_FILE, "w", encoding="utf-8") as f:
        f.write(updated_content)
else:
    print("Keine neuen Sets vorhanden. Datei bleibt unverändert.")
