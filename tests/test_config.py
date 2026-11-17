"""
CFA Prep CLI - Tests for the config module
Author: CodeBuddy AI Assistant
Purpose: Check the configuration: the settings file, the data root override and the config command.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cfa_prep.utils import (
    get_data_root,
    load_home_env,
    load_settings,
    save_settings,
    set_home_env,
    set_setting,
    write_file_text,
)


def test_settings():
    """Test config read/write (level is set via set_setting, not data_root)"""
    test_settings_data: dict[str, object] = {
        "level": "L1", "version": "1.0"
    }
    save_settings(test_settings_data)
    settings = load_settings()
    assert settings.get("level") == "L1"
    assert settings.get("version") == "1.0"
    assert "data_root" not in settings, "data_root must not be stored in settings.json"

    # set_setting round-trip
    set_setting("level", "L2")
    assert load_settings().get("level") == "L2"
    set_setting("level", "L1")  # restore
    print("  ✅ Config read/write is fine (level set via set_setting)")


def test_data_root_env_override():
    """Test that get_data_root() honors the CFA_PREP_HOME env var"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["CFA_PREP_HOME"] = tmp
        try:
            root = get_data_root()
            assert root == Path(tmp), f"Expected {tmp}, got {root}"
            assert root.exists(), "data root directory was not created"
            print(f"  ✅ Data root honors CFA_PREP_HOME: {root}")
        finally:
            _ = os.environ.pop("CFA_PREP_HOME", None)


def test_config_home_persists():
    """Test that the persisted data root (set_home_env) is written and resolved via home.env.
    home.env always lives in the fixed ~/.cfa-prep/config directory, independent of the
    currently-resolved data root."""
    import tempfile

    home_env_file = Path.home() / ".cfa-prep" / "config" / "home.env"
    previous = home_env_file.read_text(encoding="utf-8") if home_env_file.exists() else None
    _ = os.environ.pop("CFA_PREP_HOME", None)
    try:
        with tempfile.TemporaryDirectory() as base:
            home_dir = Path(base) / "mydata"
            _ = home_dir.mkdir()
            _ = set_home_env(home_dir)
            assert home_env_file.exists(), "home.env should be written under ~/.cfa-prep/config"

            # Without an env var, load_home_env should pick up home.env
            load_home_env()
            assert os.environ.get("CFA_PREP_HOME") == str(home_dir), (
                f"Expected {home_dir}, got {os.environ.get('CFA_PREP_HOME')}"
            )
            assert get_data_root() == home_dir, "data root should resolve to home.env value"

            # Env var must take precedence over home.env
            other = Path(base) / "other"
            _ = other.mkdir()
            os.environ["CFA_PREP_HOME"] = str(other)
            load_home_env()
            assert get_data_root() == other, "CFA_PREP_HOME env must take precedence over home.env"
            print(f"  ✅ config home <path> persists via home.env: {home_dir}")
    finally:
        _ = os.environ.pop("CFA_PREP_HOME", None)
        if previous is not None:
            _ = write_file_text(home_env_file, previous)
        elif home_env_file.exists():
            home_env_file.unlink()


def test_config_home_command():
    """Test that the `config home <path>` command sets the data root"""
    import io
    import tempfile
    from contextlib import redirect_stdout
    from types import SimpleNamespace

    from cfa_prep.main import cmd_config

    home_env_file = Path.home() / ".cfa-prep" / "config" / "home.env"
    previous = home_env_file.read_text(encoding="utf-8") if home_env_file.exists() else None
    try:
        with tempfile.TemporaryDirectory() as base:
            target = Path(base) / "mydata"
            _ = target.mkdir()
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                cmd_config(SimpleNamespace(
                    config_key="home",
                    config_value=str(target),
                ))  # pyright: ignore[reportArgumentType]
            output = buffer.getvalue()
            assert "Data root (home) set to" in output, output
            assert home_env_file.exists(), "home.env should be written"
            content = home_env_file.read_text(encoding="utf-8")
            assert str(target) in content, content
        print("  ✅ config home <path> sets the data root")
    finally:
        if previous is not None:
            _ = write_file_text(home_env_file, previous)
        elif home_env_file.exists():
            home_env_file.unlink()
