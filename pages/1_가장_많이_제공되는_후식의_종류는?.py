import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
import streamlit as st


st.set_page_config(
    page_title="가장 많이 제공되는 후식의 종류는?",
    page_icon="🍎",
    layout="wide",
)

st.title("가장 많이 제공되는 후식의 종류는?")


# --------------------------------------------------
# NEIS API 설정
# --------------------------------------------------

SCHOOL_API_URL = "https://open.neis.go.kr/hub/schoolInfo"
MEAL_API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"

SCHOOL_NAME = "송탄고등학교"
KST = ZoneInfo("Asia/Seoul")


# --------------------------------------------------
# 송탄고등학교 정보 조회
# --------------------------------------------------

@st.cache_data(ttl=3600)
def get_school_info():
    params = {
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "SCHUL_NM": SCHOOL_NAME,
    }

    try:
        response = requests.get(
            SCHOOL_API_URL,
            params=params,
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        if "schoolInfo" not in data:
            return None

        if len(data["schoolInfo"]) < 2:
            return None

        rows = data["schoolInfo"][1].get("row", [])

        for row in rows:
            if row.get("SCHUL_NM") == SCHOOL_NAME:
                return {
                    "office_code": row.get("ATPT_OFCDC_SC_CODE"),
                    "school_code": row.get("SD_SCHUL_CODE"),
                }

        return None

    except Exception:
        return None


# --------------------------------------------------
# 특정 날짜 급식 조회
# --------------------------------------------------

@st.cache_data(ttl=600)
def get_meal(
    office_code,
    school_code,
    date_string,
):
    params = {
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
        "MLSV_YMD": date_string,
    }

    try:
        response = requests.get(
            MEAL_API_URL,
            params=params,
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        if "mealServiceDietInfo" not in data:
            return None

        if len(data["mealServiceDietInfo"]) < 2:
            return None

        rows = data["mealServiceDietInfo"][1].get("row", [])

        for row in rows:
            if row.get("MMEAL_SC_NM") == "중식":
                return row

        return None

    except Exception:
        return None


# --------------------------------------------------
# 일정 기간 급식 조회
# --------------------------------------------------

@st.cache_data(ttl=3600)
def get_meals_for_period(
    office_code,
    school_code,
    from_date,
    to_date,
):
    params = {
        "Type": "json",
        "pIndex": 1,
        "pSize": 1000,
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
        "MLSV_FROM_YMD": from_date,
        "MLSV_TO_YMD": to_date,
    }

    try:
        response = requests.get(
            MEAL_API_URL,
            params=params,
            timeout=20,
        )
        response.raise_for_status()

        data = response.json()

        if "mealServiceDietInfo" not in data:
            return []

        if len(data["mealServiceDietInfo"]) < 2:
            return []

        rows = data["mealServiceDietInfo"][1].get("row", [])

        return [
            row
            for row in rows
            if row.get("MMEAL_SC_NM") == "중식"
        ]

    except Exception:
        return []


# --------------------------------------------------
# 메뉴 분리
# --------------------------------------------------

def split_menu(menu_text):
    return [
        menu.strip()
        for menu in re.split(
            r"<br\s*/?>",
            menu_text,
            flags=re.IGNORECASE,
        )
        if menu.strip()
    ]


# --------------------------------------------------
# 알레르기 번호 제거
# --------------------------------------------------

def remove_allergy_numbers(menu):
    return re.sub(
        r"\s*\([\d,\.\s]+\)",
        "",
        menu,
    ).strip()


# --------------------------------------------------
# 후식 종류 판별
# --------------------------------------------------

DESSERT_KEYWORDS = {
    "과일": [
        "사과",
        "배",
        "귤",
        "오렌지",
        "한라봉",
        "천혜향",
        "딸기",
        "포도",
        "샤인머스켓",
        "수박",
        "참외",
        "복숭아",
        "바나나",
        "키위",
        "파인애플",
        "망고",
        "블루베리",
        "메론",
        "멜론",
        "과일",
        "방울토마토",
        "토마토",
    ],
    "음료": [
        "주스",
        "쥬스",
        "음료",
        "차",
        "요구르트",
        "요구르트",
        "우유",
        "두유",
        "에이드",
        "식혜",
        "수정과",
        "코코아",
    ],
    "빵": [
        "빵",
        "케이크",
        "롤케이크",
        "카스텔라",
        "카스테라",
        "머핀",
        "도넛",
        "도너츠",
        "쿠키",
        "파이",
        "와플",
        "마들렌",
    ],
    "아이스크림": [
        "아이스크림",
        "아이스바",
        "바",
        "하드",
        "빙과",
    ],
    "떡": [
        "떡",
        "절편",
        "인절미",
        "백설기",
        "찹쌀떡",
        "송편",
    ],
    "과자": [
        "과자",
        "스낵",
        "칩",
        "웨하스",
        "비스킷",
        "프레첼",
    ],
    "푸딩": [
        "푸딩",
        "젤리",
        "양갱",
    ],
    "유제품": [
        "요거트",
        "요구르트",
        "플레인",
        "치즈",
    ],
}


def classify_dessert(menu):
    clean_menu = remove_allergy_numbers(menu).lower()

    for dessert_type, keywords in DESSERT_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in clean_menu:
                return dessert_type

    return None


# --------------------------------------------------
# 학교 정보
# --------------------------------------------------

school = get_school_info()

if school is None:
    st.error(
        "송탄고등학교의 학교 정보를 불러오지 못했습니다."
    )
    st.stop()


# --------------------------------------------------
# 날짜 / 알레르기 스위치
# --------------------------------------------------

today_kst = datetime.now(KST).date()

date_col, allergy_col = st.columns([3, 1])

with date_col:
    selected_date = st.date_input(
        "날짜",
        value=today_kst,
        max_value=today_kst,
    )

with allergy_col:
    st.write("")
    st.write("")

    show_allergy = st.toggle(
        "알레르기 정보 보기",
        value=True,
    )


# --------------------------------------------------
# 선택한 날짜 급식 조회
# --------------------------------------------------

date_string = selected_date.strftime("%Y%m%d")

meal = get_meal(
    school["office_code"],
    school["school_code"],
    date_string,
)

if meal is None:
    st.info("급식이 없는 날입니다")
    st.stop()


menu_text = meal.get("DDISH_NM", "")
calorie = meal.get("CAL_INFO", "")

all_menus = split_menu(menu_text)

if not all_menus:
    st.info("급식이 없는 날입니다")
    st.stop()


# --------------------------------------------------
# 후식만 추출
# --------------------------------------------------

dessert_menus = []

for menu in all_menus:
    dessert_type = classify_dessert(menu)

    if dessert_type:
        dessert_menus.append(
            {
                "menu": menu,
                "type": dessert_type,
            }
        )


if not dessert_menus:
    st.info("이날 제공되는 후식이 없습니다.")
    st.stop()


# --------------------------------------------------
# 최근 1년간 후식 종류별 제공 횟수 계산
# --------------------------------------------------

period_end = selected_date
period_start = selected_date - timedelta(days=365)

period_meals = get_meals_for_period(
    school["office_code"],
    school["school_code"],
    period_start.strftime("%Y%m%d"),
    period_end.strftime("%Y%m%d"),
)

dessert_counts = {}

for period_meal in period_meals:
    period_menu_text = period_meal.get("DDISH_NM", "")
    period_menus = split_menu(period_menu_text)

    for period_menu in period_menus:
        dessert_type = classify_dessert(period_menu)

        if dessert_type:
            dessert_counts[dessert_type] = (
                dessert_counts.get(dessert_type, 0) + 1
            )


# --------------------------------------------------
# 후식 종류 순위 계산
# --------------------------------------------------

ranking = sorted(
    dessert_counts.items(),
    key=lambda x: (-x[1], x[0]),
)

rank_map = {
    dessert_type: rank
    for rank, (dessert_type, count) in enumerate(
        ranking,
        start=1,
    )
}


# --------------------------------------------------
# 제목
# --------------------------------------------------

st.divider()

st.subheader(
    f"🍎 {selected_date.strftime('%Y년 %m월 %d일')} 후식"
)


# --------------------------------------------------
# 큰 숫자 카드
# --------------------------------------------------

metric1, metric2 = st.columns(2)

with metric1:
    st.metric(
        "메뉴 가짓수",
        f"{len(dessert_menus)}가지",
    )

with metric2:
    st.metric(
        "칼로리",
        calorie if calorie else "정보 없음",
    )


# --------------------------------------------------
# 메뉴 카드
# --------------------------------------------------

st.markdown("### 오늘의 후식")

for start in range(0, len(dessert_menus), 3):
    cols = st.columns(3)

    for i, col in enumerate(cols):
        index = start + i

        if index >= len(dessert_menus):
            break

        dessert = dessert_menus[index]

        original_menu = dessert["menu"]
        dessert_type = dessert["type"]

        if show_allergy:
            display_menu = original_menu
        else:
            display_menu = remove_allergy_numbers(
                original_menu
            )

        rank = rank_map.get(dessert_type)

        with col:
            with st.container(border=True):
                if rank is not None:
                    st.caption(
                        f"{rank}위 · {dessert_type}"
                    )

                st.markdown(
                    f"### {display_menu}"
                )
