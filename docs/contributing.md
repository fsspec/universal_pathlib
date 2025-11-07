# Contributing to Universal Pathlib :heart:

Thank you for your interest in contributing to Universal Pathlib! We're excited to have you here. :tada:

This project thrives on community contributions, and we welcome all forms of participation - whether you're reporting bugs, suggesting features, improving documentation, or contributing code.

---

## Why Contribute? :sparkles:

Universal Pathlib is an open-source project that helps developers work seamlessly with different filesystems. By contributing, you:

- :handshake: **Help the community** - Your contributions make it easier for others to work with cloud storage and remote filesystems
- :books: **Learn and grow** - Get hands-on experience with filesystems, Python internals, and testing
- :star2: **Build your profile** - Showcase your work in an active, project
- :people_holding_hands: **Join a welcoming community** - Work with friendly maintainers and contributors

!!! tip "First Time Contributing?"
    Don't worry! We're here to help. Everyone was a first-time contributor once, and we're happy to guide you through the process.

---

## Ways to Contribute :gift:

There are many ways to contribute to Universal Pathlib:

<div class="grid cards" markdown>

-   :bug: **Report Bugs**

    ---

    Found something broken? Let us know! Clear bug reports help us fix issues quickly.

    [:octicons-arrow-right-24: Report a bug](https://github.com/fsspec/universal_pathlib/issues/new)

-   :bulb: **Suggest Features**

    ---

    Have an idea for improvement? We'd love to hear it! Feature requests help shape the project's future.

    [:octicons-arrow-right-24: Request a feature](https://github.com/fsspec/universal_pathlib/issues/new)

-   :memo: **Improve Documentation**

    ---

    Spot a typo? Know a better way to explain something? Documentation improvements are always welcome!

    [:octicons-arrow-right-24: Edit the docs](https://github.com/fsspec/universal_pathlib)

-   :wrench: **Contribute Code**

    ---

    Ready to get your hands dirty? We welcome bug fixes, new features, and performance improvements.

    [:octicons-arrow-right-24: Development guide](#setting-up-your-development-environment)

</div>

---

## Reporting Bugs :bug:

Found a bug? We want to know about it! Here's how to report it effectively:

### Before Reporting

1. **Search existing issues** - Someone might have already reported it
2. **Try the latest version** - The bug might already be fixed
3. **Check the documentation** - Make sure it's actually a bug and not expected behavior

### Creating a Bug Report

When filing a bug report, please include:

- **Operating system and Python version** - Which OS and Python version are you using?
- **Universal Pathlib version** - Which version of the project are you running?
- **Filesystem type** - S3, GCS, local, etc.?
- **What you did** - Clear steps to reproduce the issue
- **What you expected** - What should have happened?
- **What actually happened** - What did you see instead?
- **Code example** - A minimal reproducible example is extremely helpful!

!!! example "Good Bug Report Example"
    ````markdown
    **Environment:**
    - OS: macOS 14.0
    - Python: 3.11.5
    - universal_pathlib: 0.2.2
    - Filesystem: S3 (s3fs 2023.10.0)

    **Issue:**
    `UPath.glob()` doesn't match files with spaces in their names on S3.

    **Reproduction:**
    ```python
    from upath import UPath

    path = UPath("s3://my-bucket/")
    # This file exists: "my file.txt"
    list(path.glob("my*.txt"))  # Returns empty list
    ```

    **Expected:** Should find "my file.txt"
    **Actual:** Returns empty list
    ````

[:octicons-arrow-right-24: Report a bug on GitHub](https://github.com/fsspec/universal_pathlib/issues/new)

---

## Requesting Features :bulb:

Have an idea to make Universal Pathlib better? We'd love to hear it!

### Before Requesting

1. **Check existing issues** - Someone might have already suggested it
2. **Think about scope** - Does it fit with the project's goals?
3. **Consider alternatives** - Could it be implemented with existing features?

### Creating a Feature Request

When requesting a feature, please explain:

- **The problem** - What are you trying to solve?
- **Your proposed solution** - How would you like it to work?
- **Alternatives considered** - What other approaches did you think about?
- **Use case** - When would this feature be useful?

!!! example "Good Feature Request Example"
    ````markdown
    **Problem:**
    When working with large directories, I need to filter paths by size
    before loading them into memory.

    **Proposed Solution:**
    Add a `glob_with_info()` method that yields tuples of (path, stat_info).

    **Use Case:**
    Processing large S3 buckets where I only want files over 100MB:
    ```python
    for path, info in bucket.glob_with_info("**/*.parquet"):
        if info.st_size > 100_000_000:
            process(path)
    ```

    **Alternatives:**
    Currently need to call `stat()` on every path, which is slow.
    ````

[:octicons-arrow-right-24: Request a feature on GitHub](https://github.com/fsspec/universal_pathlib/issues/new)

---

## Setting Up Your Development Environment :computer:

Ready to contribute code? Here's how to set up your development environment.

### Prerequisites

You'll need:

- **Python 3.9 or higher**
- **Git** - For version control
- **nox** - For running tests and other tasks

### Installation Steps

1. **Fork and clone the repository**

   ```bash
   # Fork on GitHub first, then:
   git clone https://github.com/YOUR-USERNAME/universal_pathlib.git
   cd universal_pathlib
   ```

2. **Install nox**

   ```bash
   uv tool install nox
   ```

3. **Verify your setup**

   ```bash
   # List available nox sessions
   nox --list-sessions
   ```

That's it! You're ready to start developing.

!!! tip "Using uv?"
    If you prefer `uv`, you can use it as well:
    ```bash
    uv pip install nox
    ```

---

## Running Tests :test_tube:

Universal Pathlib has a comprehensive test suite to ensure quality and compatibility.

### Run All Tests

```bash
nox
```

This runs the full test suite across multiple Python versions. It may take a while!

### Run Tests for Your Python Version

```bash
nox --session=tests
```

This runs tests using your current Python version only.

### Run Specific Test Files

```bash
nox --session=tests -- tests/test_core.py
```

### Run Tests with Coverage

```bash
nox --session=tests -- --cov=upath --cov-report=html
```

Then open `htmlcov/index.html` to view the coverage report.

### List All Available Sessions

```bash
nox --list-sessions
```

!!! info "Test Requirements"
    Some tests require additional dependencies (like `s3fs` for S3 tests). Install extras as needed:
    ```bash
    pip install -e ".[dev,s3,gcs,azure]"
    ```

---

## Code Quality :sparkles:

We use automated tools to maintain code quality and consistency.

### Running Linters

```bash
nox --session=lint
```

This runs:
- **ruff** - Fast Python linter
- **mypy** - Type checking
- **Code formatting checks**

### Type Checking

```bash
nox --session=type_checking
nox --session=typesafety
```

!!! tip "Pre-commit Hooks"
    Consider setting up pre-commit hooks to automatically check your code:
    ```bash
    pip install pre-commit
    pre-commit install
    ```

---

## Making Changes :wrench:

Here's the workflow for contributing code:

### 1. Create a Branch

```bash
git checkout -b feature/my-awesome-feature
# or
git checkout -b fix/bug-description
```

### 2. Make Your Changes

- Write clear, readable code
- Follow existing code style
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run tests
nox --session=tests

# Run linters
nox --session=lint
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "Add feature: brief description of what you did"
```

!!! tip "Good Commit Messages"
    - Start with a verb: "Add", "Fix", "Update", "Remove"
    - Be concise but descriptive
    - Reference issues: "Fix #123: Description"

### 5. Push and Create a Pull Request

```bash
git push origin feature/my-awesome-feature
```

Then open a pull request on GitHub!

---

## Pull Request Guidelines :rocket:

Your pull request should:

- ✅ **Pass all tests** - The test suite must pass without errors
- ✅ **Maintain coverage** - Add tests for new functionality
- ✅ **Update documentation** - Document any API changes
- ✅ **Follow code style** - Pass linting checks
- ✅ **Have a clear description** - Explain what and why

### Pull Request Template

When creating a PR, please include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement

## Testing
How was this tested?

## Checklist
- [ ] Tests pass locally
- [ ] Linting passes
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)
```

!!! success "Don't Worry About Perfection"
    It's okay to submit a work-in-progress PR! We can iterate and improve it together. Just mark it as a draft if it's not ready for review.

---

## Development Tips :bulb:

### Debugging Tests

```bash
# Run specific test with verbose output
nox --session=tests -- tests/test_core.py::test_name -v

# Drop into debugger on failure
nox --session=tests -- --pdb
```
---

## Getting Help :question:

Need help? We're here for you!

- **GitHub Issues** - Ask questions, report bugs, suggest features
- **Documentation** - Check the docs for guides and examples
- **Code of Conduct** - Read our [Code of Conduct](https://github.com/fsspec/universal_pathlib/blob/main/CODE_OF_CONDUCT.rst)

!!! info "Response Time"
    We're a volunteer-driven project. We'll try to respond quickly, but please be patient if it takes a few days.

---

## Recognition :star:

We appreciate all contributions! Contributors are:

- Listed in the project's contributor graph
- Mentioned in release notes for significant contributions
- Part of a welcoming, collaborative community

Thank you for making Universal Pathlib better! :heart:

---

## Quick Links :link:

<div class="grid cards" markdown>

-   :octicons-mark-github-16: **GitHub Repository**

    ---

    View the source code and contribute

    [:octicons-arrow-right-24: fsspec/universal_pathlib](https://github.com/fsspec/universal_pathlib)

-   :octicons-issue-opened-16: **Issue Tracker**

    ---

    Report bugs and request features

    [:octicons-arrow-right-24: View issues](https://github.com/fsspec/universal_pathlib/issues)

-   :octicons-git-pull-request-16: **Pull Requests**

    ---

    Submit your contributions

    [:octicons-arrow-right-24: Open a PR](https://github.com/fsspec/universal_pathlib/pulls)

-   :octicons-code-of-conduct-16: **Code of Conduct**

    ---

    Read our community guidelines

    [:octicons-arrow-right-24: View code of conduct](https://github.com/fsspec/universal_pathlib/blob/main/CODE_OF_CONDUCT.rst)

</div>

---

<div align="center" markdown>

**Ready to contribute?** :rocket:

[Create an Issue](https://github.com/fsspec/universal_pathlib/issues/new){ .md-button .md-button--primary }
[Open a Pull Request](https://github.com/fsspec/universal_pathlib/compare){ .md-button }

</div>
