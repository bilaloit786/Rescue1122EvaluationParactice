import pytest

from app.models.user import QuestionBank
from app.services.question_quality import MCQQuestion, is_valid_question


class TestQuestionQuality:
    def test_accepts_short_mobile_quiz_question(self):
        question = MCQQuestion(
            question_text="The red section of NFPA diamond indicates:",
            options=["Health", "Instability", "Flammability", "Toxicity"],
        )
        assert is_valid_question(question) is True

    @pytest.mark.parametrize(
        "question_text,options",
        [
            ("Others ________. Forcible entry tools are used with:", ["8.2", "9.2", "1.2", "10.2"]),
            ("The force required is ________", ["Low", "Medium", "High", "Extreme"]),
            ("Also used with emergency tools and rescue equipment for the operation?", ["A", "B", "C", "D"]),
            ("Which tool is used?", ["Halligan", "Axe", "Saw", "Cutter"]),
            ("This complete sentence has enough words but does not ask anything clearly", ["A", "B", "C", "D"]),
            ("Which of the following numbers matches the manual section for this topic?", ["8.2", "9.2", "1.2", "10.2"]),
            ("In Fire 02 - Fire Fighting History, what should a responder do during initial scene size-up when the main safety point is applying fire fighting history knowledge in the field?", ["Safe action", "Unsafe shortcut", "Random code", "Unrelated task"]),
        ],
    )
    def test_rejects_low_quality_questions(self, question_text, options):
        assert is_valid_question(MCQQuestion(question_text=question_text, options=options)) is False

    async def test_generate_ignores_invalid_question_bank_rows(self, client, staff_headers, db):
        for index in range(30):
            db.add(QuestionBank(
                topic_id="quality_topic",
                difficulty="easy" if index < 10 else "medium" if index < 20 else "hard",
                is_valid=True,
                question={
                    "q": f"Quality rescue rope practice item {index} is mainly used to:",
                    "question": f"Quality rescue rope practice item {index} is mainly used to:",
                    "opts": ["Safe action", "Unsafe shortcut", "Random code", "Unrelated task"],
                    "options": ["Safe action", "Unsafe shortcut", "Random code", "Unrelated task"],
                    "ans": 0,
                    "topic": "Quality Topic",
                },
            ))
        db.add(QuestionBank(
            topic_id="quality_topic",
            difficulty="easy",
            is_valid=False,
            question={
                "q": "Others ________. Forcible entry tools are used with:",
                "question": "Others ________. Forcible entry tools are used with:",
                "opts": ["8.2", "9.2", "1.2", "10.2"],
                "options": ["8.2", "9.2", "1.2", "10.2"],
                "ans": 0,
                "topic": "Quality Topic",
            },
        ))
        await db.commit()

        resp = await client.post(
            "/api/test/generate",
            headers=staff_headers,
            json={"topic_id": "quality_topic", "designation": "OTHER"},
        )

        assert resp.status_code == 200
        questions = resp.json()["questions"]
        assert len(questions) == 25
        assert all("____" not in question["question"] for question in questions)
        assert all(question["question"] != "Others ________. Forcible entry tools are used with:" for question in questions)
