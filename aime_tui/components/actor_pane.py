"""Actor pane component for AIME TUI."""

from typing import Any, List
from textual.widgets import Tree
from textual.widgets.tree import TreeNode
from rich.text import Text

from aime_tui.config import TUIConfig
from aime.base.types import ActorRecord


class ActorPane(Tree):
    """Actor pane that displays live-updating list of created actors.

    Inherits from Textual's Tree to provide hierarchical display with
    expandable items showing actor details.
    """

    def __init__(self, config: TUIConfig, **kwargs: Any) -> None:
        """Initialize the ActorPane.

        Args:
            config: TUI configuration object.
            **kwargs: Additional keyword arguments passed to Tree.
        """
        super().__init__(
            label="Actors",
            **kwargs
        )
        self._config = config
        self._current_actors: List[ActorRecord] = []
        # Show the root node initially collapsed
        self.root.expand()

    def update_actors(self, actors: List[ActorRecord]) -> None:
        """Update the tree with the current list of actors.

        Rebuilds the tree with all actors, showing their role and details
        when expanded.

        Args:
            actors: List of all actors from ActorFactory.
        """
        self._current_actors = actors

        # Clear existing tree
        self.clear()

        # Add each actor to the tree
        for actor in actors:
            self._add_actor_to_node(self.root, actor)

    def _add_actor_to_node(
        self,
        parent_node: TreeNode,
        actor: ActorRecord
    ) -> None:
        """Add an actor to the tree node.

        Args:
            parent_node: The parent tree node to add to.
            actor: The actor to add.
        """
        # Build the actor label
        label = self._build_actor_label(actor)

        # Add the actor node
        actor_node = parent_node.add(label, data=actor)

        # Add actor details as expandable nodes
        self._add_actor_details(actor_node, actor)

    def _add_actor_details(self, actor_node: TreeNode, actor: ActorRecord) -> None:
        """Add actor details as expandable child nodes.

        Args:
            actor_node: The actor node to add details to.
            actor: The actor to get details from.
        """
        details = self._get_actor_details(actor)
        for detail in details:
            # Add each detail as an unselectable, non-expandable node
            actor_node.add(detail)

    def _build_actor_label(self, actor: ActorRecord) -> Text:
        """Build a rich text label for an actor.

        Shows actor name (falls back to role) and shortened actor ID.

        Args:
            actor: The actor to build a label for.

        Returns:
            Rich Text object representing the actor.
        """
        # Shorten actor ID for display - take first 8 characters consistently
        short_id = actor.actor_id[:8]

        # Build the label parts
        parts = []

        # Actor name (main label) - fall back to role if name empty
        display_name = actor.name if actor.name else actor.role
        label = Text(display_name, style="blue")
        parts.append(label)

        # Short actor ID
        parts.append(Text(f" ({short_id})", style="dim"))

        # Combine all parts
        result = Text.assemble(*parts)

        return result

    def _get_actor_details(self, actor: ActorRecord) -> List[Text]:
        """Get detailed information about an actor.

        Used when expanding an actor to show additional details.

        Args:
            actor: The actor to get details for.

        Returns:
            List of rich Text objects with actor details.
        """
        details = []

        # Description
        if actor.description:
            details.append(
                Text(f"Description: {actor.description}", style="dim")
            )

        # Tool bundles
        if actor.tool_bundles:
            bundles = ", ".join(actor.tool_bundles)
            details.append(
                Text(f"Tool Bundles: {bundles}", style="dim")
            )

        # Created time
        created_str = actor.created_at.strftime("%H:%M:%S")
        details.append(
            Text(f"Created: {created_str}", style="dim")
        )

        # Last used time
        last_used_str = actor.last_used_at.strftime("%H:%M:%S")
        details.append(
            Text(f"Last Used: {last_used_str}", style="dim")
        )

        return details

    def clear(self) -> None:
        """Clear all actors from the tree."""
        self.root.remove_children()
