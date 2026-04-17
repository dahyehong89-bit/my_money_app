from django.shortcuts import render, redirect, get_object_or_404
from collections import defaultdict
from django.utils import timezone
from django.db.models import Sum
from .models import Transaction, CheckList
from .category_config import (
    DETAIL_CATEGORY_OPTIONS,
    CATEGORY_ICON_MAP,
    DEFAULT_CHECKLIST_ITEMS,
    HYUNDAI_MONTHLY_BUDGET,
    LIVING_CATEGORY_MAP,
)
from datetime import date
from calendar import monthrange
import json


def index(request):
    if request.method == 'POST':
        edit_pk = request.POST.get('edit_pk')
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

        if edit_pk:
            # 수정
            item = get_object_or_404(Transaction, pk=edit_pk)
            item.date = date_value
            item.account_type = account_type
            item.category = category
            item.detail_category = detail_category
            item.description = description
            item.amount = amount
            item.is_fuel = is_fuel
            item.price_per_liter = price_per_liter
            item.save()
        else:
            # 신규 생성
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

        saved_month = str(date_value)[:7]
        return redirect(f"/?month={saved_month}")

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
        for name, amount in DEFAULT_CHECKLIST_ITEMS:
            CheckList.objects.create(
                month=month_start,
                content=name,
                amount=amount,
                is_completed=False,
            )

    month_transactions = Transaction.objects.exclude(
        account_type='living'
    ).filter(
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

    budget_left = HYUNDAI_MONTHLY_BUDGET - stats['hyundai']

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

    hyundai_percent = int((stats['hyundai'] / HYUNDAI_MONTHLY_BUDGET) * 100) if stats['hyundai'] > 0 else 0
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

    account_type = item.account_type
    item_month = item.date.strftime("%Y-%m")

    item.delete()

    if account_type == "living":
        return redirect(f"/living/?month={item_month}")
    elif account_type == "incident":
        return redirect(f"/incident/?month={item_month}")
    else:
        return redirect(f"/?month={item_month}")


def toggle_checklist(request, pk):
    item = get_object_or_404(CheckList, pk=pk)

    if request.method == 'POST':
        item.is_completed = not item.is_completed
        item.save()

    item_month = item.month.strftime("%Y-%m")
    return redirect(f"/?month={item_month}")


def living(request):
    today = timezone.localdate()
    selected_month = request.GET.get("month")

    if selected_month:
        try:
            year, month = map(int, selected_month.split("-"))
            month_start = date(year, month, 1)
        except ValueError:
            month_start = today.replace(day=1)
    else:
        month_start = today.replace(day=1)

    last_day = monthrange(month_start.year, month_start.month)[1]
    month_end = date(month_start.year, month_start.month, last_day)

    if request.method == "POST":
        edit_pk = request.POST.get("edit_pk")
        selected_type = request.POST.get("category")   # income / expense / emergency / cash
        detail_category = request.POST.get("detail_category", "기타")
        description = request.POST.get("description")
        amount = int(request.POST.get("amount", 0))

        category = selected_type
        saved_detail_category = detail_category

        if selected_type == "income":
            category = "income"

        elif selected_type == "expense":
            category = "expense"

        elif selected_type == "emergency":
            category = "non_expense"
            saved_detail_category = detail_category

            if detail_category == "비상금 넣기":
                amount = abs(amount)
            elif detail_category == "비상금 빼기":
                amount = -abs(amount)

        elif selected_type == "cash":
            category = "non_expense"
            saved_detail_category = detail_category

            if detail_category == "현금 넣기":
                amount = abs(amount)
            elif detail_category == "현금 쓰기":
                amount = -abs(amount)

        if edit_pk:
            # 수정
            item = get_object_or_404(Transaction, pk=edit_pk)
            item.date = request.POST.get("date")
            item.account_type = "living"
            item.category = category
            item.detail_category = saved_detail_category
            item.description = description
            item.amount = amount
            item.save()
        else:
            # 신규 생성
            Transaction.objects.create(
                date=request.POST.get("date"),
                account_type="living",
                category=category,
                detail_category=saved_detail_category,
                description=description,
                amount=amount,
            )

        return redirect(f"/living/?month={month_start.strftime('%Y-%m')}")

    # 이번 달 거래내역
    month_transactions = Transaction.objects.filter(
        account_type="living",
        date__year=month_start.year,
        date__month=month_start.month
    ).order_by("-date", "-created_at")

    # 전달 계산용
    if month_start.month == 1:
        prev_year = month_start.year - 1
        prev_month = 12
    else:
        prev_year = month_start.year
        prev_month = month_start.month - 1

    prev_transactions = Transaction.objects.filter(
        account_type="living",
        date__year=prev_year,
        date__month=prev_month
    )

    # 전달 입금 / 지출
    prev_income = prev_transactions.filter(category="income").aggregate(
        Sum("amount")
    )["amount__sum"] or 0

    prev_expense = prev_transactions.filter(category="expense").aggregate(
        Sum("amount")
    )["amount__sum"] or 0

    # 전달 비상금 / 현금 변동
    prev_emergency = prev_transactions.filter(
        category="non_expense",
        detail_category__startswith="비상금"
    ).aggregate(
        Sum("amount")
    )["amount__sum"] or 0

    prev_cash = prev_transactions.filter(
        category="non_expense",
        detail_category__startswith="현금"
    ).aggregate(
        Sum("amount")
    )["amount__sum"] or 0

    # 전달 이월금액 = 전달 말 기준 가용생활비
    # 현금은 가용생활비 차감 대상 아님
    carry_over = prev_income - prev_expense - prev_emergency

    # 이번 달 입금 / 지출
    total_income = month_transactions.filter(category="income").aggregate(
        Sum("amount")
    )["amount__sum"] or 0

    total_expense = month_transactions.filter(category="expense").aggregate(
        Sum("amount")
    )["amount__sum"] or 0

    # 이번 달 비상금 / 현금 변동
    month_emergency = month_transactions.filter(
        category="non_expense",
        detail_category__startswith="비상금"
    ).aggregate(
        Sum("amount")
    )["amount__sum"] or 0

    month_cash = month_transactions.filter(
        category="non_expense",
        detail_category__startswith="현금"
    ).aggregate(
        Sum("amount")
    )["amount__sum"] or 0

    # 이번 달 가용생활비
    # 비상금만 가용생활비에서 빠짐 / 현금은 별도 기록만
    available_living = (
        carry_over
        + total_income
        - total_expense
        - month_emergency
    )

    # 비상금 누적액 (선택월 말일까지)
    emergency_total = Transaction.objects.filter(
        account_type="living",
        date__lte=month_end,
        category="non_expense",
        detail_category__startswith="비상금"
    ).aggregate(
        Sum("amount")
    )["amount__sum"] or 0

    # 현금보유액 누적액 (선택월 말일까지)
    cash_total = Transaction.objects.filter(
        account_type="living",
        date__lte=month_end,
        category="non_expense",
        detail_category__startswith="현금"
    ).aggregate(
        Sum("amount")
    )["amount__sum"] or 0

    # 총 보유 생활비
    total_living_assets = available_living + emergency_total + cash_total

    # 카테고리별 지출 집계
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
    for cat_name, cat_total in category_summary.items():
        category_summary_list.append({
            'name': cat_name,
            'icon': CATEGORY_ICON_MAP.get(cat_name, '📦'),
            'total': cat_total,
        })

    category_detail_map = dict(category_detail_map)

    # 도넛 차트용 JSON
    chart_labels = [f"{item['icon']} {item['name']}" for item in category_summary_list]
    chart_values = [item['total'] for item in category_summary_list]

    # 관리비 1년치 막대 그래프용 데이터
    rent_chart_labels = []
    rent_chart_values = []

    for i in range(11, -1, -1):
        m = month_start.month - i
        y = month_start.year
        while m <= 0:
            m += 12
            y -= 1

        rent_month_total = Transaction.objects.filter(
            account_type="living",
            category="expense",
            detail_category__in=["주거비", "관리비"],
            date__year=y,
            date__month=m,
        ).aggregate(Sum("amount"))["amount__sum"] or 0

        rent_chart_labels.append(f"{m}월")
        rent_chart_values.append(abs(rent_month_total))

    # 최근 12개월 관리비 추이
    rent_labels = []
    rent_values = []

    for i in range(11, -1, -1):
        y = month_start.year
        m = month_start.month - i

        while m <= 0:
            y -= 1
            m += 12

        while m > 12:
            y += 1
            m -= 12

        month_label = f"{y % 100:02d}.{m:02d}"
        rent_labels.append(month_label)

        monthly_rent_total = Transaction.objects.filter(
            account_type="living",
            date__year=y,
            date__month=m,
            category="expense",
            detail_category="주거비"
        ).aggregate(Sum("amount"))["amount__sum"] or 0

        rent_values.append(abs(monthly_rent_total))

    context = {
        "today": today,
        "selected_month": month_start.strftime("%Y-%m"),
        "selected_year": month_start.year,
        "selected_month_num": month_start.month,
        "history": month_transactions[:30],
        "detail_category_options": DETAIL_CATEGORY_OPTIONS,

        "living_category_map_json": json.dumps(LIVING_CATEGORY_MAP, ensure_ascii=False),

        "living_income": total_income,
        "living_expense": total_expense,
        "living_balance": available_living,

        "carry_over": carry_over,
        "available_living": available_living,
        "emergency_total": emergency_total,
        "cash_total": cash_total,
        "total_living_assets": total_living_assets,

        "category_summary_list": category_summary_list,
        "category_detail_map": category_detail_map,
        "category_icon_map": CATEGORY_ICON_MAP,
        
        "chart_labels_json": chart_labels,
        "chart_values_json": chart_values,

        "rent_chart_labels_json": rent_labels,
        "rent_chart_values_json": rent_values,

        "living_category_map_json": LIVING_CATEGORY_MAP,
    }

    return render(request, "account/living.html", context)