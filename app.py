from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError
import os

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ['LINE_CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])

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
    input_text = event.message.text.strip()
    
    # 入力が16進数か日本語かを判定
    try:
        # 16進数をデコード
        decoded_text = bytes.fromhex(input_text).decode('utf-8')
        reply_text_1 = f"デコード結果："
        reply_text_2 = decoded_text
    except ValueError:
        # 16進数ではない場合（日本語と仮定して16進数にエンコード）
        try:
            encoded_hex = input_text.encode('utf-8').hex()
            reply_text_1 = f"エンコード結果："
            reply_text_2 = encoded_hex
        except Exception as e:
            reply_text_1 = f"エンコードに失敗しました:"
            reply_text_2 = str(e)

    line_bot_api.reply_message(
        event.reply_token,
        [TextSendMessage(text=reply_text_1), TextSendMessage(text=reply_text_2)]
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
