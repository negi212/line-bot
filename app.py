from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, QuickReply, QuickReplyButton, MessageAction
import re
import os

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

supported_encodings = {
    "8": "utf-8",
    "16": "utf-16",
    "16l": "utf-16-le",
    "16b": "utf-16-be",
    "32": "utf-32",
    "32l": "utf-32-le",
    "32b": "utf-32-be",
    "s": "shift_jis"
}

def score_natural_text(text: str) -> int:
    score = 0
    score += len(re.findall(r'[ぁ-んァ-ヶー一-龯]', text)) * 3
    score += len(re.findall(r'[ｦ-ﾟ]', text)) * 2
    score += len(re.findall(r'[a-zA-Z]', text)) * 2
    score += len(re.findall(r'[0-9]', text)) * 1
    score += len(re.findall(r'[.,!?。、！？\s\-+*/=()\[\]{}<>@#$%^&~_]', text)) * 1
    score += len(re.findall(r'[\U0001F300-\U0001FAFF]', text)) * 5
    score -= len(re.findall(r'[^\x20-\x7Eぁ-んァ-ヶー一-龯ｦ-ﾟ.,!?。、！？\s\-+*/=()\[\]{}<>@#$%^&~_\U0001F300-\U0001FAFF]', text)) * 5
    return score

def smart_decode(hex_str: str) -> tuple[str, str] | tuple[str, None]:
    candidates = []
    raw_bytes = bytes.fromhex(hex_str)
    for enc in supported_encodings.values():
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
    input_text = event.message.text.strip()

    # --- エンコード（末尾にコード） ---
    if " " in input_text:
        try:
            main_text, code = input_text.rsplit(" ", 1)
            encoding = supported_encodings.get(code.lower())
            if not encoding:
                reply = "対応していないコードです。使えるのは: " + ", ".join(supported_encodings.keys())
            else:
                encoded = main_text.encode(encoding).hex()
                reply = encoded
        except Exception as e:
            reply = "エンコードに失敗しました。"

    # --- デコード（自動判別） ---
    elif all(c in "0123456789abcdefABCDEF" for c in input_text) and len(input_text) % 2 == 0:
        try:
            enc, decoded = smart_decode(input_text)
            if decoded is None:
                reply = "デコードに失敗しました。"
            else:
                reply = decoded
        except Exception:
            reply = "デコード処理中にエラーが発生しました。"

    # --- クイックリプライによる文字コード選択誘導 ---
    elif input_text and " " not in input_text:
        quick_reply = QuickReply(items=[
            QuickReplyButton(action=MessageAction(label="UTF-8", text=f"{input_text} 8")),
            QuickReplyButton(action=MessageAction(label="UTF-16", text=f"{input_text} 16")),
            QuickReplyButton(action=MessageAction(label="UTF-16LE", text=f"{input_text} 16l")),
            QuickReplyButton(action=MessageAction(label="UTF-16BE", text=f"{input_text} 16b")),
            QuickReplyButton(action=MessageAction(label="UTF-32", text=f"{input_text} 32")),
            QuickReplyButton(action=MessageAction(label="UTF-32LE", text=f"{input_text} 32l")),
            QuickReplyButton(action=MessageAction(label="UTF-32BE", text=f"{input_text} 32b")),
            QuickReplyButton(action=MessageAction(label="Shift_JIS", text=f"{input_text} s")),
        ])
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="文字コードを選んでください：", quick_reply=quick_reply)
        )
        return

    # --- その他の形式は不正 ---
    else:
        reply = "形式が正しくありません。"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
