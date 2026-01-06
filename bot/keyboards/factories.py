from aiogram.filters.callback_data import CallbackData


class Template(CallbackData, prefix="template_prefix"):
    template_field: str
