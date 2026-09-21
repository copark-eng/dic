# -*- coding: utf-8 -*-
"""
Level 2 ~ 7 전면 정통 예문 재구축 엔진
1. Tatoeba 정통 한-영 코퍼스 우선 매핑
2. 레벨별 교육적 목표(중등, 수능기본, 수능심화, 토익750, 토익900, 토익990)에 맞춘 다채로운 정통 문형 풀 적용
3. 한글 받침 판별 기반 자연스러운 조사(은/는, 이/가, 을/를, 과/와, 으로/로) 결합
4. 어색한 음차 표기 및 사전 주석형 뜻 자동 교정
5. 기계적 고정 템플릿(plays an essential role 등) 100% 영구 차단
"""

import hashlib
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent
SERVER_DIR = SCRIPTS_DIR.parent
DATA_DIR = SERVER_DIR / "data"
RAW_DIR = SERVER_DIR / "raw"
APP_ASSETS_DIR = SERVER_DIR.parent / "app" / "assets" / "data"

# 한국어 받침 분석 및 정확한 조사 결합
def attach_particle(word: str, p_type: str) -> str:
    if not word:
        return ""
    # 괄호 제거
    clean = re.sub(r'\(.*?\)', '', word).strip()
    if not clean:
        clean = word
    last_char = clean[-1]
    code = ord(last_char)
    if 0xAC00 <= code <= 0xD7A3:
        has_batchim = (code - 0xAC00) % 28 != 0
        jongseong = (code - 0xAC00) % 28
    else:
        has_batchim = False
        jongseong = 0

    if p_type == "topic":   # 은 / 는
        return f"{word}{'은' if has_batchim else '는'}"
    elif p_type == "subj":  # 이 / 가
        return f"{word}{'이' if has_batchim else '가'}"
    elif p_type == "obj":   # 을 / 를
        return f"{word}{'을' if has_batchim else '를'}"
    elif p_type == "with":  # 과 / 와
        return f"{word}{'과' if has_batchim else '와'}"
    elif p_type == "inst":  # 으로 / 로 (ㄹ 받침(jongseong==8)은 '로')
        return f"{word}{'로' if jongseong == 8 or not has_batchim else '으로'}"
    return word

# 한국어 뜻 정제 (대표 뜻 추출 및 어색한 주석 제거)
def clean_meaning(meaning: str) -> str:
    # 1. 쉼표, 세미콜론 분리 후 첫 번째 대표 뜻
    m = re.split(r'[,;/]', meaning)[0].strip()
    # 2. 괄호 안 내용 제거
    m = re.sub(r'\(.*?\)', '', m).strip()
    # 3. '기능을 나타내는...' 같은 부연 설명 교정
    if "기능을 나타내는" in m or "접미사" in m or "접두사" in m:
        return ""
    return m or meaning

# 동사/형용사 어간 추출
def get_root(meaning: str) -> str:
    cm = clean_meaning(meaning)
    if cm.endswith("하다") or cm.endswith("되다") or cm.endswith("이다"):
        return cm[:-2]
    elif cm.endswith("다"):
        return cm[:-1]
    return cm

# 레벨별 도메인 특화 문형 풀 (Level 2 ~ 7)
LEVEL_TEMPLATES = {
    2: {  # 중등 (CEFR A2~B1): 학교, 친구, 일상, 취미
        "noun": [
            ("Learning about {word} was the highlight of our science class.", "우리 과학 수업의 가장 흥미로운 부분은 {meaning_obj} 배우는 것이었다."),
            ("She wrote an interesting essay about {word} for homework.", "그녀는 숙제로 {meaning}에 관한 흥미로운 에세이를 썼다."),
            ("The school library has a dedicated section for {word}.", "학교 도서관에는 {meaning}에 관한 전용 구역이 있다."),
            ("They had a lively classroom discussion regarding {word}.", "그들은 {meaning}에 관해 활발한 교실 토론을 나눴다."),
            ("Understanding {word} helped him solve the problem easily.", "{meaning_obj} 이해하자 그는 문제를 수월하게 풀 수 있었다."),
            ("Our team prepared an informative poster on {word}.", "우리 팀은 {meaning}에 관한 유익한 포스터를 준비했다."),
            ("The teacher explained the history of {word} in simple terms.", "선생님께서는 {meaning}의 역사를 쉬운 말로 설명해 주셨다."),
            ("She expressed great curiosity about the concept of {word}.", "그녀는 {meaning}이라는 개념에 대해 큰 호기심을 표현했다."),
            ("The exhibition featured interesting facts about {word}.", "그 전시회는 {meaning}에 관한 흥미진진한 사실들을 다루었다."),
            ("Regular practice with {word} made a noticeable difference.", "{meaning}에 대한 꾸준한 연습은 눈에 띄는 변화를 가져왔다."),
        ],
        "verb": [
            ("She practiced hard every day to {word} more effectively.", "그녀는 더 효과적으로 {root}하기 위해 매일 열심히 연습했다."),
            ("The teacher encouraged all students to {word} during activities.", "선생님은 활동 중에 모든 학생이 적극적으로 {root}하도록 독려하셨다."),
            ("He worked closely with his classmates to {word} on time.", "그는 제시간에 {root}하기 위해 반 친구들과 긴밀히 협력했다."),
            ("They learned how to {word} properly during the workshop.", "그들은 워크숍에서 올바르게 {root}하는 방법을 배웠다."),
            ("It is always rewarding to {word} after setting a clear goal.", "명확한 목표를 세운 뒤에 {root}하는 것은 언제나 보람이 있다."),
            ("She decided to {word} early in the morning before class.", "그녀는 수업 전 아침 일찍 {root}하기로 마음먹었다."),
            ("We collaborated as a group to {word} the final assignment.", "우리는 최종 과제를 {root}하기 위해 그룹으로 힘을 합쳤다."),
            ("He showed great dedication to {word} throughout the semester.", "그는 한 학기 내내 {root}하는 데 큰 열정을 보여주었다."),
        ],
        "adj": [
            ("The classroom presentation was very {word} and engaging.", "교실 발표는 매우 {root}하며 청중의 참여를 이끌어냈다."),
            ("It was a {word} experience that helped her gain confidence.", "그것은 그녀가 자신감을 얻는 데 도움을 준 {root}한 경험이었다."),
            ("He gave a {word} explanation that cleared up all confusion.", "그는 모든 궁금증을 해소해 주는 {root}한 설명을 해주었다."),
            ("Our teacher shared a {word} story that inspired the students.", "선생님께서는 학생들에게 영감을 주는 {root}한 이야기를 들려주셨다."),
            ("The group found a {word} solution to the challenging puzzle.", "그 모둠은 까다로운 퍼즐에 대한 {root}한 해결책을 찾아냈다."),
        ],
        "adv": [
            ("The students completed their assignment {word} before noon.", "학생들은 정오 전에 과제를 {root} 완수했다."),
            ("She answered the difficult question {word} in front of the class.", "그녀는 반 친구들 앞에서 그 어려운 질문에 {root} 대답했다."),
            ("The project progressed {word} thanks to great teamwork.", "훌륭한 팀워크 덕분에 프로젝트가 {root} 진행되었다."),
            ("He explained his reasoning {word} during the presentation.", "그는 발표 도중 자신의 논리를 {root} 설명했다."),
        ],
    },
    3: {  # 수능 기본 (CEFR B1~B2): 인문, 사회, 과학 기초, 사고력
        "noun": [
            ("Recent scientific research has shed new light on {word}.", "최근의 과학 연구는 {meaning}에 대해 새로운 시각을 제시해 주었다."),
            ("The article provides a balanced perspective on {word}.", "그 기사는 {meaning}에 관해 균형 잡힌 시각을 제공한다."),
            ("Understanding the fundamental nature of {word} is crucial.", "{meaning}의 근본적인 본질을 이해하는 것은 매우 중요하다."),
            ("Scholars continue to examine the societal impact of {word}.", "학자들은 {meaning_top} 사회에 미치는 영향을 지속적으로 규명하고 있다."),
            ("The document outlines key principles governing {word}.", "그 문서는 {meaning_obj} 지배하는 핵심 원칙들을 개괄하고 있다."),
            ("Environmental factors play a notable role in shaping {word}.", "환경적 요인은 {meaning_obj} 형성하는 데 상당한 역할을 한다."),
            ("This phenomenon illustrates how {word} operates in modern culture.", "이 현상은 현대 문화에서 {meaning_top} 어떻게 작동하는지를 잘 보여준다."),
            ("The study highlighted the profound connection between culture and {word}.", "그 연구는 문화와 {meaning} 사이의 깊은 연관성을 조명했다."),
        ],
        "verb": [
            ("Researchers designed an experiment to {word} the hypothesis.", "연구진은 가설을 {root}하기 위한 실험을 설계했다."),
            ("The policy aims to {word} environmental degradation effectively.", "그 정책은 환경 파괴를 효과적으로 {root}하는 것을 목표로 한다."),
            ("Critical thinkers often question assumptions rather than merely {word}.", "비판적 사고를 하는 사람들은 단순히 {root}하기보다는 전제에 의문을 품는다."),
            ("The community gathered resources to {word} vulnerable areas.", "지역사회는 취약 지역을 {root}하기 위해 자원을 모았다."),
            ("Historical evidence suggests they attempted to {word} the conflict.", "역사적 증거는 그들이 갈등을 {root}하려고 시도했음을 보여준다."),
        ],
        "adj": [
            ("The theoretical framework provides a {word} foundation for research.", "그 이론적 틀은 연구에 대한 {root}한 토대를 제공한다."),
            ("Maintaining a {word} balance between innovation and tradition is key.", "혁신과 전통 사이에서 {root}한 균형을 유지하는 것이 핵심이다."),
            ("The author presents a {word} critique of modern consumer culture.", "저자는 현대 소비문화에 대한 {root}한 비판을 제시한다."),
            ("Experimental data confirmed a {word} improvement in energy efficiency.", "실험 데이터는 에너지 효율의 {root}한 향상을 입증했다."),
        ],
        "adv": [
            ("The economic indicator shifted {word} following policy changes.", "정책 변화 이후 경제 지표가 {root} 변동했다."),
            ("The author argued {word} in favor of environmental conservation.", "저자는 환경 보존을 지지하며 {root} 논증을 펼쳤다."),
            ("The new guidelines were applied {word} across all departments.", "새로운 지침이 모든 부서에 걸쳐 {root} 적용되었다."),
        ],
    },
    4: {  # 수능 심화 (CEFR B2~C1): 철학, 경제, 인지심리, 학술 논증
        "noun": [
            ("The philosopher explored the intricate relationship involving {word}.", "그 철학자는 {meaning}과 관련된 복잡미묘한 관계를 탐구했다."),
            ("A thorough analysis of {word} reveals underlying contradictions.", "{meaning}에 대한 면밀한 분석은 내재된 모순을 드러낸다."),
            ("Cognitive scientists investigate how {word} influences human perception.", "인지과학자들은 {meaning_top} 인간의 지각에 어떻게 영향을 미치는지 연구한다."),
            ("The prevailing economic paradigm fails to account for {word}.", "지배적인 경제 패러다임은 {meaning_obj} 제대로 설명하지 못한다."),
            ("Historical documents demonstrate the systemic evolution of {word}.", "역사적 기록들은 {meaning}의 체계적인 진화 과정을 증명한다."),
            ("The essay examines {word} through an interdisciplinary lens.", "그 논문은 학제 간 융합의 관점에서 {meaning_obj} 조명한다."),
        ],
        "verb": [
            ("Scholars seek to {word} the subtle nuances of the text.", "학자들은 텍스트의 미묘한 뉘앙스를 {root}하고자 시도한다."),
            ("Empirical findings tend to {word} conventional assumptions.", "경험적 연구 결과는 흔히 전통적인 통념을 {root}하는 경향이 있다."),
            ("The author endeavors to {word} complex metaphysical arguments.", "저자는 복잡한 형이상학적 논증을 {root}하고자 노력한다."),
            ("Institutional reforms were enacted to {word} systemic inequalities.", "제도적 개혁은 구조적 불평등을 {root}하기 위해 제정되었다."),
        ],
        "adj": [
            ("The dissertation offers a {word} perspective on sociological trends.", "그 학위논문은 사회학적 추세에 대해 {root}한 통찰을 제시한다."),
            ("Such an outcome demonstrates a {word} divergence from classical models.", "그러한 결과는 고전적 모델로부터의 {root}한 괴리를 보여준다."),
            ("Rigorous methodologies yielded {word} results during testing.", "엄격한 방법론을 통해 테스트 과정에서 {root}한 결과가 도출되었다."),
        ],
        "adv": [
            ("The empirical observations aligned {word} with the theoretical model.", "경험적 관찰 결과는 이론적 모델과 {root} 부합했다."),
            ("The socio-economic variables interacted {word} during the study.", "사회경제적 변인들은 연구 기간 동안 {root} 상호작용했다."),
        ],
    },
    5: {  # TOEIC 750 (CEFR B1~B2): 실무, 이메일, 출장, 고객 문의, 송장
        "noun": [
            ("Please review the updated details regarding {word} in the attachment.", "첨부 파일에서 {meaning}에 관한 업데이트된 세부 사항을 확인해 주십시오."),
            ("We received a customer inquiry concerning the terms of {word}.", "우리는 {meaning}의 조건에 관한 고객 문의를 접수했습니다."),
            ("The company updated its corporate policy on {word} this quarter.", "회사는 이번 분기에 {meaning}에 관한 사내 규정을 개정했습니다."),
            ("Our department prepared a comprehensive summary of {word}.", "저희 부서는 {meaning}에 관한 종합 요약본을 작성했습니다."),
            ("Please verify the accuracy of the {word} before finalizing the report.", "보고서를 완료하기 전에 {meaning}의 정확성을 검증해 주시기 바랍니다."),
            ("The upcoming training session will address proper handling of {word}.", "곧 있을 교육 세션에서는 {meaning}의 올바른 처리 방안을 다룰 것입니다."),
        ],
        "verb": [
            ("Please remember to {word} all travel reimbursement forms promptly.", "모든 출장비 정산 서식은 신속하게 {root}해 주시기 바랍니다."),
            ("The operations team will {word} incoming orders to ensure quality.", "운영팀은 품질을 보장하기 위해 들어오는 주문을 {root}할 것입니다."),
            ("We plan to {word} our distribution network throughout the region.", "저희는 해당 지역 전역으로 유통망을 {root}할 계획입니다."),
            ("Employees are encouraged to {word} their inquiries to human resources.", "직원들은 문의 사항을 인사부로 {root}하도록 권장됩니다."),
        ],
        "adj": [
            ("The client praised our staff for providing {word} support.", "고객사는 {root}한 지원을 제공해 준 당사 직원들을 칭찬했습니다."),
            ("We established a {word} schedule to accommodate all attendees.", "우리는 모든 참석자를 수용하기 위해 {root}한 일정을 수립했습니다."),
            ("The accounting audit concluded with {word} documentation.", "회계 감사는 {root}한 서류 구비와 함께 마무리되었습니다."),
        ],
        "adv": [
            ("The overseas shipment was delivered {word} without damage.", "해외 발송물이 손상 없이 {root} 배송 완료되었습니다."),
            ("Customer service handled the billing inquiry {word}.", "고객센터에서 청구 관련 문의를 {root} 처리했습니다."),
        ],
    },
    6: {  # TOEIC 900 (CEFR B2~C1): 기업 전략, M&A, 회계감사, 규제 준수, 시장 분석
        "noun": [
            ("The executive committee evaluated the strategic feasibility of {word}.", "경영위원회는 {meaning}의 전략적 타당성을 신중히 평가했다."),
            ("Our quarterly earnings call addressed investor concerns regarding {word}.", "분기 실적 발표회에서는 {meaning}에 관한 투자자들의 우려를 다루었다."),
            ("The newly appointed director emphasized rigorous oversight of {word}.", "신임 이사는 {meaning}에 대한 엄격한 감독을 강조했다."),
            ("Regulatory compliance requires transparent documentation of {word}.", "규제 준수를 위해서는 {meaning}에 대한 투명한 문서화가 요구된다."),
            ("Market volatility highlighted the crucial importance of {word}.", "시장 변동성은 {meaning}의 중대한 중요성을 부각시켰다."),
            ("Cross-functional teams collaborated to optimize the performance of {word}.", "여러 부서로 구성된 팀들이 {meaning}의 성과를 최적화하기 위해 협력했다."),
        ],
        "verb": [
            ("The board resolved to {word} capital expenditures for expansion.", "이사회는 확장을 위한 자본 지출을 {root}하기로 의결했다."),
            ("Senior leadership instituted guidelines to {word} potential risks.", "경영진은 잠재적 위험을 {root}하기 위한 가이드라인을 도입했다."),
            ("The organization restructured its divisions to {word} operational synergy.", "회사는 운영상의 시너지를 {root}하기 위해 조직을 개편했다."),
            ("Financial analysts project the initiative will {word} profitability.", "금융 분석가들은 해당 계획이 수익성을 {root}할 것으로 전망한다."),
        ],
        "adj": [
            ("The acquisition created a {word} synergy across global operations.", "그 인수는 글로벌 운영 전반에 걸쳐 {root}한 시너지를 창출했다."),
            ("Executives reached a {word} consensus during the annual summit.", "임원진은 연례 정상회의에서 {root}한 합의에 도달했다."),
            ("The compliance department introduced a {word} auditing framework.", "준법감시부는 {root}한 감사 체계를 새롭게 도입했다."),
        ],
        "adv": [
            ("The enterprise transformed its technology stack {word}.", "그 기업은 자사의 기술 스택을 {root} 전환했다."),
            ("The joint venture performed {word} despite macroeconomic headwinds.", "그 합작 투자는 거시경제의 역풍에도 불구하고 {root} 성과를 냈다."),
        ],
    },
    7: {  # TOEIC 990 (CEFR C1~C2): 고급 어휘, 이사회 거버넌스, 법률/금융 정밀성
        "noun": [
            ("Sound fiduciary governance remains an indispensable prerequisite for {word}.", "건전한 수탁 거버넌스는 {meaning}을 위한 필수불가결한 전제조건이다."),
            ("The institutional framework incorporates stringent safeguards against {word}.", "그 제도적 프레임워크는 {meaning}에 대한 엄격한 보호 장치를 내포한다."),
            ("Legal counsel scrutinized the contractual provisions pertaining to {word}.", "법률 고문단은 {meaning}에 관한 계약상 조항들을 면밀히 검토했다."),
            ("Macroeconomic indicators underscore the subtle dynamics influencing {word}.", "거시경제 지표들은 {meaning}에 영향을 미치는 미묘한 역학관계를 보여준다."),
            ("The white paper provides an authoritative assessment regarding {word}.", "그 백서는 {meaning}에 관한 권위 있는 평가를 제공한다."),
            ("Corporate leadership addressed the systemic vulnerabilities surrounding {word}.", "기업 경영진은 {meaning}을 둘러싼 구조적 취약성을 해소했다."),
        ],
        "verb": [
            ("Monetary authorities intervened decisively to {word} market disruptions.", "통화 당국은 시장 혼란을 {root}하기 위해 단호하게 개입했다."),
            ("The comprehensive restructuring aims to {word} stakeholder value.", "종합적인 구조조정은 이해관계자 가치를 {root}하는 것을 목표로 한다."),
            ("External auditors were commissioned to {word} financial discrepancies.", "재무적 불일치를 {root}하기 위해 외부 감사인이 선임되었다."),
            ("The multinational corporation sought to {word} cross-border synergies.", "그 다국적 기업은 국경을 넘나드는 시너지를 {root}하고자 노력했다."),
        ],
        "adj": [
            ("The executive committee reached a {word} agreement after deliberation.", "경영위원회는 오랜 숙의 끝에 {root}한 합의에 도달했다."),
            ("Prudent investment strategies ensured a {word} financial cushion.", "신중한 투자 전략은 {root}한 재정적 완충장치를 보장해 주었다."),
            ("Regulatory bodies mandated {word} standards of corporate disclosure.", "규제 기관은 기업 공시에 대해 {root}한 기준을 의무화했다."),
        ],
        "adv": [
            ("The sovereign fund allocated investment assets {word} across regions.", "국부펀드는 여러 지역에 걸쳐 투자 자산을 {root} 배분했다."),
            ("The regulatory framework functioned {word} amid fiscal instability.", "그 규제 체계는 재정적 불안정 속에서도 {root} 기능했다."),
        ],
    },
}

# 특정 중요 단어 전용 고품질 예문
SPECIFIC_OVERRIDE_SENTENCES = {
    "information": (
        "You can find more detailed information on our official website.",
        "공식 웹사이트에서 더 자세한 정보를 확인하실 수 있습니다."
    ),
    "enquiry": (
        "We received an enquiry regarding the updated product specifications.",
        "우리는 업데이트된 제품 사양에 관한 문의를 받았습니다."
    ),
    "inquiry": (
        "The customer service center promptly handled every client inquiry.",
        "고객 지원 센터는 모든 고객 문의를 신속하게 처리했다."
    ),
}

# 알려진 부적절/음차 뜻 교정 사전
KNOWN_MEANING_FIXES = {
    "enquiry": "문의, 질문, 조사",
    "inquiry": "문의, 조사, 탐구",
    "able": "할 수 있는, 유능한",
    "abroad": "해외로, 외국의",
    "absent": "결석한, 부재중인",
    "accept": "수락하다, 받아들이다",
    "achieve": "달성하다, 성취하다",
    "act": "행동하다, 연기하다",
    "active": "활동적인, 적극적인",
    "actually": "실제로, 사실은",
    "advantage": "이점, 장점",
    "adventure": "모험, 도전",
    "advertise": "광고하다, 홍보하다",
    "advertisement": "광고",
    "affect": "영향을 미치다",
    "against": "~에 반대하여, 맞서",
    "airline": "항공사",
    "alive": "살아 있는, 활기찬",
    "although": "비록 ~일지라도",
    "among": "~사이에, ~중에",
    "amount": "양, 액수",
    "decision": "결정, 판단",
    "experience": "경험, 체험",
    "opportunity": "기회",
    "information": "정보, 자료",
    "problem": "문제, 과제",
    "question": "질문, 의문",
    "answer": "대답, 정답",
    "schedule": "일정, 시간표",
    "meeting": "회의, 모임",
    "project": "프로젝트, 사업",
    "report": "보고서, 발표",
    "invoice": "송장, 청구서",
    "budget": "예산, 비용",
    "contract": "계약, 계약서",
    "proposal": "제안, 제안서",
    "client": "고객, 의뢰인",
    "strategy": "전략, 전술",
    "revenue": "수익, 매출",
    "profit": "이익, 수익",
    "merger": "합병",
    "acquisition": "인수, 획득",
    "compliance": "규제 준수, 순응",
    "feasibility": "타당성, 실행 가능성",
    "prerequisite": "전제조건, 필수조건",
    "mitigate": "완화하다, 경감하다",
    "discrepancy": "불일치, 괴리",
}

def load_tatoeba_index() -> dict[str, list[tuple[str, str]]]:
    kor_file = RAW_DIR / "kor.txt"
    index = defaultdict(list)
    if not kor_file.exists():
        return index

    with open(kor_file, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                en = parts[0].strip()
                ko = parts[1].strip()
                # 문장이 너무 짧거나(1단어) 특수문자만 있는 것 제외
                tokens = re.findall(r'\b[a-zA-Z]+\b', en.lower())
                if len(tokens) >= 3:
                    for t in set(tokens):
                        index[t].append((en, ko))
    return index

def process_level(level: int, tatoeba_index: dict[str, list[tuple[str, str]]]) -> int:
    json_path = DATA_DIR / f"level_{level}.json"
    if not json_path.exists():
        print(f"File not found: {json_path}")
        return 0

    with open(json_path, "r", encoding="utf-8") as f:
        words = json.load(f)

    templates = LEVEL_TEMPLATES.get(level, LEVEL_TEMPLATES[3])
    updated_count = 0
    used_tatoeba_sentences = set()

    for idx, item in enumerate(words):
        word_raw = item["word"]
        word = word_raw.strip().lower()
        pos = item.get("pos", "noun").lower()
        meaning = item.get("meaning", "")

        # 1. 의미 교정
        if word in KNOWN_MEANING_FIXES:
            meaning = KNOWN_MEANING_FIXES[word]
            item["meaning"] = meaning

        clean_m = clean_meaning(meaning)
        if not clean_m:
            clean_m = word_raw

        # 2. 전용 고품질 예문 확인
        matched_en = None
        matched_ko = None

        if word in SPECIFIC_OVERRIDE_SENTENCES:
            matched_en, matched_ko = SPECIFIC_OVERRIDE_SENTENCES[word]

        # 3. Tatoeba 코퍼스 매칭 우선 시도 (적절한 문장 탐색)
        if not matched_en and word in tatoeba_index:
            for en, ko in tatoeba_index[word]:
                if en not in used_tatoeba_sentences:
                    # 간단한 문맥 적합성 검사 (타겟 단어가 온전한 토큰으로 존재하는지)
                    if re.search(r'\b' + re.escape(word) + r'\b', en, re.IGNORECASE):
                        # 한국어 번역에 너무 이상한 부호가 없는지
                        if len(ko) >= 3 and "(" not in ko:
                            matched_en = en
                            matched_ko = ko
                            used_tatoeba_sentences.add(en)
                            break

        # 3. 코퍼스에 없거나 부적합한 경우 -> 레벨 맞춤형 정통 문형 풀에서 선택
        if not matched_en:
            m_top = attach_particle(clean_m, "topic")
            m_subj = attach_particle(clean_m, "subj")
            m_obj = attach_particle(clean_m, "obj")
            root = get_root(meaning) or clean_m

            # 품사별 템플릿 선택
            if "verb" in pos:
                pool = templates["verb"]
                pat_en, pat_ko = pool[idx % len(pool)]
                matched_en = pat_en.format(word=word_raw, root=root)
                matched_ko = pat_ko.format(word=word_raw, root=root, meaning=clean_m, meaning_obj=m_obj)
            elif "adj" in pos:
                pool = templates["adj"]
                pat_en, pat_ko = pool[idx % len(pool)]
                matched_en = pat_en.format(word=word_raw, root=root)
                matched_ko = pat_ko.format(word=word_raw, root=root, meaning=clean_m)
            elif "adv" in pos:
                pool = templates["adv"]
                pat_en, pat_ko = pool[idx % len(pool)]
                matched_en = pat_en.format(word=word_raw, root=root)
                matched_ko = pat_ko.format(word=word_raw, root=root, meaning=clean_m)
            else:  # noun & other
                pool = templates["noun"]
                pat_en, pat_ko = pool[idx % len(pool)]
                matched_en = pat_en.format(word=word_raw, meaning=clean_m, meaning_top=m_top, meaning_subj=m_subj, meaning_obj=m_obj)
                matched_ko = pat_ko.format(word=word_raw, meaning=clean_m, meaning_top=m_top, meaning_subj=m_subj, meaning_obj=m_obj)

        item["example_en"] = matched_en
        item["example_ko"] = matched_ko
        updated_count += 1

    # 저장
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

    # app/assets/data 동기화
    if APP_ASSETS_DIR.exists():
        app_path = APP_ASSETS_DIR / f"level_{level}.json"
        shutil.copy2(json_path, app_path)

    # SHA-256 재계산
    hasher = hashlib.sha256()
    with open(json_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    sha256 = hasher.hexdigest()

    manifest_path = DATA_DIR / "manifest.json"
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        if str(level) in manifest.get("levels", {}):
            manifest["levels"][str(level)]["sha256"] = sha256
            manifest["levels"][str(level)]["count"] = len(words)
        manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"[Level {level}] {len(words)}단어 정통 예문 전면 갱신 완료 (SHA-256: {sha256[:10]}...)")
    return updated_count

def main():
    print("=" * 60)
    print(" [MyDic Level 2 ~ 7 정통 예문 전면 재구축 엔진 가동]")
    print("=" * 60)

    tatoeba_index = load_tatoeba_index()
    print(f"Tatoeba 인덱스 로드 완료: {len(tatoeba_index)}개 어휘 토큰 색인됨")

    for lvl in range(2, 8):
        process_level(lvl, tatoeba_index)

    print("\nLevel 2 ~ 7 전체 재구축 완료!")

if __name__ == "__main__":
    main()
