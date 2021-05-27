from telegram import ParseMode, Update
from telegram.ext import CallbackContext, ConversationHandler

from app.decorators import register_update


@register_update
def sources_callback(update: Update, context: CallbackContext, chat_info: dict):
    update.message.reply_text(
        disable_web_page_preview=True,
        parse_mode=ParseMode.MARKDOWN,
        text="""*Sources*

https://bitfinex.com - 15min (API limits😭)
[https://bittrex.com](https://bittrex.com/Account/Register?referralCode=YIV-CNI-13Q)- 1min
[https://satang.pro](https://satang.pro/signup?referral=STZ3EEU2) - 1min
[https://bitkub.com](https://www.bitkub.com/signup?ref=64572) - 1min
https://sp-today.com - Aleppo - 60min
https://fixer.io - 3hour
https://openexchangerates.org - 60min""",
    )

    return ConversationHandler.END
