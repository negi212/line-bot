from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError
import os

app = Flask(__name__)

# 環境変数からトークンとシークレットを取得
line_bot_api = LineBotApi("r8pZIxjH2G/npqA6gSivb1aey176KncgOtrrTbtUdCXUbO93EdFX/PhMMtZr8XB4g2AHWCWaS1lO32TjWT23k/ALB4v/lQIrfJdKescVL+ZezeN4NW9zIQnROFoPJxWU4JU0U8y2gjIcInpp6qz0fAdB04t89/1O/w1cDnyilFU=")
handler = WebhookHandler("d330e551cb13fbc77eb4d4554b83201c")

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    reply_text = f"「{event.message.text}」を受け取りました！"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()
