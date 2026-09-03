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

# 1. Aktuellen SoundCloud-Feed laden
req = urllib.request.Request(SC_FEED_URL, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    sc_xml = resp.read()
root_sc = ET.fromstring(sc_xml)
channel_sc = root_sc.find("channel")
ns = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}

# 2. Archiv-XML (ältere Folgen) laden
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

    # Alle 500x500 Bild-Links automatisch auf hochauflösende 3000x3000px upgraden
    content = content.replace("t500x500", "t3000x3000")

    existing_guids = set(re.findall(r"<guid[^>]*>(.*?)</guid>", content, re.DOTALL))
    new_items = []

    for item in channel_sc.findall("item"):
        guid_el = item.find("guid")
        guid = guid_el.text.strip() if guid_el is not None else ""

        if not guid or guid in existing_guids:
            continue

        dur_el = item.find("itunes:duration", ns)
        dur_sec = parse_duration(dur_el.text.strip()) if dur_el is not None else 0

        if filter_20min and dur_sec < 1200:
            continue

        title = item.find("title").text or ""
        desc = item.find("description").text or title if item.find("description") is not None else title
        pub_date = item.find("pubDate").text or "" if item.find("pubDate") is not None else ""

        enc = item.find("enclosure")
        enc_url = enc.attrib.get("url", "") if enc is not None else ""

        img = item.find("itunes:image", ns)
        img_url = img.attrib.get("href", "") if img is not None else ""
        img_url = img_url.replace("t500x500", "t3000x3000")

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
        existing_guids.add(guid)

    extra_archive = []
    if not filter_20min:
        for it in archive_items:
            g = re.search(r"<guid[^>]*>(.*?)</guid>", it)
            if g and g.group(1).strip() not in existing_guids:
                it_upgraded = it.replace("t500x500", "t3000x3000")
                extra_archive.append("    " + it_upgraded.strip())
                existing_guids.add(g.group(1).strip())

    total_to_add = new_items + extra_archive
    updated = content
    if total_to_add:
        pos = updated.find("<item>")
        if pos != -1:
            updated = updated[:pos] + "\n".join(new_items) + "\n" + updated[pos:]
            if extra_archive:
                end_pos = updated.rfind("</channel>")
                updated = updated[:end_pos] + "\n".join(extra_archive) + "\n  " + updated[end_pos:]
        else:
            end_pos = updated.find("</channel>")
            updated = updated[:end_pos] + "\n".join(total_to_add) + "\n  " + content[end_pos:]

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(updated)
    print(f"{file_path} verarbeitet.")

process_feed(PODCAST_20MIN_FILE, filter_20min=True)
process_feed(ALL_TRACKS_FILE, filter_20min=False)
