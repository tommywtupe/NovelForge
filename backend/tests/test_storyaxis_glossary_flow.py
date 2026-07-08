import sys
import unittest
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.routing import APIRoute

from app.api import router as api_router_module
from app.db.models import Card, CardType, Project
from app.schemas.entity import GlossaryTermExtractionRequest

try:
    import app.services.glossary_service as glossary_service
except ImportError as exc:  # pragma: no cover - red stage for TDD
    glossary_service = None
    GLOSSARY_IMPORT_ERROR = exc
else:
    GLOSSARY_IMPORT_ERROR = None


class StoryAxisGlossaryFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
        )
        SQLModel.metadata.create_all(self.engine)

    def _collect_route_paths(self) -> set[str]:
        paths: set[str] = set()
        for route in api_router_module.api_router.routes:
            if isinstance(route, APIRoute):
                paths.add(route.path)
            elif hasattr(route, "original_router"):
                nested_router = getattr(route, "original_router")
                prefix = getattr(getattr(route, "include_context", None), "prefix", "") or ""
                for nested in nested_router.routes:
                    if isinstance(nested, APIRoute):
                        paths.add(f"{prefix}{nested.path}")
        return paths

    def _seed_card_type(self, session: Session, name: str) -> CardType:
        card_type = CardType(name=name, built_in=True)
        session.add(card_type)
        session.commit()
        session.refresh(card_type)
        return card_type

    def _seed_project(self, session: Session, name: str = "StoryAxis 项目") -> Project:
        project = Project(name=name)
        session.add(project)
        session.commit()
        session.refresh(project)
        return project

    def _seed_card(
        self,
        session: Session,
        *,
        project_id: int,
        card_type_id: int,
        title: str,
        content: dict,
    ) -> Card:
        card = Card(
            title=title,
            project_id=project_id,
            card_type_id=card_type_id,
            content=content,
        )
        session.add(card)
        session.commit()
        session.refresh(card)
        return card

    def test_api_router_exposes_glossary_routes(self) -> None:
        route_paths = self._collect_route_paths()

        self.assertIn("/glossary/list", route_paths)
        self.assertIn("/glossary/extract", route_paths)
        self.assertIn("/glossary/translate-terms", route_paths)

    def test_detect_new_concepts_supports_storyaxis_namespaced_cards(self) -> None:
        if glossary_service is None:
            self.fail(f"glossary_service import failed: {GLOSSARY_IMPORT_ERROR}")

        with Session(self.engine) as session:
            project = self._seed_project(session)
            role_type = self._seed_card_type(session, "StoryAxis·角色卡")
            scene_type = self._seed_card_type(session, "StoryAxis·场景卡")

            self._seed_card(
                session,
                project_id=project.id,
                card_type_id=role_type.id,
                title="林霁",
                content={"name": "林霁"},
            )
            self._seed_card(
                session,
                project_id=project.id,
                card_type_id=scene_type.id,
                title="封港区仓库",
                content={"name": "封港区仓库"},
            )

            new_terms, all_sources = glossary_service.detect_new_concepts(
                session,
                project.id,
                existing_glossary=None,
                target_language="英文",
            )

        sources = {term.source for term in new_terms}
        categories = {term.source: term.category for term in new_terms}

        self.assertEqual(sources, {"林霁", "封港区仓库"})
        self.assertEqual(set(all_sources), {"林霁", "封港区仓库"})
        self.assertEqual(categories["林霁"], "character")
        self.assertEqual(categories["封港区仓库"], "scene")

    def test_update_glossary_from_extraction_reuses_storyaxis_glossary_card(self) -> None:
        if glossary_service is None:
            self.fail(f"glossary_service import failed: {GLOSSARY_IMPORT_ERROR}")

        with Session(self.engine) as session:
            project = self._seed_project(session, "StoryAxis 术语同步项目")
            glossary_type = self._seed_card_type(session, "StoryAxis·翻译术语表")
            concept_type = self._seed_card_type(session, "StoryAxis·概念卡")

            glossary_card = self._seed_card(
                session,
                project_id=project.id,
                card_type_id=glossary_type.id,
                title="StoryAxis·术语表·英文",
                content={
                    "name": "StoryAxis·术语表·英文",
                    "target_language": "英文",
                    "terms": [
                        {
                            "source": "旧港",
                            "translated": "Old Harbor",
                            "category": "scene",
                            "source_card_id": None,
                        }
                    ],
                },
            )
            self._seed_card(
                session,
                project_id=project.id,
                card_type_id=concept_type.id,
                title="潮汐门",
                content={"name": "潮汐门"},
            )

            result = glossary_service.update_glossary_from_extraction(
                session,
                GlossaryTermExtractionRequest(
                    project_id=project.id,
                    glossary_card_id=glossary_card.id,
                    target_language="英文",
                    update_mode="scan_new_concepts",
                ),
            )

            refreshed = session.get(Card, glossary_card.id)
            terms = refreshed.content["terms"]

        self.assertEqual(result.glossary_card_id, glossary_card.id)
        self.assertEqual({item["source"] for item in terms}, {"旧港", "潮汐门"})


if __name__ == "__main__":
    unittest.main()
