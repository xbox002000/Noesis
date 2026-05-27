"""
Pytest fixtures for semantic_graph and integration tests.
"""

import pytest
from epistemic_kernel import EpistemicKernel
from experiments.token_saving.scenario import create_jwt_security_scenario


@pytest.fixture
def jwt_claims_and_contentions():
    """Return the standard JWT security scenario claims and contentions."""
    claims, contentions = create_jwt_security_scenario()
    return claims, contentions


@pytest.fixture
def populated_epistemic_kernel(jwt_claims_and_contentions):
    """Return an EpistemicKernel pre-loaded with the JWT scenario."""
    claims, contentions = jwt_claims_and_contentions
    kernel = EpistemicKernel()

    for claim in claims:
        kernel.add_claim(claim.concept, claim.confidence, claim.source)

    for cont in contentions:
        kernel.register_contention(
            claim_a=cont["claim_a"],
            claim_b=cont["claim_b"],
            description=cont["description"],
            severity=cont["severity"]
        )
    return kernel
