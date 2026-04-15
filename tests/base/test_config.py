"""Tests for configuration classes in aime.base.config."""

from aime.base.config import (
    PlannerConfig,
    ActorConfig,
    KnowledgeConfig,
    AimeConfig
)


def test_aime_config_defaults():
    config = AimeConfig()
    assert config.max_total_iterations > 0
    assert config.planner.temperature > 0
    assert config.actor.temperature > 0


def test_planner_config():
    config = PlannerConfig()
    assert config.allow_replan_on_failure is True


class TestPlannerConfig:
    """Tests for PlannerConfig dataclass."""

    def test_initialization_with_default_values(self):
        """Test initialization with default values."""
        config = PlannerConfig()
        assert config.max_iterations == 100
        assert config.temperature == 0.7
        assert config.allow_replan_on_failure is True
        assert config.max_retries_on_failure == 3

    def test_initialization_with_custom_values(self):
        """Test initialization with custom values."""
        config = PlannerConfig(
            max_iterations=10,
            temperature=0.5,
            allow_replan_on_failure=False,
            max_retries_on_failure=5
        )
        assert config.max_iterations == 10
        assert config.temperature == 0.5
        assert config.allow_replan_on_failure is False
        assert config.max_retries_on_failure == 5


class TestActorConfig:
    """Tests for ActorConfig dataclass."""

    def test_initialization_with_default_values(self):
        """Test initialization with default values."""
        config = ActorConfig()
        assert config.temperature == 0.7
        assert config.max_iterations == 50
        assert config.enable_auto_progress_update is True

    def test_initialization_with_custom_values(self):
        """Test initialization with custom values."""
        config = ActorConfig(
            temperature=0.7,
            max_iterations=10,
            enable_auto_progress_update=False
        )
        assert config.temperature == 0.7
        assert config.max_iterations == 10
        assert config.enable_auto_progress_update is False


class TestKnowledgeConfig:
    """Tests for KnowledgeConfig dataclass."""

    def test_initialization_with_default_values(self):
        """Test initialization with default values."""
        config = KnowledgeConfig()
        assert config.enable_retrieval is True
        assert config.top_k == 3

    def test_initialization_with_custom_values(self):
        """Test initialization with custom values."""
        config = KnowledgeConfig(
            enable_retrieval=True,
            top_k=5
        )
        assert config.enable_retrieval is True
        assert config.top_k == 5


class TestAimeConfig:
    """Tests for AimeConfig dataclass."""

    def test_initialization_with_default_values(self):
        """Test initialization with default values."""
        config = AimeConfig()
        assert isinstance(config.planner, PlannerConfig)
        assert isinstance(config.actor, ActorConfig)
        assert isinstance(config.knowledge, KnowledgeConfig)
        assert config.max_total_iterations == 200

    def test_initialization_with_custom_configs(self):
        """Test initialization with custom sub-configs."""
        planner_config = PlannerConfig(max_iterations=10)
        actor_config = ActorConfig(temperature=0.8)
        knowledge_config = KnowledgeConfig(enable_retrieval=True)

        config = AimeConfig(
            planner=planner_config,
            actor=actor_config,
            knowledge=knowledge_config,
            max_total_iterations=100
        )

        assert config.planner == planner_config
        assert config.actor == actor_config
        assert config.knowledge == knowledge_config
        assert config.max_total_iterations == 100
