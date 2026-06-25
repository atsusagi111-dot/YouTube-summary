"""
YouTube Data API v3 を使った動画検索プログラム

【必要なライブラリのインストール手順】
1. ターミナル（PowerShell や コマンドプロンプト）を開く
2. このファイルがあるフォルダに移動する
3. 次のコマンドを実行する:
       pip install google-api-python-client
【APIキーの設定方法】
Google Cloud Console で YouTube Data API v3 を有効化し、APIキーを取得してください。
次のいずれかの方法でキーを設定します。

  方法A: 環境変数に設定（推奨）
    PowerShell の例:
      $env:YOUTUBE_API_KEY = "AIzaSyAE8ujqK0-2azhJV0ApFvFkGQmRg8eIpQo"

  方法B: 下の API_KEY 変数に直接文字列を入力する
"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 検索キーワード（課題で指定された文字列）
SEARCH_KEYWORD = "フィリピン マニラ"

# 取得する最大件数（10件を超える場合は新しい順で10件のみ）
MAX_RESULTS = 10

# 方法B を使う場合は、ここに API キーを入力してください（例: "AIzaSy..."）
API_KEY = "AIzaSyAE8ujqK0-2azhJV0ApFvFkGQmRg8eIpQo"


def get_api_key():
    """
    APIキーを取得する。
    環境変数 YOUTUBE_API_KEY を優先し、未設定なら API_KEY 変数を使う。
    """
    api_key = os.environ.get("YOUTUBE_API_KEY") or API_KEY
    if not api_key:
        raise ValueError(
            "APIキーが設定されていません。\n"
            "  ・環境変数 YOUTUBE_API_KEY にキーを設定する\n"
            "  ・または、このファイルの API_KEY 変数にキーを入力する"
        )
    return api_key


def search_videos(api_key):
    """
    キーワードで動画を検索し、公開日時が新しい順に最大10件返す。
    """
    # YouTube Data API v3 のクライアントを API キーで作成
    youtube = build("youtube", "v3", developerKey=api_key)

    # 検索リクエスト（order=date で新しい動画から取得）
    request = youtube.search().list(
        part="snippet",           # タイトルなどの基本情報を取得
        q=SEARCH_KEYWORD,         # 検索キーワード
        type="video",             # 動画のみ対象
        maxResults=MAX_RESULTS,   # 最大10件
        order="date",             # 公開日時が新しい順
    )
    response = request.execute()
    return response.get("items", [])


def main():
    try:
        api_key = get_api_key()
        items = search_videos(api_key)

        # 検索結果を1件ずつ、番号付きで表示
        for number, item in enumerate(items, start=1):
            snippet = item["snippet"]
            video_id = item["id"]["videoId"]
            title = snippet["title"]
            url = f"https://www.youtube.com/watch?v={video_id}"

            print(f"{number}. {title}")
            print(f"   {url}")

        # 取得件数を表示
        count = len(items)
        print(f"取得件数：{count}件")

    except ValueError as e:
        # APIキー未設定など、設定ミスによるエラー
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)

    except HttpError as e:
        # YouTube API からの HTTP エラー（キー無効、クォータ超過など）
        status = e.resp.status if e.resp else "不明"
        print("エラー: YouTube Data API へのリクエストに失敗しました。", file=sys.stderr)
        print(f"  HTTPステータス: {status}", file=sys.stderr)
        print(f"  詳細: {e}", file=sys.stderr)
        if status == 403:
            print(
                "  考えられる原因: APIキーが無効、APIが未有効化、または利用上限に達しています。",
                file=sys.stderr,
            )
        elif status == 400:
            print("  考えられる原因: リクエストの内容に誤りがあります。", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        # ネットワーク障害など、その他のエラー
        print("エラー: 予期しない問題が発生しました。", file=sys.stderr)
        print(f"  原因: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
