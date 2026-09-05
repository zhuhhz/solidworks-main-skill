"""Pure pattern contracts; no CAD execution or ownership discovery."""
from dataclasses import asdict, dataclass, field
from .feature_graph import BaseBlock


@dataclass
class SeedFeature:
    feature_id: str
    pattern_id: str
    source_feature_id: str
    center_mm: tuple[float, float, float]
    diameter_mm: float
    dependencies: list[str]
    axis: str = "Z"
    through: bool = True
    feature_role: str = field(default="SEED", init=False)


@dataclass
class PatternFeature:
    feature_id: str
    pattern_id: str
    source_feature_id: str
    spacing_mm: float
    direction: tuple[float, float, float]
    total_count: int
    dependencies: list[str]
    includes_seed: bool = True
    feature_role: str = field(default="PATTERN", init=False)


@dataclass
class InstanceFeature:
    feature_id: str
    pattern_id: str
    source_feature_id: str
    instance_index: int
    center_mm: tuple[float, float, float]
    dependencies: list[str]
    feature_role: str = field(default="INSTANCE", init=False)


@dataclass
class PatternFeatureGraph:
    """Additive graph family; legacy FeatureGraph/validators stay unchanged.

    Seed pattern_id is membership metadata, not a reverse dependency.
    Index zero is the seed occurrence, not a second physical cut.
    """
    base: BaseBlock
    seed: SeedFeature | None
    pattern: PatternFeature
    instances: list[InstanceFeature]

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class PatternOperation:
    operation_id: str
    operation_type: str
    source_feature_id: str
    depends_on_operation_ids: tuple[str, ...]


@dataclass(frozen=True)
class PatternOwnership:
    entity_id: str
    pattern_id: str
    instance_id: str | None
    native_owner_feature_id: str | None
    state: str
    source: str
    identity_reference: str | None = None
    seed_id: str | None = None
    instance_index: int | None = None

    def __post_init__(self):
        if self.state not in {"API_EXACT", "INSTANCE_EXACT", "PATTERN_ONLY", "OWNERSHIP_UNRESOLVED"}:
            raise ValueError("unsupported pattern ownership state")
        if not self.entity_id or not self.pattern_id or not self.source:
            raise ValueError("entity, pattern and evidence source are required")
        if self.state in {"API_EXACT", "INSTANCE_EXACT"}:
            if (not self.instance_id or not self.native_owner_feature_id or not self.identity_reference
                    or not self.seed_id or type(self.instance_index) is not int or self.instance_index < 0):
                raise ValueError("exact ownership requires instance, seed lineage, index, native owner and identity evidence")
        elif self.instance_id is not None:
            raise ValueError("diagnostic/unresolved evidence cannot claim an instance")

    @property
    def feature_id(self):
        return self.instance_id

    @property
    def ownership_level(self):
        return self.state
