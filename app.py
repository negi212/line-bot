from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import re
import os

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

supported_encodings = [
    "utf-8", "utf-16", "utf-16-le", "utf-16-be",
    "utf-32", "utf-32-le", "utf-32-be",
    "shift_jis"
]

def score_natural_text(text: str) -> int:
    score = 0
    score += len(re.findall(r'[ぁ-んァ-ヶー一-龯]', text)) * 3              # 全角日本語文字
    score += len(re.findall(r'[ｦ-ﾟ]', text)) * 2                            # 半角カタカナ
    score += len(re.findall(r'[a-zA-Z]', text)) * 2                         # アルファベット
    score += len(re.findall(r'[0-9]', text)) * 1                            # 数字
    score += len(re.findall(r'[.,!?。、！？\s\-+*/=()\[\]{}<>@#$%^&~_]', text)) * 1  # 記号・句読点・スペース
    score += len(re.findall(r'[\U0001F300-\U0001FAFF]', text)) * 5        # 絵文字ブロック（絵文字のスコア大）
    score -= len(re.findall(r'[^\x20-\x7Eぁ-んァ-ヶー一-龯ｦ-ﾟ.,!?。、！？\s\-+*/=()\[\]{}<>@#$%^&~_\U0001F300-\U0001FAFF]', text)) * 5  # 不明文字で減点
    return score

def smart_decode(hex_str: str) -> tuple[str, str] | tuple[str, None]:
    candidates = []
    raw_bytes = bytes.fromhex(hex_str)
    for enc in supported_encodings:
        try:
            decoded = raw_bytes.decode(enc)
            score = score_natural_text(decoded)
            candidates.append((score, enc, decoded))
        except Exception:
            continue

    if candidates:
        best = max(candidates, key=lambda x: x[0])
        return best[1], best[2]
    else:
        return "unknown", None

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    input_text = event.message.text
    # --- エンコード（-f オプション付き） ---
    if " -f " in input_text:
        try:
            main_text, option = input_text.rsplit(" -f ", 1)
            encoding = option.lower()
            if encoding not in supported_encodings:
                reply = f"対応していないエンコーディングです: {encoding}\n対応可能: {', '.join(supported_encodings)}"
            else:
                encoded = main_text.encode(encoding).hex()
                reply = encoded
        except Exception as e:
            reply = f"エンコードに失敗しました：{str(e)}"

    # --- デコード（自動判別） ---
    elif all(c in "0123456789abcdefABCDEF" for c in input_text) and len(input_text) % 2 == 0:
        try:
            enc, decoded = smart_decode(input_text)
            if decoded is None:
                reply = "デコードに失敗しました。UTF-8, UTF-16, UTF-32, Shift_JIS 全て失敗または不自然でした。"
            else:
                reply = decoded
        except Exception as e:
            reply = f"デコード処理中にエラーが発生しました：{str(e)}"

    # --- 不正な形式 ---
    else:
        reply = "形式が正しくありません。\n例：こんにちは -f utf-8（エンコード）\nまたは 16進数（自動デコード）"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
