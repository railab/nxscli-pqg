import pytest
from click.exceptions import BadParameter

from nxscli_pqg.cli.types import FormatStringList, plot_options


def test_plotoptions():
    @plot_options
    def test():
        pass

    test()


def test_formatstringlist_valid():
    """Test FormatStringList with valid format strings."""
    fsl = FormatStringList(ch1="?")

    # Valid single format
    result = fsl.convert("r-", None, None)
    assert result == [["r-"]]

    # Valid multiple vectors
    result = fsl.convert("r-?g--?b:", None, None)
    assert result == [["r-", "g--", "b:"]]

    # Valid multiple channels
    result = fsl.convert("r-?g--; b:?y", None, None)
    assert result == [["r-", "g--"], ["b:", "y"]]

    # Valid with markers
    result = fsl.convert("ro?gs", None, None)
    assert result == [["ro", "gs"]]


def test_formatstringlist_invalid():
    """Test FormatStringList with invalid format strings."""
    fsl = FormatStringList(ch1="?")

    # Invalid marker
    with pytest.raises(BadParameter, match="Invalid format string"):
        fsl.convert("rz", None, None)

    # Invalid character
    with pytest.raises(BadParameter, match="Invalid format string"):
        fsl.convert("abc", None, None)

    # Invalid in vector list
    with pytest.raises(BadParameter, match="Invalid format string"):
        fsl.convert("r-?invalid?b:", None, None)


def test_formatstringlist_empty_strings():
    """Test FormatStringList with empty strings in format."""
    fsl = FormatStringList(ch1="?")

    # Empty strings should be skipped in validation
    result = fsl.convert("r-??b:", None, None)
    assert result == [["r-", "", "b:"]]

    # All empty strings
    result = fsl.convert("??", None, None)
    assert result == [["", "", ""]]
