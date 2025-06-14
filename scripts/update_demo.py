import shutil
import sys
import tomllib
from pathlib import Path
from typing import Any

import tomlkit
from tomlkit.items import Array


def update_demo() -> None:
    """Update demo project with current source code and dependencies."""
    root_dir = Path(__file__).parent.parent
    demo_dir = root_dir / "demo"

    # 1. Copy src/app to demo/src/app
    demo_app_dir = demo_dir / "src" / "app"
    if demo_app_dir.exists():
        shutil.rmtree(demo_app_dir)

    src_app_dir = root_dir / "src" / "app"
    shutil.copytree(src_app_dir, demo_app_dir)

    # 2. Read root pyproject.toml
    root_pyproject_path = root_dir / "pyproject.toml"
    with root_pyproject_path.open("rb") as f:
        root_config = tomllib.load(f)

    current_version = root_config["project"]["version"]
    root_dev_deps = root_config["tool"]["uv"]["dev-dependencies"]

    # 3. Read and update demo pyproject.toml
    demo_pyproject_path = demo_dir / "pyproject.toml"
    with demo_pyproject_path.open("r", encoding="utf-8") as f:
        demo_config = tomlkit.load(f)

    # 4. Update mm-base6 version in demo dependencies
    project_section = demo_config["project"]
    if isinstance(project_section, dict):
        demo_deps = project_section["dependencies"]
        if isinstance(demo_deps, Array):
            for i, dep in enumerate(demo_deps):
                if isinstance(dep, str) and dep.startswith("mm-base6=="):
                    demo_deps[i] = f"mm-base6=={current_version}"
                    break

    # 5. Update dev-dependencies in demo (only existing ones)
    tool_section = demo_config["tool"]
    if isinstance(tool_section, dict):
        uv_section = tool_section["uv"]
        if isinstance(uv_section, dict):
            demo_dev_deps = uv_section["dev-dependencies"]
            if isinstance(demo_dev_deps, Array):
                # Create lookup dict for root dev-dependencies
                root_dev_deps_dict: dict[str, Any] = {}
                for dep in root_dev_deps:
                    if isinstance(dep, str) and "~=" in dep:
                        name = dep.split("~=")[0]
                        root_dev_deps_dict[name] = dep

                # Update existing demo dev-dependencies
                for i, dep in enumerate(demo_dev_deps):
                    if isinstance(dep, str) and "~=" in dep:
                        name = dep.split("~=")[0]
                        if name in root_dev_deps_dict:
                            demo_dev_deps[i] = root_dev_deps_dict[name]

    # 6. Write updated demo pyproject.toml
    with demo_pyproject_path.open("w", encoding="utf-8") as f:
        tomlkit.dump(demo_config, f)

    sys.stdout.write(f"Demo updated with mm-base6 version {current_version}\n")


if __name__ == "__main__":
    update_demo()
