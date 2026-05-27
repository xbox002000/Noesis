# Contributing to Noesis

Thank you for your interest in contributing to **Noesis**!

Noesis is an experimental AI-native cognitive runtime focused on epistemic honesty, uncertainty management, and structured reasoning. We welcome contributions that align with these principles.

## Code of Conduct

Please be respectful and constructive. We expect all contributors to maintain a high standard of intellectual honesty — especially when working on features related to epistemic reasoning and uncertainty.

## Getting Started

### Prerequisites
- Python 3.10+
- Git

### Setup Development Environment

```bash
git clone https://github.com/xbox002000/Noesis.git
cd Noesis

# (Optional) Create a virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install development dependencies (if any)
pip install -r requirements-dev.txt  # if the file exists
```

## How to Contribute

### 1. Reporting Issues
- Use the [Issues](https://github.com/xbox002000/Noesis/issues) tab.
- Please include:
  - Clear description of the problem
  - Steps to reproduce
  - Expected vs actual behavior
  - Your environment (Python version, OS)

### 2. Suggesting Features or Improvements
We especially welcome ideas that improve:
- Epistemic honesty mechanisms
- Relationship inference quality in the Semantic Graph
- Usability of the Context Builder (especially Medium mode)
- Evaluation frameworks for cognitive systems

### 3. Pull Request Process
1. Fork the repository
2. Create a new branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes
4. Commit with clear messages:
   ```bash
   git commit -m "feat: add better borderline SCU detection"
   ```
5. Push and open a Pull Request against the `main` branch
6. Wait for review

### Commit Message Convention
We loosely follow Conventional Commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only changes
- `refactor:` Code change that neither fixes a bug nor adds a feature
- `test:` Adding or updating tests

## Development Guidelines

### Philosophy
When contributing, always consider:
- Does this change help the system become more **epistemically honest**?
- Does it make uncertainty and limitations more visible rather than hidden?
- Is the mechanism explainable?

### Code Style
- Follow PEP 8 for Python code
- Add docstrings for public functions and classes
- Keep functions reasonably small and focused

### Working with the Medium Honesty Level
When modifying the Context Builder (especially `_build_epistemic_framing`), please make sure any new information added to the Epistemic Note is:
- Accurate
- Actionable
- Not overly verbose

## Project Structure Overview

```
Noesis/
├── epistemic_kernel/          # Layer 1: Confidence propagation, contentions, failure detection
├── semantic_graph/            # Layer 2: SCU model, bootstrap, relationship inference
├── experiments/
│   ├── token_efficient_context/   # Main Context Builder implementation
│   └── llm_quality_ab_test.py     # Experimental evaluation framework
└── docs/                          # Development plans and experiment reports
```

## Questions?

Feel free to open an issue with the label `question` if you're unsure about anything.

Thank you for helping build more honest and thoughtful AI systems!