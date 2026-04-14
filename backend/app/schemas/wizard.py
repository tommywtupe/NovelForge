from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional, List, Tuple, Any, Union

from .entity import CharacterCard as CharacterCard  # 以完整角色卡替换简化模型
from .entity import SceneCard as SceneCard
from .entity import OrganizationCard as OrganizationCard
from .entity import EntityType as EntityType


class Text(BaseModel):
    '''
    通用的文本模型，自由存储各种内容
    '''
    content: str = Field(description="任意文本内容，需使用/转换为markdown格式文本")

# --- Schemas for Tags ---

class Tags(BaseModel):
    """
    统一的标签模型。
    """
    theme: str = Field(default="", description="主题类别，格式: 大类-子类")
    audience: Literal['通用','男生', '女生'] = Field(default='通用', description="目标读者")
    narrative_person: Literal['第一人称', '第三人称'] = Field(default='第三人称', description="写作人称（第一人称/第三人称）")
    story_tags: List[Tuple[str, Literal['低权重', '中权重', '高权重']]] = Field(default=[], description="类别标签及权重档位（低/中/高）")
    affection: str = Field(default="", description="情感关系标签")


class SpecialAbility(BaseModel):
    name: str = Field(description="金手指的名称")
    description: str = Field(description="金手指的具体描述")


class SpecialAbilityResponse(BaseModel):
    """0: 根据tags设计金手指的请求模型"""
    special_abilities_thinking: str = Field(description="从标签到金手指的创作思考过程。",examples=["示例输出，仅供学习思考方式，不要被具体内容影响：根据标签“重生”和“无敌流”，我需要设计一个让主角能够不断尝试、不断变强，最终达到无敌状态的金手指。仅仅重生一次不足以支撑“无敌流”的长期发展，因此，将“重生”特性深化为“无限复活并回溯时间”的能力，每次复活都能保留经验和记忆，这既符合“重生”的特点，又能为主角的“无敌”之路提供逻辑支撑。同时，结合“异世大陆”和“文明推演”的背景，这种能力能够让主角在面对未知世界时，通过反复试错来积累知识和经验，从而实现降维打击，迅速崛起。这个金手指的设定，能够让读者对主角如何利用这种能力解决困境、颠覆旧秩序产生强烈的期待感。"])
    special_abilities: Optional[List[SpecialAbility]] = Field(None, description="主要金手指信息。金手指可以是各种系统、模拟器等这种具体的，也可以是某种优势/天赋/体质等，例如主角重生或者穿越，那么ta的先知先觉也是一种金手指。")


class OneSentence(BaseModel):
    """1: 根据tags、金手指设计一句话概述的请求模型"""
    one_sentence_thinking: str = Field(description="从标签/金手指到一句话概述的创作思考过程。",examples=["示例输出，仅供学习思考方式，不要被具体内容影响：考虑到'玄幻奇幻-异世大陆'的主题和'穿越'、'异界科学流'等标签，我首先需要构建一个跨世界的故事框架。现代剑道高手与异世界魔法师的相遇是个很好的切入点，'禁忌魔法传送门'金手指为这一相遇提供了合理契机。同时，'单CP'的情感标签要求这段关系要成为故事的重要线索。'文明碰撞'和'异界科学流'标签则提示要让主角带来现代世界的知识优势，形成独特的冲突和看点。综合这些元素，我决定构建一个关于现代人进入魔法世界，通过知识优势与个人成长影响整个异界命运的故事。"])
    one_sentence: str = Field(description="一句话概述整本小说内容")


class ParagraphOverview(BaseModel):
    """2: 根据一句话概述等信息扩充为一段话概述的请求模型"""
    overview_thinking: str = Field(description="从一句话概述到一段话大纲的创作思考过程。",examples=["示例输出，仅供学习思考方式，不要被具体内容影响：基于一句话概述，进一步思考故事的具体展开。从'穿越'标签出发，需要交代主角穿越后的身份转变和初始困境。'反派流'和'幕后流'决定了主角必须采取非传统的反派手段。'种田流'提示要详细描写魔族社会发展过程。'傲慢天赋'金手指则提供了主角解决问题的独特方式。整个故事需要展现出主角如何利用现代思维和智谋，在有限时间内完成魔族改造和人类世界的和平渗透。"])
    overview: str = Field(description="扩展后的小说大纲")
    

class SocialSystem(BaseModel):
    power_structure: str = Field(description="权力架构（如：封建王朝/资本联邦）")
    currency_system: List[str] = Field(description="货币体系")
    background:List[str]=Field(description="该社会体系的势力格局背景、历史传说等")
    major_power_camps: List[OrganizationCard] = Field(description="主要组织/门派/势力阵营，仅在此生成跨卷长期影响的核心组织。")
    civilization_level: Optional[str] = Field(description="科技/文明发展水平")

class CoreSystem(BaseModel):
    system_type: str = Field(min_length=1,description="体系类型（力量/社会/科技/异能等）")
    name: str = Field(description="体系名称（如：斗气/资本规则/朝堂权谋）")
    levels: Optional[List[str]] = Field(None, description="等级/阶层划分（可选）")
    source: str = Field(description="能量/权力来源（如：灵气/资本/皇权）")

class SettingItem(BaseModel):
    title: str = Field(description="设定标题，例如：地理宇宙观、历史传说、种族设定等")
    description: str = Field(description="该项设定的具体描述")

class WorldviewTemplate(BaseModel):
    """
    世界观模板
    """
    world_name: str = Field(min_length=2, description="世界名称")
    core_conflict: str = Field(description="世界核心矛盾（如：资源争夺/种族仇恨）")
    social_system: SocialSystem = Field(description="社会体系")
    power_systems: List[CoreSystem] = Field(description="核心体系列表，可包含力量/科技/异能等多种体系，避免设定过于复杂，最多设置两种体系。若是现实/历史等写实题材，则可置为空",max_length=2)
    # key_settings: Optional[List[SettingItem]] = Field(description="其他关键世界观设定（可选）")

class WorldBuilding(BaseModel):
    world_view_thinking: str = Field(description="世界观设计的思考过程",examples=["示例输出，仅用于学习思考方式，不要被具体内容影响：在设计世界观时，我希望构建一个既贴近现实又充满科幻想象力的框架。首先，为了让读者有代入感，我选择将故事背景设定在现代都市，这样主角的特殊能力与日常生活的冲突会更具张力。但仅仅是现代都市显然不够支撑“时空穿越”的主题，因此，我引入了“梦境”作为连接现实与未来的桥梁。这个梦境世界，最初是现实的映射，但随着主角的干预，它会发生剧烈变化，甚至出现“旧海”和“新海市”这种未来世界的差异，这为世界观增添了层次感和探索空间。为了解释这种变化，我需要一套严谨的时空法则，比如“时空蝴蝶效应”、“历史线修正”等，这些法则不仅解释了梦境与现实的互动，也为剧情的推进和冲突的产生提供了逻辑基础。同时，为了承载“文明推演”和“异界科学流”的标签，我构思了一个隐藏在幕后的组织，他们掌握着超越时代的科技和对时空法则的深刻理解，他们的存在是世界核心矛盾的体现——即关于历史走向的掌控权。社会体系上，现实世界是现代社会，而未来梦境则可能呈现出科技高度发达但社会畸形（如积分至上）或末日废土（如辐射灾害）的多种面貌，这种对比能增强故事的深度和警示意义。核心驱动体系上，除了主角的梦境能力，还需要有“超时空粒子”等科学概念作为力量来源和理论支撑，使得整个世界观在科幻的框架下显得自洽且充满探索潜力。"])
    world_view: WorldviewTemplate


# === Step 3: Blueprint Schemas ===


class Blueprint(BaseModel):
    volume_count: int = Field(description="预期小说的分卷数,通常设置为3~6卷")
# 示例输出，仅供学习思考方式，不要被具体内容影响：在设计角色时，我遵循McKee人物创作方法论，秉持“多样性与互补性”和“内外统一与反差张力”原则，将角色视为“表演中的作品”——他们比真人更清晰、更复杂、更引人入胜。
# 【核心方法：双向溯源】我采用“由内到外”与“由表及里”双向设计路径：首先从内在核心出发，确定角色的核心真实——即角色存在的根本理由；其次追溯至秘密内在（内在渴望与恐惧的冲突）；再至公共人格（社会面具的表演）；最后外化为外在表演和外在形象。
# 【内在层面设计】根据亞里士多德辯题，我确保每个角色的“内在驱动力”与“外在表现”统一：
# - 核心渴望：角色最深处的欲望
# - 核心恐惧：与渴望形成张力的人格阴影
# - 防御机制：当恐惧被触发时，角色如何保护自己（如压抑、投射、合理化）
# - 心理创伤：造成核心恐惧的根源经历
# 【多维人格设计】在3-5个性格轴线上构建角色（如：道德轴-善↔恶、智识轴-聪↔愚、情感轴-强↔弱、主动性-主动↔被动），各维度必须矛盾又统一，追溯到统一的内在核心。
# 【面具理论应用】每个角色都有三层面具：
# - 公共面具：社交场合下展示的社会身份
# - 私人面具：仅亲密之人可见的脆弱面
# - 真实面目：角色自己都不愿承认的深层自我
# 【外在形象设计】通过外貌、体态、气质、衣着外化内在性格与社会身份，确保：
# - 相貌特征承载角色过往经历与独特记忆点
# - 体态呈现角色潜意识中的身体记忆与防备模式
# - 气质反映内在修炼与外在修养的统一
# - 衣着体现社会身份、物质状况与价值取向
# 【行动人物原则】每个场景中，角色都有明确的意图→策略→行动循环，角色的选择揭示其价值优先序。
# 【卡司设计原则】
# - 对比原则：角色之间需有鲜明对照，避免重叠
# - 功能原则：每个角色都有存在理由，服务于主题揭示
# - 张力原则：角色间存在未解决的潜在冲突
# 首先是主角王小明。他的核心驱动力是“赚取高额酬金”和“守护海雯”。他有着外冷内热、务实警惕的性格，其核心渴望是寻找情感归属与生存安全感。然而，由于曾因弱小而眼睁睁看着重要之人离去的心理创伤，他的内心充斥着“再次失去所爱”的核心恐惧，并以此衍生出“用冷漠和利益至上掩饰脆弱”的防御机制。在社会交往中，他的公共面具是“冷酷的赏金猎人”，私人面具是“偶尔流露温柔的守护者”，而真实面目其实是“极度渴望归属却害怕建立羁绊的孤独穿越者”。他的外在形象深刻承载了这些特质：在相貌上，他五官硬朗，眉骨处极浅的旧伤疤承载着战斗记忆；体态精干敏捷，双手习惯垂在腰间，呈现出随时拔剑的防备模式；气质融合了现代人的松弛与剑客的内敛杀气；而冲锋衣外罩廉价皮甲的衣着则体现了两个世界文明的碰撞。他的角色弧光是从被迫卷入的旁观者，成长为主动担当的团队核心。
# 女主角海雯是故事引路人。她的核心驱动力是“逃避家族联姻”和“拯救世界”。她外冷内烈、高傲倔强的性格下，隐藏着掌握自我命运的核心渴望。自幼作为王室工具被剥夺意志及遭遇至亲背叛的心理创伤，让她内心充斥着“失去自由、被命运吞噬”的核心恐惧，并以此衍生出“用高傲掩饰不安全感”的防御机制。她的公共面具是“高贵冷艳的逃亡公主”，私人面具是“疲惫脆弱的孤独者”，真实面目则是“渴望被爱却不敢相信他人的受伤灵魂”。她的外在形象深刻承载了这些内在特质：苍白却眼角微挑透着倔强的精致相貌，永远挺直展现宫廷礼仪本能的娇小体态，高贵清冷却偶露疲惫的气质，以及被荆棘划破、抛弃家族配饰的深蓝色魔法长袍的衣着，都展现了强烈的反差张力。她的角色弧光是从逃避命运的孤高者，蜕变为直面挑战并学会信任的王宫魔法师。
# 希斯作为主要反派，具有极强的压迫感。她的核心驱动力是“掌控世界命运”。她极度慕强、偏执病态的性格背后，是填补内心绝对空洞的核心渴望。由于曾被家族边缘化并在绝望中触碰诅咒导致情感枯竭的心理创伤，她深陷于“被遗忘和失去权力”的核心恐惧中，并发展出“通过残忍控制他人来获得安全感”的防御机制。她的公共面具是“雍容华贵的权贵女性”，私人面具是“独自承受诅咒反噬的绝望者”，真实面目则是“渴望被爱却丧失爱人能力的空洞容器”。在形象上，她具有侵略性美艳与暗青色眼影的相貌，慵懒却极具侵略性的体态，犹如深渊般压抑的病态优雅气质，以及极致奢华却色调死寂的暗红长裙的衣着，完美映照了她的内心荒芜。她的角色弧光是从掌控一切的幕后黑手，到被迫直面空虚走向毁灭。


    character_thinking: str = Field(description="角色设计思考过程",examples=[
            "示例输出，仅供学习思考方式，不要被具体内容影响：在设计角色时，我遵循McKee人物创作方法论，秉持“多样性与互补性”和“内外统一与反差张力”原则，将角色视为“表演中的作品”——他们比真人更清晰、更复杂、更引人入胜。\n【核心方法：双向溯源】我采用“由内到外”与“由表及里”双向设计路径：首先从内在核心出发，确定角色的核心真实——即角色存在的根本理由；其次追溯至秘密内在（内在渴望与恐惧的冲突）；再至公共人格（社会面具的表演）；最后外化为外在表演和外在形象。\n【内在层面设计】根据亞里士多德辯题，我确保每个角色的“内在驱动力”与“外在表现”统一：\n- 核心渴望：角色最深处的欲望\n- 核心恐惧：与渴望形成张力的人格阴影\n- 防御机制：当恐惧被触发时，角色如何保护自己（如压抑、投射、合理化）\n- 心理创伤：造成核心恐惧的根源经历\n【多维人格设计】在3-5个性格轴线上构建角色（如：道德轴-善↔恶、智识轴-聪↔愚、情感轴-强↔弱、主动性-主动↔被动），各维度必须矛盾又统一，追溯到统一的内在核心。\n【面具理论应用】每个角色都有三层面具：\n- 公共面具：社交场合下展示的社会身份\n- 私人面具：仅亲密之人可见的脆弱面\n- 真实面目：角色自己都不愿承认的深层自我\n【外在形象设计】通过外貌、体态、气质、衣着外化内在性格与社会身份，确保：\n- 相貌特征承载角色过往经历与独特记忆点\n- 体态呈现角色潜意识中的身体记忆与防备模式\n- 气质反映内在修炼与外在修养的统一\n- 衣着体现社会身份、物质状况与价值取向\n【行动人物原则】每个场景中，角色都有明确的意图→策略→行动循环，角色的选择揭示其价值优先序。\n【卡司设计原则】\n- 对比原则：角色之间需有鲜明对照，避免重叠\n- 功能原则：每个角色都有存在理由，服务于主题揭示\n- 张力原则：角色间存在未解决的潜在冲突\n首先是主角王小明。他的核心驱动力是“赚取高额酬金”和“守护海雯”。他有着外冷内热、务实警惕的性格，其核心渴望是寻找情感归属与生存安全感。然而，由于曾因弱小而眼睁睁看着重要之人离去的心理创伤，他的内心充斥着“再次失去所爱”的核心恐惧，并以此衍生出“用冷漠和利益至上掩饰脆弱”的防御机制。在社会交往中，他的公共面具是“冷酷的赏金猎人”，私人面具是“偶尔流露温柔的守护者”，而真实面目其实是“极度渴望归属却害怕建立羁绊的孤独穿越者”。他的外在形象深刻承载了这些特质：在相貌上，他五官硬朗，眉骨处极浅的旧伤疤承载着战斗记忆；体态精干敏捷，双手习惯垂在腰间，呈现出随时拔剑的防备模式；气质融合了现代人的松弛与剑客的内敛杀气；而冲锋衣外罩廉价皮甲的衣着则体现了两个世界文明的碰撞。他的角色弧光是从被迫卷入的旁观者，成长为主动担当的团队核心。\n女主角海雯是故事引路人。她的核心驱动力是“逃避家族联姻”和“拯救世界”。她外冷内烈、高傲倔强的性格下，隐藏着掌握自我命运的核心渴望。自幼作为王室工具被剥夺意志及遭遇至亲背叛的心理创伤，让她内心充斥着“失去自由、被命运吞噬”的核心恐惧，并以此衍生出“用高傲掩饰不安全感”的防御机制。她的公共面具是“高贵冷艳的逃亡公主”，私人面具是“疲惫脆弱的孤独者”，真实面目则是“渴望被爱却不敢相信他人的受伤灵魂”。她的外在形象深刻承载了这些内在特质：苍白却眼角微挑透着倔强的精致相貌，永远挺直展现宫廷礼仪本能的娇小体态，高贵清冷却偶露疲惫的气质，以及被荆棘划破、抛弃家族配饰的深蓝色魔法长袍的衣着，都展现了强烈的反差张力。她的角色弧光是从逃避命运的孤高者，蜕变为直面挑战并学会信任的王宫魔法师。\n希斯作为主要反派，具有极强的压迫感。她的核心驱动力是“掌控世界命运”。她极度慕强、偏执病态的性格背后，是填补内心绝对空洞的核心渴望。由于曾被家族边缘化并在绝望中触碰诅咒导致情感枯竭的心理创伤，她深陷于“被遗忘和失去权力”的核心恐惧中，并发展出“通过残忍控制他人来获得安全感”的防御机制。她的公共面具是“雍容华贵的权贵女性”，私人面具是“独自承受诅咒反噬的绝望者”，真实面目则是“渴望被爱却丧失爱人能力的空洞容器”。在形象上，她具有侵略性美艳与暗青色眼影的相貌，慵懒却极具侵略性的体态，犹如深渊般压抑的病态优雅气质，以及极致奢华却色调死寂的暗红长裙的衣着，完美映照了她的内心荒芜。她的角色弧光是从掌控一切的幕后黑手，到被迫直面空虚走向毁灭。\n\n通过这些由内而外、细致入微的角色设计，我希望构建一个充满张力、视觉特征鲜明，并能共同推动宏大叙事的角色群像。"
        ])
    character_cards: List[CharacterCard] = Field(description="核心角色卡片列表，仅在此生成跨卷长期影响的核心角色")
    
    # organization_thinking:str=Field(description="组织/势力/阵营设计思考过程，注意与scene区分")
    # organization_cards: List[OrganizationCard] = Field(description="核心组织/势力/阵营卡片列表，仅在此生成跨卷长期影响的核心组织。注意与scene_cards区分")
    
    scene_thinking: str = Field(description="场景设计思考过程",examples=["示例输出，仅供学习思考方式，不要被具体内容影响：在设计地图和场景时，我遵循McKee《故事》背景理论，遵循从局部到全局、从已知到未知、层层递进的原则，以确保故事的节奏感和世界观的逐步展开。\n\n【背景四维度设计】每个场景设计前，我先明确其背景四维度：\n- 时代：确定场景处于过去/现在/未来的哪个时间节点\n- 期限：明确该场景故事发生的时间跨度（一小时/一年/一生）\n- 地点：界定地理、文化、具体场景的三层空间\n- 层级：定位经济、教育、社会地位等层级关系\n\n【背景约束结构】我深知背景类型决定结构类型：\n- 史诗背景（跨越广阔时空）需要对应的史诗结构来匹配\n- 亲密背景（单一时空）则适合线性结构\n- 每个场景的设计都要服务于整体结构需求\n\n【背景深化意义】同一事件在不同背景下意义不同。我确保每个场景不仅交代\"发生什么\"，更要揭示\"为什么重要\"：\n- 这个背景如何影响角色面临的问题？\n- 背景如何设置故事特有的限制？\n- 背景如何深化或复杂化主题？\n\n【场景设计示例】\n\n第一卷：初入异世与初步探索\n\n背景四维度：时代（异世界冷兵器时期，对应蓝星现代文明交汇点）、期限（主角初入异世的适应期，约数月）、地点（墨兰塔魔法学院、明月城政治中心）、层级（从社会底层到初获魔法能力）\n\n我首先设置了蓝星（现实世界）作为故事的起点和主角的\"已知世界\"，这让读者有代入感。然后通过\"墨兰塔\"和\"兰特王国(明月城)\"引入异世界的核心地域，这里是魔法与剑并存的典型场景，也是初期冲突的爆发点。墨兰塔作为魔法师的圣地，既是海雯的背景，也为主角学习魔法提供了场所。明月城则代表了异世界的政治中心和战争前线。这些场景的作用是让主角初步适应异世界，展现其适应能力和初步实力提升，并引出主要势力。背景制约：蓝星的现代思维与异世的古老规则形成冲突，设置了主角必须适应新世界的限制；背景深化：两个世界的碰撞本身即是\"文明冲突\"主题的具象化。\n\n第二卷：势力发展与联盟建立\n\n背景四维度：时代（战乱时期的势力格局）、期限（主角团势力扩张期，约一年）、地点（惊鸿之城、临崖城、中部哨塔、日出山）、层级（从个人实力到军团作战）\n\n随着剧情发展，我需要更广阔的舞台来展现主角团的势力扩张和宏大计划。因此，引入\"兰特王国（惊鸿之城）\"作为新的盟友基地，这里将成为公主复国和建立同盟的战略中心。同时，为了展现战争的全面性，我设计了\"高栏联邦（临崖城/中部哨塔/日出山）\"作为重要的战场和政治博弈地，通过这里的冲突来推动联盟的形成。解放\"明月城\"则是这一卷的高潮，标志着复国计划的关键一步。这些场景的作用是让主角团从被动应战转变为主动出击，展现其战略眼光和领导力，并促成同盟的建立。背景制约：多势力格局要求主角不仅依靠个人实力，还要建立政治联盟；背景深化：惊鸿之城的反复出现形成叙事呼应，暗示命运的轮回感。\n\n第三卷：统一战争与古老秘密的揭示\n\n背景四维度：时代（异世界历史的关键转折点）、期限（统一战争的决战期，数月）、地点（日月国、圣瓦伦帝国特西斯丁堡）、层级（从王国到帝国的权力攀升）\n\n进入第三卷，故事重心转向统一异世界大陆和揭示更深层次的秘密。因此，我将场景扩展到\"日月国\"和\"圣瓦伦帝国（特西斯丁堡）\"。日月国是联军推进的必经之地，通过这里的战役展现主角团的强大力量。圣瓦伦帝国首都\"特西斯丁堡\"是最终决战的地点，它的陷落标志着旧秩序的终结。这些场景的作用是完成统一大业，同时揭示世界观的深层秘密，为最终的危机埋下伏笔。背景制约：帝国级别的战争需要更宏观的战略视角；背景深化：从明月城到特西斯丁堡，地理的递进对应主角从反抗者到秩序建立者的角色弧光。\n\n第四卷：末日危机与最终抉择\n\n背景四维度：时代（世界面临毁灭的终极时刻）、期限（拯救行动的最后期限，紧迫感强烈）、地点（起源之地/燃烧的山巅）、层级（从物质层面到精神/命运层面的终极抉择）\n\n最后一卷，世界面临毁灭，场景设计围绕\"拯救\"和\"终结\"展开。\"临崖城\"和\"惊鸿之城\"再次出现，但这次它们承载的是收集王族之血和科技求生的希望。最终的\"起源之地/燃烧的山巅\"是决战的舞台，这里是诅咒的源头，也是解咒的关键。这些场景的作用是集中所有线索，完成最终的救赎，并让主角团做出关于归属的最终选择，为整个故事画上句号。背景制约：末日氛围的时间压力制造强烈悬念；背景深化：起源之地作为一切开始和终结的地点，完成叙事闭环。\n\n通过这些层层递进的场景设计，我希望构建一个结构严谨、背景与结构高度统一、主题意义不断深化的故事世界。"])
    scene_cards: List[SceneCard] = Field(description="主要地图/场景/副本卡片列表，仅在此生成跨卷长期影响的核心地图/场景。注意与organization_cards联系，例如某个地图是某个组织/势力的活动范围则需要标明。")


# === Step 4: Volume Outline Schemas===

class CharacterAction(BaseModel):
    """角色卡，涵盖了各种信息"""
    name: str = Field(description="角色名称")
    description: str = Field(description="以第一视角讲述该角色在这卷内的主要事迹")

class StoryLine(BaseModel):
    """故事线信息"""
    story_type: Literal['主线', '辅线'] = Field(description="故事线类型")
    name: str = Field(description="用一个简单的名称表示该线")
    overview: str = Field(description="故事线内容概述，需要详略得当，涉及到的所有场景、角色等元素都应在这个概述中体现到。")


class VolumeOutline(BaseModel):
    """
    分卷大纲的核心数据模型
    """
    volume_number: Optional[int] = Field(description="第几卷")
    thinking: Optional[str] = Field(description="根据提供的世界观、人物、地图/副本,思考本卷要如何展开,需要设计什么主线/辅线?如何推动剧情发展?",examples=["示例输出，仅供学习思考方式，不要被具体内容影响：本卷作为开篇，我的核心思考是如何迅速确立主角“无限复活”的金手指特性，并将其与残酷的异世大陆背景相结合，制造强烈的生存压迫感，从而驱动主角从绝境中崛起。我需要设计一个循序渐进的成长路径，让主角从一个濒死之人，通过每次复活积累经验和知识，逐步适应环境，并最终在A市站稳脚跟，积累原始资本，建立初步势力。同时，为了后续的宏大叙事，我必须在这一卷中埋下世界观的伏笔，例如社会阶层的固化、更高文明的操控等，通过主角的视角逐步揭示。在人物塑造上，我将引入一群性格各异的伙伴，他们既是主角的助力，也能通过他们的视角反衬主角的强大和特殊。爽点方面，主角利用金手指的“先知”优势，在股市和冒险中实现降维打击，以及最终对早期反派的复仇，都将是重要的爽点设计。"])
    main_target: StoryLine = Field(description="根据thinking设计主线目标,要让主角发展到什么地步?需描述准确数据")
    branch_line: Optional[List[StoryLine]] = Field(description="该卷的辅线或支线,包含1~3条核心辅线")
    character_thinking: Optional[str] = Field(description="结合overview、提供的角色信息,如性格、核心驱动力、角色弧光等,思考在该卷要驱动角色实体们做什么事?要让哪些角色出场?是否要引入辅助角色?",examples=["示例输出，仅学习思考方式，不要被具体内容影响：在本卷中，我将重点驱动主角，让他充分利用“无限复活”的能力，从一个绝境中的幸存者，逐步成长为A市的领袖。他将通过反复试错来学习战斗技巧、社会规则，并利用信息差在股市中快速积累财富。我还需要引入孙清雨、王火、韩天等核心配角，让他们在主角的成长过程中扮演重要的辅助角色：孙清雨作为主角的第一个伙伴和忠实追随者，将见证并参与主角的早期崛起；王火则提供技术支持，并成为主角“复活”秘密的知情人；韩天则在装备改造和技术研发上提供关键帮助。这些角色的出场和互动，不仅能推动剧情发展，也能丰富主角的人设，展现他智谋超群、善于利用资源的特点。同时，林森作为本卷的主要反派，将是主角初期反抗旧秩序的具象化目标，他的存在将不断刺激主角变强和复仇。"])
    new_character_cards: Optional[List[CharacterCard]] = Field(default=None, description="如有新增关键角色，在此补充其信息，life_span为短期。非必要尽量不引入新角色")
    new_scene_cards: Optional[List[SceneCard]]= Field(default=None, description="如有新增关键场景/地图/副本，在此补充其信息，life_span为短期，非必要尽量不引入新场景")
    # stage_lines: Optional[List[StageLine]] = Field(default=[], description="设计该卷的详细故事脉络，按阶段来划分，注意切分故事阶段时详略得当，每个阶段章节跨度不要太大,最好不超过30章")
    stage_count:int=Field(description="预期该卷的阶段剧情，将该卷的剧情分为n个阶段来叙述，通常为4~6个")
    character_action_list: Optional[List[CharacterAction]] = Field( description="根据卷内设计，概述关键角色实体的行动与变化")
    entity_snapshot: Optional[List[str]] = Field(description="卷末时，关键实体（角色为主）快照状态信息，，包括等级/修为境界、财富、功法等准确信息，以便收束剧情")

class WritingGuide(BaseModel):
    """
    写作指南，用于指导AI在特定卷中创作时需要注意的细节。
    """
    volume_number: int = Field(description="该写作指南对应的卷号")
    content: str = Field(description="AI根据方法论生成的、用于指导本卷写作的具体内容。字数控制在1000字以内。",min_length=100)


class ReviewResultCardContent(BaseModel):
    review_target_card_id: int = Field(description="被审核卡片 ID")
    review_target_title: str = Field(description="被审核卡片标题")
    review_target_type: Literal['card'] = Field(default='card', description="被审核目标类型")
    review_type: Literal['chapter', 'stage', 'card', 'custom'] = Field(description="审核类型")
    review_profile: str = Field(description="审核 profile code")
    review_target_field: Optional[str] = Field(default=None, description="被审核字段路径")
    quality_gate: Literal['pass', 'revise', 'block'] = Field(description="审核结论")
    review_markdown: str = Field(description="审核结果正文，使用 markdown 格式")
    prompt_name: str = Field(description="审核所使用的提示词名称")
    llm_config_id: Optional[int] = Field(default=None, description="审核使用的模型配置")
    reviewed_at: str = Field(description="审核时间（ISO 字符串）")
    target_snapshot: Optional[str] = Field(default=None, description="被审核内容快照")
    meta: Optional[dict[str, Any]] = Field(default_factory=dict, description="扩展元数据")

class BeatItem(BaseModel):
    """章节节拍"""
    beat_id: str = Field(description="节拍序号")
    beat_action: str = Field(description="节拍动作：描述该节拍中角色做了什么")
    beat_subtext_action: Optional[str] = Field(None, description="节拍潜文本动作：描述该动作背后的意图/含义")
    turning_point: bool = Field(default=False, description="是否为转折点")


class ChapterOutline(BaseModel):
    """章节大纲"""
    volume_number: int = Field(description="卷号，如果没有找到，则设置为0")
    stage_number:int=Field(description="该章节属于第几个阶段，从1开始")
    title: str= Field(description="章节标题")
    chapter_number: int = Field(description="章节序号")

    overview: str = Field(description="章节细纲,详略得当，避免过于单薄。如果主角有了显著的提升，则相关信息不能省略，需要准确数据描述出来(如实力大幅提升、经济或资源大幅增长了多少)。",min_length=100)
    entity_list: List[str] = Field(
        description="章节中出场的重要实体列表，只能从上下文提供的组织/角色/场景卡实体中选择，不得新增、自创；实体名称必须是纯名称（不得包含括号/备注）。注意,为了精简上下文，避免实体列表中出现该章节未出场的冗余实体",
    )
    beat_list: List[BeatItem] = Field(
        default=None,
        description="章节节拍列表，每个节拍描述角色动作和潜文本，用于细化章节内的叙事节奏，1个节拍1000字",
    )

    

class StageLine(BaseModel):
    """故事按阶段划分的信息"""
    volume_number:int=Field(description="该故事阶段属于第几卷")
    stage_number:int=Field(description="该故事阶段是第几个阶段，从1开始")
    stage_name: str = Field(description="用一个名称或一句话简单概述这个阶段")
    reference_chapter: Tuple[int, int] = Field(description="该部分剧情的起始和结束章节号,跨度通常为10~20章左右")
    analysis: Optional[str] = Field(description="以一个经验丰富的网文写手代入作者第一人称视角,'我'是如何思考设置这部分的剧情的,该部分剧情对于分卷的主线/辅线起到什么作用?该阶段剧情的爽点是什么？末尾是否设置钩子/悬念？")
    overview: Optional[str] = Field(description="这个阶段剧情内容具体概述，需要详略得当，涉及到的主要实体，如角色、场景/地图、组织等元素都应在这个概述中体现到。另外，若主角有了显著提升（如提升了主角多少实力或地位、增长了主角多少财富或资源之类的），则相关信息需要准确数据描述，不能省略")
    chapter_outline_list:Optional[List[ChapterOutline]]=Field(description="根据reference_chapter、overview生成所需的章节大纲。注意章节大纲的标题不要包含”第x章这种前缀")
    entity_snapshot: Optional[List[str]] = Field(description="阶段末时，关键实体（角色为主）快照状态信息，包括等级/修为境界、财富、功法等准确信息，以便收束剧情，确保最后一个阶段时，剧情发展能够使得实体状态收束到该卷末的实体状态。")
    @model_validator(mode="after")
    def validate_chapter_outline_coverage(self):
        # Allow empty list for workflow post-processing cleanup.
        if not self.chapter_outline_list:
            return self

        start, end = self.reference_chapter
        if start > end:
            raise ValueError("reference_chapter start must be <= end")

        actual_numbers = [item.chapter_number for item in self.chapter_outline_list]
        expected_numbers = list(range(start, end + 1))
        if actual_numbers != expected_numbers:
            raise ValueError(
                "chapter_outline_list.chapter_number must be contiguous and fully cover reference_chapter"
            )
        return self


# === Step 6: Batch Chapter Outline Schemas===

class Chapter(BaseModel):
    volume_number: int = Field( description="卷号，如果没有找到，则设置为0")
    stage_number: int=Field(description="该章节属于第几个阶段，从1开始")
    title: str = Field(description="章节标题")
    chapter_number: int = Field(description="章节序号")

    entity_list: List[str] = Field(
        description="章节中参与的重要实体列表，只能从提供的实体中选择；name 必须是纯名称（不得包含括号/备注）",
    )
    content:Optional[str]=Field(default="",description="章节正文内容")
    

