# US Payroll

US Payroll management app for Frappe and ERPNext.

## Features

- Payroll Processing
- ACH Generation
- PTO Management
- Tax Calculations
- US Payroll Utilities

## Installation

Install the app using Bench CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/AdcompSystems/US-Payroll.git --branch version-16
bench install-app us_payroll
```

## Development

This app uses `pre-commit` for code formatting and linting.

Install pre-commit:

```bash
pip install pre-commit
```

Enable hooks:

```bash
cd apps/us_payroll
pre-commit install
```

Configured tools:

- ruff
- eslint
- prettier
- pyupgrade

## Requirements

- Frappe v16
- ERPNext v16
- Python 3.10+

## License

MIT