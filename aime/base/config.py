from dataclasses import dataclass, field


@dataclass
class PlannerConfig:
    max_iterations: int = 100
    temperature: float = 0.7
    allow_replan_on_failure: bool = True
    max_retries_on_failure: int = 3


@dataclass
class ActorConfig:
    temperature: float = 0.7
    max_iterations: int = 50
    enable_auto_progress_update: bool = True
    max_retries: int = 3


@dataclass
class KnowledgeConfig:
    enable_retrieval: bool = True
    top_k: int = 3


@dataclass
class AimeConfig:
    planner: PlannerConfig = field(default_factory=PlannerConfig)
    actor: ActorConfig = field(default_factory=ActorConfig)
    knowledge: KnowledgeConfig = field(default_factory=KnowledgeConfig)
    max_total_iterations: int = 200
    auto_save_session: bool = True
    store_full_actor_history: bool = True
