import requests
import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo


st.set_page_config(
    page_title="학교 급식 찾아보기",
    page_icon="🍱",
    layout="wide",
)

st.title("학교 급식 찾아보기")


# --------------------------------------------------
# 기본 설정
# --------------------------------------------------

SCHOOL_API_URL = (
    "https://open.neis.go.kr/hub/schoolInfo"
)

MEAL_API_URL = (
    "https://open.neis.go.kr/hub/mealServiceDietInfo"
)

KST = ZoneInfo("Asia/Seoul")


# --------------------------------------------------
# API 요청 함수
# --------------------------------------------------

@st.cache_data(ttl=600)
def search_schools(school_name):
    """학교 이름으로 학교 정보 검색"""

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

        rows = data["schoolInfo"][1]["row"]

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
def get_meal(
    office_code,
    school_code,
    date_value,
):
    """선택한 학교의 특정 날짜 중식 조회"""

    params = {
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
        "MLSV_YMD": date_value,
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

        rows = data["mealServiceDietInfo"][1]["row"]

        return rows

    except Exception:
        return []


# --------------------------------------------------
# 학교 이름 보정
# --------------------------------------------------

def make_search_names(name):
    """
    사용자가 줄여서 입력했을 경우
    한 번 더 검색할 이름을 만든다.

    예:
    수도여고 → 수도여자고등학교
    서울고 → 서울고등학교
    """

    names = [name]

    expanded = name

    if "여고" in expanded:
        expanded = expanded.replace(
            "여고",
            "여자고등학교",
        )
    elif expanded.endswith("고"):
        expanded = expanded[:-1] + "고등학교"

    if expanded != name:
        names.append(expanded)

    return names


def find_schools(user_input):
    """일반 검색 후, 필요하면 학교명 축약어를 풀어서 재검색"""

    search_names = make_search_names(user_input)

    all_schools = []

    for search_name in search_names:
        schools = search_schools(search_name)

        for school in schools:
            school_key = (
                school["office_code"],
                school["school_code"],
            )

            if not any(
                (
                    s["office_code"],
                    s["school_code"],
                ) == school_key
                for s in all_schools
            ):
                all_schools.append(school)

        # 첫 번째 검색에서 결과가 있으면
        # 불필요하게 확장 검색을 하지 않는다.
        if schools:
            break

    return all_schools


# --------------------------------------------------
# 학교 검색
# --------------------------------------------------

school_input = st.text_input(
    "학교 이름",
    placeholder="예: 수도여고, 서울고, 서울대학교사범대학부설고등학교",
)

if school_input.strip():

    schools = find_schools(school_input.strip())

    if not schools:
        st.warning(
            "입력한 학교를 찾지 못했어요. "
            "학교 이름을 조금 더 정확하게 입력해 주세요."
        )
        st.stop()

    school_options = {}

    for school in schools:
        label = (
            f'{school["school_name"]} '
            f'({school["office_name"]})'
        )

        if school["address"]:
            label += f' - {school["address"]}'

        school_options[label] = school

    selected_label = st.selectbox(
        "학교를 선택하세요",
        list(school_options.keys()),
    )

    selected_school = school_options[selected_label]

    st.success(
        f'선택한 학교: {selected_school["school_name"]} '
        f'({selected_school["office_name"]})'
    )

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
    # 중식 조회
    # --------------------------------------------------

    meals = get_meal(
        selected_school["office_code"],
        selected_school["school_code"],
        date_string,
    )

    # 중식만 선택
    lunch_meals = [
        meal
        for meal in meals
        if meal.get("MMEAL_SC_NM") == "중식"
    ]

    if not lunch_meals:
        st.info(
            f"{selected_date.strftime('%Y년 %m월 %d일')}에는 "
            "등록된 중식 급식이 없습니다."
        )
        st.stop()

    meal = lunch_meals[0]

    st.subheader(
        f"🍱 {selected_date.strftime('%Y년 %m월 %d일')} 중식"
    )

    # --------------------------------------------------
    # 메뉴
    # --------------------------------------------------

    menu = meal.get("DDISH_NM", "")

    if menu:
        # NEIS 메뉴에는 <br/>가 들어 있으므로 줄바꿈으로 변경
        menu_lines = menu.replace(
            "<br/>",
            "\n",
        ).replace(
            "<br>",
            "\n",
        )

        st.markdown("### 메뉴")

        for item in menu_lines.split("\n"):
            item = item.strip()

            if item:
                st.write(f"• {item}")

    # --------------------------------------------------
    # 알레르기 번호
    # --------------------------------------------------

    allergy = meal.get("DDISH_NM", "")

    # 메뉴 문자열 안에 붙어 있는 알레르기 번호는
    # 그대로 원문 형태로 보여 준다.
    st.markdown("### 알레르기 번호")

    allergy_numbers = []

    import re

    for number in re.findall(
        r"\(([\d.,]+)\)",
        allergy,
    ):
        allergy_numbers.append(number)

    if allergy_numbers:
        unique_numbers = []

        for number_group in allergy_numbers:
            for number in number_group.split(","):
                number = number.strip()

                if number and number not in unique_numbers:
                    unique_numbers.append(number)

        st.write(", ".join(unique_numbers))
    else:
        st.write("표시된 알레르기 번호가 없습니다.")

    # --------------------------------------------------
    # 칼로리
    # --------------------------------------------------

    calories = meal.get("CAL_INFO", "")

    st.markdown("### 칼로리")

    if calories:
        st.write(calories)
    else:
        st.write("칼로리 정보가 없습니다.")

else:
    st.info(
        "학교 이름을 입력하면 학교를 검색할 수 있습니다."
    )
