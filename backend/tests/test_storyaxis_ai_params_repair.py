import sys
import unittest
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.models import CardType

try:
    from repair_storyaxis_ai_params import repair_storyaxis_card_type_ai_params
except ModuleNotFoundError:
    repair_storyaxis_card_type_ai_params = None


class StoryAxisAIParamsRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
        )
        SQLModel.metadata.create_all(self.engine)

    def test_repair_updates_storyaxis_sampling_limits_without_touching_other_fields(self) -> None:
        self.assertIsNotNone(
            repair_storyaxis_card_type_ai_params,
            "repair_storyaxis_ai_params module is missing",
        )

        with Session(self.engine) as session:
            outdated = CardType(
                name="StoryAxis·世界观设定",
                model_name="WorldBuilding",
                ai_params={
                    "prompt_name": "StoryAxis·世界观设定",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "timeout": 150,
                    "llm_config_id": 2,
                },
                built_in=True,
            )
            already_correct = CardType(
                name="StoryAxis·章节正文",
                model_name="Chapter",
                ai_params={
                    "prompt_name": "StoryAxis·内容生成",
                    "temperature": 0.7,
                    "max_tokens": 200193,
                    "timeout": 600,
                    "llm_config_id": 3,
                },
                built_in=True,
            )
            custom_prompt = CardType(
                name="StoryAxis·角色卡",
                model_name="CharacterCard",
                ai_params={
                    "prompt_name": "我的自定义角色提示词",
                    "temperature": 0.6,
                    "max_tokens": 4096,
                    "timeout": 120,
                    "llm_config_id": 4,
                },
                built_in=True,
            )
            missing_ai_params = CardType(
                name="StoryAxis·写作指南",
                model_name="WritingGuide",
                ai_params=None,
                built_in=True,
            )
            non_storyaxis = CardType(
                name="章节正文",
                model_name="Chapter",
                ai_params={
                    "prompt_name": "内容生成",
                    "temperature": 0.7,
                    "max_tokens": 8192,
                    "timeout": 120,
                    "llm_config_id": 5,
                },
                built_in=True,
            )
            session.add(outdated)
            session.add(already_correct)
            session.add(custom_prompt)
            session.add(missing_ai_params)
            session.add(non_storyaxis)
            session.commit()

            first_result = repair_storyaxis_card_type_ai_params(session)
            second_result = repair_storyaxis_card_type_ai_params(session)

            refreshed = {
                item.name: item
                for item in session.exec(select(CardType)).all()
            }

        self.assertEqual(first_result["updated"], 2)
        self.assertEqual(first_result["already_correct"], 1)
        self.assertEqual(first_result["missing_ai_params"], 1)
        self.assertEqual(second_result["updated"], 0)

        self.assertEqual(
            refreshed["StoryAxis·世界观设定"].ai_params["prompt_name"],
            "StoryAxis·世界观设定",
        )
        self.assertEqual(
            refreshed["StoryAxis·世界观设定"].ai_params["llm_config_id"],
            2,
        )
        self.assertEqual(
            refreshed["StoryAxis·世界观设定"].ai_params["max_tokens"],
            200193,
        )
        self.assertEqual(
            refreshed["StoryAxis·世界观设定"].ai_params["timeout"],
            600,
        )
        self.assertEqual(
            refreshed["StoryAxis·角色卡"].ai_params["prompt_name"],
            "我的自定义角色提示词",
        )
        self.assertEqual(
            refreshed["StoryAxis·角色卡"].ai_params["llm_config_id"],
            4,
        )
        self.assertEqual(
            refreshed["StoryAxis·角色卡"].ai_params["max_tokens"],
            200193,
        )
        self.assertEqual(
            refreshed["StoryAxis·角色卡"].ai_params["timeout"],
            600,
        )
        self.assertEqual(
            refreshed["章节正文"].ai_params["max_tokens"],
            8192,
        )
        self.assertEqual(
            refreshed["章节正文"].ai_params["timeout"],
            120,
        )


if __name__ == "__main__":
    unittest.main()
