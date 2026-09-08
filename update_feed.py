import urllib.request
import xml.etree.ElementTree as ET
import re

SC_FEED_URL = "https://feeds.soundcloud.com/users/soundcloud:users:173046334/sounds.rss"
ARCHIV_URL = "https://raw.githubusercontent.com/KataHaifisch/podcast/main/katahaifisch_archiv.xml"
PODCAST_20MIN_FILE = "katahaifisch_podcasts.xml"
ALL_TRACKS_FILE = "applekatahaifisch_all.xml"

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

def extract_track_id(text):
    """Extrahiert die Ziffern-ID für zuverlässigen Duplikatsabgleich."""
    m = re.search(r"(\d{6,})", text)
    return m.group(1) if m else text.strip()

def clean_xml_content(xml_text):
    """Normalisiert GUIDs zu tag:soundcloud,2010:tracks/<id> und setzt 3000px Cover."""
    xml_text = re.sub(
        r"<guid([^>]*)>.*?(?:tracks[:/]|)(\d{6,})</guid>",
        r"<guid\1>tag:soundcloud,2010:tracks/\2</guid>",
        xml_text
    )
    return xml_text.replace("t500x500", "t3000x3000")

# 1. Aktuellen SoundCloud-Feed laden
req = urllib.request.Request(SC_FEED_URL, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    sc_xml = resp.read()
root_sc = ET.fromstring(sc_xml)
channel_sc = root_sc.find("channel")
ns = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}

# 2. Archiv laden (YouTube-Archiv wird nur gelesen, nie verändert)
try:
    req_arch = urllib.request.Request(ARCHIV_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_arch) as resp:
        arch_xml = resp.read().decode("utf-8")
    archive_items = re.findall(r"(<item>.*?</item>)", arch_xml, re.DOTALL)
except:
    archive_items = []

def process_feed(file_path, filter_20min=False):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    content = clean_xml_content(content)

    existing_guids = re.findall(r"<guid[^>]*>(.*?)</guid>", content, re.DOTALL)
    existing_ids = {extract_track_id(g) for g in existing_guids if g.strip()}

    new_items = []
    for item in channel_sc.findall("item"):
        guid_el = item.find("guid")
        guid_raw = guid_el.text.strip() if guid_el is not None else ""
        track_id = extract_track_id(guid_raw)

        if not track_id or track_id in existing_ids:
            continue

        dur_el = item.find("itunes:duration", ns)
        dur_sec = parse_duration(dur_el.text.strip()) if dur_el is not None else 0

        if filter_20min and dur_sec < 1200:
            continue

        title = item.find("title").text or ""
        desc_el = item.find("description")
        desc = desc_el.text if desc_el is not None and desc_el.text else title
        pub_date_el = item.find("pubDate")
        pub_date = pub_date_el.text if pub_date_el is not None and pub_date_el.text else ""

        enc = item.find("enclosure")
        enc_url = enc.attrib.get("url", "") if enc is not None else ""

        img = item.find("itunes:image", ns)
        img_url = img.attrib.get("href", "") if img is not None else ""
        img_url = img_url.replace("t500x500", "t3000x3000")

        canonical_guid = f"tag:soundcloud,2010:tracks/{track_id}"

        item_xml = f"""    <item>
      <title><![CDATA[{title}]]></title>
      <description><![CDATA[{desc}]]></description>
      <pubDate>{pub_date}</pubDate>
      <guid isPermaLink="false">{canonical_guid}</guid>
      <enclosure url="{enc_url}" length="0" type="audio/mpeg"/>
      <itunes:duration>{dur_sec}</itunes:duration>
      <itunes:image href="{img_url}"/>
    </item>"""
        new_items.append(item_xml)
        existing_ids.add(track_id)

    extra_archive = []
    if not filter_20min:
        for it in archive_items:
            g = re.search(r"<guid[^>]*>(.*?)</guid>", it)
            if g:
                arch_track_id = extract_track_id(g.group(1))
                if arch_track_id not in existing_ids:
                    extra_archive.append(clean_xml_content(it))
                    existing_ids.add(arch_track_id)

    # Neue Episoden oben vor dem ersten <item> einfügen
    if new_items:
        first_item_match = re.search(r"(\s*<item>)", content)
        if first_item_match:
            pos = first_item_match.start()
            content = content[:pos] + "\n" + "\n".join(new_items) + content[pos:]
        else:
            channel_end = content.rfind("</channel>")
            if channel_end != -1:
                content = content[:channel_end] + "\n".join(new_items) + "\n  " + content[channel_end:]

    # Fehlende Archivfolgen unten vor </channel> anfügen
    if extra_archive:
        channel_end = content.rfind("</channel>")
        if channel_end != -1:
            content = content[:channel_end] + "\n".join(extra_archive) + "\n  " + content[channel_end:]

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

process_feed(ALL_TRACKS_FILE, filter_20min=False)
process_feed(PODCAST_20MIN_FILE, filter_20min=True)
print("Feeds für Apple und Amazon erfolgreich aktualisiert!")
