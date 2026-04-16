from django import template

register = template.Library()

@register.filter
def sum_amount(items):
    return sum(abs(item.amount) for item in items)