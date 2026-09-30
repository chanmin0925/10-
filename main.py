import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st


st.set_page_config(
    page_title="학교 급식 찾아보기",
    page_icon="🍱",
)

st.title("학교 급식 찾아보기")


SCHOOL_API_URL = "https://open.neis.go.kr/hub/schoolInfo"
MEAL_API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"

KST = ZoneInfo("Asia/Seoul")


@st.cache_data(ttl=600)
def search_schools(school_name):
    params = {
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "SCHUL_NM": school_name,
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
            return []

        if len(data["schoolInfo"]) < 2:
            return []

        rows = data["schoolInfo"][1].get("row", [])

        schools = []

        for row in rows:
            schools.append(
                {
                    "school_name": row.get("SCHUL_NM", ""),
                    "school_type": row.get("SCHUL_KND_SC_NM", ""),
                    "office_name": row.get("ATPT_OFCDC_SC_NM", ""),
                    "office_code": row.get("ATPT_OFCDC_SC_CODE", ""),
                    "school_code": row.get("SD_SCHUL_CODE", ""),
                    "address": row.get("ORG_RDNMA", ""),
                }
            )

        return schools

    except Exception:
        return []


@st.cache_data(ttl=600)
def get_meal(office_code, school_code, date_string):
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
            return []

        if len(data["mealServiceDietInfo"]) < 2:
            return []

        return data["mealServiceDietInfo"][1].get("row", [])

    except Exception:
        return []


def make_search_names(name):
    names = [name]

    expanded_name = name

    if "여고" in expanded_name:
        expanded_name = expanded_name.replace(
            "여고",
            "여자고등학교",
        )
    elif expanded_name.endswith("고"):
        expanded_name = expanded_name[:-1] + "고등학교"

    if expanded_name != name:
        names.append(expanded_name)

    return names


def find_schools(name):
    search_names = make_search_names(name)

    all_schools = []

    for search_name in search_names:
        schools = search_schools(search_name)

        if schools:
            all_schools.extend(schools)

            # 원래 검색어로 찾은 학교가 있으면
            # 확장 검색은 하지 않는다.
            break

    unique_schools = []
    seen = set()

    for school in all_schools:
        key = (
            school["office_code"],
            school["school_code"],
        )

        if key not in seen:
            seen.add(key)
            unique_schools.append(school)

    return unique_schools


# --------------------------------------------------
# 학교 검색
# --------------------------------------------------

school_name = st.text_input(
    "학교 이름을 입력하세요",
    placeholder="예: 수도여고",
)

if not school_name.strip():
    st.info("학교 이름을 입력하면 학교를 검색할 수 있습니다.")
    st.stop()


schools = find_schools(school_name.strip())

if not schools:
    st.warning(
        "입력한 학교를 찾지 못했어요. "
        "학교 이름을 확인한 뒤 다시 입력해 주세요."
    )
    st.stop()


# --------------------------------------------------
# 학교 선택
# --------------------------------------------------

school_options = {}

for school in schools:
    label = (
        f'{school["school_name"]} '
        f'— {school["office_name"]}'
    )

    if school["address"]:
        label += f' — {school["address"]}'

    school_options[label] = school


selected_label = st.selectbox(
    "학교를 선택하세요",
    list(school_options.keys()),
)

selected_school = school_options[selected_label]


# --------------------------------------------------
# 날짜 선택
# --------------------------------------------------

today_kst = datetime.now(KST).date()

selected_date = st.date_input(
    "급식 날짜",
    value=today_kst,
    max_value=today_kst,
)

date_string = selected_date.strftime("%Y%m%d")


# --------------------------------------------------
# 급식 조회
# --------------------------------------------------

meals = get_meal(
    selected_school["office_code"],
    selected_school["school_code"],
    date_string,
)

lunch_meals = [
    meal
    for meal in meals
    if meal.get("MMEAL_SC_NM") == "중식"
]


if not lunch_meals:
    st.info(
        f'{selected_date.strftime("%Y년 %m월 %d일")}에는 '
        "등록된 중식 급식이 없습니다."
    )
    st.stop()


meal = lunch_meals[0]


# --------------------------------------------------
# 급식 표시
# --------------------------------------------------

st.divider()

st.subheader(
    f'🍱 {selected_school["school_name"]} '
    f'{selected_date.strftime("%Y년 %m월 %d일")} 중식'
)


# --------------------------------------------------
# 메뉴
# --------------------------------------------------

dish_name = meal.get("DDISH_NM", "")

st.markdown("### 메뉴")

if dish_name:
    menu_lines = re.split(
        r"<br\s*/?>",
        dish_name,
    )

    for menu in menu_lines:
        menu = menu.strip()

        if menu:
            st.write(f"• {menu}")
else:
    st.write("메뉴 정보가 없습니다.")


# --------------------------------------------------
# 알레르기 번호
# --------------------------------------------------

st.markdown("### 알레르기 번호")

allergy_numbers = re.findall(
    r"\(([\d,\.\s]+)\)",
    dish_name,
)

numbers = []

for group in allergy_numbers:
    for number in group.split(","):
        number = number.strip()

        if number and number not in numbers:
            numbers.append(number)

if numbers:
    st.write(", ".join(numbers))
else:
    st.write("표시된 알레르기 번호가 없습니다.")


# --------------------------------------------------
# 칼로리
# --------------------------------------------------

st.markdown("### 칼로리")

calorie = meal.get("CAL_INFO", "")

if calorie:
    st.write(calorie)
else:
    st.write("칼로리 정보가 없습니다.")
