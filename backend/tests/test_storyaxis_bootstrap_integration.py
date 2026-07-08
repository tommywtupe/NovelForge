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


if __name__ == "__main__":
    unittest.main()
