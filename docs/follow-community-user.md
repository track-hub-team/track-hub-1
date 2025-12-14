
# User Following (Follow / Unfollow Users)


## General Description

TrackHub allows users to **follow other users (dataset authors)** to stay informed about their activity within the platform.

When a user follows another, the system records this relationship and enables:
- Displaying the follow status in the dataset view
- Listing followed users in the profile
- Unfollowing users from different views (dataset and profile)

This feature encourages the discovery of relevant authors and makes it easier to keep track of their contributions without manual searches.

---


## Location

- **Data models:**
  - `models.py` → `Follower`

- **Data access repository:**
  - `repositories.py` → `FollowerRepository`

- **Main service:**
  - `services.py` → `CommunityService`

- **HTTP routes:**
  - `routes.py` → Routes `/community/user/<id>/follow` and `/community/user/<id>/unfollow`

- **View integration:**
  - `dataset/view_dataset.html`
  - `profile/summary.html`

---


## Architecture

### Follower Model

Represents the following relationship between users (User → User):

```python
def __repr__(self):
    return f"Follower<follower_id={self.follower_id}, followed_id={self.followed_id}>"

```

Each record indicates that a user (`follower_id`) follows another (`followed_id`).

Restrictions:
- A user can only follow another user once
- Self-following is not allowed



### FollowerRepository

Repository responsible for database access for user following.

Main functions:

- `follow(follower_id, followed_id)`
- `unfollow(follower_id, followed_id)`
- `is_following(follower_id, followed_id)`
- `get_followed_users(user_id)`


This repository encapsulates all persistence and query logic related to following.

---


### CommunityService

The community service also centralizes the user following logic, as it was designed together with community following.

Main functions used:

- `follow_user(follower_id, followed_id)`
- `unfollow_user(follower_id, followed_id)`
- `is_following_user(follower_id, followed_id)`
- `get_followed_users(user_id)`


This service validates business rules such as:
- Preventing a user from following themselves
- Avoiding duplicates
- Handling consistency errors

---


## Main Functionality

### Follow User

Allows an authenticated user to start following another user.

Route used:

`def follow_user(followed_id):`


Flow:
1. The user clicks the “Follow” button in the dataset view
2. A POST request is sent to the corresponding route
3. `CommunityService.follow_user` validates and creates the relationship
4. The new follow status is returned
5. The interface is dynamically updated via JavaScript

---


### Unfollow User

Allows removing an existing follow relationship.

Route used:

`def unfollow_user(followed_id):`


Flow:
1. The user clicks the “Unfollow” button
2. The relationship is removed from the database
3. The updated status is returned
4. The interface immediately reflects the change

---


### Follow Status Check

To correctly display the button status in the dataset view, the following is used:

`def is_following_user(follower_id, followed_id):`


This function is evaluated when loading the view to decide whether to show “Follow” or “Unfollow”.

---


## Integration in Dataset

In the dataset view:
- A follow button is shown next to the author
- The button changes dynamically according to the current status
- The action is performed without reloading the page (AJAX)

This allows following authors directly from their publications.

---


## Integration in Profile

In the user's profile:
- A list of followed users is shown
- Each item includes basic user information
- Unfollowing is allowed directly from the list

The list is generated dynamically from:

`def get_followed_users(user_id):`

---


## Error Handling

- Self-following is not allowed
- Duplicate relationships are not created
- If a database error occurs, a controlled message is returned
- AJAX actions always return a success or error status

---


## Flow Summary

```text
User clicks “Follow” on dataset
↓
Route /community/user/<id>/follow
↓
CommunityService.follow_user
↓
FollowerRepository.follow
↓
The follow relationship is created
↓
The interface is dynamically updated
```


## Limitations

- Currently, no email notifications are sent to the followed user
- Following is unidirectional (does not imply reciprocity)
- There is not yet a public view of the followed user's profile

---


This feature allows users to build a network of interesting authors, making it easier to follow new publications and improving the discovery experience within TrackHub.
