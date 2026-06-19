# Python Quality Pack

`python-quality` 添加本地质量检查配置。

包含：

- `ruff.toml`
- `pyrightconfig.json`
- `.pre-commit-config.yaml`
- `.gitignore`

命令：

```bash
init-ai add python-quality --dry-run
init-ai add python-quality --apply
```

如果目标项目有 `pyproject.toml`，脚本会执行：

```bash
uv add --dev ruff pyright pre-commit
uv run pre-commit install
```

如果目标项目只有 `requirements.txt` / `setup.py`，脚本会跳过 dev dependency 安装，避免改写旧项目依赖结构。
