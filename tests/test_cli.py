from pathlib import Path

import pytest

import topspin.__main__ as cli
from topspin.__main__ import main


def test_build_command_writes_the_site(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["build", "--out", str(tmp_path / "site")]) == 0
    assert (tmp_path / "site" / "index.html").is_file()
    assert "player charts" in capsys.readouterr().out


def test_a_command_is_required() -> None:
    with pytest.raises(SystemExit):
        main([])


@pytest.mark.parametrize("error", [ValueError("invalid league data"), OSError("disk full")])
def test_build_errors_are_reported_without_a_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], error: Exception
) -> None:
    def broken_data(output: Path) -> int:
        raise error

    monkeypatch.setattr(cli, "build", broken_data)
    assert main(["build"]) == 1
    assert capsys.readouterr().err == f"error: {error}\n"
