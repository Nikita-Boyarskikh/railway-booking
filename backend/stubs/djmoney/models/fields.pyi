from django.db.models.fields import DecimalField
from djmoney.money import Money

class MoneyField(DecimalField[Money, Money]): ...
