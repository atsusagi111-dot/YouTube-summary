import os
import sys
import re
import json
import pathlib
import urllib.request
from datetime import datetime, timezone, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from openai import OpenAI

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

SCRIPT_DIR = pathlib.Path(__file__).parent
LAST_VIDEO_ID_FILE = SCRIPT_DIR / "last_video_id.txt"


def load_env(path):
    env = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return env


ENV_PATH = SCRIPT_DIR / "CLAUDE.md - コピー" / ".env"
env = load_env(str(ENV_PATH))

YOUTUBE_API_KEY = (
    os.environ.get("YOUTUBE_API_KEY")
    or env.get("YOUTUBE_API_KEY")
    or "AIzaSyAE8ujqK0-2azhJV0ApFvFkGQmRg8eIpQo"
)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or env.get("OPENAI_API_KEY")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL") or env.get("DISCORD_WEBHOOK_URL")
SEARCH_KEYWORD = "フィリピン マニラ"


def load_last_video_id():
    try:
        return LAST_VIDEO_ID_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def save_last_video_id(video_id):
    LAST_VIDEO_ID_FILE.write_text(video_id, encoding="utf-8")


def parse_duration(duration_str):
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    if not match:
        return 0, 0, 0
    return int(match.group(1) or 0), int(match.group(2) or 0), int(match.group(3) or 0)


def send_to_discord(webhook_url, message):
    payload = json.dumps({"content": message}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "DiscordBot (custom, 1.0)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as res:
            return res.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise RuntimeError(f"Discord送信失敗 HTTP {e.code}: {body}") from e


def summarize_with_openai(client, title, description, channel_title):
    prompt = f"""以下のYouTube動画情報を分析し、必ずJSON形式のみで返してください。

動画タイトル: {title}
チャンネル名: {channel_title}
動画説明文: {description[:1000] if description else "説明文なし"}

{{
  "title_summary": "タイトルを10文字以内の日本語で要約（日本語でない場合は翻訳）",
  "content": "動画内容を日本語で200文字以内で説明",
  "topics": ["トピック1", "トピック2", "トピック3"]
}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content


def main():
    if not OPENAI_API_KEY:
        print("エラー: OPENAI_API_KEY が設定されていません。", file=sys.stderr)
        sys.exit(1)

    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    # 最新1件を検索
    search_res = youtube.search().list(
        part="snippet",
        q=SEARCH_KEYWORD,
        type="video",
        maxResults=1,
        order="date",
    ).execute()

    items = search_res.get("items", [])
    if not items:
        print("動画が見つかりませんでした。")
        return

    video_id = items[0]["id"]["videoId"]

    # 新着チェック
    last_id = load_last_video_id()
    if video_id == last_id:
        print("新着動画なし。")
        return

    # 動画詳細取得
    detail_res = youtube.videos().list(
        part="snippet,contentDetails",
        id=video_id,
    ).execute()
    detail = detail_res.get("items", [None])[0]
    if not detail:
        print("動画詳細の取得に失敗しました。")
        return

    snippet = detail["snippet"]
    title = snippet["title"]
    description = snippet.get("description", "")
    channel_title = snippet.get("channelTitle", "")
    published_at = snippet["publishedAt"]
    duration_str = detail["contentDetails"]["duration"]

    # 公開日時 → 日本時間
    jst = timezone(timedelta(hours=9))
    dt_jst = datetime.fromisoformat(published_at.replace("Z", "+00:00")).astimezone(jst)
    published_display = f"{dt_jst.month}月{dt_jst.day}日{dt_jst.hour}:{dt_jst.minute:02d}"

    # 動画時間
    h, m, s = parse_duration(duration_str)
    duration_display = f"{h}時間{m}分{s}秒"

    # OpenAI で要約
    client = OpenAI(api_key=OPENAI_API_KEY)
    raw = summarize_with_openai(client, title, description, channel_title)

    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        data = json.loads(json_match.group())
    else:
        data = {"title_summary": title[:10], "content": description[:200], "topics": []}

    title_summary = data.get("title_summary", title[:10])
    content = data.get("content", "")
    topics = data.get("topics", [])

    url = f"https://www.youtube.com/watch?v={video_id}"
    topics_text = "\n".join(f"・{t}" for t in topics)

    output = (
        f"\n【タイトル】\n{title_summary}\n"
        f"\n【URL】\n{url}\n"
        f"\n【動画内容】\n{content}\n"
        f"\n【トピック】\n{topics_text}\n"
        f"\n【公開日時】\n{published_display}\n"
        f"\n【動画時間】\n{duration_display}\n"
    )

    print(output)

    # Discord 送信
    if DISCORD_WEBHOOK_URL:
        send_to_discord(DISCORD_WEBHOOK_URL, output)
        print("Discordに送信しました。")

    # 最新動画IDを保存
    save_last_video_id(video_id)


if __name__ == "__main__":
    main()
