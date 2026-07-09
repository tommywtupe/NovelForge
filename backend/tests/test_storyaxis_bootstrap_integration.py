import sys
import unittest
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.endpoints import workflows as workflow_endpoints
from app.bootstrap.card_types import create_default_card_types
from app.bootstrap.workflows import init_workflows
from app.db.models import CardType, Workflow


class StoryAxisBootstrapIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
        )
        SQLModel.metadata.create_all(self.engine)

    def test_project_templates_endpoint_exposes_storyaxis_template(self) -> None:
        with Session(self.engine) as session:
            init_workflows(session)

            response = workflow_endpoints.get_project_templates(session=session)

        templates = response["templates"]
        storyaxis_templates = [item for item in templates if item.get("template") == "storyaxis"]
        self.assertEqual(len(storyaxis_templates), 1)
        self.assertEqual(storyaxis_templates[0]["workflow_name"], "StoryAxis·项目创建")

    def test_storyaxis_translation_card_types_bind_dedicated_editors(self) -> None:
        with Session(self.engine) as session:
            create_default_card_types(session)

            card_types = {
                item.name: item
                for item in session.exec(
                    select(CardType).where(
                        CardType.name.in_(
                            [
                                "StoryAxis·正文翻译卡",
                                "StoryAxis·翻译术语表",
                            ]
                        )
                    )
                ).all()
            }

        self.assertEqual(card_types["StoryAxis·正文翻译卡"].editor_component, "TransCodeMirrorEditor")
        self.assertEqual(card_types["StoryAxis·翻译术语表"].editor_component, "GlossaryEditor")

    def test_storyaxis_card_types_bind_storyaxis_prompt_names(self) -> None:
        with Session(self.engine) as session:
            create_default_card_types(session)

            card_types = {
                item.name: item
                for item in session.exec(
                    select(CardType).where(
                        CardType.name.in_(
                            [
                                "StoryAxis·金手指",
                                "StoryAxis·一句话梗概",
                                "StoryAxis·故事大纲",
                                "StoryAxis·世界观设定",
                                "StoryAxis·核心蓝图",
                                "StoryAxis·分卷大纲",
                                "StoryAxis·写作指南",
                                "StoryAxis·阶段大纲",
                                "StoryAxis·章节大纲",
                                "StoryAxis·章节正文",
                                "StoryAxis·角色卡",
                                "StoryAxis·场景卡",
                                "StoryAxis·组织卡",
                                "StoryAxis·正文翻译卡",
                            ]
                        )
                    )
                ).all()
            }

        self.assertEqual(card_types["StoryAxis·金手指"].ai_params["prompt_name"], "StoryAxis·金手指生成")
        self.assertEqual(card_types["StoryAxis·一句话梗概"].ai_params["prompt_name"], "StoryAxis·一句话梗概")
        self.assertEqual(card_types["StoryAxis·故事大纲"].ai_params["prompt_name"], "StoryAxis·一段话大纲")
        self.assertEqual(card_types["StoryAxis·世界观设定"].ai_params["prompt_name"], "StoryAxis·世界观设定")
        self.assertEqual(card_types["StoryAxis·核心蓝图"].ai_params["prompt_name"], "StoryAxis·核心蓝图")
        self.assertEqual(card_types["StoryAxis·分卷大纲"].ai_params["prompt_name"], "StoryAxis·分卷大纲")
        self.assertEqual(card_types["StoryAxis·写作指南"].ai_params["prompt_name"], "StoryAxis·写作指南")
        self.assertEqual(card_types["StoryAxis·阶段大纲"].ai_params["prompt_name"], "StoryAxis·阶段大纲")
        self.assertEqual(card_types["StoryAxis·章节大纲"].ai_params["prompt_name"], "StoryAxis·章节大纲")
        self.assertEqual(card_types["StoryAxis·章节正文"].ai_params["prompt_name"], "StoryAxis·内容生成")
        self.assertEqual(card_types["StoryAxis·角色卡"].ai_params["prompt_name"], "StoryAxis·角色动态信息提取")
        self.assertEqual(card_types["StoryAxis·场景卡"].ai_params["prompt_name"], "StoryAxis·内容生成")
        self.assertEqual(card_types["StoryAxis·组织卡"].ai_params["prompt_name"], "StoryAxis·关系提取")
        self.assertEqual(card_types["StoryAxis·正文翻译卡"].ai_params["prompt_name"], "StoryAxis·正文翻译")


if __name__ == "__main__":
    unittest.main()
