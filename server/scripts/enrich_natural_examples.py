# -*- coding: utf-8 -*-
"""
자연스러운 맞춤형 예문 생성기 및 데이터셋 보정 스크립트
1. 한글 받침 자동 분석 기반 조사(은/는, 이/가, 을/를) 자연스러운 결합
2. 고정 템플릿(plays an essential role) 제거 및 40+종 이상의 다채로운 실생활/비즈니스 예문 풀 적용
3. 잘못된 번역 표기(예: enquiry -> '인콰이어리' -> '문의, 질문') 교정 및 특화 예문 부여
"""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# 한글 받침 판별 및 조사 부착
def attach_particle(word: str, p_type: str) -> str:
    if not word:
        return ""
    last_char = word[-1]
    code = ord(last_char)
    if 0xAC00 <= code <= 0xD7A3:
        has_batchim = (code - 0xAC00) % 28 != 0
    else:
        has_batchim = False

    if p_type == "topic":  # 은/는
        return f"{word}{'은' if has_batchim else '는'}"
    elif p_type == "subj":  # 이/가
        return f"{word}{'이' if has_batchim else '가'}"
    elif p_type == "obj":   # 을/를
        return f"{word}{'을' if has_batchim else '를'}"
    elif p_type == "with":  # 과/와
        return f"{word}{'과' if has_batchim else '와'}"
    return word

# 주요 단어별 고품질 정통 사전 예문 및 한국어 뜻 교정 사전
SPECIFIC_WORDS = {
    "enquiry": {
        "meaning": "문의, 질문, 조사",
        "en": "We received an enquiry regarding the product specifications.",
        "ko": "우리는 제품 사양에 관한 문의를 받았다."
    },
    "inquiry": {
        "meaning": "문의, 조사, 탐구",
        "en": "The customer service center handled over a hundred inquiries today.",
        "ko": "고객 지원 센터는 오늘 100건 이상의 문의를 처리했다."
    },
    "breakfast": {
        "meaning": "아침 식사",
        "en": "I usually have a light breakfast with toast and coffee.",
        "ko": "나는 보통 토스트와 커피로 가벼운 아침 식사를 한다."
    },
    "meal": {
        "meaning": "식사, 한 끼",
        "en": "They enjoyed a delicious home-cooked meal together.",
        "ko": "그들은 함께 맛있는 집밥 식사를 즐겼다."
    },
    "lunch": {
        "meaning": "점심 식사",
        "en": "Let's grab a quick lunch near the office.",
        "ko": "사무실 근처에서 간단하게 점심 식사를 하자."
    },
    "dinner": {
        "meaning": "저녁 식사",
        "en": "We reserved a table for dinner at seven o'clock.",
        "ko": "우리는 7시에 저녁 식사를 위한 테이블을 예약했다."
    },
    "schedule": {
        "meaning": "일정, 시간표",
        "en": "The meeting schedule has been updated on the shared calendar.",
        "ko": "회의 일정이 공유 캘린더에 업데이트되었습니다."
    },
    "apple": {
        "meaning": "사과",
        "en": "Eating a fresh apple every day is good for your health.",
        "ko": "매일 신선한 사과를 먹는 것은 건강에 좋다."
    },
    "water": {
        "meaning": "물, 수분",
        "en": "Drinking enough water is important throughout the day.",
        "ko": "하루 종일 충분한 물을 마시는 것이 중요하다."
    },
    "pencil": {
        "meaning": "연필",
        "en": "He took notes in the meeting using a sharp pencil.",
        "ko": "그는 뾰족한 연필로 회의 내용을 필기했다."
    },
    "computer": {
        "meaning": "컴퓨터",
        "en": "She turned on her computer to start working on the project.",
        "ko": "그녀는 프로젝트 작업을 시작하기 위해 컴퓨터를 켰다."
    },
    "abandon": {
        "meaning": "버리다, 포기하다",
        "en": "Bad weather forced them to abandon the search.",
        "ko": "악천후로 인해 그들은 수색을 포기해야 했다."
    },
    "ability": {
        "meaning": "능력, 재능",
        "en": "She has the remarkable ability to solve complex problems.",
        "ko": "그녀는 복잡한 문제를 해결하는 탁월한 능력을 가지고 있다."
    },
    "decision": {
        "meaning": "결정, 판단",
        "en": "They made a final decision after reviewing all proposals.",
        "ko": "그들은 모든 제안서를 검토한 후 최종 결정을 내렸다."
    },
    "experience": {
        "meaning": "경험, 체험",
        "en": "Working abroad was a valuable experience for her career.",
        "ko": "해외 근무는 그녀의 경력에 귀중한 경험이었다."
    },
    "opportunity": {
        "meaning": "기회",
        "en": "This internship provides a great opportunity to learn new skills.",
        "ko": "이 인턴십은 새로운 기술을 배울 수 있는 훌륭한 기회를 제공한다."
    },
    "information": {
        "meaning": "정보, 자료",
        "en": "You can find more detailed information on our website.",
        "ko": "웹사이트에서 더 자세한 정보를 찾으실 수 있습니다."
    },
    "question": {
        "meaning": "질문, 문제",
        "en": "Feel free to ask any question during the presentation.",
        "ko": "발표 도중 궁금한 점이 있으면 편하게 질문해 주세요."
    },
    "answer": {
        "meaning": "대답, 정답",
        "en": "He gave a clear and thoughtful answer to the inquiry.",
        "ko": "그는 문의에 대해 명확하고 사려 깊은 대답을 주었다."
    },
    "problem": {
        "meaning": "문제",
        "en": "The team worked together to find a solution to the problem.",
        "ko": "팀은 문제에 대한 해결책을 찾기 위해 함께 협력했다."
    },
}

# 40종 이상의 다채로운 문형 패턴 풀 (Pool)
NOUN_PATTERNS = [
    ("We need to review the {word} before making a final decision.", "우리는 최종 결정을 내리기 전에 {meaning_obj} 검토해야 한다."),
    ("The new {word} was very helpful for our team project.", "새로운 {meaning_top} 우리 팀 프로젝트에 큰 도움이 되었다."),
    ("Could you please send me more details about the {word}?", "{meaning}에 관한 더 자세한 내용을 보내주시겠습니까?"),
    ("She found an interesting article about the {word}.", "그녀는 {meaning}에 관한 흥미로운 기사를 발견했다."),
    ("The quality of this {word} exceeded our expectations.", "이 {meaning}의 품질은 우리의 기대를 뛰어넘었다."),
    ("They organized a seminar to discuss the {word}.", "그들은 {meaning_obj} 논의하기 위한 세미나를 개최했다."),
    ("He has a deep understanding of the {word}.", "그는 {meaning}에 대해 깊은 이해도를 가지고 있다."),
    ("Regular practice with the {word} brings consistent improvement.", "{meaning}에 대한 꾸준한 연습은 지속적인 향상을 가져온다."),
    ("The company introduced an innovative {word} to the market.", "회사는 혁신적인 {meaning_obj} 시장에 선보였다."),
    ("I received useful advice regarding the {word}.", "나는 {meaning}에 관한 유용한 조언을 들었다."),
    ("They carefully checked the condition of the {word}.", "그들은 {meaning}의 상태를 꼼꼼하게 점검했다."),
    ("This {word} is widely recognized by professionals in the field.", "이 {meaning_top} 해당 분야 전문가들에게 널리 인정받고 있다."),
    ("Understanding the basic concept of {word} is essential.", "{meaning}의 기본 개념을 이해하는 것이 필수적이다."),
    ("She shared her personal thoughts on the {word}.", "그녀는 {meaning}에 대한 자신의 개인적인 생각을 공유했다."),
    ("The manager emphasized the importance of the {word}.", "팀장은 {meaning}의 중요성을 강조했다."),
    ("We are preparing a comprehensive report on the {word}.", "우리는 {meaning}에 관한 종합 보고서를 준비하고 있다."),
]

VERB_PATTERNS = [
    ("They decided to {word} immediately to prevent delays.", "그들은 지연을 막기 위해 즉시 {clean_m}하기로 결정했다."),
    ("It is important to {word} carefully in every step of the process.", "과정의 모든 단계에서 신중하게 {clean_m}하는 것이 중요하다."),
    ("We should {word} together to achieve the best result.", "우리는 최고의 결과를 얻기 위해 함께 {clean_m}해야 한다."),
    ("She learned how to {word} effectively from her mentor.", "그녀는 멘토로부터 효과적으로 {clean_m}하는 법을 배웠다."),
    ("Please remember to {word} before the deadline.", "마감일 전에 잊지 말고 {clean_m}해 주시기 바랍니다."),
    ("The team managed to {word} despite unexpected difficulties.", "팀은 예상치 못한 어려움에도 불구하고 잘 {clean_m}해냈다."),
    ("He promised to {word} as soon as possible.", "그는 가능한 한 빨리 {clean_m}하겠다고 약속했다."),
    ("The system allows users to {word} easily and securely.", "이 시스템을 통해 사용자는 쉽고 안전하게 {clean_m}할 수 있다."),
    ("I will {word} after checking the remaining details.", "남은 세부 사항을 확인한 후 {clean_m}하겠습니다."),
    ("They worked diligently to {word} the project on time.", "그들은 프로젝트를 제때 {clean_m}하기 위해 성실히 일했다."),
]

ADJ_PATTERNS = [
    ("The customer service was remarkably {word} and helpful.", "고객 서비스는 눈에 띄게 {clean_m}하고 도움이 되었다."),
    ("It is a {word} approach to solving this technical problem.", "이 기술적 문제를 해결하기 위한 {clean_m}한 접근 방식이다."),
    ("The experimental results showed a {word} improvement.", "실험 결과는 {clean_m}한 개선을 보여주었다."),
    ("We had a very {word} discussion during the afternoon meeting.", "우리는 오후 회의 동안 매우 {clean_m}한 토론을 나눴다."),
    ("Maintaining a {word} attitude helps in difficult situations.", "{clean_m}한 태도를 유지하는 것은 어려운 상황에서 도움이 된다."),
    ("She gave a {word} presentation that impressed the audience.", "그녀는 청중들에게 깊은 인상을 남긴 {clean_m}한 발표를 했다."),
    ("This solution is both {word} and cost-effective.", "이 해결책은 {clean_m}하면서도 비용 효율적이다."),
    ("The team achieved a {word} success in the competition.", "팀은 대회에서 {clean_m}한 성공을 거두었다."),
]

ADV_PATTERNS = [
    ("The project was completed {word} by the engineering team.", "프로젝트는 엔지니어링 팀에 의해 {clean_m} 완료되었다."),
    ("She spoke {word} during the international conference.", "그녀는 국제 콘퍼런스에서 {clean_m} 연설했다."),
    ("The software functions {word} under heavy workload.", "그 소프트웨어는 과중한 작업 부하 속에서도 {clean_m} 작동한다."),
    ("He handled the complicated situation {word}.", "그는 복잡한 상황을 {clean_m} 처리했다."),
]

def clean_meaning_for_grammar(meaning: str) -> str:
    m = re.split(r'[,;/]', meaning)[0].strip()
    m = re.sub(r'\(.*?\)', '', m).strip()
    return m or meaning

def generate_diverse_example(word: str, pos: str, meaning: str, index: int) -> tuple[str, str]:
    w_lower = word.lower()
    
    # 1. 특정 단어 매핑 확인
    if w_lower in SPECIFIC_WORDS:
        info = SPECIFIC_WORDS[w_lower]
        return info["en"], info["ko"]

    clean_m = clean_meaning_for_grammar(meaning)
    m_top = attach_particle(clean_m, "topic")
    m_subj = attach_particle(clean_m, "subj")
    m_obj = attach_particle(clean_m, "obj")

    pos_lower = (pos or "noun").lower()

    if "noun" in pos_lower:
        pat_en, pat_ko = NOUN_PATTERNS[index % len(NOUN_PATTERNS)]
        en = pat_en.format(word=word)
        ko = pat_ko.format(meaning=clean_m, meaning_top=m_top, meaning_subj=m_subj, meaning_obj=m_obj)
        return en, ko
    elif "verb" in pos_lower:
        pat_en, pat_ko = VERB_PATTERNS[index % len(VERB_PATTERNS)]
        # 한국어 동사 어미 정리 ("하다" 중복 방지)
        root_m = clean_m[:-2] if clean_m.endswith("하다") else clean_m
        en = pat_en.format(word=word)
        ko = pat_ko.format(clean_m=root_m)
        return en, ko
    elif "adj" in pos_lower:
        pat_en, pat_ko = ADJ_PATTERNS[index % len(ADJ_PATTERNS)]
        root_m = clean_m[:-2] if clean_m.endswith("하다") else clean_m
        en = pat_en.format(word=word)
        ko = pat_ko.format(clean_m=root_m)
        return en, ko
    elif "adv" in pos_lower:
        pat_en, pat_ko = ADV_PATTERNS[index % len(ADV_PATTERNS)]
        en = pat_en.format(word=word)
        ko = pat_ko.format(clean_m=clean_m)
        return en, ko
    else:
        return (
            f"The instructor highlighted the word '{word}' in class.",
            f"강사는 수업 시간에 '{word}'({clean_m}) 단어를 강조했다."
        )

def process_level(level: int):
    json_path = DATA_DIR / f"level_{level}.json"
    if not json_path.exists():
        print(f"File not found: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        words = json.load(f)

    updated_count = 0
    for idx, item in enumerate(words):
        w = item.get("word", "").strip()
        w_lower = w.lower()

        # Fix known transliterated meanings (e.g. enquiry)
        if w_lower in SPECIFIC_WORDS and "meaning" in SPECIFIC_WORDS[w_lower]:
            item["meaning"] = SPECIFIC_WORDS[w_lower]["meaning"]

        old_ex = item.get("example_en", "")
        # If it was the repetitive template or in specific list
        if "plays an essential role" in old_ex or "careful consideration" in old_ex or "in any situation" in old_ex or w_lower in SPECIFIC_WORDS:
            en, ko = generate_diverse_example(w, item.get("pos", "noun"), item.get("meaning", ""), idx)
            item["example_en"] = en
            item["example_ko"] = ko
            updated_count += 1

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

    print(f"[Level {level}] Updated {updated_count}/{len(words)} example sentences.")

def main():
    print("=== Enriching Diverse Example Sentences across Levels 1 ~ 7 ===")
    for lvl in range(1, 8):
        process_level(lvl)
    print("=== All levels enriched successfully! ===")

if __name__ == "__main__":
    main()
