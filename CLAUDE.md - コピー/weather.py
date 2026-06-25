import requests
import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# APIキーを環境変数から取得
API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

def get_weather(city: str) -> dict:
    """指定した都市の天気情報を取得する"""
    # リクエストパラメータを組み立てる
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric",  # 摂氏で取得
        "lang": "ja",       # 天気の説明を日本語で取得
    }

    # APIにリクエストを送信する
    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()
    return response.json()

def display_weather(city: str) -> None:
    """天気情報を整形して表示する"""
    data = get_weather(city)

    # 必要な情報を取り出す
    weather_desc = data["weather"][0]["description"]
    temp = data["main"]["temp"]
    humidity = data["main"]["humidity"]

    print(f"都市: {city}")
    print(f"天気: {weather_desc}")
    print(f"気温: {temp}°C")
    print(f"湿度: {humidity}%")

if __name__ == "__main__":
    display_weather("Tokyo")
