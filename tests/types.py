"""Custom testing types."""
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import Union


class MockParam:
    """Designed to form a place-holder for an eventual mock parameter."""

    def __init__(self, name: str, key: Optional[str] = None) -> None:
        """Store necessary mock information."""
        # store name
        self.name = name

        # store key
        self.key = name if key is None else key

    def __repr__(self) -> str:
        """Create string representation of MockParam object."""
        return f"MockParam(name={self.name!r}, key={self.key!r})"


# type returned by fixture params_usage_mock_args
ParamsUsageMockArgsDict = Dict[str, str]

# type of input directly passed to cli options
ParamsInput = Union[str, int, float, MockParam]

# type for all superset of all input testing: cli opts/args, and interactive
ParamsInputTest = Union[ParamsInput, Tuple[ParamsInput, ParamsInput]]

# type union of options/arguments usage errors dicts
ParamsUsageErrorDict = Dict[str, Dict[str, Tuple[Tuple[ParamsInputTest, int], ...]]]

# type union of options/arguments usage error case
ParamsUsageErrorCase = Tuple[str, str, ParamsInputTest, int]

# type for args list passed to runner command used in cli testing
RunnerArgs = Optional[ParamsInputTest]
