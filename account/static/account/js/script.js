/**
 * 가계부 주요 기능 스크립트
 */

function getValue(id) {
    const el = document.getElementById(id);
    return el ? el.value : '';
}

function getChecked(id) {
    const el = document.getElementById(id);
    return el ? el.checked : false;
}

// 1. 주유 입력칸 토글 (메인 화면용)
function toggleFuelInput() {
    const isFuel = getChecked('ui_is_fuel');
    const fuelSection = document.getElementById('ui_fuel_section');

    if (fuelSection) {
        fuelSection.style.display = isFuel ? 'block' : 'none';
    }
}

// 2. 고정비 퀵버튼
function applyQuickExpense(account, category, detailCategory, description, amount = "") {
    const dateInput = document.getElementById("ui_date");
    const accountInput = document.getElementById("ui_account");
    const categoryInput = document.getElementById("ui_category");
    const detailInput = document.getElementById("ui_detail_category");
    const descInput = document.getElementById("ui_desc");
    const amountInput = document.getElementById("ui_amount");
    const fuelCheck = document.getElementById("ui_is_fuel");
    const fuelSection = document.getElementById("ui_fuel_section");
    const fuelPrice = document.getElementById("ui_fuel_price");

    if (!accountInput || !categoryInput || !detailInput || !descInput || !amountInput) {
        console.log("빠른입력 대상 input id를 찾지 못함");
        return;
    }

    if (dateInput && !dateInput.value) {
        dateInput.value = getTodayDate();
    }

    accountInput.value = account;
    categoryInput.value = category;
    detailInput.value = detailCategory;
    descInput.value = description;
    amountInput.value = amount;

    // 주유일 때만 연료칸 표시
    const isFuel = detailCategory === "주유";

    if (fuelCheck) {
        fuelCheck.checked = isFuel;
    }

    if (fuelSection) {
        fuelSection.style.display = isFuel ? "block" : "none";
    }

    if (!isFuel && fuelPrice) {
        fuelPrice.value = "";
    }

    amountInput.focus();
    amountInput.select();
}

// 3. 기록하기 버튼 (메인 폼 -> 모달 폼으로 복사 후 오픈)
function openConfirmModal() {
    const modalDate = document.getElementById('modal_date');
    const modalDesc = document.getElementById('modal_desc');
    const modalAmount = document.getElementById('modal_amount');
    const modalAccount = document.getElementById('modal_account');
    const modalCategory = document.getElementById('modal_category');
    const modalFuelPrice = document.getElementById('modal_fuel_price');
    const fuelSection = document.getElementById('modal_fuel_section');
    const isFuelInput = document.getElementById('modal_is_fuel');
    const confirmModal = document.getElementById('confirmModal');
    const modalDetailCategory = document.getElementById('modal_detail_category');

    if (modalDate) modalDate.value = getValue('ui_date');
    if (modalDesc) modalDesc.value = getValue('ui_desc');
    if (modalAmount) modalAmount.value = getValue('ui_amount');
    if (modalAccount) modalAccount.value = getValue('ui_account');
    if (modalCategory) modalCategory.value = getValue('ui_category');
    if (modalDetailCategory) modalDetailCategory.value = getValue('ui_detail_category');

    const isFuel = getChecked('ui_is_fuel');

    if (isFuel) {
        if (fuelSection) fuelSection.style.display = 'block';
        if (isFuelInput) isFuelInput.value = 'on';
        if (modalFuelPrice) modalFuelPrice.value = getValue('ui_fuel_price');
    } else {
        if (fuelSection) fuelSection.style.display = 'none';
        if (isFuelInput) isFuelInput.value = 'off';
        if (modalFuelPrice) modalFuelPrice.value = '';
    }

    if (confirmModal) confirmModal.style.display = 'flex';
    calcLiterInModal();
}

// 4. 모달 전용 리터 계산 함수
function calcLiterInModal() {
    const amount = getValue('modal_amount');
    const price = getValue('modal_fuel_price');
    const resultP = document.getElementById('modal_calc_result');

    if (!resultP) return;

    if (amount && price && Number(price) > 0) {
        const liters = (Number(amount) / Number(price)).toFixed(2);
        resultP.innerText = `⛽ 예상 주유량: ${liters}L`;
    } else {
        resultP.innerText = '';
    }
}

// 5. 모달 닫기 함수
function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.style.display = 'none';
    }
}

// 6. 데이터 제출 함수
function submitData() {
    const modalForm = document.getElementById('modal_form');
    if (modalForm) {
        modalForm.submit();
    }
}

// 7. 주유 그래프 모달 열기 및 그리기
function openChartModal() {
    const modal = document.getElementById('chartModal');
    const chartEl = document.getElementById('fuelChart');
    const labelsEl = document.getElementById('fuel_labels_data');
    const pricesEl = document.getElementById('fuel_prices_data');

    if (!modal || !chartEl || !labelsEl || !pricesEl) return;

    modal.style.display = 'flex';

    const ctx = chartEl.getContext('2d');

    if (window.myChart) {
        window.myChart.destroy();
    }

    window.myChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: JSON.parse(labelsEl.textContent),
            datasets: [{
                label: '리터당 단가 변화',
                data: JSON.parse(pricesEl.textContent),
                borderColor: '#ff8a93',
                backgroundColor: 'rgba(255, 138, 147, 0.1)',
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: false
                }
            }
        }
    });
}

const categoryDetailMapEl = document.getElementById('category-detail-data');
const categoryDetailMap = categoryDetailMapEl
    ? JSON.parse(categoryDetailMapEl.textContent)
    : {};

function openCategoryModal(category) {
    const modal = document.getElementById('categoryModal');
    const title = document.getElementById('categoryModalTitle');
    const body = document.getElementById('categoryModalBody');

    if (!modal || !title || !body) {
        console.log('categoryModal 요소를 찾지 못함');
        return;
    }

    const items = categoryDetailMap[category] || [];

    title.textContent = category + ' 세부내역';

    if (items.length === 0) {
        body.innerHTML = '<p class="empty-text">내역이 없습니다.</p>';
    } else {
        body.innerHTML = items.map(item => `
            <div class="modal-history-row compact-row">
                <div class="modal-history-left compact-left">
                    <span class="history-date">${item.date}</span>
                    <span class="history-desc-inline">${item.description || '-'}</span>
                </div>

                <div class="compact-right">
                    <strong class="expense">
                        ${Number(item.amount).toLocaleString()}원
                    </strong>
                </div>
            </div>
        `).join('');
    }

    modal.style.display = 'flex';
}

function closeCategoryModal() {
    const modal = document.getElementById('categoryModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

window.addEventListener('click', function(e) {
    const modal = document.getElementById('categoryModal');
    if (e.target === modal) {
        closeCategoryModal();
    }
});

// 체크 전 스크롤 위치 저장
document.querySelectorAll('.check-form').forEach(form => {
    form.addEventListener('submit', function () {
        sessionStorage.setItem('scrollY', window.scrollY);
    });
});

// 새로고침 후 스크롤 복원
window.addEventListener('load', function () {
    const savedY = sessionStorage.getItem('scrollY');

    if (savedY !== null) {
        window.scrollTo(0, parseInt(savedY));
        sessionStorage.removeItem('scrollY');
    }
});

document.addEventListener("DOMContentLoaded", function () {
    const pickerInputs = document.querySelectorAll('input[type="date"], input[type="month"]');

    pickerInputs.forEach((input) => {
        input.style.cursor = "pointer";

        const openPicker = () => {
            input.focus();
            if (typeof input.showPicker === "function") {
                try {
                    input.showPicker();
                } catch (e) {
                    console.log("showPicker not available:", e);
                }
            }
        };

        input.addEventListener("mousedown", function () {
            openPicker();
        });

        input.addEventListener("focus", function () {
            openPicker();
        });
    });
});

let fixedDetailName = "";
let fixedMappedDetail = "";

function openFixedModal(title, detail, amount, isFuel, price) {
    fixedDetailName = detail;

    if (detail === "통신비" || detail === "인터넷") {
        fixedMappedDetail = "통신비";
    } else if (detail === "쿠팡와우" || detail === "이모티콘") {
        fixedMappedDetail = "구독";
    } else if (detail === "주유") {
        fixedMappedDetail = "주유";
    } else {
        fixedMappedDetail = "기타";
    }

    document.getElementById("fixedModalTitle").textContent = title + " 입력";

    document.getElementById("fixed_date").value = getTodayDate();
    document.getElementById("fixed_desc").value = detail;
    document.getElementById("fixed_amount").value = amount;
    document.getElementById("fixed_is_fuel").checked = isFuel;
    document.getElementById("fixed_price_per_liter").value = price || "";

    const fixedCategoryWrap = document.getElementById("fixed_category_wrap");
    const fixedCategory = document.getElementById("fixed_category");
    const fixedDetailCategory = document.getElementById("fixed_detail_category");

    if (fixedCategoryWrap) {
        fixedCategoryWrap.style.display = isFuel ? "block" : "none";
    }

    if (fixedCategory) {
        fixedCategory.value = "expense";
    }

    if (fixedDetailCategory) {
        fixedDetailCategory.value = fixedMappedDetail;
    }

    toggleFuelFields();

    document.getElementById("fixedModal").style.display = "flex";
}

function closeFixedModal() {
    document.getElementById("fixedModal").style.display = "none";
}

function toggleFuelFields() {
    const checked = document.getElementById("fixed_is_fuel").checked;
    document.getElementById("fixed_price_wrap").style.display =
        checked ? "flex" : "none";
}

function getTodayDate() {
    const d = new Date();
    const offset = d.getTimezoneOffset();
    const local = new Date(d.getTime() - offset * 60000);
    return local.toISOString().slice(0, 10);
}

function applyFixedModal() {
    document.getElementById("ui_date").value =
        document.getElementById("fixed_date").value;

    document.getElementById("ui_account").value = "shinhan";

    const isFuel = document.getElementById("fixed_is_fuel").checked;
    const fixedCategory = document.getElementById("fixed_category");
    const fixedDetailCategory = document.getElementById("fixed_detail_category");

    if (isFuel && fixedCategory) {
        document.getElementById("ui_category").value = fixedCategory.value;
    } else {
        document.getElementById("ui_category").value = "expense";
    }

    document.getElementById("ui_category").dispatchEvent(new Event('change'));

    if (fixedDetailCategory) {
        document.getElementById("ui_detail_category").value = fixedDetailCategory.value;
    } else {
        document.getElementById("ui_detail_category").value = fixedMappedDetail || "기타";
    }

    document.getElementById("ui_desc").value =
        document.getElementById("fixed_desc").value;

    document.getElementById("ui_amount").value =
        document.getElementById("fixed_amount").value;

    document.getElementById("ui_is_fuel").checked = isFuel;

    if (isFuel) {
        document.getElementById("ui_fuel_section").style.display = "block";
        document.getElementById("ui_fuel_price").value =
            document.getElementById("fixed_price_per_liter").value;
    } else {
        document.getElementById("ui_fuel_section").style.display = "none";
        document.getElementById("ui_fuel_price").value = "";
    }

    closeFixedModal();
    document.getElementById("main_form").submit();
}

document.addEventListener("DOMContentLoaded", function () {
    // LIVING_CATEGORY_MAP은 living.html의 <script> 태그에서 전역으로 주입됨
    // 메인 페이지(index.html)에서는 주입되지 않으므로, 없으면 빈 객체로 처리

    const categoryMap = (typeof LIVING_CATEGORY_MAP !== "undefined") ? LIVING_CATEGORY_MAP : {};

    window.updateLivingDetailOptions = function (groupId, detailId, selectedValue = null) {
        const groupSelect = document.getElementById(groupId);
        const detailSelect = document.getElementById(detailId);

        if (!groupSelect || !detailSelect) return;

        const groupValue = groupSelect.value;
        const options = categoryMap[groupValue] || [];

        detailSelect.innerHTML = "";

        options.forEach((item) => {
            const option = document.createElement("option");
            option.value = item.value;
            option.textContent = item.label;

            if (selectedValue && selectedValue === item.value) {
                option.selected = true;
            }

            detailSelect.appendChild(option);
        });
    };

    function bindLivingCategory(groupId, detailId) {
        const groupSelect = document.getElementById(groupId);
        if (!groupSelect) return;

        groupSelect.addEventListener("change", function () {
            updateLivingDetailOptions(groupId, detailId);
        });

        updateLivingDetailOptions(groupId, detailId);
    }

    bindLivingCategory("living-category-select", "ui_detail_category");
    bindLivingCategory("modal_category", "modal_detail_category");
});

// 수정 모달도 동일한 LIVING_CATEGORY_MAP 사용
function updateLivingEditDetailOptions(category, selectedValue = "") {
    const select = document.getElementById("edit_detail_category");
    if (!select) return;

    const categoryMap = (typeof LIVING_CATEGORY_MAP !== "undefined") ? LIVING_CATEGORY_MAP : {};
    const options = categoryMap[category] || [];

    select.innerHTML = "";

    options.forEach((item) => {
        const option = document.createElement("option");
        option.value = item.value;
        option.textContent = item.label;

        if (item.value === selectedValue) {
            option.selected = true;
        }

        select.appendChild(option);
    });
}

function openLivingEditModal(pk, date, category, detailCategory, description, amount) {
    const modal = document.getElementById("livingEditModal");
    if (!modal) return;

    document.getElementById("edit_pk").value = pk;
    document.getElementById("edit_date").value = date;
    document.getElementById("edit_description").value = description || "";
    document.getElementById("edit_amount").value = Math.abs(Number(amount));

    let uiCategory = category;

    if ((detailCategory || "").startsWith("비상금")) {
        uiCategory = "emergency";
    } else if ((detailCategory || "").startsWith("현금")) {
        uiCategory = "cash";
    }

    document.getElementById("edit_category").value = uiCategory;
    updateLivingEditDetailOptions(uiCategory, detailCategory);

    modal.style.display = "flex";
}

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".living-edit-btn").forEach((btn) => {
        btn.addEventListener("click", function () {
            openLivingEditModal(
                this.dataset.pk,
                this.dataset.date,
                this.dataset.category,
                this.dataset.detail,
                this.dataset.description,
                this.dataset.amount
            );
        });
    });

    // 메인 가계부 수정 모달
    document.querySelectorAll(".main-edit-btn").forEach((btn) => {
        btn.addEventListener("click", function () {
            openMainEditModal(
                this.dataset.pk,
                this.dataset.date,
                this.dataset.account,
                this.dataset.category,
                this.dataset.detail,
                this.dataset.description,
                this.dataset.amount,
                this.dataset.isFuel === "true",
                this.dataset.price,
                this.dataset.odometer
            );
        });
    });
});

document.addEventListener("DOMContentLoaded", function () {

    const editCategory = document.getElementById("main_edit_category");

    if (editCategory) {
        editCategory.addEventListener("change", function () {
            updateDetailOptions("main_edit_detail", this.value);
        });
    }

});

// 메인 가계부 수정 모달 열기
function openMainEditModal(pk, date, account, category, detail, description, amount, isFuel, price, odometer) {
    const modal = document.getElementById("mainEditModal");
    if (!modal) return;

    document.getElementById("main_edit_pk").value = pk;
    document.getElementById("main_edit_date").value = date;
    document.getElementById("main_edit_account").value = account;
    document.getElementById("main_edit_category").value = category;
    document.getElementById("main_edit_desc").value = description || "";
    document.getElementById("main_edit_amount").value = Math.abs(Number(amount));

    updateDetailOptions("main_edit_detail", category, detail);

    // 주유 체크
    const fuelCheck = document.getElementById("main_edit_is_fuel");
    const fuelWrap = document.getElementById("main_edit_fuel_wrap");
    const priceInput = document.getElementById("main_edit_price");
    const odometerInput = document.getElementById("main_edit_odometer");

    if (fuelCheck) fuelCheck.checked = isFuel;
    if (fuelWrap) fuelWrap.style.display = isFuel ? "block" : "none";
    if (priceInput) {
        // 1975.0 → 1975 처럼 소수점 제거
        priceInput.value = price ? Math.round(Number(price)) : "";
    }
    if (odometerInput) {
        // 139055 → 139,055 콤마 포맷
        odometerInput.value = odometer ? Number(odometer).toLocaleString("en-US") : "";
    }

    if (fuelCheck) {
        fuelCheck.addEventListener("change", function () {
            if (fuelWrap) fuelWrap.style.display = this.checked ? "block" : "none";
        });
    }

    modal.style.display = "flex";
}

// =========================
// 메인 가계부 category → detail 필터
// =========================
document.addEventListener("DOMContentLoaded", function () {
    const categorySelect = document.getElementById('ui_category');
    const detailSelect = document.getElementById('ui_detail_category');

    if (!categorySelect || !detailSelect) return;

    // 👉 Python에서 내려준 데이터
    const detailCategoryDataEl = document.getElementById('category-map-data');
    const detailCategoryMap = detailCategoryDataEl
        ? JSON.parse(detailCategoryDataEl.textContent)
        : {};

    categorySelect.addEventListener('change', function () {
        const selected = this.value;

        detailSelect.innerHTML = '';

        // 🔥 핵심: 이제 이걸 씀
        const options = detailCategoryMap[selected] || [];

        options.forEach(opt => {
            const option = document.createElement('option');
            option.value = opt.value;
            option.textContent = opt.label;
            detailSelect.appendChild(option);
        });
    });

    // 처음 실행
    categorySelect.dispatchEvent(new Event('change'));
});

function updateDetailOptions(selectId, category, selectedValue = null) {
    const select = document.getElementById(selectId);
    if (!select) return;

    const dataEl = document.getElementById('category-map-data');
    const categoryMap = dataEl ? JSON.parse(dataEl.textContent) : {};

    const options = categoryMap[category] || [];

    select.innerHTML = '';

    options.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt.value;
        option.textContent = opt.label;

        if (selectedValue && selectedValue === opt.value) {
            option.selected = true;
        }

        select.appendChild(option);
    });
}

function applyLivingQuickInput(category, detailCategory, description, amount = "") {
    const dateInput = document.getElementById("ui_date");
    const categorySelect = document.getElementById("living-category-select");
    const detailSelect = document.getElementById("ui_detail_category");
    const descInput = document.getElementById("ui_desc");
    const amountInput = document.getElementById("ui_amount");

    if (!categorySelect || !detailSelect) return;

    if (dateInput && !dateInput.value) {
        dateInput.value = getTodayDate();
    }

    categorySelect.value = category;

    if (typeof updateLivingDetailOptions === "function") {
        updateLivingDetailOptions("living-category-select", "ui_detail_category", detailCategory);
    } else {
        detailSelect.value = detailCategory;
    }

    if (descInput) descInput.value = description || "";
    if (amountInput) {
        amountInput.value = amount || "";
        amountInput.focus();
    }
}

// =========================
//  생활비 페이지 차트
// =========================

// 카테고리 도넛 차트
function initDonutChart() {
    const chartEl = document.getElementById('livingDonutChart');
    if (!chartEl || typeof DONUT_CHART_DATA === 'undefined') return;

    const labels = Array.isArray(DONUT_CHART_DATA.labels) ? DONUT_CHART_DATA.labels : [];
    const values = Array.isArray(DONUT_CHART_DATA.values) ? DONUT_CHART_DATA.values : [];

    if (!values.length) return;

    const total = values.reduce((a, b) => a + b, 0);
    if (total === 0) return;

    const palette = [
        '#d87955', '#e8a87c', '#f2c894',
        '#7cc9b1', '#5db89a', '#4969d9',
        '#7a62d7', '#b48610', '#17956f',
        '#c96d5a', '#8c6bd8', '#d77f75',
        '#cf7f5f',
    ];

    new Chart(chartEl, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: palette.slice(0, values.length),
                borderWidth: 2,
                borderColor: '#ffffff',
                hoverBorderWidth: 3,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '62%',
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            const v = ctx.parsed;
                            const pct = ((v / total) * 100).toFixed(1);
                            return `${ctx.label}: ${v.toLocaleString()}원 (${pct}%)`;
                        }
                    }
                }
            }
        },
        plugins: [{
            id: 'centerText',
            afterDraw: function(chart) {
                const { ctx, chartArea } = chart;
                const cx = (chartArea.left + chartArea.right) / 2;
                const cy = (chartArea.top + chartArea.bottom) / 2;

                ctx.save();
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';

                ctx.font = '700 13px "LeeJiEun", "Pretendard", sans-serif';
                ctx.fillStyle = '#9a7a7d';
                ctx.fillText('총 지출', cx, cy - 14);

                ctx.font = '900 20px "LeeJiEun", "Pretendard", sans-serif';
                ctx.fillStyle = '#d87955';
                ctx.fillText(total.toLocaleString() + '원', cx, cy + 12);

                ctx.restore();
            }
        }]
    });
}

// 관리비 1년 추이 (올해 막대 + 작년 선)
function initRentChart() {
    const chartEl = document.getElementById('livingRentChart');
    if (!chartEl || typeof RENT_CHART_DATA === 'undefined') return;

    const labels = RENT_CHART_DATA.labels;
    const values = RENT_CHART_DATA.values;
    const prevValues = RENT_CHART_DATA.prevValues || [];

    // 올해 막대: 마지막 달(선택월)만 진한 민트, 나머지는 연한 민트
    const barColors = values.map((v, i) =>
        i === values.length - 1 ? '#5db89a' : '#b8e7d7'
    );

    new Chart(chartEl, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '올해',
                    type: 'bar',
                    data: values,
                    backgroundColor: barColors,
                    borderRadius: 6,
                    borderSkipped: false,
                    maxBarThickness: 28,
                    order: 2,
                },
                {
                    label: '작년',
                    type: 'line',
                    data: prevValues,
                    borderColor: '#d8a7a7',
                    backgroundColor: '#d8a7a7',
                    borderWidth: 2,
                    borderDash: [5, 4],
                    pointRadius: 3,
                    pointBackgroundColor: '#d8a7a7',
                    tension: 0.3,
                    fill: false,
                    order: 1,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    align: 'end',
                    labels: {
                        font: { size: 11, family: '"LeeJiEun", "Pretendard", sans-serif' },
                        color: '#9a7a7d',
                        boxWidth: 12,
                        padding: 10,
                    }
                },
                tooltip: {
                    callbacks: {
                        title: function(ctx) {
                            return ctx[0].label;
                        },
                        label: function(ctx) {
                            return ctx.dataset.label + ': ' + ctx.parsed.y.toLocaleString() + '원';
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: {
                        font: { size: 11, family: '"LeeJiEun", "Pretendard", sans-serif' },
                        color: '#9a7a7d',
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: '#f0ebe8' },
                    ticks: {
                        font: { size: 11, family: '"LeeJiEun", "Pretendard", sans-serif' },
                        color: '#9a7a7d',
                        callback: function(v) {
                            if (v >= 10000) return (v / 10000) + '만';
                            return v.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

// =========================
// living.html JSON 데이터 읽기
// =========================

function getJsonScriptData(id, defaultValue = null) {
    const el = document.getElementById(id);
    if (!el) return defaultValue;

    try {
        return JSON.parse(el.textContent);
    } catch (e) {
        console.log(id + " JSON parse error:", e);
        return defaultValue;
    }
}

// 생활비 카테고리 맵
const livingCategoryMapData = getJsonScriptData("living-category-map-data", {});
if (Object.keys(livingCategoryMapData).length > 0) {
    window.LIVING_CATEGORY_MAP = livingCategoryMapData;
}

// 도넛차트 데이터
const donutLabels = getJsonScriptData("living-chart-labels", []);
const donutValues = getJsonScriptData("living-chart-values", []);

if (donutLabels.length && donutValues.length) {
    window.DONUT_CHART_DATA = {
        labels: donutLabels,
        values: donutValues
    };
}

// 관리비 차트 데이터
const rentLabels = getJsonScriptData("living-rent-labels", []);
const rentValues = getJsonScriptData("living-rent-values", []);
const rentPrevValues = getJsonScriptData("living-rent-prev-values", []);

if (rentLabels.length && rentValues.length) {
    window.RENT_CHART_DATA = {
        labels: rentLabels,
        values: rentValues,
        prevValues: rentPrevValues
    };
}

// 페이지 로드 시 차트 초기화
document.addEventListener("DOMContentLoaded", function () {
    initDonutChart();
    initRentChart();
});

// ===== 거래 내역 필터 =====
document.addEventListener("DOMContentLoaded", function () {
    // 생활비 통장 필터
    const livingFilter = document.getElementById("living_history_filter");
    if (livingFilter) {
        livingFilter.addEventListener("change", function () {
            const val = this.value;
            const items = document.querySelectorAll(".living-history-item");
            let visible = 0;
            items.forEach(el => {
                const show = (val === "all" || el.dataset.filterType === val);
                el.style.display = show ? "" : "none";
                if (show) visible++;
            });
            document.getElementById("living_history_empty").style.display = visible ? "none" : "block";
        });
    }

    // 메인 가계부 필터
    const mainFilter = document.getElementById("main_history_filter");
    if (mainFilter) {
        mainFilter.addEventListener("change", function () {
            const val = this.value;
            const items = document.querySelectorAll(".history-row[data-filter-account]");
            let visible = 0;
            items.forEach(el => {
                const show = (val === "all" || el.dataset.filterAccount === val);
                el.style.display = show ? "" : "none";
                if (show) visible++;
            });
            document.getElementById("main_history_empty").style.display = visible ? "none" : "block";
        });
    }
});

document.addEventListener("DOMContentLoaded", function () {
    const rows = document.querySelectorAll(".main-history-row");
    const btn = document.getElementById("loadMoreBtn");

    const SHOW_COUNT = 8;
    let visibleCount = SHOW_COUNT;

    // 처음에는 5개만 보여주기
    rows.forEach((row, index) => {
        if (index >= SHOW_COUNT) {
            row.classList.add("hidden");
        }
    });

    btn.addEventListener("click", () => {
        const hiddenRows = document.querySelectorAll(".history-row.hidden");

        hiddenRows.forEach(row => {
            row.classList.remove("hidden");
        });

        btn.style.display = "none";
    });

    if (rows.length <= SHOW_COUNT) {
        btn.style.display = "none";
    }
});

document.addEventListener("DOMContentLoaded", function () {
    const details = document.querySelector(".check-details");
    const checkboxes = document.querySelectorAll(".check-form input[type='checkbox']");

    // 체크 안된 게 하나라도 있는지 확인
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);

    if (allChecked) {
        details.removeAttribute("open"); // 닫기
    }
});

function updateSummary() {
    const items = document.querySelectorAll(".checklist-line");
    let total = 0;
    let done = 0;

    items.forEach(item => {
        const checkbox = item.querySelector("input");
        const text = item.innerText;

        const amountMatch = text.match(/([\d,]+)원/);
        const amount = amountMatch ? Number(amountMatch[1].replace(/,/g, "")) : 0;

        total += amount;

        if (checkbox.checked) {
            done += amount;
        }
    });

    document.querySelector(".check-summary-title").innerText =
        `완료 ${document.querySelectorAll(".check-form input:checked").length}/${items.length}`;

    document.querySelector(".check-summary-amount").innerText =
        `${done.toLocaleString()}원 / ${total.toLocaleString()}원`;
}

document.querySelectorAll(".check-form input[type='checkbox']").forEach(cb => {
    cb.addEventListener("change", function () {

        const form = this.closest("form");
        const label = this.closest(".checklist-line");
        const amount = parseInt(label.dataset.amount || 0);

        const summary = document.getElementById("checkSummary");

        let total = parseInt(summary.dataset.total || 0);
        let done = parseInt(summary.dataset.done || 0);

        // 👉 체크 상태에 따라 금액 증감
        if (this.checked) {
            done += amount;
        } else {
            done -= amount;
        }

        // 👉 화면 즉시 반영
        summary.dataset.done = done;
        summary.innerText = `${done.toLocaleString()}원 / ${total.toLocaleString()}원`;

        // 👉 서버에도 저장
        fetch(form.action, {
            method: "POST",
            body: new FormData(form),
            headers: {
                "X-CSRFToken": form.querySelector('[name=csrfmiddlewaretoken]').value
            }
        });
    });
});

document.addEventListener("DOMContentLoaded", function () {
    setTimeout(() => {
        updateSummary();
    }, 0);
});

// =========================
// 누적 주행거리 - 실시간 콤마 포맷 & 제출 시 콤마 제거
// =========================
document.addEventListener("DOMContentLoaded", function () {
    const odometerIds = ["ui_odometer", "modal_odometer", "main_edit_odometer"];

    odometerIds.forEach((id) => {
        const input = document.getElementById(id);
        if (!input) return;

        // 타이핑할 때마다 콤마 포맷
        input.addEventListener("input", function () {
            // 숫자만 남기기
            const raw = this.value.replace(/[^\d]/g, "");
            if (raw === "") {
                this.value = "";
                return;
            }
            // 콤마 포맷
            this.value = Number(raw).toLocaleString("en-US");
        });
    });

    // 폼 submit 직전에 콤마 제거해서 숫자만 서버로 전송
    document.querySelectorAll("form").forEach((form) => {
        form.addEventListener("submit", function () {
            odometerIds.forEach((id) => {
                const input = form.querySelector("#" + id);
                if (input && input.value) {
                    input.value = input.value.replace(/,/g, "");
                }
            });
        });
    });
});