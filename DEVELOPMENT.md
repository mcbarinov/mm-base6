# Development

## Project Structure

This repository contains both the framework and a development project.

### `/src/`

- **`mm_base6/`** — Framework code (published to PyPI)
- **`app/`** — Development project for testing the framework. Not part of the published library. Structured like a real application that uses mm_base6.

### `/demo/`

Standalone demo application with deployment configuration:

- **`src/`** — Demo application code
- **`ansible/`** — Ansible playbooks for server deployment
- **`docker/`** — Dockerfile and docker-compose for containerized deployment
