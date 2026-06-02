import random

from scripts.seed_document_question_bank import (
    SourceFact,
    apply_required_metadata,
    build_options,
    build_source_question,
    validate_mcq,
)


class TestQuestionGenerationTemplates:
    def _question(self, difficulty):
        fact = SourceFact(
            subject="Forcible entry tools",
            answer="open locked or blocked doors",
            relation="use",
            source_text="Forcible entry tools are used to open locked or blocked doors.",
        )
        options = build_options(
            fact.answer,
            [
                fact.answer,
                "control smoke spread",
                "supply water to hoses",
                "protect breathing in smoke",
                "support evacuation routes",
            ],
            "fire",
            random.Random(f"test-{difficulty}"),
        )
        question = build_source_question(
            fact=fact,
            book="FireFighting",
            topic_label="Fire 25 - Forcible Entry",
            difficulty=difficulty,
            options=options,
            variant=0,
        )
        assert question is not None
        return apply_required_metadata(
            question,
            mcq_id=f"TEST_{difficulty}",
            book="FireFighting",
            topic_label="Fire 25 - Forcible Entry",
            difficulty=difficulty,
        )

    def test_easy_question_uses_short_mobile_language(self):
        question = self._question("easy")

        assert validate_mcq(question, "easy") is True
        assert question["question"] == "Forcible entry tools are mainly used to:"
        assert "main safety point" not in question["question"].lower()
        assert question["question"].endswith(":")

    def test_medium_question_uses_source_concept_language(self):
        question = self._question("medium")

        assert validate_mcq(question, "medium") is True
        assert "Forcible entry tools" in question["question"]
        assert question["q"] == question["question"]

    def test_hard_question_keeps_answer_mapping_consistent(self):
        question = self._question("hard")

        assert validate_mcq(question, "hard") is True
        assert question["opts"][question["ans"]] == "open locked or blocked doors"
        assert question["correct"] in question["options"]
