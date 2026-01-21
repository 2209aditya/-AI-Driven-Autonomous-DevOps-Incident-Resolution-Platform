# Contributing to AI-Driven DevOps Platform

We love your input! We want to make contributing to this project as easy and transparent as possible.

## Development Process

1. Fork the repo and create your branch from `main`
2. If you've added code, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code lints
6. Issue that pull request!

## Pull Request Process

1. Update the README.md with details of changes if applicable
2. Update the docs/ with any new documentation
3. The PR will be merged once you have the sign-off of maintainers

## Code Style

- Follow PEP 8 for Python code
- Use Black for code formatting
- Use type hints where possible
- Write descriptive commit messages

## Testing

```bash
# Run unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/ --cov=ai-engine --cov-report=html

# Run integration tests
pytest tests/integration/ -v
```

## Reporting Bugs

Report bugs by opening a new issue with:
- Quick summary and/or background
- Steps to reproduce
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
