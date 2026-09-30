import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st


st.set_page_config(
    page_title="가장 많이 제공되는 후식의 종류는?",
    page_icon="🍱",
    layout="wide",
)

st.title("가장 많이 제공되는 후식의 종류는?")


# --------------------------------------------------
# NEIS API
# --------------------------------------------------

SCHOOL_API_URL = "https://open.neis.go.kr/hub/schoolInfo"
MEAL_API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"

SCHOOL_NAME = "송탄고등학교"
KST = ZoneInfo("Asia/Seoul")


@st.cache_data(ttl=600)
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


@st.cache_data(ttl=600)
def get_lunch(office_code, school_code, date_string):
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
# 메뉴 처리
# --------------------------------------------------

def split_menu(menu_text):
    """NEIS의 <br/>를 기준으로 메뉴를 나눈다."""
    return [
        menu.strip()
        for menu in re.split(
            r"<br\s*/?>",
            menu_text,
            flags=re.IGNORECASE,
        )
        if menu.strip()
    ]


def remove_allergy_numbers(menu):
    """메뉴 뒤의 알레르기 번호를 제거한다."""
    return re.sub(
        r"\s*\([\d,\.\s]+\)",
        "",
        menu,
    ).strip()


# --------------------------------------------------
# 학교 정보 가져오기
# --------------------------------------------------

school = get_school_info()

if school is None:
    st.error(
        "송탄고등학교의 학교 정보를 불러오지 못했습니다."
    )
    st.stop()


# --------------------------------------------------
# 날짜 + 알레르기 스위치
# --------------------------------------------------

date_col, allergy_col = st.columns([3, 1])

with date_col:
    today_kst = datetime.now(KST).date()

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
# 중식 조회
# --------------------------------------------------

date_string = selected_date.strftime("%Y%m%d")

meal = get_lunch(
    school["office_code"],
    school["school_code"],
    date_string,
)


# --------------------------------------------------
# 급식이 없는 경우
# --------------------------------------------------

if meal is None:
    st.info("급식이 없는 날입니다")
    st.stop()


# --------------------------------------------------
# 급식 정보
# --------------------------------------------------

menu_text = meal.get("DDISH_NM", "")
calorie = meal.get("CAL_INFO", "")

menus = split_menu(menu_text)

if not menus:
    st.info("급식이 없는 날입니다")
    st.stop()


# --------------------------------------------------
# 날짜 제목
# --------------------------------------------------

st.divider()

st.subheader(
    f"🍱 {selected_date.strftime('%Y년 %m월 %d일')} 중식"
)


# --------------------------------------------------
# 메뉴 가짓수 / 칼로리
# --------------------------------------------------

metric1, metric2 = st.columns(2)

with metric1:
    st.metric(
        "메뉴 가짓수",
        f"{len(menus)}가지",
    )

with metric2:
    st.metric(
        "칼로리",
        calorie if calorie else "정보 없음",
    )


# --------------------------------------------------
# 메뉴 카드
# --------------------------------------------------

st.markdown("### 오늘의 메뉴")

# 메뉴를 3개씩 한 줄에 배치
for start in range(0, len(menus), 3):
    cols = st.columns(3)

    for i, col in enumerate(cols):
        index = start + i

        if index >= len(menus):
            break

        menu = menus[index]

        if not show_allergy:
            menu = remove_allergy_numbers(menu)

        with col:
            with st.container(border=True):
                st.markdown(
                    f"### {menu}"
                )
