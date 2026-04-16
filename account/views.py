from django.shortcuts import render, redirect, get_object_or_404
from collections import defaultdict
from django.utils import timezone
from django.db.models import Sum
from .models import Transaction, CheckList
from datetime import date
import json

DETAIL_CATEGORY_OPTIONS = [
    ("🍽 외식", "외식"),
    ("☕ 커피", "커피"),
    ("🛵 배달", "배달"),
    ("🛒 장보기", "장보기"),
    ("🛍 쇼핑", "쇼핑"),
    ("🧻 생활용품", "생활용품"),
    ("💄 미용", "미용"),
    ("⛽ 주유", "주유"),
    ("🚌 교통", "교통"),
    ("🏠 관리비", "관리비"),
    ("🛡 보험", "보험"),
    ("📱 통신비", "통신비"),
    ("📺 구독", "구독"),
    ("🏥 병원비", "병원비"),
    ("🎗 경조사", "경조사"),
    ("🎁 선물", "선물"),
    ("✈️ 여행", "여행"),
    ("💸 정산", "정산"),
    ("📦 기타", "기타"),
]

CATEGORY_ICON_MAP = {
    "외식": "🍽",
    "커피": "☕",
    "배달": "🛵",
    "장보기": "🛒",
    "쇼핑": "🛍",
    "생활용품": "🧻",
    "미용": "💄",
    "주유": "⛽",
    "교통": "🚌",
    "관리비": "🏠",
    "보험": "🛡",
    "통신비": "📱",
    "구독": "📺",
    "병원비": "🏥",
    "경조사": "🎗",
    "선물": "🎁",
    "여행": "✈️",
    "정산": "💸",
    "기타": "📦",
}


def index(request):
    if request.method == 'POST':
        date_value = request.POST.get('date')
        account_type = request.POST.get('account_type')
        category = request.POST.get('category')
        detail_category = request.POST.get('detail_category', '기타')
        description = request.POST.get('description')

        try:
            amount = int(request.POST.get('amount', 0))
        except (TypeError, ValueError):
            amount = 0

        is_fuel = request.POST.get('is_fuel') == 'on'

        try:
            price_per_liter_raw = request.POST.get('price_per_liter')
            price_per_liter = float(price_per_liter_raw) if price_per_liter_raw else None
        except (TypeError, ValueError):
            price_per_liter = None

        Transaction.objects.create(
            date=date_value,
            account_type=account_type,
            category=category,
            detail_category=detail_category,
            description=description,
            amount=amount,
            is_fuel=is_fuel,
            price_per_liter=price_per_liter,
        )

        return redirect('index')

    today = timezone.localdate()

    selected_month = request.GET.get('month')

    if selected_month:
        try:
            year, month = map(int, selected_month.split('-'))
            month_start = date(year, month, 1)
        except ValueError:
            month_start = today.replace(day=1)
    else:
        month_start = today.replace(day=1)

    # 이번달 체크리스트 없으면 자동 생성
    if not CheckList.objects.filter(month=month_start).exists():
        default_items = [
            ("공용 생활비", 1000000),
            ("사건비 통장", 200000),
            ("수원 지역화폐 충전", 100000),
            ("모임비", 190000),
            ("정기 주차비", 80000),
            ("적금", 300000),
            ("청약", 20000),
            ("보험료1", 23226),
            ("보험료2", 60712),
        ]

        for name, amount in default_items:
            CheckList.objects.create(
                month=month_start,
                content=name,
                amount=amount,
                is_completed=False,
            )

    month_transactions = Transaction.objects.filter(
        date__year=month_start.year,
        date__month=month_start.month
    )

    def group_by_detail_category(queryset):
        grouped = defaultdict(list)
        for item in queryset:
            grouped[item.detail_category].append(item)
        return dict(grouped)

    def get_monthly_total(acc_type):
        return month_transactions.filter(
            account_type=acc_type,
            category='expense'
        ).aggregate(Sum('amount'))['amount__sum'] or 0

    stats = {
        'hyundai': get_monthly_total('hyundai'),
        'shinhan': get_monthly_total('shinhan'),
        'incident': get_monthly_total('incident'),
        'cash_transfer': get_monthly_total('cash_transfer'),
    }

    budget_left = 600000 - stats['hyundai']

    checklist_items = CheckList.objects.filter(
        month=month_start
    ).order_by('id')

    check_total = checklist_items.count()
    check_done = checklist_items.filter(is_completed=True).count()
    check_percent = int((check_done / check_total) * 100) if check_total else 0

    check_total_amount = sum(item.amount for item in checklist_items)
    check_done_amount = sum(item.amount for item in checklist_items if item.is_completed)

    history = month_transactions.order_by('-date', '-created_at')[:10]
    fuel_list = month_transactions.filter(
        is_fuel=True,
        detail_category='주유'
    ).exclude(category='income').order_by('date')

    fuel_labels = [f.date.strftime('%m/%d') for f in fuel_list]
    fuel_prices = [f.price_per_liter for f in fuel_list]

    fuel_items = month_transactions.filter(
        is_fuel=True,
        detail_category='주유'
    ).exclude(category='income').order_by('-date', '-created_at')

    fuel_detail_list = []
    fuel_total_amount = 0
    fuel_total_liters = 0
    fuel_price_sum = 0
    fuel_price_count = 0

    for item in fuel_items:
        liters = None

        if item.price_per_liter and item.price_per_liter > 0:
            liters = abs(item.amount) / item.price_per_liter
            fuel_total_liters += liters
            fuel_price_sum += item.price_per_liter
            fuel_price_count += 1

        fuel_total_amount += abs(item.amount)

        fuel_detail_list.append({
            'date': item.date.strftime('%m/%d'),
            'account_type': item.get_account_type_display(),
            'category': item.category,
            'description': item.description,
            'amount': abs(item.amount),
            'price_per_liter': item.price_per_liter,
            'liters': round(liters, 2) if liters is not None else None,
        })

    fuel_avg_price = round(fuel_price_sum / fuel_price_count, 0) if fuel_price_count > 0 else 0
    fuel_total_liters = round(fuel_total_liters, 2)

    hyundai_items = month_transactions.filter(
        account_type='hyundai',
        category='expense'
    ).order_by('-date', '-created_at')

    shinhan_items = month_transactions.filter(
        account_type='shinhan',
        category='expense'
    ).order_by('-date', '-created_at')

    incident_items = month_transactions.filter(
        account_type='incident',
        category='expense'
    ).order_by('-date', '-created_at')

    cash_transfer_items = month_transactions.filter(
        account_type='cash_transfer',
        category='expense'
    ).order_by('-date', '-created_at')

    hyundai_grouped = group_by_detail_category(hyundai_items)
    shinhan_grouped = group_by_detail_category(shinhan_items)
    incident_grouped = group_by_detail_category(incident_items)
    cash_transfer_grouped = group_by_detail_category(cash_transfer_items)

    hyundai_percent = int((stats['hyundai'] / 600000) * 100) if stats['hyundai'] > 0 else 0
    if hyundai_percent > 100:
        hyundai_percent = 100

    category_summary = defaultdict(int)
    category_detail_map = defaultdict(list)

    for item in month_transactions.filter(category='expense').order_by('-date', '-created_at'):
        category_name = item.detail_category or "기타"
        category_summary[category_name] += abs(item.amount)

        category_detail_map[category_name].append({
            'date': item.date.strftime('%m/%d'),
            'account_type': item.get_account_type_display(),
            'description': item.description,
            'amount': abs(item.amount),
        })

    category_summary = dict(
        sorted(category_summary.items(), key=lambda x: x[1], reverse=True)
    )

    category_summary_list = []
    for category, total in category_summary.items():
        category_summary_list.append({
            'name': category,
            'icon': CATEGORY_ICON_MAP.get(category, '📦'),
            'total': total,
        })

    category_detail_map = dict(category_detail_map)

    context = {
        'today': today,
        'selected_month': month_start.strftime('%Y-%m'),
        'selected_year': month_start.year,
        'selected_month_num': month_start.month,
        'stats': stats,
        'budget_left': budget_left,

        'check_items': checklist_items,
        'progress': check_percent,
        'total_check': check_total,
        'completed_check': check_done,
        'check_total_amount': check_total_amount,
        'check_done_amount': check_done_amount,

        'history': history,

        'category_summary': category_summary,
        'category_summary_list': category_summary_list,
        'category_detail_map': category_detail_map,
        'category_icon_map': CATEGORY_ICON_MAP,

        'detail_category_options': DETAIL_CATEGORY_OPTIONS,

        'fuel_labels': json.dumps(fuel_labels),
        'fuel_prices': json.dumps(fuel_prices),
        'fuel_detail_list': fuel_detail_list,
        'fuel_total_amount': fuel_total_amount,
        'fuel_avg_price': fuel_avg_price,
        'fuel_total_liters': fuel_total_liters,

        'hyundai_percent': hyundai_percent,
        'hyundai_items': hyundai_items,
        'shinhan_items': shinhan_items,
        'incident_items': incident_items,
        'cash_transfer_items': cash_transfer_items,
        'hyundai_grouped': hyundai_grouped,
        'shinhan_grouped': shinhan_grouped,
        'incident_grouped': incident_grouped,
        'cash_transfer_grouped': cash_transfer_grouped,
    }

    return render(request, 'account/index.html', context)


def delete_transaction(request, pk):
    item = get_object_or_404(Transaction, pk=pk)
    item.delete()
    return redirect('index')


def edit_transaction(request, pk):
    item = get_object_or_404(Transaction, pk=pk)

    if request.method == 'POST':
        item.date = request.POST.get('date')
        item.account_type = request.POST.get('account_type')
        item.category = request.POST.get('category')
        item.detail_category = request.POST.get('detail_category', '기타')
        item.description = request.POST.get('description')

        try:
            item.amount = int(request.POST.get('amount', 0))
        except (TypeError, ValueError):
            item.amount = 0

        item.is_fuel = request.POST.get('is_fuel') == 'on'

        try:
            price_per_liter_raw = request.POST.get('price_per_liter')
            item.price_per_liter = float(price_per_liter_raw) if price_per_liter_raw else None
        except (TypeError, ValueError):
            item.price_per_liter = None

        item.save()
        return redirect('index')

    return render(request, 'account/edit.html', {
        'item': item,
        'detail_category_options': DETAIL_CATEGORY_OPTIONS,
    })


def toggle_checklist(request, pk):
    if request.method == 'POST':
        item = get_object_or_404(CheckList, pk=pk)
        item.is_completed = not item.is_completed
        item.save()

    return redirect('index')