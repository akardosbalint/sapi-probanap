from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from sapi_probanap.knowledge_agent import TudasbazisAgent
from sapi_probanap.models import KnowledgeCategory, TudasElem, TudasbazisResult


def _mock_response(payload: dict) -> MagicMock:
    msg = MagicMock()
    msg.content = [MagicMock(text=json.dumps(payload))]
    return msg


SAMPLE_PAYLOAD = {
    "tudaselemek": [
        {
            "cim": "Szegmentálás növeli a megnyitási arányt",
            "tartalom": "Ha a feliratkozókat viselkedés alapján szegmentálod, az e-mailek relevánsabbak lesznek. Ez átlagosan 20-30%-kal növeli a megnyitási arányt. A szegmenseket rendszeresen frissíteni kell az aktualitás megőrzéséhez.",
            "kategoria": "Email marketing",
            "hasznossagi_pont": 9,
            "miert_hasznos": "Email marketingeseknek, akik javítani szeretnék a kampányok teljesítményét.",
        },
        {
            "cim": "Webhook alapú integráció Make.com-mal",
            "tartalom": "Make.com scenariók webhook trigger segítségével kapcsolhatók össze külső rendszerekkel. A webhook URL-t a scenarióban kell generálni, majd a külső rendszerbe beilleszteni.",
            "kategoria": "Integráció",
            "hasznossagi_pont": 7,
            "miert_hasznos": "Rendszerintegrátoroknak, akik Make.com-ot és külső API-kat kapcsolnak össze.",
        },
    ],
    "osszesen": 2,
    "legfontosabb_tanuls": "A szegmentálás és az automatizálás együttes alkalmazása a leghatékonyabb.",
}


def test_process_returns_validated_result():
    with patch("sapi_probanap.knowledge_agent.anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = _mock_response(SAMPLE_PAYLOAD)
        agent = TudasbazisAgent(api_key="test-key")
        result = agent.process("Teszt szöveg")

    assert isinstance(result, TudasbazisResult)
    assert result.osszesen == 2
    assert len(result.tudaselemek) == 2


def test_elements_sorted_descending():
    unsorted_payload = {
        **SAMPLE_PAYLOAD,
        "tudaselemek": list(reversed(SAMPLE_PAYLOAD["tudaselemek"])),
    }
    with patch("sapi_probanap.knowledge_agent.anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = _mock_response(unsorted_payload)
        agent = TudasbazisAgent(api_key="test-key")
        result = agent.process("Teszt szöveg")

    scores = [e.hasznossagi_pont for e in result.tudaselemek]
    assert scores == sorted(scores, reverse=True)


def test_categories_validated():
    with patch("sapi_probanap.knowledge_agent.anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = _mock_response(SAMPLE_PAYLOAD)
        agent = TudasbazisAgent(api_key="test-key")
        result = agent.process("Teszt")

    assert result.tudaselemek[0].kategoria == KnowledgeCategory.EMAIL_MARKETING
    assert result.tudaselemek[1].kategoria == KnowledgeCategory.INTEGRATION


def test_osszesen_auto_corrected():
    wrong_count = {**SAMPLE_PAYLOAD, "osszesen": 99}
    with patch("sapi_probanap.knowledge_agent.anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = _mock_response(wrong_count)
        agent = TudasbazisAgent(api_key="test-key")
        result = agent.process("Teszt")

    assert result.osszesen == len(result.tudaselemek)


def test_hasznossagi_pont_range():
    elem = TudasElem(
        cim="Test",
        tartalom="Részletes tartalom itt.",
        kategoria=KnowledgeCategory.STRATEGY,
        hasznossagi_pont=5,
        miert_hasznos="Releváns stratégáknak.",
    )
    assert 1 <= elem.hasznossagi_pont <= 10


def test_hasznossagi_pont_out_of_range():
    with pytest.raises(Exception):
        TudasElem(
            cim="Test",
            tartalom="Tartalom.",
            kategoria=KnowledgeCategory.AUTOMATION,
            hasznossagi_pont=11,
            miert_hasznos="Valaki.",
        )
