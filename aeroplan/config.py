"""Immutable policy inputs; all costs and risk coefficients are fictional."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    seed: int = 42
    weeks: int = 26
    disruption_week: int = 10
    disruption_duration: int = 4
    capacity_loss: float = 0.40
    demand_uplift: float = 0.15
    expedite_unit_cost: float = 18000.0
    secondary_unit_cost: float = 26000.0
    resequence_unit_cost: float = 6000.0
    lookahead: int = 2

    def __post_init__(self):
        if self.weeks < 14 or not 1 <= self.disruption_week <= self.weeks:
            raise ValueError('Use at least 14 weeks and an in-horizon disruption')
        if not 0 <= self.capacity_loss <= 1 or self.demand_uplift < 0:
            raise ValueError('Invalid disruption magnitude')
        if self.disruption_duration < 1 or self.lookahead < 0:
            raise ValueError('Invalid duration or lookahead')
        if min(self.expedite_unit_cost, self.secondary_unit_cost, self.resequence_unit_cost) < 0:
            raise ValueError('Costs cannot be negative')


SCENARIOS = {
    -1: 'Undisrupted reference',
    0: 'No action',
    1: 'Expedite transportation',
    2: 'Existing secondary allocation',
    3: 'FAL rescheduling and priority',
    4: 'Integrated recovery',
}
WEIGHTS = {'otif': .30, 'backlog_reduction': .25, 'inventory_stability': .15,
           'recovery_cost': .20, 'operational_risk': .10}
