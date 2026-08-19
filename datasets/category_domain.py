from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DatasetCategoryCombination(BaseModel):
    """One stable, named category tuple in a dataset schema's domain."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    identifier: str
    categories: dict[UUID, UUID]


class DatasetCategoryDomain(BaseModel):
    """The meaningful category tuples of a dataset schema."""

    model_config = ConfigDict(frozen=True)

    mode: Literal['open', 'closed'] = 'open'
    combinations: list[DatasetCategoryCombination] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_unique_combinations(self) -> DatasetCategoryDomain:
        ids = [combination.id for combination in self.combinations]
        if len(ids) != len(set(ids)):
            raise ValueError('category combination ids must be unique')

        identifiers = [combination.identifier for combination in self.combinations]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError('category combination identifiers must be unique')

        tuples = [tuple(sorted(combination.categories.items())) for combination in self.combinations]
        if len(tuples) != len(set(tuples)):
            raise ValueError('category combinations must be unique')
        return self


class DatasetCategoryCombinationSpec(BaseModel):
    """Identifier-based authoring form compiled against a scoped catalogue."""

    model_config = ConfigDict(extra='forbid', frozen=True)

    id: str
    categories: dict[str, str]


class DatasetCategoryDomainSpec(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    mode: Literal['open', 'closed'] = 'open'
    combinations: list[DatasetCategoryCombinationSpec] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_unique_combinations(self) -> DatasetCategoryDomainSpec:
        identifiers = [combination.id for combination in self.combinations]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError('category combination identifiers must be unique')
        tuples = [tuple(sorted(combination.categories.items())) for combination in self.combinations]
        if len(tuples) != len(set(tuples)):
            raise ValueError('category combinations must be unique')
        return self


def empty_category_domain() -> DatasetCategoryDomain:
    return DatasetCategoryDomain()
