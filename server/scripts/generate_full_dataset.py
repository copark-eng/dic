# -*- coding: utf-8 -*-
from __future__ import annotations
"""
로컬 단어 데이터셋 종합 구축 스크립트 (Generate Full Dataset)
Level 1부터 Level 7까지의 완전한 단어 데이터(단어, 한국어 뜻, 품사, US/UK 발음기호,
예문 및 한국어 해석, US/UK 오디오 URL, 유의어/반의어)를 로컬에서 즉시 구축하고
manifest.json을 갱신합니다.
Python 3.9+ 호환, UTF-8 인코딩 적용
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 스크립트 디렉터리 경로 등록
SCRIPTS_DIR = Path(__file__).resolve().parent
SERVER_DIR = SCRIPTS_DIR.parent
DATA_DIR = SERVER_DIR / "data"
RAW_DIR = SERVER_DIR / "raw"

# 레벨 정보 메타데이터
LEVEL_META = {
    1: {"name": "기초", "code": "L1"},
    2: {"name": "중등", "code": "L2"},
    3: {"name": "수능기본", "code": "L3"},
    4: {"name": "수능심화", "code": "L4"},
    5: {"name": "TOEIC 750", "code": "L5"},
    6: {"name": "TOEIC 900", "code": "L6"},
    7: {"name": "TOEIC 990", "code": "L7"},
}

# 레벨별 어휘 데이터베이스 (단어, 품사, 한국어 뜻, US발음, UK발음, 영문예문, 한글해석, 유의어, 반의어)
DATASET: dict[int, list[dict[str, Any]]] = {
    1: [
        {"word": "apple", "pos": "noun", "meaning": "사과", "us_p": "/ˈæp.əl/", "uk_p": "/ˈæp.əl/",
         "ex_en": "I eat a fresh apple every morning.", "ex_ko": "나는 매일 아침 신선한 사과를 먹는다.",
         "syn": [], "ant": []},
        {"word": "book", "pos": "noun", "meaning": "책, 도서", "us_p": "/bʊk/", "uk_p": "/bʊk/",
         "ex_en": "She is reading an interesting book.", "ex_ko": "그녀는 흥미로운 책을 읽고 있다.",
         "syn": ["volume", "tome"], "ant": []},
        {"word": "school", "pos": "noun", "meaning": "학교", "us_p": "/skuːl/", "uk_p": "/skuːl/",
         "ex_en": "The children walk to school together.", "ex_ko": "아이들은 함께 학교로 걸어간다.",
         "syn": ["academy"], "ant": []},
        {"word": "water", "pos": "noun", "meaning": "물", "us_p": "/ˈwɑː.t̬ɚ/", "uk_p": "/ˈwɔː.tər/",
         "ex_en": "Please drink plenty of water every day.", "ex_ko": "매일 물을 충분히 마시세요.",
         "syn": [], "ant": []},
        {"word": "friend", "pos": "noun", "meaning": "친구", "us_p": "/frend/", "uk_p": "/frend/",
         "ex_en": "A good friend is a great treasure in life.", "ex_ko": "좋은 친구는 인생의 큰 보물이다.",
         "syn": ["companion", "pal"], "ant": ["enemy", "foe"]},
        {"word": "happy", "pos": "adjective", "meaning": "행복한, 기쁜", "us_p": "/ˈhæp.i/", "uk_p": "/ˈhæp.i/",
         "ex_en": "They were very happy to hear the good news.", "ex_ko": "그들은 좋은 소식을 듣고 매우 행복했다.",
         "syn": ["cheerful", "glad"], "ant": ["sad", "unhappy"]},
        {"word": "family", "pos": "noun", "meaning": "가족", "us_p": "/ˈfæm.əl.i/", "uk_p": "/ˈfæm.əl.i/",
         "ex_en": "We spend time with our family on weekends.", "ex_ko": "우리는 주말에 가족과 함께 시간을 보낸다.",
         "syn": ["household", "relatives"], "ant": []},
        {"word": "house", "pos": "noun", "meaning": "집, 주택", "us_p": "/haʊs/", "uk_p": "/haʊs/",
         "ex_en": "They built a beautiful new house near the lake.", "ex_ko": "그들은 호수 근처에 아름다운 새 집을 지었다.",
         "syn": ["home", "dwelling"], "ant": []},
        {"word": "study", "pos": "verb", "meaning": "공부하다, 연구하다", "us_p": "/ˈstʌd.i/", "uk_p": "/ˈstʌd.i/",
         "ex_en": "I study English for two hours every day.", "ex_ko": "나는 매일 두 시간씩 영어를 공부한다.",
         "syn": ["learn", "examine"], "ant": []},
        {"word": "music", "pos": "noun", "meaning": "음악", "us_p": "/ˈmjuː.zɪk/", "uk_p": "/ˈmjuː.zɪk/",
         "ex_en": "Listening to classical music helps me relax.", "ex_ko": "클래식 음악을 듣는 것은 긴장을 푸는 데 도움이 된다.",
         "syn": ["melody", "tune"], "ant": []},
        {"word": "morning", "pos": "noun", "meaning": "아침, 오전", "us_p": "/ˈmɔːr.nɪŋ/", "uk_p": "/ˈmɔː.nɪŋ/",
         "ex_en": "The air is very clean early in the morning.", "ex_ko": "이른 아침에는 공기가 매우 맑다.",
         "syn": ["dawn"], "ant": ["evening", "night"]},
        {"word": "night", "pos": "noun", "meaning": "밤, 야간", "us_p": "/naɪt/", "uk_p": "/naɪt/",
         "ex_en": "The stars shine brightly in the dark night sky.", "ex_ko": "어두운 밤하늘에 별들이 밝게 빛난다.",
         "syn": ["evening"], "ant": ["day", "morning"]},
        {"word": "smile", "pos": "verb", "meaning": "미소 짓다, 웃다", "us_p": "/smaɪl/", "uk_p": "/smaɪl/",
         "ex_en": "She always smiles warmly when she greets people.", "ex_ko": "그녀는 사람들을 맞이할 때 항상 따뜻하게 미소 짓는다.",
         "syn": ["grin", "beam"], "ant": ["frown"]},
        {"word": "travel", "pos": "verb", "meaning": "여행하다, 이동하다", "us_p": "/ˈtræv.əl/", "uk_p": "/ˈtræv.əl/",
         "ex_en": "I want to travel to many different countries.", "ex_ko": "나는 많은 다른 나라들을 여행하고 싶다.",
         "syn": ["journey", "tour"], "ant": ["stay"]},
        {"word": "weather", "pos": "noun", "meaning": "날씨, 기상", "us_p": "/ˈweð.ɚ/", "uk_p": "/ˈweð.ər/",
         "ex_en": "The weather is very sunny and warm today.", "ex_ko": "오늘 날씨는 매우 화창하고 따뜻하다.",
         "syn": ["climate"], "ant": []},
    ],
    2: [
        {"word": "achieve", "pos": "verb", "meaning": "성취하다, 이루다", "us_p": "/əˈtʃiːv/", "uk_p": "/əˈtʃiːv/",
         "ex_en": "You can achieve your goals with consistent effort.", "ex_ko": "꾸준한 노력을 통해 목표를 달성할 수 있다.",
         "syn": ["accomplish", "attain"], "ant": ["fail"]},
        {"word": "balance", "pos": "noun", "meaning": "균형, 조화", "us_p": "/ˈbæl.əns/", "uk_p": "/ˈbæl.əns/",
         "ex_en": "It is important to keep a balance between work and rest.", "ex_ko": "일과 휴식의 균형을 유지하는 것이 중요하다.",
         "syn": ["equilibrium", "harmony"], "ant": ["imbalance"]},
        {"word": "climate", "pos": "noun", "meaning": "기후, 풍토", "us_p": "/ˈklaɪ.mət/", "uk_p": "/ˈklaɪ.mət/",
         "ex_en": "Global climate change affects all living things.", "ex_ko": "지구 기후 변화는 모든 생물에게 영향을 미친다.",
         "syn": ["weather", "atmosphere"], "ant": []},
        {"word": "discover", "pos": "verb", "meaning": "발견하다, 알아내다", "us_p": "/dɪˈskʌv.ɚ/", "uk_p": "/dɪˈskʌv.ər/",
         "ex_en": "Scientists discovered a new species in the ocean.", "ex_ko": "과학자들은 바다에서 새로운 종을 발견했다.",
         "syn": ["find", "uncover"], "ant": ["hide", "conceal"]},
        {"word": "essential", "pos": "adjective", "meaning": "필수적인, 본질적인", "us_p": "/ɪˈsen.ʃəl/", "uk_p": "/ɪˈsen.ʃəl/",
         "ex_en": "Good communication is essential for team success.", "ex_ko": "원활한 의사소통은 팀의 성공에 필수적이다.",
         "syn": ["vital", "crucial"], "ant": ["optional", "unnecessary"]},
        {"word": "culture", "pos": "noun", "meaning": "문화, 교양", "us_p": "/ˈkʌl.tʃɚ/", "uk_p": "/ˈkʌl.tʃər/",
         "ex_en": "Traveling allows us to experience diverse cultures.", "ex_ko": "여행은 우리가 다양한 문화를 경험하게 해준다.",
         "syn": ["customs", "heritage"], "ant": []},
        {"word": "environment", "pos": "noun", "meaning": "환경, 주위", "us_p": "/ɪnˈvaɪ.rən.mənt/", "uk_p": "/ɪnˈvaɪ.rən.mənt/",
         "ex_en": "We must protect the natural environment for future generations.", "ex_ko": "우리는 미래 세대를 위해 자연환경을 보호해야 한다.",
         "syn": ["surroundings", "ecosystem"], "ant": []},
        {"word": "improve", "pos": "verb", "meaning": "향상시키다, 개선하다", "us_p": "/ɪmˈpruːv/", "uk_p": "/ɪmˈpruːv/",
         "ex_en": "Practicing every day will improve your speaking skills.", "ex_ko": "매일 연습하면 말하기 실력이 향상될 것이다.",
         "syn": ["enhance", "upgrade"], "ant": ["worsen", "deteriorate"]},
        {"word": "protect", "pos": "verb", "meaning": "보호하다, 지키다", "us_p": "/prəˈtekt/", "uk_p": "/prəˈtekt/",
         "ex_en": "Wear a helmet to protect your head while cycling.", "ex_ko": "자전거를 탈 때는 머리를 보호하기 위해 헬멧을 착용하세요.",
         "syn": ["guard", "defend"], "ant": ["attack", "endanger"]},
        {"word": "solution", "pos": "noun", "meaning": "해결책, 해결", "us_p": "/səˈluː.ʃən/", "uk_p": "/səˈluː.ʃən/",
         "ex_en": "The team worked together to find a creative solution.", "ex_ko": "팀은 창의적인 해결책을 찾기 위해 협력했다.",
         "syn": ["answer", "resolution"], "ant": ["problem"]},
        {"word": "tradition", "pos": "noun", "meaning": "전통, 관습", "us_p": "/trəˈdɪʃ.ən/", "uk_p": "/trəˈdɪʃ.ən/",
         "ex_en": "Making rice cakes is a long-standing holiday tradition.", "ex_ko": "떡을 만드는 것은 오랜 명절 전통이다.",
         "syn": ["custom", "heritage"], "ant": ["innovation"]},
        {"word": "opinion", "pos": "noun", "meaning": "의견, 견해", "us_p": "/əˈpɪn.jən/", "uk_p": "/əˈpɪn.jən/",
         "ex_en": "Everyone has the right to express their own opinion.", "ex_ko": "모든 사람은 자신의 의견을 표현할 권리가 있다.",
         "syn": ["viewpoint", "perspective"], "ant": []},
        {"word": "prepare", "pos": "verb", "meaning": "준비하다, 대비하다", "us_p": "/prɪˈper/", "uk_p": "/prɪˈpeər/",
         "ex_en": "Students need to prepare thoroughly for the upcoming exam.", "ex_ko": "학생들은 다가오는 시험을 철저히 준비해야 한다.",
         "syn": ["arrange", "ready"], "ant": []},
        {"word": "reduce", "pos": "verb", "meaning": "줄이다, 감소시키다", "us_p": "/rɪˈduːs/", "uk_p": "/rɪˈdʒuːs/",
         "ex_en": "Using public transit helps reduce carbon emissions.", "ex_ko": "대중교통을 이용하면 탄소 배출을 줄이는 데 도움이 된다.",
         "syn": ["decrease", "lessen"], "ant": ["increase", "expand"]},
        {"word": "succeed", "pos": "verb", "meaning": "성공하다, 계승하다", "us_p": "/səkˈsiːd/", "uk_p": "/səkˈsiːd/",
         "ex_en": "If you keep trying, you will eventually succeed.", "ex_ko": "계속해서 노력한다면 결국 성공할 것이다.",
         "syn": ["triumph", "prevail"], "ant": ["fail"]},
    ],
    3: [
        {"word": "adequate", "pos": "adjective", "meaning": "적절한, 충분한", "us_p": "/ˈæd.ə.kwət/", "uk_p": "/ˈæd.ɪ.kwət/",
         "ex_en": "Ensure you get an adequate amount of sleep each night.", "ex_ko": "매일 밤 적절한 수면 시간을 확보하도록 하세요.",
         "syn": ["sufficient", "suitable"], "ant": ["inadequate", "insufficient"]},
        {"word": "comprehend", "pos": "verb", "meaning": "이해하다, 파악하다", "us_p": "/ˌkɑːm.prɪˈhend/", "uk_p": "/ˌkɒm.prɪˈhend/",
         "ex_en": "It took some time to comprehend the complex theory.", "ex_ko": "그 복잡한 이론을 이해하는 데 약간의 시간이 걸렸다.",
         "syn": ["understand", "grasp"], "ant": ["misunderstand"]},
        {"word": "distinction", "pos": "noun", "meaning": "구별, 차이, 탁월함", "us_p": "/dɪˈstɪŋk.ʃən/", "uk_p": "/dɪˈstɪŋk.ʃən/",
         "ex_en": "There is a clear distinction between truth and rumors.", "ex_ko": "진실과 소문 사이에는 명확한 구별이 있다.",
         "syn": ["difference", "contrast"], "ant": ["similarity"]},
        {"word": "fluctuate", "pos": "verb", "meaning": "변동하다, 요동치다", "us_p": "/ˈflʌk.tʃu.eɪt/", "uk_p": "/ˈflʌk.tʃu.eɪt/",
         "ex_en": "Vegetable prices fluctuate depending on the season.", "ex_ko": "채소 가격은 계절에 따라 변동한다.",
         "syn": ["vary", "oscillate"], "ant": ["stabilize", "remain"]},
        {"word": "inevitable", "pos": "adjective", "meaning": "불가피한, 필연적인", "us_p": "/ɪnˈev.ə.t̬ə.bəl/", "uk_p": "/ɪnˈev.ɪ.tə.bəl/",
         "ex_en": "Change is an inevitable part of human progress.", "ex_ko": "변화는 인류 발전의 불가피한 부분이다.",
         "syn": ["unavoidable", "inescapable"], "ant": ["preventable", "avoidable"]},
        {"word": "contribute", "pos": "verb", "meaning": "기여하다, 공헌하다", "us_p": "/kənˈtrɪb.juːt/", "uk_p": "/kənˈtrɪb.juːt/",
         "ex_en": "Volunteers contribute greatly to the local community.", "ex_ko": "자원봉사자들은 지역 사회에 크게 기여한다.",
         "syn": ["donate", "assist"], "ant": ["detract"]},
        {"word": "fundamental", "pos": "adjective", "meaning": "근본적인, 핵심적인", "us_p": "/ˌfʌn.dəˈmen.t̬əl/", "uk_p": "/ˌfʌn.dəˈmen.təl/",
         "ex_en": "Freedom of speech is a fundamental human right.", "ex_ko": "언론의 자유는 근본적인 인권이다.",
         "syn": ["basic", "essential"], "ant": ["secondary", "minor"]},
        {"word": "influence", "pos": "noun", "meaning": "영향력, 작용", "us_p": "/ˈɪn.flu.əns/", "uk_p": "/ˈɪn.flu.əns/",
         "ex_en": "Social media has a strong influence on young people.", "ex_ko": "소셜 미디어는 젊은이들에게 강한 영향을 미친다.",
         "syn": ["impact", "effect"], "ant": []},
        {"word": "perceive", "pos": "verb", "meaning": "인지하다, 인식하다", "us_p": "/pɚˈsiːv/", "uk_p": "/pəˈsiːv/",
         "ex_en": "Different people perceive the same event in varied ways.", "ex_ko": "서로 다른 사람들은 같은 사건을 다양한 방식으로 인지한다.",
         "syn": ["recognize", "discern"], "ant": ["ignore"]},
        {"word": "reinforce", "pos": "verb", "meaning": "강화하다, 보강하다", "us_p": "/ˌriː.ɪnˈfɔːrs/", "uk_p": "/ˌriː.ɪnˈfɔːs/",
         "ex_en": "Positive feedback helps reinforce good study habits.", "ex_ko": "긍정적인 피드백은 좋은 공부 습관을 강화하는 데 도움이 된다.",
         "syn": ["strengthen", "fortify"], "ant": ["weaken", "undermine"]},
        {"word": "transform", "pos": "verb", "meaning": "변형시키다, 탈바꿈하다", "us_p": "/trænˈsfɔːrm/", "uk_p": "/trænˈsfɔːm/",
         "ex_en": "Digital technology has transformed how we communicate.", "ex_ko": "디지털 기술은 우리의 소통 방식을 완전히 탈바꿈시켰다.",
         "syn": ["convert", "alter"], "ant": ["preserve"]},
        {"word": "vulnerable", "pos": "adjective", "meaning": "취약한, 상처받기 쉬운", "us_p": "/ˈvʌl.nɚ.ə.bəl/", "uk_p": "/ˈvʌl.nər.ə.bəl/",
         "ex_en": "Elderly people are particularly vulnerable to cold weather.", "ex_ko": "노인들은 특히 추운 날씨에 취약하다.",
         "syn": ["susceptible", "fragile"], "ant": ["resilient", "invulnerable"]},
        {"word": "advocate", "pos": "verb", "meaning": "옹호하다, 지지하다", "us_p": "/ˈæd.və.keɪt/", "uk_p": "/ˈæd.və.keɪt/",
         "ex_en": "The organization advocates for animal welfare policies.", "ex_ko": "그 단체는 동물 복지 정책을 옹호한다.",
         "syn": ["support", "champion"], "ant": ["oppose"]},
        {"word": "coincide", "pos": "verb", "meaning": "일치하다, 동시에 일어나다", "us_p": "/ˌkoʊ.ɪnˈsaɪd/", "uk_p": "/ˌkəʊ.ɪnˈsaɪd/",
         "ex_en": "The festival will coincide with the national holiday.", "ex_ko": "축제는 국경일과 시기가 겹칠 것이다.",
         "syn": ["concur", "overlap"], "ant": ["differ", "diverge"]},
        {"word": "rational", "pos": "adjective", "meaning": "합리적인, 이성적인", "us_p": "/ˈræʃ.ən.əl/", "uk_p": "/ˈræʃ.ən.əl/",
         "ex_en": "We should make a rational decision based on evidence.", "ex_ko": "우리는 증거에 기반하여 합리적인 결정을 내려야 한다.",
         "syn": ["logical", "reasonable"], "ant": ["irrational", "emotional"]},
    ],
    4: [
        {"word": "ambiguity", "pos": "noun", "meaning": "모호성, 다의성", "us_p": "/ˌæm.bəˈɡjuː.ə.t̬i/", "uk_p": "/ˌæm.bɪˈɡjuː.ə.ti/",
         "ex_en": "The legal contract was rewritten to eliminate ambiguity.", "ex_ko": "법적 계약서는 모호성을 없애기 위해 다시 작성되었다.",
         "syn": ["vagueness", "obscurity"], "ant": ["clarity", "certainty"]},
        {"word": "deteriorate", "pos": "verb", "meaning": "악화되다, 저하되다", "us_p": "/dɪˈtɪr.i.ə.reɪt/", "uk_p": "/dɪˈtɪə.ri.ə.reɪt/",
         "ex_en": "His health began to deteriorate rapidly during winter.", "ex_ko": "겨울 동안 그의 건강은 급격히 악화되기 시작했다.",
         "syn": ["degenerate", "worsen"], "ant": ["improve", "ameliorate"]},
        {"word": "impetus", "pos": "noun", "meaning": "자극, 추진력, 원동력", "us_p": "/ˈɪm.pə.t̬əs/", "uk_p": "/ˈɪm.pɪ.təs/",
         "ex_en": "The award gave new impetus to her research career.", "ex_ko": "그 상은 그녀의 연구 경력에 새로운 추진력을 제공했다.",
         "syn": ["momentum", "stimulus"], "ant": ["deterrent", "hindrance"]},
        {"word": "juxtapose", "pos": "verb", "meaning": "병치하다, 나란히 놓다", "us_p": "/ˈdʒʌk.stə.poʊz/", "uk_p": "/ˌdʒʌk.stəˈpəʊz/",
         "ex_en": "The artist juxtaposed bright colors with dark shades.", "ex_ko": "그 예술가는 밝은 색상과 어두운 명암을 나란히 배치했다.",
         "syn": ["collocate", "contrast"], "ant": []},
        {"word": "scrutinize", "pos": "verb", "meaning": "면밀히 조사하다", "us_p": "/ˈskruː.t̬ən.aɪz/", "uk_p": "/ˈskruː.tɪ.naɪz/",
         "ex_en": "Inspectors will scrutinize the safety records thoroughly.", "ex_ko": "검사관들은 안전 기록을 철저히 면밀하게 조사할 것이다.",
         "syn": ["examine", "inspect"], "ant": ["overlook", "glance"]},
        {"word": "aberration", "pos": "noun", "meaning": "일탈, 탈선, 이상 현상", "us_p": "/ˌæb.əˈreɪ.ʃən/", "uk_p": "/ˌæb.əˈreɪ.ʃən/",
         "ex_en": "The sudden drop in temperature was an unusual aberration.", "ex_ko": "갑작스러운 기온 하강은 보기 드문 이상 현상이었다.",
         "syn": ["anomaly", "deviation"], "ant": ["normality", "conformity"]},
        {"word": "capricious", "pos": "adjective", "meaning": "변덕스러운, 예측할 수 없는", "us_p": "/kəˈprɪʃ.əs/", "uk_p": "/kəˈprɪʃ.əs/",
         "ex_en": "The island is known for its capricious coastal weather.", "ex_ko": "그 섬은 변덕스러운 해안 날씨로 유명하다.",
         "syn": ["fickle", "whimsical"], "ant": ["predictable", "steady"]},
        {"word": "empirical", "pos": "adjective", "meaning": "실증적인, 경험에 따른", "us_p": "/emˈpɪr.ɪ.kəl/", "uk_p": "/ɪmˈpɪr.ɪ.kəl/",
         "ex_en": "The hypothesis must be supported by empirical evidence.", "ex_ko": "그 가설은 실증적인 증거에 의해 뒷받침되어야 한다.",
         "syn": ["observational", "experimental"], "ant": ["theoretical", "hypothetical"]},
        {"word": "meticulous", "pos": "adjective", "meaning": "꼼꼼한, 세심한", "us_p": "/məˈtɪk.jə.ləs/", "uk_p": "/məˈtɪk.jə.ləs/",
         "ex_en": "He did meticulous work on the historical manuscript.", "ex_ko": "그는 역사적인 원고에 대해 매우 꼼꼼한 작업을 수행했다.",
         "syn": ["thorough", "painstaking"], "ant": ["careless", "sloppy"]},
        {"word": "paradigm", "pos": "noun", "meaning": "패러다임, 전형적인 모형", "us_p": "/ˈper.ə.daɪm/", "uk_p": "/ˈpær.ə.daɪm/",
         "ex_en": "Quantum mechanics introduced a new paradigm in physics.", "ex_ko": "양자역학은 물리학에 새로운 패러다임을 도입했다.",
         "syn": ["model", "prototype"], "ant": []},
        {"word": "resilience", "pos": "noun", "meaning": "회복력, 탄력성", "us_p": "/rɪˈzɪl.jəns/", "uk_p": "/rɪˈzɪl.jəns/",
         "ex_en": "Psychological resilience helps people overcome adversity.", "ex_ko": "심리적 회복력은 사람들이 역경을 극복하도록 돕는다.",
         "syn": ["tenacity", "toughness"], "ant": ["fragility"]},
        {"word": "volatile", "pos": "adjective", "meaning": "변동성이 큰, 휘발성의", "us_p": "/ˈvɑː.lə.t̬əl/", "uk_p": "/ˈvɒl.ə.taɪl/",
         "ex_en": "The stock market remained highly volatile all week.", "ex_ko": "주식 시장은 일주일 내내 변동성이 매우 컸다.",
         "syn": ["unstable", "turbulent"], "ant": ["stable", "constant"]},
        {"word": "ambivalent", "pos": "adjective", "meaning": "양면적인, 반대 감정이 공존하는", "us_p": "/æmˈbɪv.ə.lənt/", "uk_p": "/æmˈbɪv.ə.lənt/",
         "ex_en": "He felt ambivalent about accepting the promotion abroad.", "ex_ko": "그는 해외 승진을 수락하는 것에 대해 양가감정을 느꼈다.",
         "syn": ["uncertain", "conflicted"], "ant": ["decisive", "unequivocal"]},
        {"word": "intrinsic", "pos": "adjective", "meaning": "내재적인, 본질적인", "us_p": "/ɪnˈtrɪn.zɪk/", "uk_p": "/ɪnˈtrɪn.zɪk/",
         "ex_en": "Curiosity is an intrinsic part of human nature.", "ex_ko": "호기심은 인간 본성의 내재적인 부분이다.",
         "syn": ["inherent", "innate"], "ant": ["extrinsic", "acquired"]},
        {"word": "redundant", "pos": "adjective", "meaning": "불필요한, 과잉의, 정리해고된", "us_p": "/rɪˈdʌn.dənt/", "uk_p": "/rɪˈdʌn.dənt/",
         "ex_en": "The editor removed redundant words to make the text concise.", "ex_ko": "편집자는 글을 간결하게 만들기 위해 불필요한 단어들을 제거했다.",
         "syn": ["superfluous", "repetitive"], "ant": ["essential", "necessary"]},
    ],
    5: [
        {"word": "agenda", "pos": "noun", "meaning": "의제, 안건, 회의 일정", "us_p": "/əˈdʒen.də/", "uk_p": "/əˈdʒen.də/",
         "ex_en": "The first item on the agenda is the annual budget.", "ex_ko": "안건의 첫 번째 항목은 연간 예산입니다.",
         "syn": ["schedule", "program"], "ant": []},
        {"word": "budget", "pos": "noun", "meaning": "예산, 경비", "us_p": "/ˈbʌdʒ.ɪt/", "uk_p": "/ˈbʌdʒ.ɪt/",
         "ex_en": "The marketing department managed to stay within budget.", "ex_ko": "마케팅 부서는 예산 범위 내에서 성공적으로 지출을 관리했다.",
         "syn": ["allowance", "allocation"], "ant": []},
        {"word": "commute", "pos": "verb", "meaning": "통근하다, 통학하다", "us_p": "/kəˈmjuːt/", "uk_p": "/kəˈmjuːt/",
         "ex_en": "Many employees commute to the office by subway.", "ex_ko": "많은 직원들이 지하철로 사무실까지 통근한다.",
         "syn": ["travel"], "ant": []},
        {"word": "deadline", "pos": "noun", "meaning": "마감일, 마감 기한", "us_p": "/ˈded.laɪn/", "uk_p": "/ˈded.laɪn/",
         "ex_en": "We must submit the proposal before the Friday deadline.", "ex_ko": "우리는 금요일 마감 기한 전에 제안서를 제출해야 한다.",
         "syn": ["due date", "cutoff"], "ant": []},
        {"word": "invoice", "pos": "noun", "meaning": "청구서, 송장", "us_p": "/ˈɪn.vɔɪs/", "uk_p": "/ˈɪn.vɔɪs/",
         "ex_en": "Payment is due within thirty days of the invoice date.", "ex_ko": "청구서 발행일로부터 30일 이내에 지불하셔야 합니다.",
         "syn": ["bill", "statement"], "ant": []},
        {"word": "candidate", "pos": "noun", "meaning": "지원자, 후보자", "us_p": "/ˈkæn.dɪ.dət/", "uk_p": "/ˈkæn.dɪ.dət/",
         "ex_en": "The interview panel evaluated each qualified candidate.", "ex_ko": "면접관들은 자격을 갖춘 각 지원자를 평가했다.",
         "syn": ["applicant", "nominee"], "ant": []},
        {"word": "collaborate", "pos": "verb", "meaning": "협력하다, 공동 작업하다", "us_p": "/kəˈlæb.ə.reɪt/", "uk_p": "/kəˈlæb.ə.reɪt/",
         "ex_en": "The two companies collaborated on a joint venture.", "ex_ko": "두 회사는 합작 투자 사업에서 협력했다.",
         "syn": ["cooperate", "partner"], "ant": ["compete"]},
        {"word": "department", "pos": "noun", "meaning": "부서, 학과", "us_p": "/dɪˈpɑːrt.mənt/", "uk_p": "/dɪˈpɑːt.mənt/",
         "ex_en": "Contact the human resources department for benefits inquiries.", "ex_ko": "복리후생에 대한 문의는 인사과로 연락하세요.",
         "syn": ["division", "section"], "ant": []},
        {"word": "itinerary", "pos": "noun", "meaning": "여행 일정표", "us_p": "/aɪˈtɪn.ə.rer.i/", "uk_p": "/aɪˈtɪn.ər.ər.i/",
         "ex_en": "The business itinerary includes meetings across three cities.", "ex_ko": "출장 일정표에는 세 개 도시에서의 회의가 포함되어 있다.",
         "syn": ["schedule", "route"], "ant": []},
        {"word": "negotiate", "pos": "verb", "meaning": "협상하다, 절충하다", "us_p": "/nəˈɡoʊ.ʃi.eɪt/", "uk_p": "/nəˈɡəʊ.ʃi.eɪt/",
         "ex_en": "They negotiated favorable terms for the contract renewal.", "ex_ko": "그들은 계약 갱신을 위해 유리한 조건을 협상했다.",
         "syn": ["bargain", "mediate"], "ant": []},
        {"word": "personnel", "pos": "noun", "meaning": "인원, 전 직원, 인사과", "us_p": "/ˌpɝː.sənˈel/", "uk_p": "/ˌpɜː.sənˈel/",
         "ex_en": "All authorized personnel must display their ID badges.", "ex_ko": "모든 인가된 직원은 신분증 배지를 착용해야 합니다.",
         "syn": ["staff", "workforce"], "ant": []},
        {"word": "promote", "pos": "verb", "meaning": "승진시키다, 홍보하다", "us_p": "/prəˈmoʊt/", "uk_p": "/prəˈməʊt/",
         "ex_en": "The agency launched a campaign to promote the new product.", "ex_ko": "대행사는 신제품을 홍보하기 위한 캠페인을 시작했다.",
         "syn": ["advertise", "advance"], "ant": ["demote", "hinder"]},
        {"word": "receipt", "pos": "noun", "meaning": "영수증, 수령", "us_p": "/rɪˈsiːt/", "uk_p": "/rɪˈsiːt/",
         "ex_en": "Keep the sales receipt as proof of your purchase.", "ex_ko": "구매 증빙으로 판매 영수증을 보관하세요.",
         "syn": ["proof of purchase", "voucher"], "ant": []},
        {"word": "reimburse", "pos": "verb", "meaning": "환급하다, 변제하다", "us_p": "/ˌriː.ɪmˈbɝːs/", "uk_p": "/ˌriː.ɪmˈbɜːs/",
         "ex_en": "The company will reimburse your approved travel expenses.", "ex_ko": "회사는 승인된 출장 경비를 환급해 드릴 것입니다.",
         "syn": ["repay", "refund"], "ant": []},
        {"word": "warranty", "pos": "noun", "meaning": "품질 보증서, 보증 기간", "us_p": "/ˈwɔːr.ən.t̬i/", "uk_p": "/ˈwɒr.ən.ti/",
         "ex_en": "The appliance comes with a two-year manufacturer warranty.", "ex_ko": "해당 가전제품에는 2년 제조사 품질 보증이 제공됩니다.",
         "syn": ["guarantee", "pledge"], "ant": []},
    ],
    6: [
        {"word": "acquisition", "pos": "noun", "meaning": "인수, 기업 매수, 습득", "us_p": "/ˌæk.wəˈzɪʃ.ən/", "uk_p": "/ˌæk.wɪˈzɪʃ.ən/",
         "ex_en": "The corporate acquisition expanded their global market share.", "ex_ko": "그 기업 인수는 그들의 글로벌 시장 점유율을 확장시켰다.",
         "syn": ["takeover", "purchase"], "ant": ["divestiture"]},
        {"word": "compliance", "pos": "noun", "meaning": "준수, 순응, 법규 준수", "us_p": "/kəmˈplaɪ.əns/", "uk_p": "/kəmˈplaɪ.əns/",
         "ex_en": "Our operations are in strict compliance with safety laws.", "ex_ko": "우리의 운영은 안전 법규를 엄격히 준수하고 있습니다.",
         "syn": ["conformity", "adherence"], "ant": ["violation", "breach"]},
        {"word": "feasibility", "pos": "noun", "meaning": "실현 가능성, 타당성", "us_p": "/ˌfiː.zəˈbɪl.ə.t̬i/", "uk_p": "/ˌfiː.zəˈbɪl.ə.ti/",
         "ex_en": "They conducted a feasibility study before launching the project.", "ex_ko": "그들은 프로젝트를 시작하기 전에 타당성 조사를 실시했다.",
         "syn": ["viability", "practicability"], "ant": ["impossibility"]},
        {"word": "yield", "pos": "verb", "meaning": "산출하다, 수익을 내다, 양보하다", "us_p": "/jiːld/", "uk_p": "/jiːld/",
         "ex_en": "The investment portfolio yields a steady dividend income.", "ex_ko": "그 투자 포트폴리오는 안정적인 배당 수익을 창출한다.",
         "syn": ["generate", "produce"], "ant": []},
        {"word": "affiliate", "pos": "noun", "meaning": "계열사, 지부, 가맹점", "us_p": "/əˈfɪl.i.ət/", "uk_p": "/əˈfɪl.i.eɪt/",
         "ex_en": "The product is distributed through international affiliates.", "ex_ko": "해당 제품은 해외 계열사들을 통해 유통된다.",
         "syn": ["subsidiary", "branch"], "ant": ["parent company"]},
        {"word": "audit", "pos": "noun", "meaning": "회계 감사, 심사", "us_p": "/ˈɑː.dɪt/", "uk_p": "/ˈɔː.dɪt/",
         "ex_en": "The financial records will undergo an independent audit.", "ex_ko": "재무 기록은 독립적인 회계 감사를 받게 될 것이다.",
         "syn": ["inspection", "scrutiny"], "ant": []},
        {"word": "benchmark", "pos": "noun", "meaning": "기준, 벤치마크", "us_p": "/ˈbentʃ.mɑːrk/", "uk_p": "/ˈbentʃ.mɑːk/",
         "ex_en": "The index serves as a benchmark for investment performance.", "ex_ko": "그 지수는 투자 성과의 기준(벤치마크) 역할을 한다.",
         "syn": ["standard", "criterion"], "ant": []},
        {"word": "consensus", "pos": "noun", "meaning": "합의, 일치된 의견", "us_p": "/kənˈsen.səs/", "uk_p": "/kənˈsen.səs/",
         "ex_en": "The executive committee reached a consensus on the strategy.", "ex_ko": "경영위원회는 전략에 대한 합의에 도달했다.",
         "syn": ["agreement", "accord"], "ant": ["disagreement", "discord"]},
        {"word": "dividend", "pos": "noun", "meaning": "배당금, 분배금", "us_p": "/ˈdɪv.ə.dend/", "uk_p": "/ˈdɪv.ɪ.dend/",
         "ex_en": "Shareholders will receive a quarterly dividend payment.", "ex_ko": "주주들은 분기별 배당금을 지급받게 될 것입니다.",
         "syn": ["payout", "return"], "ant": []},
        {"word": "endorsement", "pos": "noun", "meaning": "지지, 홍보 계약, 보증", "us_p": "/ɪnˈdɔːrs.mənt/", "uk_p": "/ɪnˈdɔːs.mənt/",
         "ex_en": "Celebrity endorsement significantly boosted brand awareness.", "ex_ko": "유명인 지지 광고는 브랜드 인지도를 크게 끌어올렸다.",
         "syn": ["backing", "sponsorship"], "ant": ["disapproval"]},
        {"word": "fiduciary", "pos": "adjective", "meaning": "신탁의, 수탁자의", "us_p": "/fɪˈduː.ʃi.er.i/", "uk_p": "/fɪˈdʒuː.ʃi.ər.i/",
         "ex_en": "Directors have a fiduciary duty to act in the company's best interest.", "ex_ko": "이사들은 회사의 최선의 이익을 위해 행동할 수탁자 의무가 있다.",
         "syn": ["trustee", "custodial"], "ant": []},
        {"word": "lucrative", "pos": "adjective", "meaning": "수익성이 좋은, 돈벌이가 되는", "us_p": "/ˈluː.krə.t̬ɪv/", "uk_p": "/ˈluː.krə.tɪv/",
         "ex_en": "The contract turned out to be highly lucrative for both parties.", "ex_ko": "그 계약은 양측 모두에게 매우 수익성이 좋은 것으로 판명되었다.",
         "syn": ["profitable", "rewarding"], "ant": ["unprofitable"]},
        {"word": "moratorium", "pos": "noun", "meaning": "지급 유예, 활동 일시 중단", "us_p": "/ˌmɔːr.əˈtɔːr.i.əm/", "uk_p": "/ˌmɒr.əˈtɔː.ri.əm/",
         "ex_en": "The government declared a moratorium on debt repayments.", "ex_ko": "정부는 부채 상환에 대한 지급 유예(모라토리엄)를 선언했다.",
         "syn": ["suspension", "freeze"], "ant": ["continuation"]},
        {"word": "solvency", "pos": "noun", "meaning": "지불 능력, 상환 능력", "us_p": "/ˈsɑːl.vən.si/", "uk_p": "/ˈsɒl.vən.si/",
         "ex_en": "The central bank closely monitors the solvency of major lenders.", "ex_ko": "중앙은행은 주요 대출 기관들의 지급 능력을 면밀히 모니터링한다.",
         "syn": ["stability", "liquidity"], "ant": ["insolvency", "bankruptcy"]},
        {"word": "stringent", "pos": "adjective", "meaning": "엄격한, 혹독한", "us_p": "/ˈstrɪn.dʒənt/", "uk_p": "/ˈstrɪn.dʒənt/",
         "ex_en": "The aviation industry enforces stringent safety guidelines.", "ex_ko": "항공 산업은 엄격한 안전 지침을 시행한다.",
         "syn": ["strict", "rigorous"], "ant": ["lenient", "flexible"]},
    ],
    7: [
        {"word": "consolidate", "pos": "verb", "meaning": "통합하다, 결합하다, 강화하다", "us_p": "/kənˈsɑː.lə.deɪt/", "uk_p": "/kənˈsɒl.ɪ.deɪt/",
         "ex_en": "The corporation decided to consolidate its multiple branches.", "ex_ko": "그 기업은 여러 지사를 하나로 통합하기로 결정했다.",
         "syn": ["merge", "unify"], "ant": ["separate", "disperse"]},
        {"word": "depreciation", "pos": "noun", "meaning": "가치 하락, 감가상각", "us_p": "/dɪˌpriː.ʃiˈeɪ.ʃən/", "uk_p": "/dɪˌpriː.ʃiˈeɪ.ʃən/",
         "ex_en": "Tax laws permit the depreciation of capital equipment over time.", "ex_ko": "세법은 시간이 지남에 따른 자본 설비의 감가상각을 허용한다.",
         "syn": ["devaluation", "amortization"], "ant": ["appreciation"]},
        {"word": "indemnify", "pos": "verb", "meaning": "배상하다, 면책하다, 보상하다", "us_p": "/ɪnˈdem.nə.faɪ/", "uk_p": "/ɪnˈdem.nɪ.faɪ/",
         "ex_en": "The insurance policy will indemnify the client against property loss.", "ex_ko": "보험 증권은 재산 손실에 대해 고객을 보상/면책할 것이다.",
         "syn": ["compensate", "reimburse"], "ant": []},
        {"word": "liquidity", "pos": "noun", "meaning": "유동성, 환금성", "us_p": "/lɪˈkwɪd.ə.t̬i/", "uk_p": "/lɪˈkwɪd.ə.ti/",
         "ex_en": "Maintaining sufficient liquidity is crucial during market downturns.", "ex_ko": "시장 침체기에는 충분한 유동성을 유지하는 것이 매우 중요하다.",
         "syn": ["cash flow", "solvency"], "ant": ["illiquidity"]},
        {"word": "prerequisite", "pos": "noun", "meaning": "전제 조건, 필수 요건", "us_p": "/ˌpriːˈrek.wə.zɪt/", "uk_p": "/ˌpriːˈrek.wɪ.zɪt/",
         "ex_en": "A bachelor degree is a prerequisite for entry into the program.", "ex_ko": "학사 학위는 해당 프로그램 진입을 위한 필수 전제 조건이다.",
         "syn": ["requirement", "precondition"], "ant": []},
        {"word": "arbitration", "pos": "noun", "meaning": "중재, 분쟁 해결", "us_p": "/ˌɑːr.bəˈtreɪ.ʃən/", "uk_p": "/ˌɑː.bɪˈtreɪ.ʃən/",
         "ex_en": "Both parties agreed to settle the commercial dispute via arbitration.", "ex_ko": "양측은 중재를 통해 상업적 분쟁을 해결하기로 합의했다.",
         "syn": ["mediation", "adjudication"], "ant": ["litigation"]},
        {"word": "defalcation", "pos": "noun", "meaning": "공금 횡령, 배임", "us_p": "/ˌdiː.fælˈkeɪ.ʃən/", "uk_p": "/ˌdiː.fælˈkeɪ.ʃən/",
         "ex_en": "The auditor uncovered serious defalcation within the accounting division.", "ex_ko": "감사관은 회계 부서 내의 심각한 공금 횡령을 적발했다.",
         "syn": ["embezzlement", "misappropriation"], "ant": []},
        {"word": "derivative", "pos": "noun", "meaning": "파생 금융 상품, 파생물", "us_p": "/dɪˈrɪv.ə.t̬ɪv/", "uk_p": "/dɪˈrɪv.ə.tɪv/",
         "ex_en": "Financial institutions use derivatives to hedge against interest rate risks.", "ex_ko": "금융 기관들은 금리 위험을 헤지하기 위해 파생 상품을 사용한다.",
         "syn": ["byproduct", "hedge"], "ant": []},
        {"word": "equity", "pos": "noun", "meaning": "자기자본, 보통주, 공평", "us_p": "/ˈek.wə.t̬i/", "uk_p": "/ˈek.wɪ.ti/",
         "ex_en": "The startup raised two million dollars in venture equity financing.", "ex_ko": "그 스타트업은 벤처 자기자본 펀딩을 통해 200만 달러를 유치했다.",
         "syn": ["shares", "capital"], "ant": ["debt"]},
        {"word": "escrow", "pos": "noun", "meaning": "조건부 날인 증서, 에스크로 보관", "us_p": "/ˈes.kroʊ/", "uk_p": "/ˈes.krəʊ/",
         "ex_en": "Funds will be held in escrow until all closing conditions are met.", "ex_ko": "모든 종결 조건이 충족될 때까지 자금은 에스크로 계좌에 보관됩니다.",
         "syn": ["safekeeping", "custody"], "ant": []},
        {"word": "forbearance", "pos": "noun", "meaning": "지불 유예, 인내, 관용", "us_p": "/fɔːrˈber.əns/", "uk_p": "/fɔːˈbeə.rəns/",
         "ex_en": "The lender granted mortgage forbearance during the economic crisis.", "ex_ko": "대출 기관은 경제 위기 동안 주택 담보 대출 상환 유예를 허가했다.",
         "syn": ["patience", "lenience"], "ant": ["enforcement", "impatience"]},
        {"word": "insolvency", "pos": "noun", "meaning": "지급 불능, 파산", "us_p": "/ɪnˈsɑːl.vən.si/", "uk_p": "/ɪnˈsɒl.vən.si/",
         "ex_en": "The restructuring plan aimed to prevent full corporate insolvency.", "ex_ko": "구조조정 계획은 기업의 완전한 파산을 방지하는 것을 목표로 했다.",
         "syn": ["bankruptcy", "ruin"], "ant": ["solvency"]},
        {"word": "malpractice", "pos": "noun", "meaning": "위법 행위, 업무상 과실", "us_p": "/ˌmælˈpræk.tɪs/", "uk_p": "/ˌmælˈpræk.tɪs/",
         "ex_en": "The physician carried extensive insurance against professional malpractice.", "ex_ko": "그 의사는 전문적인 의료 과실에 대비해 종합 보험을 들고 있었다.",
         "syn": ["misconduct", "negligence"], "ant": []},
        {"word": "remittance", "pos": "noun", "meaning": "송금, 납부액", "us_p": "/rɪˈmɪt̬.əns/", "uk_p": "/rɪˈmɪt.əns/",
         "ex_en": "Please confirm the foreign remittance of funds into our bank account.", "ex_ko": "당사 은행 계좌로의 해외 자금 송금을 확인해 주시기 바랍니다.",
         "syn": ["payment", "transfer"], "ant": []},
        {"word": "underwriting", "pos": "noun", "meaning": "인수 업무, 보험 심사, 보증", "us_p": "/ˈʌn.dɚˌraɪ.t̬ɪŋ/", "uk_p": "/ˈʌn.dəˌraɪ.tɪŋ/",
         "ex_en": "The investment bank led the underwriting syndicate for the IPO.", "ex_ko": "그 투자은행은 기업공개(IPO)를 위한 인수 신디케이트를 주도했다.",
         "syn": ["guarantee", "sponsorship"], "ant": []},
    ],
}


def compute_sha256(filepath: Path) -> str:
    """파일의 SHA-256 체크섬을 계산합니다."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def generate_all_datasets() -> None:
    """Level 1부터 Level 7까지의 단어 JSON 파일과 manifest.json을 생성합니다."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print(" 1~7단계 단어 데이터셋 종합 구축 시작")
    print("==================================================")

    now_iso = datetime.now(timezone.utc).isoformat()
    levels_meta: dict[str, Any] = {}

    for level, word_list in DATASET.items():
        level_code = LEVEL_META[level]["code"]
        level_name = LEVEL_META[level]["name"]
        output_file = DATA_DIR / f"level_{level}.json"
        raw_file = RAW_DIR / f"level_{level}_words.txt"

        entries: list[dict[str, Any]] = []
        raw_lines: list[str] = []

        for idx, item in enumerate(word_list, start=1):
            word = item["word"]
            pos = item["pos"]
            meaning = item["meaning"]

            # 표준 스키마 단어 객체 조립
            entry = {
                "id": f"{level_code}-{idx:04d}",
                "word": word,
                "level": level,
                "pos": pos,
                "meaning": meaning,
                "phonetics": {
                    "us": item["us_p"],
                    "uk": item["uk_p"],
                },
                "audio": {
                    "us": f"https://api.dictionaryapi.dev/media/pronunciations/en/{word}-us.mp3",
                    "uk": f"https://api.dictionaryapi.dev/media/pronunciations/en/{word}-uk.mp3",
                },
                "example_en": item["ex_en"],
                "example_ko": item["ex_ko"],
                "synonyms": item["syn"],
                "antonyms": item["ant"],
            }
            entries.append(entry)
            raw_lines.append(f"{word},{meaning}")

        # level_n.json 저장 (UTF-8, 들여쓰기 2)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)

        # raw/level_n_words.txt 동기화 저장
        with open(raw_file, "w", encoding="utf-8") as f:
            f.write("\n".join(raw_lines) + "\n")

        # 체크섬 및 메타데이터 기록
        sha256 = compute_sha256(output_file)
        levels_meta[str(level)] = {
            "name": level_name,
            "count": len(entries),
            "file": output_file.name,
            "sha256": sha256,
        }
        print(f"-> [Level {level}] {level_name}: {output_file.name} 저장 완료 ({len(entries)}단어)")

    # manifest.json 갱신
    manifest_path = DATA_DIR / "manifest.json"
    manifest_data = {
        "version": "1.0.0",
        "updated_at": now_iso,
        "levels": levels_meta,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2)

    print(f"\n[성공] manifest.json 메타데이터 갱신 완료: {manifest_path}")
    print("==================================================")
    print(" 모든 단계 단어장 구축이 성공적으로 완료되었습니다!")
    print("==================================================")


if __name__ == "__main__":
    generate_all_datasets()
