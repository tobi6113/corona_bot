import re

from telegram import Update
from telegram.ext import CallbackQueryHandler


class ChannelCallbackQueryHandler(CallbackQueryHandler):
    """Handler class to handle Telegram callback queries only from channel. Optionally based on a regex.

        Read the documentation of the ``re`` module for more information.

        Attributes:
            callback (:obj:`callable`): The callback function for this handler.
            pattern (:obj:`str` | `Pattern`): Optional. Regex pattern to test
                :attr:`telegram.CallbackQuery.data` against.

        Note:
            Note that this is works with context based callbacks only. See
            https://git.io/fxJuV for more info.

        Args:
            callback (:obj:`callable`): The callback function for this handler. Will be called when
                :attr:`check_update` has determined that an update should be processed by this handler.
                Callback signature for context based API:

                    ``def callback(update: Update, context: CallbackContext)``

                The return value of the callback is usually ignored except for the special case of
                :class:`telegram.ext.ConversationHandler`.
            pattern (:obj:`str` | `Pattern`, optional): Regex pattern. If not ``None``, ``re.match``
                is used on :attr:`telegram.CallbackQuery.data` to determine if an update should be
                handled by this handler.


        """

    def __init__(self, callback, pattern=None):
        super().__init__(callback, pattern)

    def check_update(self, update):
        """Determines whether an update should be passed to this handlers :attr:`callback`.

                Args:
                    update (:class:`telegram.Update`): Incoming telegram update.

                Returns:
                    :obj:`bool`

                """
        if isinstance(update, Update) and update.callback_query:
            if update.effective_chat.type == "channel":
                if self.pattern:
                    if update.callback_query.data:
                        match = re.match(self.pattern, update.callback_query.data)
                        if match:
                            return match
                else:
                    return True
