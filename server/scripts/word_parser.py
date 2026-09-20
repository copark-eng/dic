# -*- coding: utf-8 -*-
from __future__ import annotations
"""
단어 응답 파서 (Word Parser)
api.dictionaryapi.dev 응답을 분석하여 US/UK 발음기호 및 오디오 링크를 추출하고
server_requirements.md 표준 스키마로 정규화
Python 3.9+ 호환, UTF-8 인코딩 적용
"""

from typing import Any, Optional


class WordParser:
    """Dictionary API 응답을 정규화된 사전 데이터 스키마로 변환하는 파서"""

    @staticmethod
    def _normalize_audio_url(url: Optional[str]) -> Optional[str]:
        """오디오 URL 정규화 (상대 경로 및 스키마 보정)"""
        if not url or not isinstance(url, str):
            return None
        url = url.strip()
        if not url:
            return None
        if url.startswith("//"):
            return f"https:{url}"
        if not url.startswith("http"):
            return f"https://{url}"
        return url

    @classmethod
    def extract_phonetics_and_audio(cls, entry: dict[str, Any]) -> tuple[dict[str, str], dict[str, Optional[str]]]:
        """
        API 응답 항목에서 미국식(US)과 영국식(UK) 발음기호 및 오디오 링크를 추출합니다.
        """
        us_phonetic: str = ""
        uk_phonetic: str = ""
        us_audio: Optional[str] = None
        uk_audio: Optional[str] = None

        # 기본 탑레벨 phonetic 필드 확인
        general_phonetic: str = entry.get("phonetic", "") or ""

        phonetics_list = entry.get("phonetics", [])
        if isinstance(phonetics_list, list):
            for item in phonetics_list:
                if not isinstance(item, dict):
                    continue

                text = item.get("text", "") or ""
                audio_url = cls._normalize_audio_url(item.get("audio"))

                if audio_url:
                    lower_url = audio_url.lower()
                    # 미국식 오디오 식별
                    if any(k in lower_url for k in ["-us.mp3", "/us/", "_us_", "en-us"]):
                        if not us_audio:
                            us_audio = audio_url
                            if text and not us_phonetic:
                                us_phonetic = text
                    # 영국식 오디오 식별
                    elif any(k in lower_url for k in ["-uk.mp3", "/uk/", "_uk_", "-gb.mp3", "/gb/", "en-uk", "en-gb"]):
                        if not uk_audio:
                            uk_audio = audio_url
                            if text and not uk_phonetic:
                                uk_phonetic = text
                    else:
                        # 지역 구분이 명시되지 않은 경우 우선 미국식/영국식 빈자리에 폴백 배정
                        if not us_audio:
                            us_audio = audio_url
                        elif not uk_audio:
                            uk_audio = audio_url

                # 텍스트 발음기호가 있고 아직 채워지지 않은 경우
                if text:
                    if not us_phonetic:
                        us_phonetic = text
                    elif not uk_phonetic and text != us_phonetic:
                        uk_phonetic = text

        # 발음기호가 비어있으면 general_phonetic으로 보정
        if not us_phonetic and general_phonetic:
            us_phonetic = general_phonetic
        if not uk_phonetic and us_phonetic:
            uk_phonetic = us_phonetic

        phonetics = {
            "us": us_phonetic,
            "uk": uk_phonetic,
        }
        audio = {
            "us": us_audio,
            "uk": uk_audio,
        }
        return phonetics, audio

    @classmethod
    def parse_word_entry(
        cls,
        word: str,
        korean_meaning: str,
        level: int,
        word_index: int,
        api_data: Optional[list[dict[str, Any]]],
    ) -> dict[str, Any]:
        """
        API 응답 데이터를 취합하여 최종 표준 단어 객체를 구성합니다.
        """
        word_id = f"L{level}-{word_index:04d}"
        pos = "noun"
        example_en = ""
        synonyms: list[str] = []
        antonyms: list[str] = []

        phonetics = {"us": "", "uk": ""}
        audio = {"us": None, "uk": None}

        if api_data and len(api_data) > 0:
            first_entry = api_data[0]

            # 발음 및 오디오 링크 추출
            phonetics, audio = cls.extract_phonetics_and_audio(first_entry)

            # 품사, 예문, 유의어/반의어 추출
            meanings = first_entry.get("meanings", [])
            if isinstance(meanings, list) and len(meanings) > 0:
                first_meaning = meanings[0]
                pos = first_meaning.get("partOfSpeech", pos)

                # 유의어/반의어 수집
                for m in meanings:
                    for s in m.get("synonyms", []):
                        if s and s not in synonyms and len(synonyms) < 5:
                            synonyms.append(str(s))
                    for a in m.get("antonyms", []):
                        if a and a not in antonyms and len(antonyms) < 5:
                            antonyms.append(str(a))

                    # 예문 탐색
                    if not example_en:
                        definitions = m.get("definitions", [])
                        for d in definitions:
                            ex = d.get("example")
                            if ex:
                                example_en = str(ex).strip()
                                break

        # 예문 기본값 (API에 예문이 없을 때 단어 활용 기본 문장)
        if not example_en:
            example_en = f"This is an example sentence for {word}."

        return {
            "id": word_id,
            "word": word.strip(),
            "level": level,
            "pos": pos,
            "meaning": korean_meaning.strip(),
            "phonetics": phonetics,
            "audio": audio,
            "example_en": example_en,
            "example_ko": "",  # 한국어 예문 해석 (원천 데이터 또는 추후 보정)
            "synonyms": synonyms,
            "antonyms": antonyms,
        }
