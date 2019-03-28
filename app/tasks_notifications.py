import logging
from decimal import Decimal

import telegram
import transaction
from celery_once import QueueOnce
from pyramid_sqlalchemy import Session
from sqlalchemy import true, false
from telegram import ParseMode
from telegram.error import RetryAfter, TimedOut
from suite.conf import settings

from . import translations
from app.celery import celery_app
from app.converter.converter import convert
from app.converter.formatter import NotifyFormatPriceRequestResult
from app.models import Notification, Currency, NotifyTriggerClauseEnum
from app.parsers.base import PriceRequest


def is_triggered(trigger_clause: str, trigger_value: Decimal, last_rate: Decimal, current_rate: Decimal):
    if trigger_clause == NotifyTriggerClauseEnum.more:
        return current_rate >= last_rate

    elif trigger_clause == NotifyTriggerClauseEnum.less:
        return current_rate <= last_rate

    elif trigger_clause == NotifyTriggerClauseEnum.diff:
        return abs(last_rate - current_rate) >= trigger_value

    elif trigger_clause == NotifyTriggerClauseEnum.percent:
        return abs(last_rate - current_rate) / last_rate * Decimal('100') >= trigger_value

    else:
        raise NotImplemented


def notification_auto_disable(pair: list):
    # TODO: modify decorator, in personal_settings
    _ = translations['en'].gettext

    db_session = Session()

    notifications = db_session.query(
        Notification
    ).filter_by(
        is_active=true(),
        from_currency_id=pair[0],
        to_currency_id=pair[1]
    ).all()

    for n in notifications:
        send_notification(
            n.chat_id,
            _('Your notification has been disabled, due to one of the currencies %(from_currency)s %(to_currency)s has been deactivated.') % {  # NOQA
                'from_currency': n.from_currency.code, 'to_currency': n.to_currency.code
            }
        )

    db_session.query(
        Notification
    ).filter_by(
        is_active=true(),
        from_currency_id=pair[0],
        to_currency_id=pair[1]
    ).update({'is_active': false()})

    transaction.commit()


@celery_app.task(bind=True, queue='send_notification', time_limit=60, rate_limit='15/s', default_retry_delay=10)
def send_notification(self, chat_id, text):
    """
    https://core.telegram.org/bots/faq#how-can-i-message-all-of-my-bot-39s-subscribers-at-once
    The API will not allow more than ~30 messages to different users per second
    """
    try:
        bot = telegram.Bot(settings.BOT_TOKEN)

        bot.send_message(
            chat_id=chat_id,
            disable_web_page_preview=True,
            parse_mode=ParseMode.MARKDOWN,
            text=text)

    except TimedOut as e:
        raise self.retry(exc=e)

    except RetryAfter as e:
        raise self.retry(exc=e, countdown=int(e.retry_after))

    # TODO: Forbidden - unsubscribe, disable notification
    # TODO: /stop - disable notifications


# base=QueueOnce
@celery_app.task(queue='notifications', time_limit=60)
def notification_checker():
    # TODO: check is_subscribed flag
    db_session = Session()
    pairs = db_session.query(
        Notification.from_currency_id,
        Notification.to_currency_id,
    ).filter_by(
        is_active=true()
    ).group_by(
        Notification.from_currency_id,
        Notification.to_currency_id
    ).all()

    for pair in pairs:
        from_currency = db_session.query(Currency).get(pair[0])
        to_currency = db_session.query(Currency).get(pair[1])

        if not from_currency.is_active or not to_currency.is_active:
            logging.info('Disable notifications because currency %s %s is not active anymore',
                         from_currency.code, to_currency.code)
            notification_auto_disable(pair)
            continue

        pr = PriceRequest(
            amount=None,
            currency=from_currency.code,
            to_currency=to_currency.code,
            parser_name='notifications'
        )

        prr = convert(pr)

        notifications = db_session.query(
            Notification
        ).filter_by(
            is_active=true()
        ).filter_by(
            from_currency_id=pair[0],
            to_currency_id=pair[1]
        ).all()

        for n in notifications:
            if is_triggered(n.trigger_clause, n.trigger_value, n.last_rate, prr.rate):
                n.last_rate = prr.rate
                # TODO: transaction.commit()

                text_to = NotifyFormatPriceRequestResult(prr, n.chat.locale).get()
                send_notification(n.chat_id, text_to)

        transaction.commit()
