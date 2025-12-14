<div style="text-align: center;">
  <img src="app/static/img/logos/logo-light.svg" alt="Logo">
</div>

# Track Hub

A web platform for managing and sharing GPS tracks (GPX files), built on top of Trackhub. Upload, visualize, and collaborate on GPS route collections following Open Science principles.

## Features

- **GPX Track Management**: Upload and organize GPS tracks in GPX format
- **Interactive Visualization**: View routes on an interactive map with statistics (distance, elevation, duration)
- **Version Control**: Track changes to your datasets over time
- **[Community Features](docs/communities.md)**: Organize datasets into curated communities

## Getting Started

To set up your development environment, follow the [Developer Setup Guide](docs/setup-guide.md).

## For Developers and Team Members

- [Project Management & Workflow](docs/project-management.md) - Jira workflow, task and issues management
- [Branching and Commit Strategy](docs/branching-strategy.md) - Git workflow, commit conventions, and EGC Flow
- [Continuous Integration](docs/ci.md) - Local pre-commit hooks and remote GitHub Actions workflows
- [Track Hub 2 Integration](docs/track-hub-2-integration.md) - Collaboration and feature integration with Track Hub 2 team

### Core Features Documentation

- [Fakenodo Service](docs/fakenodo.md) - Mock Zenodo service for development and testing
- [Zenodo Integration](docs/zenodo.md) - Integration with Zenodo for DOI publishing and deployment on Render
- [Comment Moderation System](docs/comment-moderation.md) - Comment management and moderation features
- [ZIP Upload Feature](docs/zip-upload.md) - Bulk file upload functionality via ZIP archives
- [Email Notification](docs/email-notification.md) - Usage of SendGrid for sending email notifications

### Deployment
- [Deployment on Render](docs/deployment-render.md) - Staging and production environments on Render

## Testing

### Running Tests

```bash
# Run all tests
rosemary test

# Run tests for a specific module
rosemary test dataset
rosemary test auth
```

### Selenium Tests

Selenium tests run in **headless mode** by default (compatible with servers and CI/CD).

```bash
# Run all Selenium tests (headless)
rosemary selenium

# Run Selenium tests for a specific module
rosemary selenium dataset
rosemary selenium auth
rosemary selenium community
```

**To see the browser during tests** (useful for debugging):

```bash
SELENIUM_HEADLESS=false rosemary selenium
```

**Requirements for Selenium tests:**
- Firefox installed (`sudo apt-get install firefox`)
- Application running (`flask run` in another terminal)
- Database initialized with seeders (`rosemary db:reset`)
