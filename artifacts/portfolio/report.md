# Portfolio Complexity & Cost Analytics

Synthetic independent portfolio project. No company data, calibrated costs or realized savings.
All four portfolios rerun the same IBP engine with integrated recovery (4). Cost rank sorts total modeled cost only; it is not a recommendation.

| portfolio_scenario | complexity_index | total_modeled_cost | otif | ending_backlog | average_inventory_units | exceptions | recovery_cost | standardization_proxy | flexibility_proxy | resilience_proxy | cost_rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Baseline | 60.9865 | 4047350.0 | 0.896 | 21 | 14.1923 | 342 | 3948000.0 | 0.1429 | 1.0 | 0.8054 | 2 |
| Standardization | 45.4476 | 4072375.0 | 0.896 | 21 | 15.1923 | 171 | 3966000.0 | 0.4 | 0.7143 | 0.7741 | 3 |
| Consolidation | 59.2777 | 4037750.0 | 0.896 | 21 | 14.1923 | 342 | 3948000.0 | 0.1429 | 1.0 | 0.6516 | 1 |
| Global Product Adoption | 21.8052 | 4157140.0 | 0.8684 | 20 | 13.0385 | 316 | 4047000.0 | 1.0 | 0.4286 | 0.4109 | 4 |

## Evidence-linked interpretation
Mode: deterministic_fallback

Baseline: compare modeled cost and service with commonality, retained variant choice and vendor diversification. Proxies are not calibrated resilience probabilities; all coefficients and portfolio changes are synthetic.
Evidence: portfolio_comparison:Baseline, portfolio_assumptions:Baseline

Standardization: compare modeled cost and service with commonality, retained variant choice and vendor diversification. Proxies are not calibrated resilience probabilities; all coefficients and portfolio changes are synthetic.
Evidence: portfolio_comparison:Standardization, portfolio_assumptions:Standardization

Consolidation: compare modeled cost and service with commonality, retained variant choice and vendor diversification. Proxies are not calibrated resilience probabilities; all coefficients and portfolio changes are synthetic.
Evidence: portfolio_comparison:Consolidation, portfolio_assumptions:Consolidation

Global Product Adoption: compare modeled cost and service with commonality, retained variant choice and vendor diversification. Proxies are not calibrated resilience probabilities; all coefficients and portfolio changes are synthetic.
Evidence: portfolio_comparison:Global Product Adoption, portfolio_assumptions:Global Product Adoption
