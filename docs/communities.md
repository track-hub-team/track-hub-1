# Community Features

The Communities module allows users to organize and curate collections of GPS track datasets around specific topics or interests. Communities provide a collaborative space where datasets can be proposed, reviewed, and shared by a group of curators.

## Overview

Communities allow users to:
- Create and moderate thematic collections of GPS route datasets.
- Submit their datasets for inclusion in relevant communities.
- Select and moderate submitted datasets through a review process.

## Core Functionality

### 1. Community Creation

Any authenticated user can create a community:
- **Name and description**: Define the community's purpose and scope
- **Custom logo**: Upload a logo image (JPG, PNG, GIF, WEBP, max 2MB)
- **Automatic curator assignment**: The creator is automatically assigned as the first curator

### 2. Dataset Proposal Workflow

Users can propose their datasets for inclusion in communities:

1. **Propose Dataset**: Users submit one of their datasets to a community with an optional message explaining why it fits
2. **Curator Review**: Community curators review pending proposals
3. **Approval/Rejection**: Curators can approve (adding the dataset to the community) or reject the proposal

### 3. Curator Management

Communities are managed by curators who have special permissions:

**Curator Responsibilities**:
- Review and approve/reject dataset proposals
- Add or remove other curators
- Update community settings (description, logo)

**Curator Rules**:
- The community creator is always a curator and cannot be removed
- Only curators can add other curators
- Curators can remove other curators (except the creator)

### 4. Community Discovery

- **Browse all communities**: View all available communities in the platform
- **Search communities**: Filter communities by name or description
- **View community details**: See datasets, curators, and community information

## Key Features Implemented

### Community Management
- Slug-based URLs for clean, shareable community links
- Automatic slug generation with collision handling

### Dataset Proposals
- Eligible dataset filtering (excludes datasets already in the community or with pending requests)
- Request status tracking (pending, approved, rejected)

### Curator Workflow
- Email notifications on approval (requester is notified when their dataset is accepted)

### User Search
- Search users by name or email to add as curators in real-time with autocomplete

## Important Notes

### Logo Handling
- **Fallback behavior**: If a logo file is missing or not uploaded, communities display a generated avatar with the community's initials
- **Supported formats**: JPG, JPEG, PNG, GIF, WEBP
- **Size limit**: 2MB maximum
- **Storage**: Logos are stored in `uploads/communities/` with the community slug as filename (except for seeder communities, with logo in static)

### Dataset Management
- **No deletion from communities**: Once a dataset is approved and added to a community, it cannot be removed through the UI
- **One dataset, multiple communities**: A dataset can belong to multiple communities simultaneously

### Rejection Workflow
- **No email notification**: When a proposal is rejected, no email is sent to the requester
- **Comment storage**: Rejection reasons are stored in the database for audit purposes

### URL Structure
- Communities use slug-based URLs: `/community/<slug>`
- Slugs are generated from community names and are unique
- If a slug collision occurs, a numeric suffix is added (e.g., `my-community-1`) (should not occur due to restrictions on unique names)

## Testing

The community module has comprehensive test coverage across multiple layers:

### Unit Tests (`test_unit.py`)
- `test_create_community_creator_becomes_curator` - Verifies creator is automatically assigned as curator
- `test_get_eligible_datasets_excludes_already_added` - Validates dataset filtering logic (excludes datasets already in community or with pending requests)
- `test_approve_request_adds_dataset_to_community` - Checks approval workflow adds dataset and updates request status
- `test_reject_request_does_not_add_dataset` - Ensures rejection doesn't add dataset and updates status correctly
- `test_cannot_remove_community_creator_as_curator` - Validates creator protection from curator removal
- `test_cannot_create_community_with_duplicate_name` - Verifies duplicate community names are prevented with proper error message

### Integration Tests (`test_integration.py`)
- `test_propose_dataset_full_workflow` - End-to-end test of proposal submission and approval flow
- `test_curator_management_full_workflow` - End-to-end test for adding and removing curators

### Selenium Tests (`test_selenium.py`)
- `test_propose_and_reject_dataset` - UI test for proposing dataset and curator rejection
- `test_add_curator_via_manage_interface` - UI test for curator search and addition through management interface

### Load Tests (`locustfile.py`)
- `list_communities` - Simulates concurrent users browsing community listings
- `view_community_with_datasets` - Simulates concurrent users viewing communities
