# Integration with Track Hub 2

This document describes the integration work between Track Hub 1 and Track Hub 2 teams, coordinated to share common functionality and avoid duplicating efforts.

## Starting point

To carry out the work, an organization has been created in which the repositories of both teams have been created. This is an attempt to facilitate the integration of changes between repositories.

## Team Coordination

- **Track Hub 1 Coordinator**: Antonio Rodríguez
- **Track Hub 2 Coordinator**: Germán Sánchez

## Integrated Features

### 1. GPX Format Adaptation

**Source**: Track Hub 2
**Pull Request**: [#4 - Implement GPX adaptation based on track-hub-2](https://github.com/track-hub-team/track-hub-1/pull/4)

**Description**:
The original UVLHub platform was designed to handle UVL files for feature model management. Track Hub 2 developed the initial adaptation to support GPX (GPS Exchange Format) files instead, which are the standard format for GPS track data.

**What was integrated**:
- GPX file parsing and validation
- Data model adaptation from UVL to GPX format
- File upload and storage mechanisms for GPX files
- Initial dataset versioning system

### 2. Continuous Deployment Workflow

**Source**: Track Hub 2
**Pull Request**: [#3 - Integration of the cd flow from track-hub-2](https://github.com/track-hub-team/track-hub-1/pull/3)

**Description**:
Track Hub 2 developed a comprehensive Continuous Deployment (CD) pipeline for deploying to Render.

**What was integrated**:
- GitHub Actions workflows for automated deployment to Render
- Deployment triggers and automation scripts

## Integration Process

The integration between teams followed these steps:

1. **Feature Identification**: Teams identified common needs and complementary features
2. **Coordination**: Team coordinators aligned on integration strategy (in person on a cherry-pick basis)
3. **Pull Request Submission**: The changes were brought locally from track-hub-2 to the track-hub-1 repository and uploaded to a branch ready for pull requests.
4. **Merge**: Features were merged and validated in Track Hub 1's environment
5. **Adaptation**: Track Hub 1 adapted the code to fit their architecture

## Problems encountered

Given the initial requirement to clean up the commits from the original fork, GitHub did not recognize the joint starting point for both repositories. Therefore, it has not been possible to make pull requests between repositories.

The best solution to facilitate integration has been to use cherry-pick strategies to bring in specific changes one by one, creating a clean branch locally on the track-hub-1 base repository, allowing merging into trunk.
