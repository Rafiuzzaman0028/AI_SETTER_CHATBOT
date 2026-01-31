# JamieBot/app/routing/product_catalog.py
from dataclasses import dataclass
from typing import Optional
from app.routing.problem_inference import ProblemTag

@dataclass(frozen=True)
class Product:
    id: str
    name: str
    link: str
    price: Optional[str]
    problem_tag: ProblemTag

# Encoding of Product Catalog 

PRODUCTS = [
    Product(
        id="banter_blueprint",
        name="Banter Blueprint",
        link="https://jamie-date.mykajabi.com/the-banter-blueprint",
        price="$147",
        problem_tag=ProblemTag.TEXTING,
    ),
    Product(
        id="online_dating_mastery",
        name="Online Dating Mastery",
        link="https://jamie-date.mykajabi.com/online-dating-mastery-2",
        price="$174",
        problem_tag=ProblemTag.MATCHES,
    ),
    Product(
        id="cold_approach_mastery",
        name="Cold Approach Mastery",
        link="https://jamie-date.mykajabi.com/cold-approach-training",
        price="$97",
        problem_tag=ProblemTag.APPROACH,
    ),
    Product(
        id="creating_spark",
        name="Creating Spark",
        link="https://jamie-date.mykajabi.com/creating-spark-course",
        price="$147",
        problem_tag=ProblemTag.SPARK,
    ),
    Product(
        id="sexual_escalation",
        name="Secrets of Sexual Escalation",
        link="https://jamie-date.mykajabi.com/offers/DX9qJe9C/checkout",
        price="$75",
        problem_tag=ProblemTag.ESCALATION,
    ),
    Product(
        id="golden_guide",
        name="Golden Guide",
        link="https://jamie-date.mykajabi.com/goldenguide",
        price="$147",
        problem_tag=ProblemTag.CONFIDENCE,
    ),
]

# Default/fallback product
DEFAULT_PRODUCT = Product(
    id="general_dating_guide",
    name="How to Make Online Dating Suck Less",
    link="https://www.jamiedatecoaching.com/courses",
    price=None,
    problem_tag=ProblemTag.GENERAL,
)

PRODUCT_BY_PROBLEM = {product.problem_tag: product for product in PRODUCTS}

# Helper 
def get_product_for_problem(problem_tag: ProblemTag) -> Product:
    """
    Returns the best product for the given problem tag.
    Always returns exactly one product.
    """
    return PRODUCT_BY_PROBLEM.get(problem_tag, DEFAULT_PRODUCT)
