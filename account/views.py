from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from collections import defaultdict
from django.utils import timezone
from django.db.models import Sum, Q
from .models import Transaction, CheckList
from .category_config import DETAIL_CATEGORY_CHOICES
from .category_config import (
    DETAIL_CATEGORY_OPTIONS,
    CATEGORY_ICON_MAP,
    DEFAULT_CHECKLIST_ITEMS,
    HYUNDAI_MONTHLY_BUDGET,
    LIVING_CATEGORY_MAP,
    MAIN_EXPENSE_CATEGORIES,
    MAIN_INCOME_CATEGORIES,
)
from datetime import date
from calendar import monthrange
import json
from django.http import JsonResponse
from .models import Memo
from .decorators import simple_login_required
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta

@simple_login_required
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

        try:
            odometer_raw = request.POST.get('odometer')
            odometer = int(odometer_raw) if odometer_raw else None
        except (TypeError, ValueError):
            odometer = None

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
            item.odometer = odometer
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
                odometer=odometer,
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

    history = month_transactions.order_by('-date', '-created_at')
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

    # 구간거리/연비 계산을 위해 오름차순(오래된 것부터)으로도 정렬
    fuel_items_asc = list(fuel_items.order_by('date', 'created_at'))

    fuel_detail_list = []
    fuel_total_amount = 0
    fuel_total_liters = 0
    fuel_price_sum = 0
    fuel_price_count = 0

    # 주행거리 / 연비 관련 누적 변수
    fuel_total_distance = 0
    fuel_distance_liters = 0  # 구간거리가 계산된 주유량만 합산 (평균 연비 분모)

    # 이번달 첫 기록의 구간거리 계산을 위해 이전 달 마지막 odometer 조회
    prev_odometer = None
    if fuel_items_asc:
        first_item = fuel_items_asc[0]
        previous_fuel = Transaction.objects.filter(
            is_fuel=True,
            detail_category='주유',
            odometer__isnull=False,
            date__lt=first_item.date,
        ).exclude(category='income').order_by('-date', '-created_at').first()
        if previous_fuel:
            prev_odometer = previous_fuel.odometer

    # 각 기록별 구간거리/연비를 pk로 매핑
    calc_map = {}

    for item in fuel_items_asc:
        liters_calc = None
        if item.price_per_liter and item.price_per_liter > 0:
            liters_calc = abs(item.amount) / item.price_per_liter

        distance = None
        mileage = None

        if item.odometer and prev_odometer is not None:
            diff = item.odometer - prev_odometer
            if diff > 0:
                distance = diff
                fuel_total_distance += diff
                if liters_calc and liters_calc > 0:
                    mileage = diff / liters_calc
                    fuel_distance_liters += liters_calc

        if item.odometer:
            prev_odometer = item.odometer

        calc_map[item.pk] = {
            'distance': distance,
            'mileage': round(mileage, 2) if mileage is not None else None,
        }

    # 화면 표시는 최신순(fuel_items 원본 순서)으로
    for item in fuel_items:
        liters = None

        if item.price_per_liter and item.price_per_liter > 0:
            liters = abs(item.amount) / item.price_per_liter
            fuel_total_liters += liters
            fuel_price_sum += item.price_per_liter
            fuel_price_count += 1

        fuel_total_amount += abs(item.amount)

        calc = calc_map.get(item.pk, {})

        fuel_detail_list.append({
            'date': item.date.strftime('%m/%d'),
            'account_type': item.get_account_type_display(),
            'category': item.category,
            'description': item.description,
            'amount': abs(item.amount),
            'price_per_liter': item.price_per_liter,
            'liters': round(liters, 2) if liters is not None else None,
            'odometer': item.odometer,
            'distance': calc.get('distance'),
            'mileage': calc.get('mileage'),
        })

    fuel_avg_price = round(fuel_price_sum / fuel_price_count, 0) if fuel_price_count > 0 else 0
    fuel_total_liters = round(fuel_total_liters, 2)
    fuel_avg_mileage = round(fuel_total_distance / fuel_distance_liters, 2) if fuel_distance_liters > 0 else 0

    # ─────────────────────────────────────────
    # ✅ 누적 주유 통계 (전체 기간)
    # ─────────────────────────────────────────
    all_fuel_items = Transaction.objects.filter(
        is_fuel=True,
        detail_category='주유'
    ).exclude(category='income').order_by('date', 'created_at')

    cumulative_count = all_fuel_items.count()
    cumulative_total_amount = sum(abs(f.amount) for f in all_fuel_items)
    cumulative_total_liters = 0
    cumulative_total_distance = 0
    cumulative_distance_liters = 0

    prev_odo = None
    for f in all_fuel_items:
        # 누적 주유량
        if f.price_per_liter and f.price_per_liter > 0:
            liters_calc = abs(f.amount) / f.price_per_liter
            cumulative_total_liters += liters_calc

            # 누적 주행거리/연비
            if f.odometer and prev_odo is not None:
                diff = f.odometer - prev_odo
                if diff > 0:
                    cumulative_total_distance += diff
                    cumulative_distance_liters += liters_calc

        if f.odometer:
            prev_odo = f.odometer

    cumulative_total_liters = round(cumulative_total_liters, 2)
    cumulative_avg_mileage = (
        round(cumulative_total_distance / cumulative_distance_liters, 2)
        if cumulative_distance_liters > 0 else 0
    )

    # ─────────────────────────────────────────
    # ✅ 최근 1년 주유 추이 차트 데이터
    # ─────────────────────────────────────────
    

    one_year_ago = timezone.now().date() - timedelta(days=365)

    recent_fuel = Transaction.objects.filter(
        is_fuel=True,
        detail_category='주유',
        date__gte=one_year_ago,
    ).exclude(category='income').order_by('date', 'created_at')

    fuel_chart_labels = [f.date.strftime('%y/%m/%d') for f in recent_fuel]
    fuel_chart_prices = [f.price_per_liter or 0 for f in recent_fuel]
    fuel_chart_amounts = [abs(f.amount) for f in recent_fuel]

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

    total_expense = 0
    total_inflow = 0
    total_refund_only = 0

    category_summary = defaultdict(int)
    category_detail_map = defaultdict(list)

    target_items = month_transactions.filter(
        Q(category='expense') |
        Q(category='income')
    ).order_by('-date', '-created_at')

    for item in target_items:
        category_name = item.detail_category or "기타"
        is_inflow = (item.category == 'income')

        amount = abs(item.amount)

        if is_inflow:
            total_inflow += amount

            if '환급' in (item.detail_category or ''):
                total_refund_only += amount

            # ❌ continue 제거 (이게 핵심)
        else:
            total_expense += amount

        # 🔥 카테고리에는 둘 다 넣되 금액은 항상 양수
        category_summary[category_name] += amount

        category_detail_map[category_name].append({
            'date': item.date.strftime('%m/%d'),
            'account_type': item.get_account_type_display(),
            'description': item.description,
            'amount': amount,
            'is_inflow': is_inflow,
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

    category_map = {
        "expense": [],
        "income": [],
    }

    # 중복 방지용 set
    seen = {"expense": set(), "income": set()}

    for value, label in DETAIL_CATEGORY_CHOICES:
        icon = CATEGORY_ICON_MAP.get(value, "")
        item = {"value": value, "label": f"{icon} {label}"}

        if value in MAIN_EXPENSE_CATEGORIES and value not in seen["expense"]:
            category_map["expense"].append(item)
            seen["expense"].add(value)

        if value in MAIN_INCOME_CATEGORIES and value not in seen["income"]:
            category_map["income"].append(item)
            seen["income"].add(value)

    # 비지출은 지출이랑 동일한 카테고리 사용
    category_map["non_expense"] = category_map["expense"]

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

        'DETAIL_CATEGORY_OPTIONS': json.dumps(DETAIL_CATEGORY_OPTIONS),
        'CATEGORY_MAP_JSON': json.dumps(category_map, ensure_ascii=False),

        'fuel_labels': json.dumps(fuel_labels),
        'fuel_prices': json.dumps(fuel_prices),
        'fuel_detail_list': fuel_detail_list,
        'fuel_total_amount': fuel_total_amount,
        'fuel_avg_price': fuel_avg_price,
        'fuel_total_liters': fuel_total_liters,
        'fuel_total_distance': fuel_total_distance,
        'fuel_avg_mileage': fuel_avg_mileage,
        'cumulative_count': cumulative_count,
        'cumulative_total_amount': cumulative_total_amount,
        'cumulative_total_liters': cumulative_total_liters,
        'cumulative_avg_mileage': cumulative_avg_mileage,
        'fuel_chart_labels': fuel_chart_labels,
        'fuel_chart_prices': fuel_chart_prices,
        'fuel_chart_amounts': fuel_chart_amounts,

        'hyundai_percent': hyundai_percent,
        'hyundai_items': hyundai_items,
        'shinhan_items': shinhan_items,
        'incident_items': incident_items,
        'cash_transfer_items': cash_transfer_items,
        'hyundai_grouped': hyundai_grouped,
        'shinhan_grouped': shinhan_grouped,
        'incident_grouped': incident_grouped,
        'cash_transfer_grouped': cash_transfer_grouped,

        'total_expense': total_expense,
        'total_inflow': total_inflow,
        'net_expense': total_expense - total_refund_only
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


@simple_login_required
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
            elif detail_category == "비상금 직접입금":
                amount = abs(amount)  

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
        detail_category__in=["비상금 넣기", "비상금 빼기"]
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

    # 이번 달 비상금 이동 (내 돈 이동만)
    month_emergency = month_transactions.filter(
        category="non_expense",
        detail_category__in=["비상금 넣기", "비상금 빼기"]
    ).aggregate(
        Sum("amount")
    )["amount__sum"] or 0

    # 이번 달 비상금 직접입금 (이자, 외부돈)
    emergency_direct_total = month_transactions.filter(
        category="non_expense",
        detail_category="비상금 직접입금"
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

    # 최근 12개월 관리비 추이 (올해 + 작년 동일월)
    rent_labels = []
    rent_values = []         # 올해 (현재 12개월)
    rent_prev_values = []    # 작년 같은 달 (12개월)

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

        # 올해 주거비
        monthly_rent_total = Transaction.objects.filter(
            account_type="living",
            date__year=y,
            date__month=m,
            category="expense",
            detail_category="주거비"
        ).aggregate(Sum("amount"))["amount__sum"] or 0
        rent_values.append(abs(monthly_rent_total))

        # 작년 같은 달 주거비
        prev_rent_total = Transaction.objects.filter(
            account_type="living",
            date__year=y - 1,
            date__month=m,
            category="expense",
            detail_category="주거비"
        ).aggregate(Sum("amount"))["amount__sum"] or 0
        rent_prev_values.append(abs(prev_rent_total))

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
        "rent_chart_prev_values_json": rent_prev_values,

        "living_category_map_json": LIVING_CATEGORY_MAP,

        "emergency_direct_total": emergency_direct_total,
    }

    return render(request, "account/living.html", context)


def simple_login(request):
    if request.session.get("simple_auth_ok"):
        return redirect("index")   # 메인 가계부 url name에 맞게 수정

    error = ""

    if request.method == "POST":
        password = request.POST.get("password", "").strip()

        if password == settings.SIMPLE_LOGIN_PASSWORD:
            request.session["simple_auth_ok"] = True
            return redirect("index")   # 로그인 후 이동할 페이지
        else:
            error = "비밀번호가 틀렸어요."

    return render(request, "account/simple_login.html", {"error": error})


def simple_logout(request):
    request.session.flush()
    return redirect("simple_login")

@csrf_exempt
def memo_list(request):
    if request.method == "GET":
        # 3일 지난 체크된 메모는 서버에서도 자동 정리
        cutoff = timezone.now() - timezone.timedelta(days=3)
        Memo.objects.filter(checked=True, checked_at__lt=cutoff).delete()

        memos = Memo.objects.all().order_by("-created_at")
        data = [{
            "id": m.id,
            "text": m.text,
            "checked": m.checked,
            "date": f"{m.created_at.month}/{m.created_at.day}",
            # ✅ 밀리초로 통일 + 체크된 메모는 checked_at 기준
            "checked_time": m.checked_at.timestamp() * 1000 if m.checked_at else None,
        } for m in memos]
        return JsonResponse(data, safe=False)

    if request.method == "POST":
        body = json.loads(request.body)
        memo = Memo.objects.create(text=body["text"])
        return JsonResponse({
            "id": memo.id,
            "text": memo.text,
            "checked": memo.checked,
            "date": f"{memo.created_at.month}/{memo.created_at.day}",
            "checked_time": None,
        })


@csrf_exempt
def memo_detail(request, id):
    memo = Memo.objects.get(id=id)

    if request.method == "POST":
        body = json.loads(request.body)
        memo.checked = body["checked"]
        # ✅ 체크 상태에 따라 checked_at 갱신
        memo.checked_at = timezone.now() if memo.checked else None
        memo.save()
        return JsonResponse({
            "ok": True,
            "checked_time": memo.checked_at.timestamp() * 1000 if memo.checked_at else None,
        })

    if request.method == "DELETE":
        memo.delete()
        return JsonResponse({"ok": True})