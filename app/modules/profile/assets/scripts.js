document.addEventListener("DOMContentLoaded", function () {
    console.log("PROFILE REAL SCRIPT LOADED");

    const communitiesList = document.getElementById("followed-communities-list");

    // Leer JSON insertado por backend
    const jsonEl = document.getElementById("followed-communities-json");
    let followedCommunities = [];

    if (jsonEl) {
        followedCommunities = JSON.parse(jsonEl.textContent);
    }

    // Renderizar lista
    if (followedCommunities.length === 0) {
        communitiesList.innerHTML = `<li class="text-muted">You are not following any communities yet.</li>`;
    } else {
        followedCommunities.forEach(comm => {
            const li = document.createElement("li");
            li.classList.add("mb-3");

            li.innerHTML = `
                <a href="/community/${comm.slug}" class="d-flex align-items-center text-decoration-none text-dark">
                    <img src="${comm.logo}" class="rounded me-3" style="width:50px;height:50px;object-fit:cover;">
                    <div>
                        <strong>${comm.name}</strong><br>
                        <span class="text-muted small">${comm.description.substring(0, 60)}...</span>
                    </div>
                </a>
            `;
            li.style.listStyle = "none";
            li.style.borderBottom = "1px solid #ccc";
            li.style.padding = "12px 4px";
            communitiesList.appendChild(li);
        });
    }
    // -------------------------------
    // 2. USERS FOLLOWED FROM BACKEND
    // -------------------------------
    const usersList = document.getElementById("followed-users-list");
    const usersJsonEl = document.getElementById("followed-users-json");

    let followedUsers = [];
    if (usersJsonEl) {
        followedUsers = JSON.parse(usersJsonEl.textContent || "[]");
    }

    if (followedUsers.length === 0) {
        usersList.innerHTML = `<li class="text-muted">You are not following any users yet.</li>`;
    } else {
        followedUsers.forEach(user => {
            const initials =
                ((user.name || "").charAt(0) + (user.surname || "").charAt(0)).toUpperCase();

            const li = document.createElement("li");
            li.classList.add("mb-3");

            li.innerHTML = `
                <div class="d-flex align-items-center justify-content-between">

                    <div class="d-flex align-items-center">
                        <div class="follow-avatar me-3">${initials}</div>

                        <div>
                            <strong>${user.name} ${user.surname}</strong><br>
                            <span class="text-muted small">${user.email}</span>
                        </div>
                    </div>

                    <button
                        class="btn btn-sm btn-outline-danger unfollow-user-btn"
                        data-user-id="${user.id}">
                        Unfollow
                    </button>
                </div>
            `;
            li.style.listStyle = "none";
            li.style.borderBottom = "1px solid #ccc";
            li.style.padding = "12px 4px";
            usersList.appendChild(li);
        });
    }

    // ---------------------------
    // UNFOLLOW USER FROM PROFILE
    // ---------------------------
    document.addEventListener("click", function (event) {
        if (!event.target.classList.contains("unfollow-user-btn")) return;

        const btn = event.target;
        const userId = btn.dataset.userId;

        fetch(`/community/user/${userId}/unfollow`, {
            method: "POST",
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                // Remove the element from DOM
                btn.closest("li").remove();

                // If no users left, show empty message
                if (usersList.children.length === 0) {
                    usersList.innerHTML = `<li class="text-muted">You are not following any users yet.</li>`;
                }
            } else {
                alert(data.error || "Could not unfollow user.");
            }
        })
        .catch(err => console.error(err));
    });

});
