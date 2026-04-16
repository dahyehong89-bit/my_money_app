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

// 2. 고정비 퀵버튼 (클릭 시 값을 모달에 채우고 오픈)
function quickSave(label, amount, account) {
    const today = new Date().toISOString().substring(0, 10);

    const modalDate = document.getElementById('modal_date');
    const modalDesc = document.getElementById('modal_desc');
    const modalAmount = document.getElementById('modal_amount');
    const modalAccount = document.getElementById('modal_account');
    const modalCategory = document.getElementById('modal_category');
    const fuelSection = document.getElementById('modal_fuel_section');
    const isFuelInput = document.getElementById('modal_is_fuel');
    const confirmModal = document.getElementById('confirmModal');

    if (modalDate) modalDate.value = today;
    if (modalDesc) modalDesc.value = label;
    if (modalAmount) modalAmount.value = amount;
    if (modalAccount) modalAccount.value = account;
    if (modalCategory) modalCategory.value = 'expense';

    if (label.includes('주유')) {
        if (fuelSection) fuelSection.style.display = 'block';
        if (isFuelInput) isFuelInput.value = 'on';
    } else {
        if (fuelSection) fuelSection.style.display = 'none';
        if (isFuelInput) isFuelInput.value = 'off';

        const modalFuelPrice = document.getElementById('modal_fuel_price');
        if (modalFuelPrice) modalFuelPrice.value = '';
    }

    if (confirmModal) confirmModal.style.display = 'flex';
    calcLiterInModal();
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

    const items = categoryDetailMap[category] || [];

    title.textContent = category + ' 세부내역';

    if (items.length === 0) {
        body.innerHTML = '<p class="empty-text">내역이 없습니다.</p>';
    } else {
        body.innerHTML = items.map(item => `
            <div class="modal-history-row">
                <div class="modal-history-left">
                    <span class="history-date">${item.date}</span>
                    <span class="tag">${item.account_type}</span>
                    <span>${item.description || ''}</span>
                </div>
                <div>
                    <strong class="expense">${Number(item.amount).toLocaleString()}원</strong>
                </div>
            </div>
        `).join('');
    }

    modal.style.display = 'flex';
}

function closeCategoryModal() {
    document.getElementById('categoryModal').style.display = 'none';
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