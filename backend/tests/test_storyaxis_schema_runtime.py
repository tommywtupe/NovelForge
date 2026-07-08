import json
import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.endpoints import cards
from app.schemas import ai as ai_schemas
from app.schemas import entity, response_registry, wizard
from app.services.ai.core import llm_service
from app.services.ai.generation import continuation_budget_runtime


class StoryAxisSchemaRuntimeTests(unittest.TestCase):
    def test_character_card_supports_storyaxis_deep_fields(self) -> None:
        card = entity.CharacterCard(
            name="林霁",
            entity_type="character",
            life_span="长期",
            role_type="男主角",
            born_scene="海港城",
            description="重生回来的调查员。",
            personality="冷静、克制、观察欲强",
            physique="瘦高，站姿总是微微前倾。",
            aura="安静却带压迫感。",
            appearance="眼尾有旧伤，神情总像在审讯别人。",
            dressing="深色风衣，袖口磨损严重。",
            core_desire="查清父亲死亡真相。",
            core_fear="再次目睹重要之人死在自己面前。",
            defense_mechanism="用理性分析隔开情绪。",
            psychological_trauma="少年时在爆炸案里失去家人。",
            public_persona="办案效率极高的冷面调查员。",
            private_persona="只在妹妹面前会放松警惕。",
            the_shadow_self="享受逼问真相时对他人的控制感。",
            core_drive="阻止旧案重演。",
            character_arc="从只信证据到愿意信任同伴。",
            dynamic_info={
                "知识/情报": [
                    entity.DynamicInfoItem(id=1, info="确认码头仓库与旧案有关。", chapter=12),
                ]
            },
        )

        self.assertEqual(card.role_type, "男主角")
        self.assertEqual(card.dynamic_info["知识/情报"][0].chapter, 12)
        self.assertEqual(card.core_desire, "查清父亲死亡真相。")

    def test_chapter_outline_and_translation_chapter_are_registered(self) -> None:
        outline = wizard.ChapterOutline(
            volume_number=1,
            stage_number=1,
            title="雾港回潮",
            chapter_number=7,
            overview=(
                "林霁重返封港区，确认仓库失火并非意外，且被迫与旧案幸存者正面接触。"
                "他必须在一夜之内重新排列手上的证据链，重新审视自己过去一年对旧案的全部判断，"
                "同时还要处理沈见微带来的情绪冲击与新的录音线索，为下一章逼近幕后主使埋下清晰、"
                "可执行且不会越章的调查路径。"
            ),
            entity_list=["林霁", "沈见微", "封港区仓库"],
            beat_list=[
                wizard.BeatItem(
                    beat_id=1,
                    beat_action="林霁潜入仓库，确认起火时间线被人伪造。",
                    beat_subtext_action="他第一次承认自己对旧案判断可能有误。",
                    beat_main_perspective="林霁",
                ),
                wizard.BeatItem(
                    beat_id=2,
                    beat_action="幸存者沈见微出现，强行打断调查节奏。",
                    turning_point=True,
                    beat_main_perspective="沈见微",
                ),
            ],
        )

        self.assertEqual(outline.beat_list[1].turning_point, True)
        self.assertEqual(outline.beat_list[1].beat_main_perspective, "沈见微")

        translation_model = response_registry.RESPONSE_MODEL_MAP["TranslationChapter"]
        translation = translation_model(
            volume_number=1,
            stage_number=1,
            title="Mist Returning to the Harbor",
            chapter_number=7,
            target_language="英文",
            entity_list=["林霁", "沈见微"],
            content="Test content",
        )
        self.assertEqual(translation.target_language, "英文")

    def test_continuation_runtime_uses_beats_for_budget_and_prompt(self) -> None:
        beat_list = [
            {
                "beat_id": 1,
                "beat_action": "林霁潜入仓库，确认起火时间线被人伪造。",
                "beat_subtext_action": "他意识到自己过去一年都被人引导。",
                "beat_main_perspective": "林霁",
            },
            {
                "beat_id": 2,
                "beat_action": "沈见微逼问他为何一直隐瞒旧案录音。",
                "turning_point": True,
                "beat_main_perspective": "沈见微",
            },
            {
                "beat_id": 3,
                "beat_action": "两人交换证据后决定联手追查幕后主使。",
                "beat_main_perspective": "林霁",
            },
        ]
        context_info = (
            "角色卡:"
            + json.dumps(
                [
                    {
                        "name": "林霁",
                        "role_type": "男主角",
                        "description": "重生回来的调查员。",
                        "personality": "冷静、克制、观察欲强",
                        "physique": "瘦高，站姿微微前倾。",
                        "aura": "安静却带压迫感。",
                        "appearance": "眼尾有旧伤。",
                        "dressing": "深色风衣，袖口磨损严重。",
                        "core_desire": "查清父亲死亡真相。",
                        "core_fear": "再次失去重要之人。",
                        "defense_mechanism": "用理性隔绝情绪。",
                        "psychological_trauma": "少年时在爆炸案里失去家人。",
                        "public_persona": "高效冷面的调查员。",
                        "private_persona": "只在妹妹面前放松。",
                        "the_shadow_self": "享受控制审讯节奏。",
                        "core_drive": "阻止旧案重演。",
                        "character_arc": "从只信证据到愿意信任同伴。",
                        "born_scene": "海港城",
                    },
                    {
                        "name": "沈见微",
                        "role_type": "女副主角",
                        "description": "旧案幸存者。",
                    },
                ],
                ensure_ascii=False,
            )
        )
        request = ai_schemas.ContinuationRequest(
            previous_content="",
            llm_config_id=1,
            stream=False,
            context_info=context_info,
            target_word_count=1800,
            existing_word_count=600,
            word_control_mode="balanced",
            continuation_guidance="严守章纲，不引入新实体。",
            beat_list_json=json.dumps(beat_list, ensure_ascii=False),
        )

        self.assertEqual(continuation_budget_runtime.estimate_required_call_count(request), 3)

        plan = continuation_budget_runtime.build_round_plan(request, current_word_count=600, round_index=2)
        self.assertEqual(plan.max_rounds, 3)
        self.assertEqual(plan.rounds_left, 2)

        prompt = llm_service._build_continuation_user_prompt(request, plan)
        self.assertIn("当前节拍：第 2 节拍 / 共 3 节拍", prompt)
        self.assertIn("沈见微逼问他为何一直隐瞒旧案录音。", prompt)
        self.assertIn("【角色身份】", prompt)
        self.assertIn("主视角锁定", prompt)
        self.assertIn("严守章纲，不引入新实体。", prompt)

    def test_storyaxis_control_markers_are_removed_before_save(self) -> None:
        content = {
            "content": "第一段。\n<节拍完成>\n===自查结果===\n- 本章合格\n第二段。"
        }

        cleaned = cards._sanitize_storyaxis_chapter_content(content)
        self.assertEqual(cleaned["content"], "第一段。\n\n第二段。")


if __name__ == "__main__":
    unittest.main()
